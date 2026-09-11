#!/usr/bin/env python3
"""Lee las exportaciones de Google Search Console y dice donde esta el trabajo.

Search Console es la unica fuente que dice para que te muestra Google de
verdad. Un plan de keywords que la ignora empieza de cero cuando ya hay paginas
en la posicion 8 con cientos de impresiones y ningun clic.

No usa la API: lee los ZIP o carpetas que exporta la consola (boton
"Exportar" > "Descargar CSV") en espanol o ingles. Sin credenciales, sin red,
sin gastar nada.

    python gsc.py exports/ --content-dir src/content/blog --md informe.md
    python gsc.py rendimiento.zip cobertura.zip ia.zip --json gsc.json

Acepta cualquier mezcla de:

  Rendimiento en resultados de busqueda   Consultas.csv, Paginas.csv, ...
  Rendimiento en funciones de IA          Paginas.csv con solo impresiones
  Cobertura / Indexacion                  Problemas criticos.csv

Que saca:

  1. Casi en el top 10. Paginas en posicion 4 a 20 con impresiones. Es el
     trabajo mas rentable que existe: una seccion nueva y tres enlaces
     internos valen mas ahi que un post nuevo desde cero.
  2. CTR bajo para su posicion. Paginas que Google ya muestra alto y nadie
     clica. El titulo y la descripcion no convencen; se reescriben.
  3. Consultas sin pagina. Busquedas con impresiones que ningun post cubre.
     Van al plan de contenido, o como H2 en el post mas cercano.
  4. URLs duplicadas. La misma ruta con y sin www, o con http. Cada
     variante reparte la senal.
  5. Paginas en AI Overviews y problemas de indexacion, si los archivos estan.

Limite honesto: la exportacion no cruza consulta con pagina. Para saber que
consulta lleva a que pagina hay dos caminos: filtrar por pagina en la consola
antes de exportar, o `dfs.py ranked dominio`, que devuelve keyword, URL y
posicion desde el indice de DataForSEO.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tempfile
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# CTR que cabe esperar por posicion en Google, orientativo. Sale de los
# estudios publicos de CTR (Backlinko, Advanced Web Ranking) redondeados hacia
# abajo, porque un titulo mediocre en un nicho B2B no llega a la media.
EXPECTED_CTR = {1: 0.27, 2: 0.15, 3: 0.11, 4: 0.08, 5: 0.06, 6: 0.045,
                7: 0.035, 8: 0.03, 9: 0.025, 10: 0.02}

STOP = {
    "de", "la", "el", "los", "las", "un", "una", "y", "o", "a", "en", "para",
    "por", "con", "sin", "que", "del", "al", "es", "como", "cual", "donde",
    "the", "an", "of", "for", "and", "or", "to", "in", "on", "with", "what",
    "how", "why", "is", "are", "best", "top", "vs", "free", "your", "my", "i",
    "can", "do", "does", "get", "it", "its", "you",
}

# Nombres de archivo por idioma de la exportacion.
QUERIES_NAMES = ("consultas", "queries", "consulta", "query")
PAGES_NAMES = ("paginas", "pages", "pagina", "page")
COVERAGE_NAMES = ("problemas criticos", "critical issues", "problemas",
                  "issues")
CHART_NAMES = ("grafico", "chart")
FILTER_NAMES = ("filtros", "filters")


# --------------------------------------------------------------------------
# lectura
# --------------------------------------------------------------------------

def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def tokens(text: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+", fold(text))
            if len(t) > 1 and t not in STOP}


def number(value: str) -> float:
    """'1.234', '1,94%', '0.09%' y '6,21' a float. Las exportaciones en
    espanol usan punto decimal pero el usuario a veces las abre en Excel y
    vuelve a guardar con coma."""
    value = (value or "").strip().replace("%", "").replace("\xa0", "")
    if not value or value in ("-", "N/D", "n/a"):
        return 0.0
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return 0.0


def read_csv(path: Path) -> list[list[str]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    rows = list(csv.reader(text.splitlines()))
    return [r for r in rows if r and any(c.strip() for c in r)]


def classify(name: str) -> str | None:
    base = fold(Path(name).stem)
    if any(base.startswith(n) for n in QUERIES_NAMES):
        return "queries"
    if any(base.startswith(n) for n in PAGES_NAMES):
        return "pages"
    if any(base.startswith(n) for n in COVERAGE_NAMES):
        return "coverage"
    if any(base.startswith(n) for n in CHART_NAMES):
        return "chart"
    if any(base.startswith(n) for n in FILTER_NAMES):
        return "filters"
    return None


def collect_files(inputs: list[str], workdir: Path) -> list[Path]:
    """ZIPs y carpetas, en cualquier mezcla. Los ZIP se abren en un temporal."""
    files: list[Path] = []
    for item in inputs:
        path = Path(item)
        if path.is_file() and path.suffix.lower() == ".zip":
            dest = workdir / path.stem
            with zipfile.ZipFile(path) as zf:
                zf.extractall(dest)
            files += [p for p in dest.rglob("*.csv")]
        elif path.is_dir():
            files += [p for p in path.rglob("*.csv")]
        elif path.is_file():
            files.append(path)
    return files


def parse_table(rows: list[list[str]]) -> tuple[str, list[dict]]:
    """Devuelve ('performance' | 'impressions_only', filas)."""
    header = [fold(h) for h in rows[0]]
    kind = "performance" if len(header) >= 5 else "impressions_only"
    out = []
    for r in rows[1:]:
        if kind == "performance" and len(r) >= 5:
            out.append({"key": r[0].strip(), "clicks": int(number(r[1])),
                        "impressions": int(number(r[2])),
                        "ctr": number(r[3]) / 100.0, "position": number(r[4])})
        elif kind == "impressions_only" and len(r) >= 2:
            out.append({"key": r[0].strip(), "impressions": int(number(r[1]))})
    return kind, out


def load(inputs: list[str]) -> dict:
    data = {"queries": [], "pages": [], "ai_pages": [], "coverage": [],
            "chart": [], "ai_chart": [], "period": None, "files": []}
    with tempfile.TemporaryDirectory() as tmp:
        for path in collect_files(inputs, Path(tmp)):
            kind = classify(path.name)
            if not kind:
                continue
            rows = read_csv(path)
            if len(rows) < 2 and kind != "filters":
                continue
            data["files"].append(f"{path.parent.name}/{path.name}")
            if kind == "filters":
                for r in rows[1:]:
                    if len(r) >= 2 and fold(r[0]).startswith(("fecha", "date")):
                        data["period"] = r[1].replace("\xa0", " ")
                continue
            if kind == "coverage":
                for r in rows[1:]:
                    if len(r) >= 4:
                        data["coverage"].append({
                            "reason": r[0], "source": r[1],
                            "validation": r[2], "pages": int(number(r[3]))})
                continue
            if kind == "chart":
                header = [fold(h) for h in rows[0]]
                target = "chart" if len(header) >= 5 else "ai_chart"
                for r in rows[1:]:
                    entry = {"date": r[0]}
                    if target == "chart" and len(r) >= 5:
                        entry.update(clicks=int(number(r[1])),
                                     impressions=int(number(r[2])),
                                     position=number(r[4]))
                    elif len(r) >= 2:
                        entry.update(impressions=int(number(r[1])))
                    data[target].append(entry)
                continue
            table_kind, parsed = parse_table(rows)
            if kind == "queries":
                data["queries"] += parsed
            elif kind == "pages":
                if table_kind == "performance":
                    data["pages"] += parsed
                else:
                    data["ai_pages"] += parsed
    return data


# --------------------------------------------------------------------------
# analisis
# --------------------------------------------------------------------------

def normalize_path(url: str) -> str:
    path = re.sub(r"^https?://[^/]+", "", url.strip())
    path = path.split("#")[0].split("?")[0]
    return (path.rstrip("/") or "/")


def merge_pages(pages: list[dict]) -> tuple[list[dict], list[dict]]:
    """Junta www / sin www / http en una fila por ruta, con la posicion
    ponderada por impresiones. Devuelve tambien las duplicadas."""
    by_path: dict[str, dict] = {}
    for p in pages:
        key = normalize_path(p["key"])
        slot = by_path.setdefault(key, {"path": key, "urls": [], "clicks": 0,
                                        "impressions": 0, "pos_weight": 0.0})
        slot["urls"].append(p["key"])
        slot["clicks"] += p["clicks"]
        slot["impressions"] += p["impressions"]
        slot["pos_weight"] += p["position"] * max(1, p["impressions"])
    merged, duplicates = [], []
    for slot in by_path.values():
        weight = sum(max(1, x["impressions"]) for x in pages
                     if normalize_path(x["key"]) == slot["path"])
        slot["position"] = round(slot["pos_weight"] / max(1, weight), 1)
        slot["ctr"] = slot["clicks"] / slot["impressions"] if slot["impressions"] else 0.0
        del slot["pos_weight"]
        merged.append(slot)
        if len(slot["urls"]) > 1:
            duplicates.append({"path": slot["path"], "urls": slot["urls"]})
    merged.sort(key=lambda s: -s["impressions"])
    return merged, duplicates


def striking_distance(pages: list[dict], min_impressions: int) -> list[dict]:
    out = [p for p in pages
           if 3.5 <= p["position"] <= 20 and p["impressions"] >= min_impressions]
    # Mas impresiones y mas cerca del top 10 primero.
    out.sort(key=lambda p: (-p["impressions"] / max(1.0, p["position"] - 3)))
    return out


def low_ctr(pages: list[dict], min_impressions: int) -> list[dict]:
    out = []
    for p in pages:
        if p["impressions"] < min_impressions or p["position"] > 12:
            continue
        expected = EXPECTED_CTR.get(max(1, round(p["position"])), 0.015)
        if p["ctr"] < expected * 0.5:
            missed = int(p["impressions"] * expected) - p["clicks"]
            out.append({**p, "expected_ctr": expected,
                        "missed_clicks": max(0, missed)})
    out.sort(key=lambda p: -p["missed_clicks"])
    return out


def existing_content(content_dir: Path | None) -> list[dict]:
    found = []
    if not content_dir or not content_dir.exists():
        return found
    for path in sorted(content_dir.rglob("*.md")):
        head = path.read_text(encoding="utf-8", errors="replace")[:4000]
        get = lambda field: re.search(rf'^\s*{field}:\s*["\']?(.+?)["\']?\s*$',
                                      head, re.MULTILINE)
        slug = get("slug")
        title = get("title") or get("metaTitle")
        keyword = get("focus_keyword")
        words = tokens(" ".join(x.group(1) for x in (title, keyword) if x))
        found.append({"file": path.name,
                      "slug": slug.group(1).strip() if slug else path.stem,
                      "title": title.group(1).strip() if title else path.stem,
                      "keyword": keyword.group(1).strip() if keyword else "",
                      "tokens": words | tokens(path.stem)})
    return found


def coverage_of(query: str, posts: list[dict]) -> tuple[float, dict | None]:
    q = tokens(query)
    if not q:
        return 1.0, None
    best, best_post = 0.0, None
    for post in posts:
        shared = len(q & post["tokens"]) / len(q)
        if shared > best:
            best, best_post = shared, post
    return best, best_post


def query_mining(queries: list[dict], posts: list[dict], brand: list[str],
                 min_impressions: int) -> dict:
    uncovered, partial, branded = [], [], []
    brand_tokens = {fold(b) for b in brand}
    for q in queries:
        if q["impressions"] < min_impressions:
            continue
        low = fold(q["key"])
        if any(b and b in low for b in brand_tokens):
            branded.append(q)
            continue
        share, post = coverage_of(q["key"], posts)
        row = {**q, "closest": post["slug"] if post else None,
               "overlap": round(share, 2)}
        if share < 0.34:
            uncovered.append(row)
        elif share < 0.75:
            partial.append(row)
    uncovered.sort(key=lambda r: -r["impressions"])
    partial.sort(key=lambda r: -r["impressions"])
    branded.sort(key=lambda r: -r["impressions"])
    return {"uncovered": uncovered, "partial": partial, "branded": branded}


def totals(data: dict) -> dict:
    pages = data["pages"]
    clicks = sum(p["clicks"] for p in pages)
    impressions = sum(p["impressions"] for p in pages)
    chart = data["chart"]
    first, last = (chart[:7], chart[-7:]) if len(chart) >= 14 else ([], [])
    trend = None
    if first and last:
        a = sum(x.get("impressions", 0) for x in first) / len(first)
        b = sum(x.get("impressions", 0) for x in last) / len(last)
        trend = {"impressions_first_week": round(a), "impressions_last_week": round(b),
                 "change": round((b - a) / a, 2) if a else None,
                 "position_first_week": round(sum(x.get("position", 0) for x in first) / len(first), 1),
                 "position_last_week": round(sum(x.get("position", 0) for x in last) / len(last), 1)}
    ai_total = sum(p["impressions"] for p in data["ai_pages"])
    return {"pages": len(pages), "clicks": clicks, "impressions": impressions,
            "ctr": round(clicks / impressions, 4) if impressions else 0,
            "queries": len(data["queries"]), "ai_impressions": ai_total,
            "trend": trend}


def analyze(data: dict, content_dir: Path | None, brand: list[str],
            min_impressions: int) -> dict:
    merged, duplicates = merge_pages(data["pages"])
    posts = existing_content(content_dir)
    ai_merged, _ = merge_pages([{**p, "clicks": 0, "position": 0.0, "ctr": 0.0}
                                for p in data["ai_pages"]]) if data["ai_pages"] else ([], [])
    ai_total = sum(p["impressions"] for p in ai_merged) or 1
    for p in ai_merged:
        p["share"] = round(p["impressions"] / ai_total, 2)
        p.pop("position", None); p.pop("ctr", None); p.pop("clicks", None)
    return {
        "period": data["period"],
        "files": data["files"],
        "totals": totals(data),
        "striking_distance": striking_distance(merged, min_impressions),
        "low_ctr": low_ctr(merged, max(30, min_impressions)),
        "queries": query_mining(data["queries"], posts, brand, min_impressions),
        "duplicates": duplicates,
        "ai_overview_pages": ai_merged[:20],
        "coverage": data["coverage"],
        "top_pages": merged[:30],
        "posts_indexed": len(posts),
    }


# --------------------------------------------------------------------------
# informe
# --------------------------------------------------------------------------

def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def to_markdown(r: dict) -> str:
    t = r["totals"]
    out = ["# Search Console: donde esta el trabajo", ""]
    out.append(f"Periodo: {r['period'] or 'segun exportacion'}. "
               f"{t['pages']} paginas, {t['queries']} consultas.  ")
    out.append(f"**{t['clicks']} clics** de **{t['impressions']:,} impresiones** "
               f"(CTR {pct(t['ctr'])}).")
    if t["trend"] and t["trend"]["change"] is not None:
        tr = t["trend"]
        out.append(f"Impresiones por dia: {tr['impressions_first_week']} la primera "
                   f"semana, {tr['impressions_last_week']} la ultima "
                   f"({tr['change']:+.0%}). Posicion media: "
                   f"{tr['position_first_week']} a {tr['position_last_week']}.")
    if t["ai_impressions"]:
        out.append(f"Impresiones en funciones de IA: {t['ai_impressions']:,}.")
    out.append("")

    sd = r["striking_distance"]
    out += ["## 1. Casi en el top 10", "",
            "Paginas en posicion 4 a 20 con impresiones. Una seccion nueva con "
            "la consulta exacta como H2, tres enlaces internos desde posts "
            "relacionados y un titulo mejor. Es el trabajo mas rentable.", ""]
    if sd:
        out += ["| Pagina | Posicion | Impresiones | Clics | CTR |",
                "| --- | ---: | ---: | ---: | ---: |"]
        for p in sd[:20]:
            out.append(f"| {p['path']} | {p['position']} | {p['impressions']} | "
                       f"{p['clicks']} | {pct(p['ctr'])} |")
    else:
        out.append("Nada en ese rango todavia.")
    out.append("")

    lc = r["low_ctr"]
    out += ["## 2. CTR bajo para su posicion", "",
            "Google ya las muestra alto y nadie clica. El problema es el titulo "
            "y la descripcion, no el contenido. Reescribilos con beneficio, "
            "numero, ano y segunda persona.", ""]
    if lc:
        out += ["| Pagina | Posicion | Impresiones | CTR | Esperado | Clics que faltan |",
                "| --- | ---: | ---: | ---: | ---: | ---: |"]
        for p in lc[:15]:
            out.append(f"| {p['path']} | {p['position']} | {p['impressions']} | "
                       f"{pct(p['ctr'])} | {pct(p['expected_ctr'])} | {p['missed_clicks']} |")
    else:
        out.append("Ninguna pagina en el top 12 con CTR anormalmente bajo.")
    out.append("")

    q = r["queries"]
    out += ["## 3. Consultas sin pagina", "",
            "Busquedas con impresiones que ningun post cubre. Cada una es un "
            "post nuevo o un H2 en el post mas cercano. Es la fuente de "
            "keywords mas barata que existe: ya te muestran por ellas.", ""]
    if q["uncovered"]:
        out += ["| Consulta | Impresiones | Posicion | Post mas cercano |",
                "| --- | ---: | ---: | --- |"]
        for x in q["uncovered"][:25]:
            out.append(f"| {x['key']} | {x['impressions']} | {x['position']} | "
                       f"{x['closest'] or '-'} |")
    else:
        out.append("Todas las consultas con impresiones tienen un post cercano.")
    out.append("")
    if q["partial"]:
        out += ["### Cubiertas a medias", "",
                "Hay un post que toca el tema pero no con esas palabras. "
                "Anadi un H2 con la consulta literal.", "",
                "| Consulta | Impresiones | Posicion | Post |",
                "| --- | ---: | ---: | --- |"]
        for x in q["partial"][:20]:
            out.append(f"| {x['key']} | {x['impressions']} | {x['position']} | "
                       f"{x['closest']} |")
        out.append("")

    if r["duplicates"]:
        out += ["## 4. URLs duplicadas", "",
                "La misma ruta aparece con varias URLs. Cada variante reparte "
                "impresiones y posicion. Verifica la redireccion 301 y el "
                "canonical, y pide en la consola que se reindexe la buena.", ""]
        for d in r["duplicates"][:15]:
            out.append(f"- `{d['path']}`: " + ", ".join(d["urls"]))
        out.append("")

    if r["ai_overview_pages"]:
        out += ["## 5. Paginas en AI Overviews", "",
                "| Pagina | Impresiones | Cuota |", "| --- | ---: | ---: |"]
        for p in r["ai_overview_pages"][:12]:
            out.append(f"| {p['path']} | {p['impressions']} | {pct(p['share'])} |")
        out.append("")

    if r["coverage"]:
        out += ["## 6. Indexacion", "",
                "| Motivo | Fuente | Paginas |", "| --- | --- | ---: |"]
        for c in r["coverage"]:
            if c["pages"]:
                out.append(f"| {c['reason']} | {c['source']} | {c['pages']} |")
        out.append("")

    return "\n".join(out)


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Lee exportaciones de Search Console y prioriza el trabajo.")
    ap.add_argument("inputs", nargs="+", help="ZIP, carpeta o CSV. Repetible")
    ap.add_argument("--content-dir", help="posts publicados, para cruzar consultas")
    ap.add_argument("--brand", action="append", default=[],
                    help="palabras de marca a apartar, por ejemplo pengu. Repetible")
    ap.add_argument("--min-impressions", type=int, default=20)
    ap.add_argument("--json", help="ruta del JSON")
    ap.add_argument("--md", help="ruta del informe markdown")
    args = ap.parse_args()

    data = load(args.inputs)
    if not data["pages"] and not data["queries"]:
        print(json.dumps({"error": "No se encontro Consultas.csv ni Paginas.csv "
                                   "en lo indicado."}, ensure_ascii=False, indent=2))
        sys.exit(1)

    report = analyze(data, Path(args.content_dir) if args.content_dir else None,
                     args.brand, args.min_impressions)
    report["generated_at"] = datetime.now().isoformat(timespec="seconds")

    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    if args.md:
        Path(args.md).write_text(to_markdown(report), encoding="utf-8")
        print(f"Informe: {args.md}")
    if not args.json and not args.md:
        print(to_markdown(report))
    else:
        print(json.dumps({
            "clics": report["totals"]["clicks"],
            "impresiones": report["totals"]["impressions"],
            "casi_top10": len(report["striking_distance"]),
            "ctr_bajo": len(report["low_ctr"]),
            "consultas_sin_pagina": len(report["queries"]["uncovered"]),
            "duplicadas": len(report["duplicates"]),
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
