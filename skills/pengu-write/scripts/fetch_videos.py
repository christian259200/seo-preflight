#!/usr/bin/env python3
"""Buscar los videos de YouTube mas vistos en espanol para uno o varios temas.

Ordena por vistas reales, no por relevancia de YouTube, porque lo que interesa
es un video que el lector ya reconozca como util. Filtra los no embebibles.

Uso:
    YTKEY=<clave> python fetch_videos.py "que es dtf textil" "grabado laser"
    YTKEY=<clave> python fetch_videos.py --json salida.json "tema 1" "tema 2"

La clave es de YouTube Data API v3. Se lee de YTKEY o YOUTUBE_API_KEY y no se
imprime nunca.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/youtube/v3/%s?%s"


def call(path: str, key: str, **params) -> dict:
    params["key"] = key
    url = API % (path, urllib.parse.urlencode(params))
    with urllib.request.urlopen(url, timeout=40) as response:
        return json.load(response)


def top_videos(query: str, key: str, limit: int) -> list:
    """Buscar candidatos, pedir sus estadisticas y ordenar por vistas."""
    found = call(
        "search", key, part="snippet", q=query, type="video", maxResults=12,
        relevanceLanguage="es", videoEmbeddable="true", order="relevance",
    )
    ids = [item["id"]["videoId"] for item in found.get("items", [])]
    if not ids:
        return []

    detail = call("videos", key, part="snippet,statistics,contentDetails,status",
                  id=",".join(ids))

    rows = []
    for video in detail.get("items", []):
        # Un video puede pasar el filtro de la busqueda y seguir sin permitir
        # embeber, asi que se vuelve a comprobar sobre el dato real.
        if not video.get("status", {}).get("embeddable", True):
            continue
        snippet = video["snippet"]
        stats = video.get("statistics", {})
        rows.append({
            "id": video["id"],
            "titulo": snippet["title"],
            "canal": snippet["channelTitle"],
            "vistas": int(stats.get("viewCount", 0)),
            "duracion": video["contentDetails"]["duration"],
            "idioma": (snippet.get("defaultAudioLanguage")
                       or snippet.get("defaultLanguage") or "?").lower(),
            "url": "https://www.youtube.com/watch?v=" + video["id"],
        })

    rows.sort(key=lambda row: -row["vistas"])
    return rows[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queries", nargs="+", help="Temas a buscar")
    parser.add_argument("--limit", type=int, default=6, help="Videos por tema")
    parser.add_argument("--json", dest="out", default="", help="Guardar el resultado")
    args = parser.parse_args()

    key = os.environ.get("YTKEY") or os.environ.get("YOUTUBE_API_KEY", "")
    if not key:
        sys.exit("Falta YTKEY. Exportala antes de correr el script.")

    results = {}
    for query in args.queries:
        try:
            rows = top_videos(query, key, args.limit)
        except urllib.error.HTTPError as error:
            print("FALLO  %s  (%s)" % (query, error.code), file=sys.stderr)
            continue
        results[query] = rows
        print("== %s" % query)
        for row in rows:
            print("   %s  %-7s %-9s %10s  %s | %s" % (
                row["id"], row["idioma"], row["duracion"],
                format(row["vistas"], ","), row["titulo"][:64], row["canal"][:24]))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(results, handle, ensure_ascii=False, indent=1)
        print("\nguardado en %s" % args.out)

    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
