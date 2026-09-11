#!/usr/bin/env python3
"""Comprobacion tecnica de un sitio publicado: robots, sitemap, redirecciones,
canonicals y jerarquia de encabezados, URL por URL.

El auditor de markdown no ve la plantilla. Un H1 en `display: none`, un
canonical que apunta a otra URL, una redireccion que llego tarde o un sitemap
con URLs que devuelven 308 solo se ven pidiendo la pagina. Esto la pide.

Solo biblioteca estandar. Sin API de pago. Respeta un retardo entre peticiones
para no parecer un ataque.

    python site_check.py https://www.example.com
    python site_check.py https://www.example.com --limit 40 --md sitio.md
    python site_check.py https://www.example.com --only /blog/ --json sitio.json

Que comprueba, y por que (todo sale del curso de SEO y de la documentacion de
Google):

  robots.txt      existe, no bloquea todo, declara el sitemap
  sitemap.xml     existe, cada URL responde 200 sin redirigir, lastmod valido,
                  no lista URLs con noindex ni con canonical a otra URL
  host            la variante sin www (o con) y http redirigen con 301/308 a
                  la canonica, en un solo salto
  por URL         titulo de 30 a 70, descripcion de 120 a 160, un solo H1,
                  H2 presentes, canonical autorreferente, sin noindex, sin
                  H1 vacio, sin encabezados que saltan de H1 a H3

Codigo de salida 1 si hay errores, para engancharlo a un despliegue.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urlunparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = "pengu-seo-site-check/1.1 (+https://github.com/christian259200/seo-preflight)"
TITLE_MIN, TITLE_MAX = 30, 70
DESC_MIN, DESC_MAX = 120, 160
# Rastreadores que alimentan respuestas de IA. Bloquearlos quita las citas,
# no protege el contenido.
AI_BOTS = {"gptbot", "oai-searchbot", "claudebot", "claude-web", "anthropic-ai",
           "perplexitybot", "google-extended", "bingbot", "applebot-extended"}


# --------------------------------------------------------------------------
# red
# --------------------------------------------------------------------------

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url: str, follow: bool = True, timeout: int = 20) -> dict:
    """Devuelve status, url final, cadena de redirecciones y cuerpo (texto)."""
    chain = []
    current = url
    for _ in range(6):
        req = urllib.request.Request(current, headers={"User-Agent": UA,
                                                       "Accept": "text/html,*/*"})
        opener = urllib.request.build_opener(NoRedirect)
        try:
            with opener.open(req, timeout=timeout) as resp:
                body = resp.read(2_000_000).decode("utf-8", "replace")
                return {"status": resp.status, "url": current, "chain": chain,
                        "body": body, "headers": dict(resp.headers)}
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308) and follow:
                target = exc.headers.get("Location") or ""
                if target.startswith("/"):
                    p = urlparse(current)
                    target = f"{p.scheme}://{p.netloc}{target}"
                chain.append((exc.code, current, target))
                current = target
                continue
            return {"status": exc.code, "url": current, "chain": chain, "body": "",
                    "headers": dict(exc.headers)}
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return {"status": 0, "url": current, "chain": chain, "body": "",
                    "headers": {}, "error": str(exc)}
    return {"status": 0, "url": current, "chain": chain, "body": "", "headers": {},
            "error": "demasiadas redirecciones"}


# --------------------------------------------------------------------------
# html
# --------------------------------------------------------------------------

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self.canonical = ""
        self.robots = ""
        self.headings: list[tuple[int, str]] = []
        self._in_title = False
        self._heading: int | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title" and not self.title:
            self._in_title = True
        elif tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower()
            if name == "description":
                self.description = a.get("content") or ""
            elif name == "robots":
                self.robots = (a.get("content") or "").lower()
        elif tag == "link" and (a.get("rel") or "").lower() == "canonical":
            self.canonical = a.get("href") or ""
        elif tag in ("h1", "h2", "h3", "h4"):
            self._heading = int(tag[1])
            self._buf = []

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in ("h1", "h2", "h3", "h4") and self._heading:
            self.headings.append((self._heading, " ".join("".join(self._buf).split())))
            self._heading = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._heading:
            self._buf.append(data)


def parse(body: str) -> Page:
    page = Page()
    try:
        page.feed(body)
    except Exception:
        pass
    page.title = " ".join(page.title.split())
    return page


# --------------------------------------------------------------------------
# comprobaciones
# --------------------------------------------------------------------------

def normalize(url: str) -> str:
    p = urlparse(url)
    path = p.path.rstrip("/") or "/"
    return urlunparse((p.scheme, p.netloc.lower(), path, "", "", ""))


def check_robots(origin: str) -> tuple[list, list, list]:
    errors, warns, sitemaps = [], [], []
    r = fetch(f"{origin}/robots.txt")
    if r["status"] != 200:
        errors.append(("ROBOTS-MISSING", f"robots.txt responde {r['status']}."))
        return errors, warns, sitemaps
    body = r["body"]
    for line in body.splitlines():
        if line.lower().startswith("sitemap:"):
            sitemaps.append(line.split(":", 1)[1].strip())
    if not sitemaps:
        warns.append(("ROBOTS-NO-SITEMAP", "robots.txt no declara Sitemap:. Google lo encuentra igual, pero declararlo cuesta una linea."))
    # Solo el bloque de "User-agent: *": las reglas de otro agente (CCBot,
    # por ejemplo) no cuentan. Un regex que cruzaba bloques daba un falso
    # positivo en cualquier sitio que bloquee un scraper concreto.
    agent, blocks_all, ai_blocked = None, False, []
    for line in body.splitlines():
        low = line.strip().lower()
        if low.startswith("user-agent:"):
            agent = low.split(":", 1)[1].strip()
        elif low.startswith("disallow:") and low.split(":", 1)[1].strip() == "/":
            if agent == "*":
                blocks_all = True
            elif agent in AI_BOTS:
                ai_blocked.append(agent)
    if blocks_all:
        errors.append(("ROBOTS-BLOCKS-ALL", "robots.txt tiene 'Disallow: /' para todos los agentes."))
    if ai_blocked:
        warns.append(("ROBOTS-BLOCKS-AI", f"robots.txt bloquea a {', '.join(ai_blocked)}. Sin ellos no hay citas en respuestas de IA; el contenido es publico igual."))
    if "—" in body or "–" in body:
        warns.append(("ROBOTS-DASH", "Guion largo en robots.txt. No rompe nada, pero la regla del sitio es sin guiones largos en ningun texto."))
    llms = fetch(f"{origin}/llms.txt")
    if llms["status"] != 200 or "<html" in llms["body"][:300].lower():
        warns.append(("LLMS-TXT-MISSING", "Sin /llms.txt. Es un archivo de texto con las paginas clave y una linea por cada una; varios asistentes de IA lo leen para saber que citar."))
    return errors, warns, sitemaps


def read_sitemap(url: str, depth: int = 0) -> list[dict]:
    r = fetch(url)
    if r["status"] != 200:
        return [{"loc": url, "error": f"sitemap responde {r['status']}"}]
    body = r["body"]
    if "<sitemapindex" in body and depth < 2:
        out = []
        for child in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body):
            out += read_sitemap(child, depth + 1)
        return out
    entries = []
    for block in re.findall(r"<url>(.*?)</url>", body, re.S):
        loc = re.search(r"<loc>\s*([^<\s]+)\s*</loc>", block)
        lastmod = re.search(r"<lastmod>\s*([^<\s]+)\s*</lastmod>", block)
        if loc:
            entries.append({"loc": loc.group(1), "lastmod": lastmod.group(1) if lastmod else None})
    return entries


def check_host(origin: str) -> list:
    """Las variantes del host redirigen a la canonica en un salto."""
    findings = []
    p = urlparse(origin)
    host = p.netloc
    alt = host[4:] if host.startswith("www.") else "www." + host
    for variant in (f"{p.scheme}://{alt}/", f"http://{host}/", f"http://{alt}/"):
        r = fetch(variant)
        final = normalize(r["url"])
        if r["status"] == 0:
            findings.append(("warn", "HOST-UNREACHABLE", f"{variant} no responde ({r.get('error', '')[:60]})."))
        elif final != normalize(origin + "/"):
            findings.append(("error", "HOST-NO-REDIRECT", f"{variant} termina en {r['url']} con {r['status']}, no en {origin}/."))
        elif len(r["chain"]) > 1:
            findings.append(("warn", "HOST-CHAIN", f"{variant} llega a la canonica en {len(r['chain'])} saltos. Deberia ser uno."))
        elif r["chain"] and r["chain"][0][0] not in (301, 308):
            findings.append(("warn", "HOST-TEMP-REDIRECT", f"{variant} redirige con {r['chain'][0][0]}. Para un cambio de host es 301 o 308."))
    return findings


def check_url(entry: dict, origin: str) -> dict:
    url = entry["loc"]
    result = {"url": url, "errors": [], "warns": [], "notes": []}
    e, w, n = result["errors"], result["warns"], result["notes"]

    lastmod = entry.get("lastmod")
    if lastmod:
        try:
            datetime.fromisoformat(lastmod.replace("Z", "+00:00"))
        except ValueError:
            w.append(("SITEMAP-LASTMOD", f"lastmod '{lastmod}' no es una fecha ISO."))
    else:
        n.append(("SITEMAP-NO-LASTMOD", "Sin lastmod en el sitemap."))

    r = fetch(url)
    result["status"] = r["status"]
    if r["status"] != 200:
        e.append(("URL-STATUS", f"Responde {r['status']}{' tras ' + str(len(r['chain'])) + ' redirecciones' if r['chain'] else ''}. Una URL del sitemap tiene que responder 200 directa."))
        return result
    if r["chain"]:
        e.append(("SITEMAP-REDIRECT", f"El sitemap lista {url} pero redirige a {r['url']}. Lista la URL final."))

    page = parse(r["body"])
    if "noindex" in page.robots:
        e.append(("NOINDEX-IN-SITEMAP", "La pagina lleva noindex y esta en el sitemap. Una de las dos sobra."))
    if page.canonical:
        if normalize(page.canonical) != normalize(r["url"]):
            e.append(("CANONICAL-OTHER", f"El canonical apunta a {page.canonical}. Si esta pagina es la buena, el canonical tiene que ser ella misma."))
    else:
        w.append(("CANONICAL-MISSING", "Sin etiqueta canonical."))

    if not page.title:
        e.append(("TITLE-MISSING", "Sin <title>."))
    elif len(page.title) > TITLE_MAX:
        w.append(("TITLE-LONG", f"Titulo de {len(page.title)} caracteres, se corta a partir de {TITLE_MAX}."))
    elif len(page.title) < TITLE_MIN:
        w.append(("TITLE-SHORT", f"Titulo de {len(page.title)} caracteres."))
    if re.search(r"(\|\s*[^|]+)\1\s*$", page.title):
        e.append(("TITLE-DOUBLE-BRAND", f"La marca aparece dos veces en el titulo: '{page.title}'. La plantilla ya la anade."))

    if not page.description:
        w.append(("DESC-MISSING", "Sin meta description."))
    elif not (DESC_MIN <= len(page.description) <= DESC_MAX):
        n.append(("DESC-LEN", f"Descripcion de {len(page.description)} caracteres, fuera de {DESC_MIN} a {DESC_MAX}."))

    h1s = [t for lvl, t in page.headings if lvl == 1]
    h2s = [t for lvl, t in page.headings if lvl == 2]
    if len(h1s) == 0:
        e.append(("H1-MISSING", "Sin H1. Es el sitio mas fuerte para la keyword y esta vacio."))
    elif len(h1s) > 1:
        e.append(("H1-MULTIPLE", f"{len(h1s)} H1: {h1s[:3]}. Uno por pagina."))
    elif not h1s[0].strip():
        e.append(("H1-EMPTY", "El H1 existe pero no tiene texto (icono o imagen)."))
    if not h2s and len(r["body"]) > 20000:
        w.append(("H2-MISSING", "Pagina larga sin ningun H2."))
    levels = [lvl for lvl, _ in page.headings]
    for prev, cur in zip(levels, levels[1:]):
        if cur > prev + 1:
            n.append(("HEADING-SKIP", f"Salto de H{prev} a H{cur}: '{page.headings[levels.index(cur)][1][:50]}'."))
            break
    if "—" in r["body"] and re.search(r"<(h1|h2|title)[^>]*>[^<]*—", r["body"]):
        w.append(("DASH-IN-HEADING", "Guion largo en un titulo o encabezado."))
    return result


# --------------------------------------------------------------------------

def to_markdown(report: dict) -> str:
    out = [f"# Comprobacion tecnica: {report['origin']}", "",
           f"{report['urls_checked']} URLs del sitemap comprobadas de {report['urls_total']}. "
           f"{report['totals']['errors']} errores, {report['totals']['warns']} avisos.", ""]
    out += ["## Sitio", ""]
    for level, code, msg in report["site"]:
        out.append(f"- **{level}** `{code}`: {msg}")
    if not report["site"]:
        out.append("- robots.txt, sitemap y redirecciones de host: todo en orden.")
    out.append("")
    bad = [u for u in report["urls"] if u["errors"] or u["warns"]]
    if bad:
        out += ["## URLs con hallazgos", ""]
        for u in bad:
            out.append(f"### {u['url']}")
            for code, msg in u["errors"]:
                out.append(f"- ERROR `{code}`: {msg}")
            for code, msg in u["warns"]:
                out.append(f"- aviso `{code}`: {msg}")
            out.append("")
    else:
        out += ["## URLs", "", "Todas responden 200, con canonical propio, un H1 y sin noindex.", ""]
    codes: dict[str, int] = {}
    for u in report["urls"]:
        for code, _ in u["errors"] + u["warns"] + u["notes"]:
            codes[code] = codes.get(code, 0) + 1
    if codes:
        out += ["## Recuento por codigo", "", "| Codigo | URLs |", "| --- | ---: |"]
        for code, n in sorted(codes.items(), key=lambda x: -x[1]):
            out.append(f"| {code} | {n} |")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Comprobacion tecnica de un sitio publicado.")
    ap.add_argument("origin", help="https://www.example.com")
    ap.add_argument("--limit", type=int, default=200, help="maximo de URLs a pedir")
    ap.add_argument("--only", help="solo URLs que contengan este texto, por ejemplo /blog/")
    ap.add_argument("--delay", type=float, default=0.4, help="segundos entre peticiones")
    ap.add_argument("--md")
    ap.add_argument("--json")
    args = ap.parse_args()

    origin = args.origin.rstrip("/")
    site: list = []
    r_err, r_warn, sitemaps = check_robots(origin)
    site += [("error", c, m) for c, m in r_err] + [("warn", c, m) for c, m in r_warn]
    site += check_host(origin)

    entries: list[dict] = []
    for sm in sitemaps or [f"{origin}/sitemap.xml"]:
        entries += read_sitemap(sm)
    broken = [x for x in entries if x.get("error")]
    site += [("error", "SITEMAP-MISSING", x["error"]) for x in broken]
    entries = [x for x in entries if not x.get("error")]
    seen = set()
    for x in entries:
        key = normalize(x["loc"])
        if key in seen:
            site.append(("warn", "SITEMAP-DUPLICATE", f"{x['loc']} aparece mas de una vez."))
        seen.add(key)
    if args.only:
        entries = [x for x in entries if args.only in x["loc"]]

    urls = []
    for entry in entries[:args.limit]:
        urls.append(check_url(entry, origin))
        time.sleep(args.delay)

    report = {
        "origin": origin, "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sitemaps": sitemaps, "urls_total": len(entries), "urls_checked": len(urls),
        "site": site, "urls": urls,
        "totals": {"errors": sum(len(u["errors"]) for u in urls) + sum(1 for s in site if s[0] == "error"),
                   "warns": sum(len(u["warns"]) for u in urls) + sum(1 for s in site if s[0] == "warn")},
    }
    if args.md:
        Path(args.md).write_text(to_markdown(report), encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not (args.md or args.json):
        print(to_markdown(report))
    else:
        print(json.dumps(report["totals"] | {"urls": len(urls)}, indent=2))
    sys.exit(1 if report["totals"]["errors"] else 0)


if __name__ == "__main__":
    main()
