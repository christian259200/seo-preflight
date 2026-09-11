#!/usr/bin/env python3
"""Mapa de keywords: cada post, la keyword que ataca y como le va de verdad.

Es la hoja que el curso de SEO manda tener y que casi nadie tiene: keyword,
pagina, posicion y fecha de revision, para volver cada mes a las paginas
importantes en vez de escribir otra nueva.

Cruza tres cosas:

  1. El contenido publicado (frontmatter: slug, title, focus_keyword, fechas).
  2. La exportacion de Search Console (Paginas.csv y Consultas.csv), leida con
     gsc.py, para la posicion e impresiones reales de cada pagina.
  3. Opcionalmente, `dfs.py ranked dominio --out ranked.json`, que si cruza
     consulta con URL y sirve para elegir la keyword con datos y no por
     parecido.

Para los posts sin focus_keyword propone una, con este orden:

  a. la consulta con mas impresiones de ranked.json que apunte a esa URL
  b. la consulta con mas impresiones de Consultas.csv cuyos terminos esten
     todos en el titulo
  c. el titulo SEO sin numero, ano, parentesis ni marca

Con --apply escribe `focus_keyword` en el frontmatter de los que no la tienen.
No toca nada mas, y no toca los que ya la tienen.

    python kw_map.py src/content/blog --gsc exports/ --md mapa.md
    python kw_map.py src/content/blog --gsc exports/ --ranked ranked.json --apply
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gsc  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BRAND_SUFFIX = re.compile(r"\s*[|]\s*[A-Z][\w ]{2,30}$")
NOISE = re.compile(r"\(.*?\)|\b(19|20)\d{2}\b|\b\d+\b|[:|,+?!]|\bcompared\b|\bexplained\b",
                   re.IGNORECASE)
TRAILING = {"in", "for", "to", "of", "the", "a", "an", "and", "with", "on", "vs"}
# Palabras vacias que si pueden abrir una keyword: "how to check website
# traffic" es una keyword real, "to check website traffic" no.
EDGE_OK = {"how", "what", "why", "when", "which", "best", "top", "free"}


def read_post(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    head = text.split("\n---", 2)[0] if text.startswith("---") else ""

    def get(field: str, block: str = head) -> str:
        m = re.search(rf'^\s*{field}:\s*["\']?(.+?)["\']?\s*$', block, re.MULTILINE)
        return m.group(1).strip() if m else ""

    seo_block = re.search(r"^seo:\n((?:[ \t]+.*\n?)+)", head, re.MULTILINE)
    meta_title = get("metaTitle", seo_block.group(1)) if seo_block else ""
    parts = text.split("\n---", 1) if text.startswith("---") else [text]
    body = parts[1] if len(parts) > 1 else text
    body = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body)
    return {
        "file": path.name,
        "body": gsc.fold(re.sub(r"\s+", " ", body)),
        "slug": get("slug") or path.stem,
        "title": get("title"),
        "meta_title": meta_title,
        "keyword": get("focus_keyword"),
        "published": get("publishedAt") or get("date"),
        "updated": get("updatedAt") or get("updated"),
        "draft": get("draft").lower() == "true",
    }


def derive_keyword(title: str) -> str:
    t = BRAND_SUFFIX.sub("", title or "")
    t = NOISE.sub(" ", t)
    words = re.sub(r"\s+", " ", t).strip(" .-").lower().split()
    while words and words[-1] in TRAILING:
        words.pop()
    while words and words[0] in TRAILING:
        words.pop(0)
    return " ".join(words)[:70]


def title_window(title: str, slug: str) -> str:
    """El tramo mas largo del titulo cuyas palabras de contenido estan en el
    slug. Sale literal del titulo, asi que el auditor lo encuentra entero:
    'How to Analyze a Competitor Website in 2026' con slug
    analyze-competitor-website da 'analyze a competitor website'."""
    slug_parts = set(gsc.fold(slug).split("-"))
    slug_tokens = gsc.tokens(slug.replace("-", " "))

    def in_slug(word: str) -> bool:
        # 'competitors' cuenta como 'competitor' y 'affects' como 'affect':
        # cinco letras de raiz bastan para no partir la keyword en un plural.
        if word in slug_tokens:
            return True
        return len(word) >= 4 and any(
            t[:4] == word[:4] for t in slug_tokens if len(t) >= 4)

    def edge_ok(word: str) -> bool:
        return word not in gsc.STOP or word in EDGE_OK or word in slug_parts

    words = re.findall(r"[a-z0-9]+", gsc.fold(title))
    best: list[str] = []
    for i in range(len(words)):
        for j in range(i + 1, len(words) + 1):
            window = words[i:j]
            content = [w for w in window if w not in gsc.STOP]
            if any(not in_slug(w) for w in content):
                break
            if not content or not edge_ok(window[0]) or window[-1] in gsc.STOP:
                continue
            if len(content) >= 2 and len(content) > len([w for w in best if w not in gsc.STOP]):
                best = window
    return " ".join(best)


def in_title(candidate: str, post: dict) -> bool:
    """Contra el mismo titulo que mira el auditor: el meta titulo si existe,
    si no el titulo de la pagina."""
    c = gsc.fold(candidate)
    return bool(c) and c in gsc.fold(post["meta_title"] or post["title"])


def in_body(candidate: str, post: dict) -> bool:
    return bool(candidate) and gsc.fold(candidate) in post["body"]


def suggest(post: dict, queries: list[dict], ranked: dict) -> tuple[str, str]:
    """Devuelve (keyword, origen).

    Toda propuesta tiene que estar entera en el titulo: es lo que exige el
    auditor (E-TITLE-KW), y una keyword que no esta en el titulo no la ataca
    nadie. Entre las que cumplen, se prefiere la que ademas ya aparece en el
    cuerpo: declarar una keyword que el texto no usa es abrir tres errores
    mas (E-KW-ABSENT, W-FIRST-P, W-H2-KW) y no arregla ninguno."""
    candidates: list[tuple[str, str]] = []
    for row in sorted(ranked.get(post["slug"]) or [], key=lambda r: -(r.get("volume") or 0)):
        if in_title(row["keyword"], post):
            candidates.append((row["keyword"], "ranked"))
    for q in sorted(queries, key=lambda q: -q["impressions"]):
        if len(q["key"].split()) >= 2 and in_title(q["key"], post):
            candidates.append((q["key"], "consultas"))
    window = title_window(post["meta_title"] or post["title"], post["slug"])
    if window:
        candidates.append((window, "titulo"))
        # Recortes del tramo, por si el tramo entero no esta en el cuerpo.
        words = window.split()
        for size in range(len(words) - 1, 1, -1):
            for start in range(0, len(words) - size + 1):
                sub = " ".join(words[start:start + size])
                if gsc.tokens(sub) and sub.split()[0] not in gsc.STOP - EDGE_OK \
                        and sub.split()[-1] not in gsc.STOP:
                    candidates.append((sub, "titulo"))
    candidates.append((derive_keyword(post["meta_title"] or post["title"]), "titulo"))

    for keyword, source in candidates:
        if in_body(keyword, post):
            return keyword, source
    return candidates[0]


def load_ranked(path: Path | None, url_prefix: str) -> dict:
    """ranked.json de dfs.py: {slug: [{keyword, position, volume}]}."""
    if not path or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list] = {}
    for row in data.get("rows", []):
        slug_path = gsc.normalize_path(row.get("url") or "")
        prefix = url_prefix.rstrip("/") + "/"
        if not slug_path.startswith(prefix):
            continue
        out.setdefault(slug_path[len(prefix):], []).append(row)
    return out


def band(position: float | None) -> str:
    if position is None:
        return "sin datos"
    if position <= 3:
        return "top 3"
    if position <= 10:
        return "top 10"
    if position <= 20:
        return "casi top 10"
    if position <= 50:
        return "lejos"
    return "muy lejos"


def apply_keyword(path: Path, keyword: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---") or re.search(r"^focus_keyword:", text, re.MULTILINE):
        return False
    safe = keyword.replace('"', "'")
    # Detras de slug si existe, si no detras de title. Nunca fuera del bloque.
    for anchor in (r"^slug:.*$", r"^title:.*$"):
        m = re.search(anchor, text, re.MULTILINE)
        if m:
            insert = m.end()
            text = text[:insert] + f'\nfocus_keyword: "{safe}"' + text[insert:]
            path.write_text(text, encoding="utf-8")
            return True
    return False


def to_markdown(rows: list[dict], summary: dict) -> str:
    out = ["# Mapa de keywords", "",
           f"{summary['posts']} posts. {summary['with_keyword']} con keyword declarada, "
           f"{summary['suggested']} con propuesta.  ",
           "Bandas: " + ", ".join(f"{k} {v}" for k, v in summary["bands"].items()),
           "", "Revisar cada mes las filas en **casi top 10** y **top 10**: "
           "seccion nueva, enlaces internos y titulo. Es donde mas rinde el trabajo.",
           "",
           "| Post | Keyword | Origen | Posicion | Impr. | Clics | Banda | Actualizado |",
           "| --- | --- | --- | ---: | ---: | ---: | --- | --- |"]
    order = {"casi top 10": 0, "top 10": 1, "top 3": 2, "lejos": 3, "muy lejos": 4, "sin datos": 5}
    for r in sorted(rows, key=lambda r: (order[r["band"]], -(r["impressions"] or 0))):
        out.append(f"| {r['slug']} | {r['keyword']} | {r['source']} | "
                   f"{r['position'] if r['position'] is not None else '-'} | "
                   f"{r['impressions'] or 0} | {r['clicks'] or 0} | {r['band']} | "
                   f"{(r['updated'] or r['published'] or '')[:10]} |")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Mapa de keywords por post.")
    ap.add_argument("content_dir")
    ap.add_argument("--gsc", nargs="*", default=[], help="ZIP o carpeta de Search Console")
    ap.add_argument("--ranked", help="salida de dfs.py ranked, JSON")
    ap.add_argument("--url-prefix", default="/blog")
    ap.add_argument("--md")
    ap.add_argument("--json")
    ap.add_argument("--csv")
    ap.add_argument("--apply", action="store_true",
                    help="escribe focus_keyword donde falte")
    args = ap.parse_args()

    content_dir = Path(args.content_dir)
    posts = [read_post(p) for p in sorted(content_dir.rglob("*.md"))]

    pages_by_path: dict[str, dict] = {}
    queries: list[dict] = []
    if args.gsc:
        data = gsc.load(args.gsc)
        merged, _ = gsc.merge_pages(data["pages"])
        pages_by_path = {p["path"]: p for p in merged}
        queries = data["queries"]
    ranked = load_ranked(Path(args.ranked) if args.ranked else None, args.url_prefix)

    rows, applied = [], 0
    prefix = args.url_prefix.rstrip("/")
    for post in posts:
        page = pages_by_path.get(f"{prefix}/{post['slug']}")
        if post["keyword"]:
            keyword, source = post["keyword"], "declarada"
        else:
            keyword, source = suggest(post, queries, ranked)
            if args.apply and not post["draft"]:
                if apply_keyword(content_dir / post["file"], keyword):
                    applied += 1
                    source = "aplicada"
        rows.append({
            "slug": post["slug"], "file": post["file"], "keyword": keyword,
            "source": source,
            "position": page["position"] if page else None,
            "impressions": page["impressions"] if page else None,
            "clicks": page["clicks"] if page else None,
            "band": band(page["position"] if page else None),
            "published": post["published"], "updated": post["updated"],
        })

    bands: dict[str, int] = {}
    for r in rows:
        bands[r["band"]] = bands.get(r["band"], 0) + 1
    summary = {"posts": len(rows), "with_keyword": sum(1 for r in rows if r["source"] in ("declarada", "aplicada")),
               "suggested": sum(1 for r in rows if r["source"] not in ("declarada", "aplicada")),
               "applied": applied, "bands": bands, "generated": date.today().isoformat()}

    if args.md:
        Path(args.md).write_text(to_markdown(rows, summary), encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps({"summary": summary, "rows": rows},
                                              ensure_ascii=False, indent=2), encoding="utf-8")
    if args.csv:
        import csv
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
    if not (args.md or args.json or args.csv):
        print(to_markdown(rows, summary))
    else:
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
