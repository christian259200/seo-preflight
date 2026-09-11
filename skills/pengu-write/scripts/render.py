#!/usr/bin/env python3
"""Convierte un post en formato canonico al formato de la plataforma destino.

Se escribe una vez y se publica en cualquier parte. La alternativa, que es
mantener una skill por CMS, termina en tres versiones del mismo articulo que
divergen al tercer cambio.

Destinos:

  wordpress   frontmatter del plugin ai-blog-bridge. El plugin renderiza el
              FAQ, las fuentes, el indice y los enlaces internos, asi que el
              cuerpo se entrega tal cual.
  nextjs      frontmatter de la landing de Pengu. La plantilla NO renderiza
              nada del frontmatter salvo el FAQ como JSON-LD, asi que aqui hay
              que escribir en el cuerpo lo que alla es automatico: puntos clave,
              enlaces internos, seccion de FAQ visible y fuentes.
  markdown    markdown limpio con todo visible. Para Ghost, Obsidian o revision.

Uso:

    python render.py post.md --to nextjs  --out src/content/blog/post.md
    python render.py post.md --to wordpress --out posts/post.md
    python render.py post.md --to nextjs --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

# Reemplazar sys.stdout por un TextIOWrapper nuevo deja al objeto original sin
# referencias, y al recolectarlo cierra el buffer subyacente. reconfigure()
# cambia la codificacion sobre el mismo objeto y no tiene ese problema.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import yaml
except ImportError:
    yaml = None

sys.path.insert(0, str(Path(__file__).resolve().parents[2]
                       / "pengu-audit" / "scripts"))
try:
    from audit import parse_frontmatter  # type: ignore
except ImportError:  # el auditor no esta al lado
    def parse_frontmatter(text: str):
        if not text.startswith("---"):
            return {}, text
        parts = text.split("\n---", 2)
        raw, body = parts[0][3:], parts[1].lstrip("\n")
        return (yaml.safe_load(raw) if yaml else {}) or {}, body


def fold(text: str) -> str:
    """Minusculas sin acentos, **conservando las posiciones**.

    El fold del auditor colapsa espacios, y eso esta bien para comparar. Aqui
    no sirve: la posicion que devuelve la busqueda se usa para cortar el texto
    original, asi que un fold que mueva indices inserta el enlace en mitad de
    una palabra. Cada caracter acentuado se descompone y se le quita la marca,
    de modo que la cadena resultante mide exactamente lo mismo."""
    out = []
    for char in (text or "").lower():
        decomposed = unicodedata.normalize("NFKD", char)
        base = "".join(c for c in decomposed if not unicodedata.combining(c))
        out.append(base if len(base) == 1 else char)
    return "".join(out)


# --------------------------------------------------------------------------
# inyeccion de enlaces internos
# --------------------------------------------------------------------------

def inject_links(body: str, links: list) -> tuple[str, list]:
    """Mete cada enlace interno en el cuerpo, una vez y en un bloque distinto.

    Copia deliberada de la regla del plugin de WordPress: un bloque que ya
    tiene un enlace se salta. Si no se replica aqui, un post escrito para
    Next.js pasa la auditoria y el mismo post en WordPress pierde enlaces en
    silencio. La regla comun es lo que hace que el formato canonico sirva.

    Devuelve el cuerpo y la lista de anchors que no se pudieron colocar.
    """
    blocks = body.split("\n\n")
    pending = [dict(link) for link in links if link.get("anchor")]
    placed = set()

    for index, block in enumerate(blocks):
        stripped = block.strip()
        if not stripped or stripped.startswith(("#", "|", "```", ">", "!")):
            continue
        if re.search(r"\[[^\]]+\]\([^)]+\)", block):
            continue  # ya tiene un enlace: el inyector real lo saltaria

        for link in pending:
            anchor = link["anchor"]
            if anchor in placed:
                continue
            # Coincidencia insensible a acentos y mayusculas, pero se respeta
            # el texto original del cuerpo para no alterar la redaccion.
            match = re.search(re.escape(fold(anchor)), fold(block))
            if not match:
                continue
            start, end = match.span()
            original = block[start:end]
            title = link.get("title", "")
            replacement = (f'[{original}]({link["url"]} "{title}")'
                           if title else f'[{original}]({link["url"]})')
            blocks[index] = block[:start] + replacement + block[end:]
            placed.add(anchor)
            break

    missing = [link["anchor"] for link in pending if link["anchor"] not in placed]
    return "\n\n".join(blocks), missing


# --------------------------------------------------------------------------
# bloques visibles
# --------------------------------------------------------------------------

def takeaways_block(items: list, heading: str) -> str:
    if not items:
        return ""
    lines = [f"## {heading}", ""]
    lines += [f"- {item}" for item in items]
    return "\n".join(lines) + "\n"


def faq_block(entries: list, heading: str) -> str:
    if not entries:
        return ""
    lines = [f"## {heading}", ""]
    for entry in entries:
        question = entry.get("question") or entry.get("pregunta") or ""
        answer = entry.get("answer") or entry.get("respuesta") or ""
        lines += [f"### {question}", "", answer, ""]
    return "\n".join(lines)


def sources_block(entries: list, heading: str) -> str:
    if not entries:
        return ""
    lines = [f"## {heading}", ""]
    for entry in entries:
        if isinstance(entry, dict):
            lines.append(f"- [{entry.get('title', entry.get('url'))}]"
                         f"({entry.get('url')})")
        else:
            lines.append(f"- {entry}")
    return "\n".join(lines) + "\n"


def video_block(video) -> str:
    if not video:
        return ""
    url = video if isinstance(video, str) else video.get("url", "")
    return f"\n{url}\n" if url else ""


# --------------------------------------------------------------------------
# adaptadores
# --------------------------------------------------------------------------

def to_wordpress(meta: dict, body: str) -> tuple[dict, str, list]:
    """El plugin hace el trabajo pesado. Aqui solo se mapean nombres."""
    hero = meta.get("hero") or {}
    out = {
        "title": meta["title"],
        "slug": meta["slug"],
        "external_id": meta.get("external_id") or f"pengu-{meta['slug']}",
        "status": meta.get("status", "publish"),
        "description": meta.get("description", ""),
        "focus_keyword": meta.get("focus_keyword", ""),
        "categories": meta.get("categories", ["Blog"]),
        "tags": meta.get("tags", []),
        "date": meta.get("date"),
        "toc": meta.get("toc", True),
        "show_updated_date": True,
        "comment_status": meta.get("comment_status", "closed"),
    }
    if hero.get("attachment_id"):
        out["featured_image"] = {"attachment_id": hero["attachment_id"]}
    elif hero.get("path") or hero.get("url"):
        out["featured_image"] = {"url": hero.get("path") or hero.get("url"),
                                 "alt": hero.get("alt", "")}
    for key in ("key_takeaways", "internal_links", "faq", "sources",
                "tooltips", "byline", "updated"):
        if meta.get(key):
            out[key] = meta[key]
    # El cuerpo se entrega crudo: el plugin inyecta enlaces, FAQ y fuentes.
    return out, body, []


def to_nextjs(meta: dict, body: str, lang: str) -> tuple[dict, str, list]:
    """La plantilla de Next.js no renderiza el frontmatter, asi que todo lo que
    en WordPress es automatico aqui hay que escribirlo en el cuerpo."""
    es = lang.startswith("es")
    hero = meta.get("hero") or {}
    author = meta.get("byline") or meta.get("author") or {}

    body, missing = inject_links(body, meta.get("internal_links", []))

    parts = []
    if meta.get("key_takeaways"):
        parts.append(takeaways_block(
            meta["key_takeaways"],
            "Lo esencial" if es else "Key takeaways"))
    parts.append(body.rstrip())
    if meta.get("faq"):
        parts.append(faq_block(
            meta["faq"],
            "Preguntas frecuentes" if es else "Frequently asked questions"))
    if meta.get("sources"):
        parts.append(sources_block(
            meta["sources"], "Fuentes" if es else "Sources"))
    rendered = "\n\n".join(p for p in parts if p.strip()) + "\n"

    out = {
        "title": meta["title"],
        "slug": meta["slug"],
        "publishedAt": iso(meta.get("date")),
        "excerpt": meta.get("excerpt") or meta.get("description", ""),
        "isFeatured": meta.get("featured", False),
        "readingTime": max(1, round(len(rendered.split()) / 200)),
        "draft": meta.get("status", "publish") != "publish",
        "focus_keyword": meta.get("focus_keyword", ""),
        "mainImage": {"url": hero.get("path") or hero.get("url", ""),
                      "alt": hero.get("alt", "")},
        "author": {
            "name": author.get("name", "Christian Monge"),
            "url": author.get("url", ""),
            "image": {"url": "/authors/christian-monge.png",
                      "alt": author.get("name", "Christian Monge")},
            "bio": author.get("bio", ""),
        },
        "categories": [
            c if isinstance(c, dict) else {"title": c, "slug": slugify(c)}
            for c in meta.get("categories", [])
        ],
        "seo": {
            "metaTitle": meta.get("meta_title") or meta["title"],
            "metaDescription": meta.get("description", ""),
        },
    }
    if meta.get("updated"):
        out["updatedAt"] = iso(meta["updated"])
    if meta.get("faq"):
        # Se emiten a JSON-LD y ademas quedan visibles en el cuerpo, que es lo
        # que exige Google: marcado y contenido tienen que coincidir.
        out["faqs"] = [{"question": f.get("question"),
                        "answer": strip_markdown(f.get("answer", ""))}
                       for f in meta["faq"]]
    return out, rendered, missing


def to_markdown(meta: dict, body: str, lang: str) -> tuple[dict, str, list]:
    es = lang.startswith("es")
    body, missing = inject_links(body, meta.get("internal_links", []))
    parts = []
    if meta.get("key_takeaways"):
        parts.append(takeaways_block(meta["key_takeaways"],
                                     "Lo esencial" if es else "Key takeaways"))
    parts.append(body.rstrip())
    if meta.get("video"):
        parts.append(video_block(meta["video"]))
    if meta.get("faq"):
        parts.append(faq_block(meta["faq"], "Preguntas frecuentes"
                               if es else "Frequently asked questions"))
    if meta.get("sources"):
        parts.append(sources_block(meta["sources"],
                                   "Fuentes" if es else "Sources"))
    # hero y byline se conservan: son la portada y la autoria, que es la parte
    # mas barata del E-E-A-T. Perderlas al convertir seria tirar senal.
    keep = {k: v for k, v in meta.items()
            if k in ("title", "slug", "description", "excerpt", "focus_keyword",
                     "date", "updated", "categories", "tags", "hero", "byline")}
    return keep, "\n\n".join(p for p in parts if p.strip()) + "\n", missing


# --------------------------------------------------------------------------

def slugify(text: str) -> str:
    text = fold(text)
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text)).strip("-")


def strip_markdown(text: str) -> str:
    """Un enlace markdown dentro de un valor YAML rompe el parseo. Se quita el
    enlace y se conserva el texto."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", str(text))
    return re.sub(r"[*_`]", "", text).strip()


def iso(value) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds") \
            .replace("+00:00", "Z")
    if isinstance(value, str):
        if value.endswith("Z"):
            return value
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return value
    else:
        parsed = value if isinstance(value, datetime) else \
            datetime.combine(value, datetime.min.time())
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc) \
        .isoformat(timespec="milliseconds").replace("+00:00", "Z")


def dump_frontmatter(meta: dict) -> str:
    if yaml is not None:
        text = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False,
                              default_flow_style=False, width=1000)
    else:
        text = simple_dump(meta)
    return f"---\n{text}---\n\n"


def simple_dump(data, indent: int = 0) -> str:
    """Volcado YAML minimo para cuando pyyaml no esta."""
    pad = "  " * indent
    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{pad}{key}:")
            lines.append(simple_dump(value, indent + 1).rstrip("\n"))
        elif isinstance(value, list):
            lines.append(f"{pad}{key}:")
            for item in value:
                if isinstance(item, dict):
                    inner = simple_dump(item, indent + 2).rstrip("\n").split("\n")
                    lines.append(f"{pad}  - {inner[0].strip()}")
                    lines += inner[1:]
                else:
                    lines.append(f"{pad}  - {quote(item)}")
        else:
            lines.append(f"{pad}{key}: {quote(value)}")
    return "\n".join(lines) + "\n"


def quote(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if re.search(r'[:#\[\]{}"\']|^\s|\s$', text) or text == "":
        escaped = text.replace('"', '\\"')
        return f'"{escaped}"'
    return text


def main() -> None:
    ap = argparse.ArgumentParser(description="Canonico -> plataforma.")
    ap.add_argument("source")
    ap.add_argument("--to", choices=["wordpress", "nextjs", "markdown"],
                    required=True)
    ap.add_argument("--out")
    ap.add_argument("--lang", default="es")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    text = Path(args.source).read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    for field in ("title", "slug"):
        if not meta.get(field):
            print(json.dumps({"error": f"Falta '{field}' en el frontmatter."}))
            sys.exit(1)

    if args.to == "wordpress":
        out_meta, out_body, missing = to_wordpress(meta, body)
    elif args.to == "nextjs":
        out_meta, out_body, missing = to_nextjs(meta, body, args.lang)
    else:
        out_meta, out_body, missing = to_markdown(meta, body, args.lang)

    rendered = dump_frontmatter(out_meta) + out_body

    if missing:
        print(f"AVISO: {len(missing)} enlaces internos sin colocar: "
              f"{', '.join(missing)}", file=sys.stderr)
        print("       El anchor no aparece en ningun parrafo libre. O lo "
              "escribis en el texto, o lo quitas de internal_links.",
              file=sys.stderr)

    if args.dry_run or not args.out:
        print(rendered)
    else:
        destination = Path(args.out)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
        print(f"Escrito: {destination}  ({len(out_body.split())} palabras, "
              f"{len(missing)} enlaces sin colocar)")


if __name__ == "__main__":
    main()
