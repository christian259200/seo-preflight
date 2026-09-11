#!/usr/bin/env python3
"""Cliente REST de DataForSEO con control de gasto, cache y presupuesto diario.

Solo biblioteca estandar. No hace falta pip install nada: el objetivo es que
esto corra igual en Claude Code, en Cursor, en un runner de CI y en la maquina
de un cliente sin entorno de Python preparado.

Credenciales, en este orden:

  1. DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD
  2. DATA_FOR_SEO="login:password"   (mismo formato que usa la landing)
  3. ~/.config/pengu-seo/dataforseo.json  -> {"login": "...", "password": "..."}

Nunca se imprimen las credenciales, ni siquiera con --debug.

Uso:

    python dfs.py volume "camisetas personalizadas" "serigrafia managua" --loc Nicaragua
    python dfs.py ideas "articulos promocionales" --loc Nicaragua --limit 200
    python dfs.py serp "que es serigrafia" --loc Nicaragua
    python dfs.py difficulty "serigrafia managua" --loc Nicaragua
    python dfs.py intent "comprar termos personalizados" --loc Nicaragua
    python dfs.py costs
    python dfs.py budget --daily 5.00 --threshold 0.25
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

API = "https://api.dataforseo.com/v3"

CONFIG_DIR = Path.home() / ".config" / "pengu-seo"
CACHE_DIR = Path.home() / ".cache" / "pengu-seo" / "dataforseo"
LEDGER = CONFIG_DIR / "ledger.json"
BUDGET = CONFIG_DIR / "budget.json"

# Precio aproximado por llamada, en USD. Sale de la tabla publica de DataForSEO
# y del reference de claude-seo. Es una estimacion para el guardarrail: el costo
# real que devuelve la API se registra despues en el ledger y manda ese.
COST = {
    "serp/google/organic/live/advanced": 0.002,
    "serp/google/organic/live/regular": 0.001,
    "serp/youtube/organic/live/advanced": 0.002,
    "keywords_data/google_ads/search_volume/live": 0.05,
    "keywords_data/google_trends/explore/live": 0.01,
    "dataforseo_labs/google/keyword_ideas/live": 0.05,
    "dataforseo_labs/google/keyword_suggestions/live": 0.05,
    "dataforseo_labs/google/related_keywords/live": 0.05,
    "dataforseo_labs/google/keyword_overview/live": 0.05,
    "dataforseo_labs/google/bulk_keyword_difficulty/live": 0.01,
    "dataforseo_labs/google/search_intent/live": 0.01,
    "dataforseo_labs/google/ranked_keywords/live": 0.05,
    "dataforseo_labs/google/competitors_domain/live": 0.05,
    "dataforseo_labs/google/serp_competitors/live": 0.05,
    "on_page/instant_pages": 0.01,
    "on_page/lighthouse/live/json": 0.02,
    "backlinks/summary/live": 0.02,
    "content_analysis/search/live": 0.02,
}

# Endpoints que siempre piden confirmacion, sin importar el umbral, porque
# pueden devolver conjuntos enormes y cobrar mucho mas que la estimacion.
ALWAYS_CONFIRM = {
    "backlinks/summary/live",
    "dataforseo_labs/google/ranked_keywords/live",
    "content_analysis/search/live",
}

DEFAULT_BUDGET = {"daily_limit": 5.00, "threshold": 0.25, "mode": "threshold"}

CACHE_TTL = {
    "serp/": 60 * 60 * 24,               # la SERP se mueve, 1 dia
    "keywords_data/": 60 * 60 * 24 * 7,  # el volumen es mensual, 7 dias
    "dataforseo_labs/": 60 * 60 * 24 * 7,
    "on_page/": 60 * 60 * 6,
    "backlinks/": 60 * 60 * 24 * 3,
    "content_analysis/": 60 * 60 * 24 * 3,
}


# --------------------------------------------------------------------------
# credenciales
# --------------------------------------------------------------------------

def credentials() -> tuple[str, str]:
    login = os.environ.get("DATAFORSEO_LOGIN")
    password = os.environ.get("DATAFORSEO_PASSWORD")
    if login and password:
        return login, password

    combined = os.environ.get("DATA_FOR_SEO", "")
    if ":" in combined:
        login, password = combined.split(":", 1)
        return login.strip(), password.strip()

    path = CONFIG_DIR / "dataforseo.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("login") and data.get("password"):
            return data["login"], data["password"]

    die(
        "Sin credenciales de DataForSEO.\n"
        "  export DATAFORSEO_LOGIN=... y DATAFORSEO_PASSWORD=...\n"
        "  o DATA_FOR_SEO='login:password'\n"
        f"  o escribi {CONFIG_DIR / 'dataforseo.json'} con login y password."
    )
    raise SystemExit(1)  # inalcanzable, calla al type checker


# --------------------------------------------------------------------------
# presupuesto y ledger
# --------------------------------------------------------------------------

def load_json(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return dict(fallback)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(fallback)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def spent_today() -> float:
    ledger = load_json(LEDGER, {})
    return float(ledger.get(date.today().isoformat(), {}).get("total", 0.0))


def log_spend(endpoint: str, cost: float) -> None:
    ledger = load_json(LEDGER, {})
    today = date.today().isoformat()
    day = ledger.setdefault(today, {"total": 0.0, "calls": {}})
    day["total"] = round(float(day["total"]) + cost, 5)
    day["calls"][endpoint] = round(float(day["calls"].get(endpoint, 0.0)) + cost, 5)
    # Conservar solo 60 dias, el archivo no tiene por que crecer sin limite.
    for key in sorted(ledger)[:-60]:
        ledger.pop(key, None)
    save_json(LEDGER, ledger)


def check_budget(endpoint: str, estimate: float, assume_yes: bool) -> None:
    """Corta antes de gastar. Sale con codigo 2 si el usuario no aprueba."""
    budget = load_json(BUDGET, DEFAULT_BUDGET)
    already = spent_today()
    limit = float(budget.get("daily_limit", DEFAULT_BUDGET["daily_limit"]))

    if already + estimate > limit:
        die(
            f"Bloqueado: el limite diario es ${limit:.2f}, ya van ${already:.4f} "
            f"y esta llamada suma ${estimate:.4f}.\n"
            f"  Subilo con: python dfs.py budget --daily {limit + 5:.2f}",
            code=2,
        )

    mode = budget.get("mode", "threshold")
    threshold = float(budget.get("threshold", DEFAULT_BUDGET["threshold"]))
    needs_ok = mode == "always" or (mode == "threshold" and estimate >= threshold)
    if endpoint in ALWAYS_CONFIRM:
        needs_ok = True

    if needs_ok and not assume_yes:
        die(
            f"Necesita aprobacion: {endpoint} cuesta ~${estimate:.4f} "
            f"(umbral ${threshold:.2f}, gastado hoy ${already:.4f}).\n"
            "  Repeti el comando con --yes si queres seguir.",
            code=2,
        )


# --------------------------------------------------------------------------
# cache
# --------------------------------------------------------------------------

def cache_ttl(endpoint: str) -> int:
    for prefix, ttl in CACHE_TTL.items():
        if endpoint.startswith(prefix):
            return ttl
    return 60 * 60 * 24


def cache_path(endpoint: str, payload: list) -> Path:
    blob = json.dumps([endpoint, payload], sort_keys=True, ensure_ascii=False)
    key = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"{endpoint.replace('/', '_')}__{key}.json"


def cache_read(path: Path, ttl: int) -> dict | None:
    if not path.exists():
        return None
    if time.time() - path.stat().st_mtime > ttl:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# --------------------------------------------------------------------------
# llamada
# --------------------------------------------------------------------------

def call(endpoint: str, payload: list, *, assume_yes: bool = False,
         no_cache: bool = False, count: int = 1) -> dict:
    """Una llamada POST a DataForSEO, con cache y guardarrail de gasto."""
    path = cache_path(endpoint, payload)
    if not no_cache:
        cached = cache_read(path, cache_ttl(endpoint))
        if cached is not None:
            cached["_pengu_cache"] = True
            return cached

    estimate = COST.get(endpoint, 0.05) * max(1, count)
    check_budget(endpoint, estimate, assume_yes)

    login, password = credentials()
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{API}/{endpoint}",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "User-Agent": "pengu-seo/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        die(f"HTTP {exc.code} en {endpoint}: {detail}", code=3)
    except urllib.error.URLError as exc:
        die(f"Sin conexion con DataForSEO: {exc.reason}", code=3)

    if data.get("status_code") != 20000:
        die(f"DataForSEO respondio {data.get('status_code')}: "
            f"{data.get('status_message')}", code=3)

    real_cost = float(data.get("cost") or estimate)
    log_spend(endpoint, real_cost)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    data["_pengu_cache"] = False
    return data


def results(data: dict) -> list:
    """Aplana la respuesta de DataForSEO, que anida tasks > result > items."""
    out = []
    for task in data.get("tasks") or []:
        for result in task.get("result") or []:
            out.append(result)
    return out


# --------------------------------------------------------------------------
# comandos
# --------------------------------------------------------------------------

def loc_payload(args, extra: dict) -> list:
    base = {"language_name": args.lang, "location_name": args.loc}
    base.update(extra)
    return [base]


def cmd_volume(args) -> dict:
    """Volumen, CPC y competencia. Datos directos de Google Ads, no scraping."""
    data = call(
        "keywords_data/google_ads/search_volume/live",
        loc_payload(args, {"keywords": args.keywords[:1000]}),
        assume_yes=args.yes, no_cache=args.no_cache,
    )
    rows = []
    for result in results(data):
        for item in result if isinstance(result, list) else [result]:
            if not isinstance(item, dict) or "keyword" not in item:
                continue
            rows.append({
                "keyword": item.get("keyword"),
                "volume": item.get("search_volume") or 0,
                "cpc": round(item.get("cpc") or 0, 2),
                "competition": item.get("competition"),
                "competition_index": item.get("competition_index"),
                "trend": (item.get("monthly_searches") or [])[:12],
            })
    rows.sort(key=lambda r: r["volume"], reverse=True)
    return {"command": "volume", "rows": rows, "cached": data.get("_pengu_cache")}


def cmd_ideas(args) -> dict:
    """Ideas de keyword a partir de una semilla. El pozo mas ancho que hay."""
    data = call(
        "dataforseo_labs/google/keyword_ideas/live",
        loc_payload(args, {"keywords": [args.seed], "limit": args.limit,
                           "order_by": ["keyword_info.search_volume,desc"]}),
        assume_yes=args.yes, no_cache=args.no_cache,
    )
    rows = []
    for result in results(data):
        for item in result.get("items") or []:
            info = item.get("keyword_info") or {}
            props = item.get("keyword_properties") or {}
            intent = (item.get("search_intent_info") or {}).get("main_intent")
            rows.append({
                "keyword": item.get("keyword"),
                "volume": info.get("search_volume") or 0,
                "cpc": round(info.get("cpc") or 0, 2),
                "competition": info.get("competition_level"),
                "difficulty": props.get("keyword_difficulty"),
                "intent": intent,
            })
    return {"command": "ideas", "seed": args.seed, "rows": rows,
            "cached": data.get("_pengu_cache")}


def cmd_related(args) -> dict:
    data = call(
        "dataforseo_labs/google/related_keywords/live",
        loc_payload(args, {"keyword": args.seed, "limit": args.limit, "depth": 2}),
        assume_yes=args.yes, no_cache=args.no_cache,
    )
    rows = []
    for result in results(data):
        for item in result.get("items") or []:
            kd = item.get("keyword_data") or {}
            info = kd.get("keyword_info") or {}
            rows.append({
                "keyword": kd.get("keyword"),
                "volume": info.get("search_volume") or 0,
                "cpc": round(info.get("cpc") or 0, 2),
                "difficulty": (kd.get("keyword_properties") or {}).get("keyword_difficulty"),
            })
    rows.sort(key=lambda r: r["volume"], reverse=True)
    return {"command": "related", "seed": args.seed, "rows": rows,
            "cached": data.get("_pengu_cache")}


def cmd_difficulty(args) -> dict:
    data = call(
        "dataforseo_labs/google/bulk_keyword_difficulty/live",
        loc_payload(args, {"keywords": args.keywords[:1000]}),
        assume_yes=args.yes, no_cache=args.no_cache,
    )
    rows = []
    for result in results(data):
        for item in result.get("items") or []:
            rows.append({"keyword": item.get("keyword"),
                         "difficulty": item.get("keyword_difficulty")})
    return {"command": "difficulty", "rows": rows, "cached": data.get("_pengu_cache")}


def cmd_intent(args) -> dict:
    """Intencion de busqueda. Decide si la keyword pide blog o pagina comercial."""
    data = call(
        "dataforseo_labs/google/search_intent/live",
        [{"language_name": args.lang, "keywords": args.keywords[:1000]}],
        assume_yes=args.yes, no_cache=args.no_cache,
    )
    rows = []
    for result in results(data):
        for item in result.get("items") or []:
            info = item.get("keyword_intent") or {}
            rows.append({
                "keyword": item.get("keyword"),
                "intent": info.get("label"),
                "probability": round(info.get("probability") or 0, 3),
                "secondary": [s.get("label") for s in
                              (item.get("secondary_keyword_intents") or [])],
            })
    return {"command": "intent", "rows": rows, "cached": data.get("_pengu_cache")}


def cmd_serp(args) -> dict:
    """Top 10 organico mas features. Lo que hay que superar para entrar."""
    data = call(
        "serp/google/organic/live/advanced",
        loc_payload(args, {"keyword": args.keyword, "depth": args.depth,
                           "device": args.device,
                           "people_also_ask_click_depth": 2}),
        assume_yes=args.yes, no_cache=args.no_cache,
    )
    organic, features, paa = [], [], []
    for result in results(data):
        for item in result.get("items") or []:
            kind = item.get("type")
            if kind == "organic":
                organic.append({
                    "position": item.get("rank_absolute"),
                    "url": item.get("url"),
                    "domain": item.get("domain"),
                    "title": item.get("title"),
                    "description": item.get("description"),
                    "title_len": len(item.get("title") or ""),
                    "desc_len": len(item.get("description") or ""),
                })
            elif kind == "people_also_ask":
                for q in item.get("items") or []:
                    paa.append(q.get("title"))
            elif kind:
                features.append(kind)
    return {
        "command": "serp",
        "keyword": args.keyword,
        "organic": organic,
        "features": sorted(set(features)),
        "people_also_ask": paa,
        "cached": data.get("_pengu_cache"),
    }


def cmd_competitors(args) -> dict:
    data = call(
        "dataforseo_labs/google/serp_competitors/live",
        loc_payload(args, {"keywords": args.keywords[:200], "limit": 20}),
        assume_yes=args.yes, no_cache=args.no_cache,
    )
    rows = []
    for result in results(data):
        for item in result.get("items") or []:
            rows.append({
                "domain": item.get("domain"),
                "avg_position": item.get("avg_position"),
                "visibility": item.get("visibility"),
                "keywords_count": item.get("keywords_count"),
            })
    return {"command": "competitors", "rows": rows, "cached": data.get("_pengu_cache")}


# Checks de on_page donde True significa "esta bien", no "hay un problema".
# Todos los demas nombran el defecto, asi que un True es un fallo.
POSITIVE_CHECKS = {
    "canonical", "seo_friendly_url", "seo_friendly_url_characters_check",
    "seo_friendly_url_dynamic_check", "seo_friendly_url_keywords_check",
    "seo_friendly_url_relative_length_check", "has_html_doctype",
    "has_meta_title", "has_meta_description", "is_https", "is_indexable",
}


def failed_checks(checks: dict) -> list:
    """Devuelve solo lo que esta mal, ya normalizado."""
    bad = []
    for name, value in (checks or {}).items():
        if name in POSITIVE_CHECKS:
            if value is False:
                bad.append(f"falta_{name}")
        elif value is True:
            bad.append(name)
    return sorted(bad)


def cmd_onpage(args) -> dict:
    data = call(
        "on_page/instant_pages",
        [{"url": args.url, "enable_javascript": False}],
        assume_yes=args.yes, no_cache=args.no_cache,
    )
    rows = []
    for result in results(data):
        for item in result.get("items") or []:
            meta = item.get("meta") or {}
            htags = meta.get("htags") or {}
            content = meta.get("content") or {}
            checks = item.get("checks") or {}
            rows.append({
                "url": item.get("url"),
                "title": meta.get("title"),
                "title_len": len(meta.get("title") or ""),
                "description": meta.get("description"),
                "desc_len": len(meta.get("description") or ""),
                "h1": htags.get("h1") or [],
                "h2": htags.get("h2") or [],
                "words": content.get("plain_text_word_count"),
                "readability": content.get("flesch_kincaid_readability_index"),
                "internal_links": meta.get("internal_links_count"),
                "external_links": meta.get("external_links_count"),
                "images_without_alt": meta.get("images_count_without_alt"),
                # DataForSEO nombra casi todos los checks como el problema
                # ("no_description", "title_too_long"), asi que un True es un
                # fallo. Las excepciones se listan aparte para no invertirlas.
                "failed_checks": failed_checks(checks),
            })
    return {"command": "onpage", "rows": rows, "cached": data.get("_pengu_cache")}


def cmd_costs(args) -> dict:
    ledger = load_json(LEDGER, {})
    budget = load_json(BUDGET, DEFAULT_BUDGET)
    days = sorted(ledger)[-args.days:]
    return {
        "command": "costs",
        "budget": budget,
        "today": round(spent_today(), 4),
        "history": {d: ledger[d] for d in days},
        "total_period": round(sum(float(ledger[d]["total"]) for d in days), 4),
    }


def cmd_budget(args) -> dict:
    budget = load_json(BUDGET, DEFAULT_BUDGET)
    if args.daily is not None:
        budget["daily_limit"] = args.daily
    if args.threshold is not None:
        budget["threshold"] = args.threshold
    if args.mode:
        budget["mode"] = args.mode
    save_json(BUDGET, budget)
    return {"command": "budget", "budget": budget}


# --------------------------------------------------------------------------

def die(message: str, code: int = 1) -> None:
    print(json.dumps({"error": message}, ensure_ascii=False, indent=2))
    sys.exit(code)


def common_flags() -> argparse.ArgumentParser:
    """Los flags globales, como parser padre.

    Argparse solo acepta las opciones del parser principal **antes** del
    subcomando, asi que `dfs.py volume x --loc Nicaragua` fallaba aunque es la
    forma en que cualquiera lo escribe. Heredandolos en cada subparser, las dos
    posiciones funcionan."""
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--loc", default=os.environ.get("PENGU_LOCATION", "United States"),
                        help="location_name, por ejemplo Nicaragua o Spain")
    parent.add_argument("--lang", default=os.environ.get("PENGU_LANGUAGE", "English"),
                        help="language_name, por ejemplo Spanish")
    parent.add_argument("--yes", action="store_true",
                        help="aprueba el gasto sin preguntar")
    parent.add_argument("--no-cache", action="store_true")
    parent.add_argument("--out", help="escribe el JSON a un archivo ademas de imprimirlo")
    return parent


def main() -> None:
    parent = common_flags()
    parser = argparse.ArgumentParser(
        description="Cliente DataForSEO con guardarrail de gasto.",
        parents=[parent])
    sub = parser.add_subparsers(dest="cmd", required=True)
    add = lambda name: sub.add_parser(name, parents=[parent])

    p = add("volume"); p.add_argument("keywords", nargs="+"); p.set_defaults(fn=cmd_volume)
    p = add("ideas"); p.add_argument("seed"); p.add_argument("--limit", type=int, default=200); p.set_defaults(fn=cmd_ideas)
    p = add("related"); p.add_argument("seed"); p.add_argument("--limit", type=int, default=100); p.set_defaults(fn=cmd_related)
    p = add("difficulty"); p.add_argument("keywords", nargs="+"); p.set_defaults(fn=cmd_difficulty)
    p = add("intent"); p.add_argument("keywords", nargs="+"); p.set_defaults(fn=cmd_intent)
    p = add("serp"); p.add_argument("keyword"); p.add_argument("--depth", type=int, default=10); p.add_argument("--device", default="desktop"); p.set_defaults(fn=cmd_serp)
    p = add("competitors"); p.add_argument("keywords", nargs="+"); p.set_defaults(fn=cmd_competitors)
    p = add("onpage"); p.add_argument("url"); p.set_defaults(fn=cmd_onpage)
    p = add("costs"); p.add_argument("--days", type=int, default=7); p.set_defaults(fn=cmd_costs)
    p = add("budget"); p.add_argument("--daily", type=float); p.add_argument("--threshold", type=float); p.add_argument("--mode", choices=["none", "threshold", "always"]); p.set_defaults(fn=cmd_budget)

    args = parser.parse_args()
    payload = args.fn(args)
    payload["generated_at"] = datetime.now().isoformat(timespec="seconds")
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
