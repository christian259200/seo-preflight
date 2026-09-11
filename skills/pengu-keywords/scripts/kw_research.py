#!/usr/bin/env python3
"""Pipeline de keyword research: de semillas a un plan de contenido priorizado.

Lo que separa esto de exportar un CSV de volumenes:

  1. **Puerta de tipo de SERP.** Antes de recomendar un blog, mira que hay
     rankeando. Si el top 10 son fichas de producto, un articulo no entra por
     mucho que lo optimices. Es la causa numero uno de blogs que nunca rankean.
  2. **Puerta de dificultad contra autoridad.** Una keyword de KD 70 no es una
     oportunidad para un sitio nuevo, es tiempo perdido. El umbral se mueve con
     el parametro --authority.
  3. **Canibalizacion.** Cruza contra el contenido que ya existe en disco y
     avisa antes de escribir el segundo articulo sobre lo mismo.
  4. **Agrupacion en clusters.** Devuelve el pilar y sus satelites, no una lista
     plana de 400 filas que nadie va a leer.

Uso:

    python kw_research.py "articulos promocionales" "serigrafia" \\
        --loc Nicaragua --lang Spanish \\
        --content-dir posts/ \\
        --authority low --out plan.json --md plan.md

Sin --yes no gasta nada por encima del umbral configurado en dfs.py.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
DFS = HERE / "dfs.py"

# Palabras vacias que no deben pesar al agrupar en clusters ni al detectar
# canibalizacion. Espanol e ingles porque los clientes mezclan.
STOP = {
    "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o", "a",
    "en", "para", "por", "con", "sin", "que", "del", "al", "es", "son", "se",
    "su", "sus", "lo", "mas", "como", "cual", "cuales", "donde", "cuando",
    "the", "a", "an", "of", "for", "and", "or", "to", "in", "on", "with",
    "what", "how", "why", "best", "top", "vs",
}

# Marcadores de intencion. El dato de DataForSEO manda cuando existe; esto es
# el respaldo y sirve para explicar la decision en el informe.
INFORMATIONAL = ("que es", "qué es", "como", "cómo", "por que", "por qué",
                 "cuando", "cuánto", "cuanto", "guia", "guía", "tutorial",
                 "ejemplos", "tipos de", "diferencia", "what is", "how to",
                 "why", "guide", "examples", "tips")
COMMERCIAL = ("mejor", "mejores", "comparativa", "vs", "alternativa",
              "alternativas", "review", "opiniones", "best", "top",
              "comparison", "alternatives", "cual elegir", "cuál elegir")
TRANSACTIONAL = ("comprar", "precio", "precios", "cotizar", "cotizacion",
                 "cotización", "tienda", "venta", "barato", "oferta",
                 "buy", "price", "pricing", "cheap", "for sale", "near me",
                 "cerca de mi", "cerca de mí")

# Cuanto vale cada intencion para un negocio que vende. Informational trae
# trafico, transactional trae dinero. Un plan solo informacional es un blog que
# no factura, y es el defecto mas comun de los blogs corporativos.
INTENT_VALUE = {
    "transactional": 1.00,
    "commercial": 0.85,
    "navigational": 0.30,
    "informational": 0.55,
}

# Techo de dificultad segun la autoridad del dominio. Por encima de esto la
# keyword se marca como "todavia no", no como oportunidad.
AUTHORITY_CEILING = {"low": 30, "medium": 50, "high": 70}

# Tipos de resultado que, si dominan el top 10, significan que Google no quiere
# un articulo ahi. Un blog contra una SERP de producto no entra.
COMMERCIAL_SERP_HINTS = ("shopping", "product", "carousel", "local_pack",
                         "google_flights", "hotels_pack", "jobs")


# --------------------------------------------------------------------------

def fold(text: str) -> str:
    """Minusculas sin acentos. Sin esto 'serigrafia' nunca encuentra
    'serigrafía' y todos los cruces fallan en silencio."""
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def tokens(text: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+", fold(text))
            if len(t) > 2 and t not in STOP}


def run_dfs(args_list: list, common: list) -> dict:
    """Llama a dfs.py y devuelve su JSON. Propaga el corte de presupuesto."""
    cmd = [sys.executable, str(DFS)] + common + args_list
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode == 2:
        print(proc.stdout or proc.stderr, file=sys.stderr)
        sys.exit(2)
    if proc.returncode != 0:
        print(f"dfs.py fallo ({proc.returncode}): "
              f"{(proc.stdout or proc.stderr)[:500]}", file=sys.stderr)
        return {}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}


# --------------------------------------------------------------------------
# clasificacion
# --------------------------------------------------------------------------

def guess_intent(keyword: str) -> str:
    low = fold(keyword)
    for marker in TRANSACTIONAL:
        if fold(marker) in low:
            return "transactional"
    for marker in COMMERCIAL:
        if fold(marker) in low:
            return "commercial"
    for marker in INFORMATIONAL:
        if fold(marker) in low:
            return "informational"
    return "informational"


def content_type(intent: str, serp_kind: str | None) -> str:
    """Que hay que escribir. La SERP manda por encima de la intencion."""
    if serp_kind == "comercial":
        return "pagina comercial o categoria"
    if serp_kind == "mixta":
        return "pagina comercial con bloque de contenido"
    if intent == "transactional":
        return "pagina comercial o categoria"
    if intent == "commercial":
        return "comparativa o listado"
    return "articulo de blog"


def classify_serp(features: list, organic: list) -> str:
    """Comercial, mixta o informativa. Decide si un blog tiene sitio ahi."""
    feature_hits = sum(1 for f in features
                       if any(h in f for h in COMMERCIAL_SERP_HINTS))
    blog_signals = 0
    for row in organic[:10]:
        url = fold(row.get("url") or "")
        if any(p in url for p in ("/blog/", "/guia", "/guide", "/articulo",
                                  "/post", "/recursos", "/resources", "/news")):
            blog_signals += 1
    if feature_hits >= 2 and blog_signals <= 2:
        return "comercial"
    if blog_signals >= 5:
        return "informativa"
    if blog_signals == 0 and organic:
        return "comercial"
    return "mixta"


# --------------------------------------------------------------------------
# puntuacion
# --------------------------------------------------------------------------

def opportunity(row: dict, ceiling: int) -> tuple[float, list]:
    """Puntaje 0-100 y las razones. Tres factores multiplicativos: demanda,
    posibilidad de ganar y valor comercial. Multiplicativos a proposito: si
    cualquiera de los tres es cero, la keyword no sirve, por mucho que los
    otros dos brillen. Una suma ponderada esconde eso."""
    reasons = []

    volume = row.get("volume") or 0
    # Escala logaritmica. La diferencia util entre 10 y 100 busquedas es mucho
    # mayor que entre 10.000 y 100.000, donde ya no vas a ganar igual.
    demand = min(1.0, math.log10(volume + 1) / 4.0)
    if volume == 0:
        demand = 0.05
        reasons.append("sin volumen medible, solo vale dentro de un cluster")
    elif volume < 20:
        reasons.append(f"volumen bajo ({volume}), long tail")

    difficulty = row.get("difficulty")
    if difficulty is None:
        winnability = 0.5
        reasons.append("sin dato de dificultad")
    else:
        if difficulty > ceiling:
            winnability = max(0.05, 0.5 * (ceiling / max(difficulty, 1)))
            reasons.append(
                f"KD {difficulty} por encima de tu techo ({ceiling}), "
                "no la ataques todavia")
        else:
            winnability = 1.0 - (difficulty / (ceiling * 2.0))

    intent = row.get("intent") or "informational"
    value = INTENT_VALUE.get(intent, 0.5)
    cpc = row.get("cpc") or 0
    if cpc >= 1.0:
        value = min(1.0, value + 0.15)
        reasons.append(f"CPC ${cpc:.2f}, hay anunciantes pujando, hay dinero")
    elif cpc == 0 and intent == "informational":
        value = max(0.2, value - 0.15)

    serp_kind = row.get("serp_kind")
    if serp_kind == "comercial" and intent == "informational":
        winnability *= 0.35
        reasons.append(
            "la SERP es comercial: un articulo no entra, hace falta pagina de "
            "producto o categoria")

    score = round(demand * winnability * value * 100, 1)
    return score, reasons


def band(score: float) -> str:
    if score >= 25:
        return "atacar ya"
    if score >= 12:
        return "segunda ola"
    if score >= 5:
        return "cluster de apoyo"
    return "descartar"


# --------------------------------------------------------------------------
# clusters y canibalizacion
# --------------------------------------------------------------------------

def build_clusters(rows: list) -> list:
    """Agrupa por solapamiento de tokens. El de mas volumen es el pilar."""
    ordered = sorted(rows, key=lambda r: r.get("volume") or 0, reverse=True)
    clusters, assigned = [], set()

    for row in ordered:
        if row["keyword"] in assigned:
            continue
        head = tokens(row["keyword"])
        if not head:
            continue
        members = [row]
        assigned.add(row["keyword"])
        for other in ordered:
            if other["keyword"] in assigned:
                continue
            shared = head & tokens(other["keyword"])
            # Dos tokens de contenido en comun es suficiente para que compitan
            # por la misma intencion en la practica.
            if len(shared) >= 2 or (len(head) == 1 and shared):
                members.append(other)
                assigned.add(other["keyword"])
        clusters.append({
            "pilar": row["keyword"],
            "volumen_total": sum(m.get("volume") or 0 for m in members),
            "score_pilar": row.get("score"),
            "miembros": [m["keyword"] for m in members[1:]],
            "tamano": len(members),
        })

    clusters.sort(key=lambda c: c["volumen_total"], reverse=True)
    return clusters


def existing_targets(content_dir: Path) -> list:
    """Lee el contenido publicado y saca la keyword que ataca cada archivo."""
    found = []
    if not content_dir or not content_dir.exists():
        return found
    for path in sorted(content_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        head = text[:4000]
        keyword = None
        for field in ("focus_keyword", "focus_kw", "keyword", "primary_keyword"):
            match = re.search(rf'^{field}:\s*["\']?(.+?)["\']?\s*$',
                              head, re.MULTILINE)
            if match:
                keyword = match.group(1).strip()
                break
        if not keyword:
            match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', head, re.MULTILINE)
            keyword = match.group(1).strip() if match else path.stem.replace("-", " ")
        found.append({"file": path.name, "keyword": keyword,
                      "tokens": tokens(keyword)})
    return found


def cannibalization(rows: list, existing: list) -> list:
    """Avisa antes de escribir el segundo articulo sobre lo mismo."""
    clashes = []
    for row in rows:
        row_tokens = tokens(row["keyword"])
        if not row_tokens:
            continue
        for post in existing:
            shared = row_tokens & post["tokens"]
            if not shared:
                continue
            overlap = len(shared) / max(1, min(len(row_tokens), len(post["tokens"])))
            if overlap >= 0.7:
                clashes.append({
                    "keyword": row["keyword"],
                    "choca_con": post["file"],
                    "keyword_existente": post["keyword"],
                    "solapamiento": round(overlap, 2),
                    "accion": "actualizar el post existente"
                              if overlap >= 0.9 else
                              "diferenciar el angulo o enlazar al existente",
                })
                break
    return clashes


# --------------------------------------------------------------------------
# informe
# --------------------------------------------------------------------------

def to_markdown(plan: dict) -> str:
    out = ["# Plan de keywords", ""]
    meta = plan["meta"]
    out += [
        f"Semillas: {', '.join(meta['seeds'])}  ",
        f"Mercado: {meta['location']} / {meta['language']}  ",
        f"Autoridad asumida: {meta['authority']} (techo de KD {meta['ceiling']})  ",
        f"Keywords evaluadas: {meta['evaluated']}  ",
        f"Costo de esta corrida: ${meta['cost_estimate']:.4f}",
        "",
    ]

    if plan["cannibalization"]:
        out += ["## Aviso de canibalizacion", "",
                "Estas keywords chocan con contenido que ya tenes publicado. "
                "Escribir un articulo nuevo divide la senal entre dos URLs y "
                "las dos bajan.", "",
                "| Keyword nueva | Choca con | Solapamiento | Que hacer |",
                "| --- | --- | --- | --- |"]
        for c in plan["cannibalization"][:20]:
            out.append(f"| {c['keyword']} | {c['choca_con']} | "
                       f"{c['solapamiento']} | {c['accion']} |")
        out.append("")

    for label in ("atacar ya", "segunda ola", "cluster de apoyo"):
        rows = [r for r in plan["keywords"] if r["banda"] == label]
        if not rows:
            continue
        out += [f"## {label.capitalize()} ({len(rows)})", "",
                "| Keyword | Vol | KD | CPC | Intencion | SERP | Que escribir | Score |",
                "| --- | ---: | ---: | ---: | --- | --- | --- | ---: |"]
        for r in rows[:40]:
            out.append(
                f"| {r['keyword']} | {r['volume']} | "
                f"{r['difficulty'] if r['difficulty'] is not None else '?'} | "
                f"{r['cpc']} | {r['intent']} | {r.get('serp_kind') or '-'} | "
                f"{r['que_escribir']} | {r['score']} |")
        out.append("")

    if plan["clusters"]:
        out += ["## Clusters", "",
                "El pilar va primero. Los satelites enlazan al pilar y el pilar "
                "a todos. Sin esos enlaces son articulos sueltos, no un cluster.",
                "",
                "| Pilar | Volumen del grupo | Satelites |",
                "| --- | ---: | --- |"]
        for c in plan["clusters"][:15]:
            sat = ", ".join(c["miembros"][:6]) or "-"
            out.append(f"| {c['pilar']} | {c['volumen_total']} | {sat} |")
        out.append("")

    descartadas = [r for r in plan["keywords"] if r["banda"] == "descartar"]
    if descartadas:
        out += [f"## Descartadas ({len(descartadas)})", "",
                "No es que no sirvan nunca. Es que hoy, con la autoridad que "
                "tenes, el retorno esta en las de arriba.", ""]
        for r in descartadas[:15]:
            razon = r["razones"][0] if r["razones"] else "score bajo"
            out.append(f"- **{r['keyword']}** ({r['volume']}/mes): {razon}")
        out.append("")

    return "\n".join(out)


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Keyword research priorizado.")
    ap.add_argument("seeds", nargs="+")
    ap.add_argument("--loc", default="United States")
    ap.add_argument("--lang", default="English")
    ap.add_argument("--limit", type=int, default=150,
                    help="ideas por semilla")
    ap.add_argument("--authority", choices=["low", "medium", "high"],
                    default="low", help="autoridad del dominio")
    ap.add_argument("--content-dir", help="carpeta con el contenido publicado")
    ap.add_argument("--serp-check", type=int, default=8,
                    help="cuantas finalistas verificar contra la SERP real")
    ap.add_argument("--min-volume", type=int, default=10)
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--out", help="ruta del JSON")
    ap.add_argument("--md", help="ruta del informe markdown")
    args = ap.parse_args()

    common = ["--loc", args.loc, "--lang", args.lang]
    if args.yes:
        common.append("--yes")

    # 1. Ampliar el pozo -----------------------------------------------------
    pool: dict[str, dict] = {}
    for seed in args.seeds:
        data = run_dfs(["ideas", seed, "--limit", str(args.limit)], common)
        for row in data.get("rows", []):
            if row.get("keyword"):
                pool.setdefault(row["keyword"], row)

    if not pool:
        print(json.dumps({"error": "Sin resultados. Revisa credenciales, "
                                   "mercado y presupuesto."}, indent=2))
        sys.exit(1)

    # 2. Filtrar antes de gastar en dificultad ------------------------------
    rows = [r for r in pool.values() if (r.get("volume") or 0) >= args.min_volume]
    rows.sort(key=lambda r: r.get("volume") or 0, reverse=True)
    rows = rows[:200]

    # 3. Dificultad para las que no la traen --------------------------------
    missing = [r["keyword"] for r in rows if r.get("difficulty") is None]
    if missing:
        kd = run_dfs(["difficulty"] + missing[:1000], common)
        lookup = {x["keyword"]: x["difficulty"] for x in kd.get("rows", [])}
        for r in rows:
            if r.get("difficulty") is None:
                r["difficulty"] = lookup.get(r["keyword"])

    # 4. Intencion ----------------------------------------------------------
    for r in rows:
        if not r.get("intent"):
            r["intent"] = guess_intent(r["keyword"])

    # 5. Puntuar ------------------------------------------------------------
    ceiling = AUTHORITY_CEILING[args.authority]
    for r in rows:
        r["score"], r["razones"] = opportunity(r, ceiling)

    rows.sort(key=lambda r: r["score"], reverse=True)

    # 6. Verificar la SERP real de las finalistas ---------------------------
    # Solo de las mejores: cada consulta cuesta, y es la comprobacion que
    # evita escribir un articulo que jamas iba a rankear.
    for r in rows[:args.serp_check]:
        serp = run_dfs(["serp", r["keyword"]], common)
        if not serp:
            continue
        r["serp_kind"] = classify_serp(serp.get("features", []),
                                       serp.get("organic", []))
        r["serp_top3"] = [o.get("domain") for o in serp.get("organic", [])[:3]]
        r["people_also_ask"] = serp.get("people_also_ask", [])[:8]
        r["score"], r["razones"] = opportunity(r, ceiling)

    rows.sort(key=lambda r: r["score"], reverse=True)
    for r in rows:
        r["banda"] = band(r["score"])
        r["que_escribir"] = content_type(r["intent"], r.get("serp_kind"))

    # 7. Clusters y canibalizacion -----------------------------------------
    clusters = build_clusters([r for r in rows if r["banda"] != "descartar"])
    existing = existing_targets(Path(args.content_dir)) if args.content_dir else []
    clashes = cannibalization(rows[:60], existing)

    plan = {
        "meta": {
            "seeds": args.seeds,
            "location": args.loc,
            "language": args.lang,
            "authority": args.authority,
            "ceiling": ceiling,
            "evaluated": len(rows),
            "existing_posts": len(existing),
            "cost_estimate": round(
                0.05 * len(args.seeds) + 0.01 + 0.002 * args.serp_check, 4),
        },
        "keywords": rows,
        "clusters": clusters,
        "cannibalization": clashes,
    }

    text = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    if args.md:
        Path(args.md).write_text(to_markdown(plan), encoding="utf-8")
        print(f"Informe: {args.md}")
    if not args.out and not args.md:
        print(text)
    else:
        summary = {b: sum(1 for r in rows if r["banda"] == b)
                   for b in ("atacar ya", "segunda ola", "cluster de apoyo",
                             "descartar")}
        print(json.dumps({"resumen": summary,
                          "clusters": len(clusters),
                          "canibalizacion": len(clashes)},
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
