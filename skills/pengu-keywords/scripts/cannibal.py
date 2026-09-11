#!/usr/bin/env python3
"""Canibalizacion entre los posts que ya estan publicados.

Una pagina, un tema. Cuando dos URLs del mismo sitio atacan la misma
keyword, Google tiene que elegir y suele elegir mal: reparte la senal y las
dos rankean peor que una sola. El curso lo cuenta con un caso real, dos
keywords en una pagina y un salto del puesto 9 al 2 al separarlas.

Este script mira el contenido publicado por pares: keyword declarada, titulo
y slug de cada post, y las consultas de Search Console que caen sobre cada
URL cuando se le pasa `--ranked` (salida de `dfs.py ranked`). Agrupa los que
se pisan y propone que hacer con cada grupo:

  fusionar       solapan tanto que son el mismo articulo. Una URL absorbe a
                 la otra y la otra redirige con 301. Se conserva la que mejor
                 posicion e impresiones tenga en Search Console.
  diferenciar    tocan el mismo tema desde angulos distintos. Se separan las
                 keywords, se cambia el titulo del secundario y se enlazan
                 entre si con el anchor de cada uno.
  vigilar        comparten palabras pero la intencion es distinta. Nada que
                 hacer salvo no acercarlos mas.

    python cannibal.py src/content/blog --gsc exports/ --md canibalizacion.md
    python cannibal.py src/content/blog --ranked ranked.json --md canibalizacion.md

No cambia ningun archivo. La fusion implica redirecciones y eso lo decide
una persona.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gsc  # noqa: E402
import kw_map  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Palabras que marcan intencion. Dos posts con la misma keyword de fondo pero
# uno "que es" y otro "herramientas" no se canibalizan: uno informa, el otro
# compara. Se usan para bajar el solapamiento cuando la intencion difiere.
INTENT_MARKERS = {
    "informational": {"what", "que", "guide", "guia", "how", "como", "explained", "types", "tipos"},
    "commercial": {"tools", "herramientas", "best", "mejores", "alternatives", "alternativas",
                   "vs", "compared", "comparativa", "pricing", "precio", "cost", "costo"},
}


def intent_of(text: str) -> str:
    t = gsc.tokens(text) | set(gsc.fold(text).split())
    for label, markers in INTENT_MARKERS.items():
        if t & markers:
            return label
    return "neutral"


def overlap(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def build_pairs(posts: list[dict], pages: dict, ranked: dict, threshold: float) -> list[dict]:
    pairs = []
    for x, y in itertools.combinations(posts, 2):
        kx = gsc.tokens(f"{x['keyword']} {x['slug'].replace('-', ' ')}")
        ky = gsc.tokens(f"{y['keyword']} {y['slug'].replace('-', ' ')}")
        score = overlap(kx, ky)
        same_intent = intent_of(x["title"]) == intent_of(y["title"])
        shared_queries = []
        if ranked:
            qx = {r["keyword"] for r in ranked.get(x["slug"], [])}
            qy = {r["keyword"] for r in ranked.get(y["slug"], [])}
            shared_queries = sorted(qx & qy)
            if shared_queries:
                score = max(score, 0.7 + min(0.3, len(shared_queries) / 10))
        if score < threshold:
            continue
        if score >= 0.85 and same_intent:
            action = "fusionar"
        elif score >= threshold and same_intent:
            action = "diferenciar"
        else:
            action = "vigilar"
        px, py = pages.get(x["slug"]), pages.get(y["slug"])
        pairs.append({
            "a": x["slug"], "b": y["slug"],
            "keyword_a": x["keyword"], "keyword_b": y["keyword"],
            "solapamiento": round(score, 2), "misma_intencion": same_intent,
            "consultas_compartidas": shared_queries[:8],
            "gsc_a": px, "gsc_b": py,
            "accion": action,
            "conservar": keep(x, y, px, py) if action == "fusionar" else None,
        })
    pairs.sort(key=lambda p: (-p["solapamiento"], p["a"]))
    return pairs


def keep(x: dict, y: dict, px: dict | None, py: dict | None) -> str:
    """La URL que se queda cuando se fusiona: mas impresiones, y a igualdad,
    mejor posicion; sin datos, la mas reciente."""
    if px and py:
        if px["impressions"] != py["impressions"]:
            return x["slug"] if px["impressions"] > py["impressions"] else y["slug"]
        return x["slug"] if px["position"] <= py["position"] else y["slug"]
    if px or py:
        return x["slug"] if px else y["slug"]
    return x["slug"] if (x["published"] or "") >= (y["published"] or "") else y["slug"]


def to_markdown(pairs: list[dict], n_posts: int) -> str:
    out = ["# Canibalizacion entre posts publicados", "",
           f"{n_posts} posts, {len(pairs)} pares que se pisan.", "",
           "Una pagina, un tema. Dos URLs por la misma keyword rankean peor que una. "
           "La fusion implica un 301 y la decide una persona: aqui solo se propone.", ""]
    for label, title, blurb in (
        ("fusionar", "Fusionar", "Son el mismo articulo con dos URLs. La que se conserva absorbe lo que la otra tenga de unico; la otra redirige con 301 y se quitan sus enlaces internos."),
        ("diferenciar", "Diferenciar", "Mismo tema, angulo distinto. Separar las keywords, cambiar el titulo del secundario para que diga su angulo, y enlazarlos entre si con el anchor de cada uno."),
        ("vigilar", "Vigilar", "Comparten palabras pero no intencion. Nada que hacer salvo no acercarlos mas."),
    ):
        rows = [p for p in pairs if p["accion"] == label]
        if not rows:
            continue
        out += [f"## {title} ({len(rows)})", "", blurb, "",
                "| Post A | Post B | Solap. | GSC A | GSC B | Conservar | Consultas compartidas |",
                "| --- | --- | ---: | --- | --- | --- | --- |"]
        for p in rows:
            g = lambda d: f"pos {d['position']}, {d['impressions']} impr" if d else "-"
            out.append(f"| {p['a']} | {p['b']} | {p['solapamiento']} | {g(p['gsc_a'])} | "
                       f"{g(p['gsc_b'])} | {p['conservar'] or '-'} | "
                       f"{', '.join(p['consultas_compartidas']) or '-'} |")
        out.append("")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Canibalizacion entre posts publicados.")
    ap.add_argument("content_dir")
    ap.add_argument("--gsc", nargs="*", default=[])
    ap.add_argument("--ranked", help="salida de dfs.py ranked")
    ap.add_argument("--url-prefix", default="/blog")
    ap.add_argument("--threshold", type=float, default=0.6,
                    help="solapamiento minimo para listar un par (0 a 1)")
    ap.add_argument("--md")
    ap.add_argument("--json")
    args = ap.parse_args()

    posts = [kw_map.read_post(p) for p in sorted(Path(args.content_dir).rglob("*.md"))]
    posts = [p for p in posts if not p["draft"]]
    pages: dict[str, dict] = {}
    if args.gsc:
        data = gsc.load(args.gsc)
        merged, _ = gsc.merge_pages(data["pages"])
        prefix = args.url_prefix.rstrip("/") + "/"
        pages = {p["path"][len(prefix):]: p for p in merged if p["path"].startswith(prefix)}
    ranked = kw_map.load_ranked(Path(args.ranked) if args.ranked else None, args.url_prefix)

    pairs = build_pairs(posts, pages, ranked, args.threshold)
    if args.md:
        Path(args.md).write_text(to_markdown(pairs, len(posts)), encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8")
    if not (args.md or args.json):
        print(to_markdown(pairs, len(posts)))
    else:
        counts = {k: sum(1 for p in pairs if p["accion"] == k) for k in ("fusionar", "diferenciar", "vigilar")}
        print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
