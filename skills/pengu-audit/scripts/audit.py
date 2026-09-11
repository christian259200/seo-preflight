#!/usr/bin/env python3
"""Auditor on-page ejecutable. Devuelve codigo 1 si hay errores.

La diferencia entre esto y una checklist en un SKILL.md es que esto corre. Una
regla escrita se incumple, y se incumple en silencio: en la landing de Pengu
Insights, 45 de 50 posts violaban la regla de CTA que estaba escrita en tres
documentos distintos. Una regla ejecutable no.

Perfiles de plataforma:

  wordpress   frontmatter del plugin ai-blog-bridge (focus_keyword, faq,
              internal_links, key_takeaways, sources)
  nextjs      frontmatter de la landing de Pengu (seo.metaTitle, faqs,
              mainImage, categories)
  canonical   el formato propio de pengu-seo, superset de los dos

Uso:

    python audit.py posts/                      --profile wordpress
    python audit.py src/content/blog/ --profile nextjs --site-root .
    python audit.py post.md --profile nextjs --json informe.json
    python audit.py posts/ --profile wordpress --strict   # los WARN cortan

Sin dependencias externas. Usa pyyaml si esta instalado, y si no, un parser
minimo que cubre el subconjunto de YAML que aparece en frontmatter real.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

# La consola de Windows usa cp1252 por defecto y destroza los acentos del
# informe. Sin esto, "catálogo" sale como "cat?logo" y el mensaje pierde
# sentido justo cuando hay que leerlo.
# Reemplazar sys.stdout por un TextIOWrapper nuevo deja al objeto original sin
# referencias, y al recolectarlo cierra el buffer subyacente. reconfigure()
# cambia la codificacion sobre el mismo objeto y no tiene ese problema.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import yaml  # opcional
except ImportError:
    yaml = None

# --------------------------------------------------------------------------
# Umbrales. Salen del curso de SEO ("70 caracteres para el titulo, 140 para la
# descripcion", "URLs bajo 100 caracteres, 1 o 2 directorios") y del material
# del master. Editar aqui cambia todos los perfiles a la vez.
# --------------------------------------------------------------------------

TITLE_MIN, TITLE_MAX = 30, 70
TITLE_KEYWORD_HEAD = 40      # la keyword deberia caer en los primeros 40 chars
DESC_MIN, DESC_MAX = 120, 160
DESC_IDEAL = 140
H2_MIN, H2_MAX = 3, 12
WORDS_ERROR, WORDS_WARN, WORDS_IDEAL = 300, 900, 1400
INTERNAL_MIN, INTERNAL_MAX = 3, 12
ANCHOR_REPEAT_MAX = 2
DENSITY_MAX = 0.025
URL_MAX = 100
URL_DIRS_MAX = 2
FIRST_PARAGRAPH_WORDS = 120

# Frases que le dicen a un modelo de lenguaje que ese parrafo es la respuesta.
# Es lo que decide si te citan en un AI Overview o en ChatGPT, y no cuesta nada.
SEMANTIC_CUES = (
    "en resumen", "en resumidas cuentas", "lo mas importante", "punto clave",
    "paso 1", "errores comunes", "por ejemplo", "en conclusion",
    "en pocas palabras", "la respuesta corta", "dicho de otro modo",
    "in short", "key takeaway", "for example", "step 1", "common mistakes",
    "the short answer", "bottom line",
)

# Marcadores que delatan que el texto salio de una plantilla de IA sin limpiar.
AI_MARKERS = (
    "[unique insight]", "[citation capsule]", "[personal experience]",
    "[insert ", "[todo", "[placeholder", "lorem ipsum",
    "as an ai language model", "as an ai assistant",
    "como modelo de lenguaje", "como asistente de ia", "[completar", "tbd]",
)

# Aperturas de relleno. El curso es explicito: nada de parrafos de contexto
# antes de la respuesta. Google y los modelos leen el primer parrafo.
FLUFF_OPENERS = (
    "en el mundo actual", "en la era digital", "hoy en dia, en un mundo",
    "en el acelerado mundo", "no es ningun secreto que",
    "in today's fast-paced", "in today's digital", "in the ever-evolving",
    "it's no secret that", "in the world of",
)

STOP_URL = {"de", "la", "el", "los", "las", "un", "una", "y", "o", "en", "para",
            "por", "con", "the", "a", "an", "of", "for", "and", "or", "to", "in"}


# --------------------------------------------------------------------------
# perfiles
# --------------------------------------------------------------------------

PROFILES = {
    "wordpress": {
        "title": ["title"],
        "description": ["description"],
        "keyword": ["focus_keyword"],
        "slug": ["slug"],
        "faq": ["faq"],
        "hero": ["featured_image.url", "featured_image.attachment_id"],
        "hero_alt": ["featured_image.alt"],
        "updated": ["updated", "modified"],
        "internal_links": ["internal_links"],
        "sources": ["sources"],
        "body_h1_allowed": False,
        "money_pages": [],
        "faq_needs_visible": False,   # el plugin renderiza el FAQ solo
    },
    "nextjs": {
        "title": ["seo.metaTitle", "title"],
        "description": ["seo.metaDescription", "excerpt"],
        "keyword": ["focus_keyword", "seo.focusKeyword"],
        "slug": ["slug"],
        "faq": ["faqs"],
        "hero": ["mainImage.url"],
        "hero_alt": ["mainImage.alt"],
        "updated": ["updatedAt", "updated"],
        "internal_links": [],
        "sources": [],
        "body_h1_allowed": False,
        "money_pages": [],            # se declaran en pengu-seo.json
        "faq_needs_visible": True,    # la pagina no renderiza el frontmatter
    },
    "canonical": {
        "title": ["title"],
        "description": ["description"],
        "keyword": ["focus_keyword"],
        "slug": ["slug"],
        "faq": ["faq"],
        "hero": ["hero.path", "hero.url"],
        "hero_alt": ["hero.alt"],
        "updated": ["updated"],
        "internal_links": ["internal_links"],
        "sources": ["sources"],
        "body_h1_allowed": False,
        "money_pages": [],
        "faq_needs_visible": False,
    },
}


# --------------------------------------------------------------------------
# utilidades
# --------------------------------------------------------------------------

def fold(text: str) -> str:
    """Minusculas sin acentos ni puntuacion colapsada. Sin esto, la keyword
    'que es serigrafia' nunca encuentra 'Qué es serigrafía' y todos los
    chequeos de keyword fallan en silencio, que es peor que no tenerlos."""
    text = unicodedata.normalize("NFKD", (text or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip()


def dig(data: dict, path: str):
    """Lee 'seo.metaTitle' dentro de un dict anidado."""
    node = data
    for part in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
        if node is None:
            return None
    return node


def first_present(data: dict, paths: list):
    for path in paths:
        value = dig(data, path)
        if value not in (None, "", [], {}):
            return value
    return None


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Separa frontmatter YAML del cuerpo."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("\n---", 2)
    if len(parts) < 2:
        return {}, text
    raw = parts[0][3:].lstrip("\n")
    body = parts[1].lstrip("\n")
    if yaml is not None:
        try:
            return (yaml.safe_load(raw) or {}), body
        except Exception:
            pass
    return mini_yaml(raw), body


def _scalar(value: str):
    value = value.strip()
    if value.startswith("#"):
        return ""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [_scalar(v) for v in inner.split(",")] if inner else []
    if value in ("true", "True", "yes"):
        return True
    if value in ("false", "False", "no"):
        return False
    if value in ("null", "~", ""):
        return ""
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def mini_yaml(raw: str) -> dict:
    """Parser minimo para el subconjunto de YAML que aparece en un frontmatter
    real: escalares, listas de escalares, listas de diccionarios y diccionarios
    anidados. No es un parser de YAML completo, es el respaldo para cuando
    pyyaml no esta instalado. Si pyyaml esta, no se usa.

    El detalle que importa: cuando una clave viene sin valor todavia no se sabe
    si abre una lista o un diccionario. Se deja pendiente y lo decide la primera
    linea hija, segun empiece o no con guion."""
    root: dict = {}
    # Cada nivel es [indent, contenedor, clave_pendiente, dict_padre]
    stack: list = [[-1, root, None, None]]

    for line in raw.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        # Solo se sale de un nivel cuando la indentacion baja de verdad. Los
        # hermanos comparten indentacion con el nivel, no lo cierran.
        while len(stack) > 1 and indent < stack[-1][0]:
            stack.pop()
        level = stack[-1]

        # Resolver una clave que quedo pendiente en el nivel anterior.
        if level[2] is not None:
            container: list | dict = [] if stripped.startswith("- ") else {}
            level[3][level[2]] = container
            level[2] = level[3] = None      # sin esto se resuelve dos veces
            stack.append([indent, container, None, None])
            level = stack[-1]

        if stripped.startswith("- ") or stripped == "-":
            # Un guion cierra el elemento anterior de la lista y vuelve a ella.
            while len(stack) > 1 and not isinstance(stack[-1][1], list):
                stack.pop()
            level = stack[-1]

        parent = level[1]

        if stripped.startswith("- ") or stripped == "-":
            if not isinstance(parent, list):
                continue
            item = stripped[2:].strip() if len(stripped) > 1 else ""
            # "- key: value" abre un diccionario dentro de la lista.
            match = re.match(r"^([A-Za-z_][\w\-]*):\s*(.*)$", item)
            if match:
                entry = {}
                key, value = match.group(1), match.group(2)
                if value.strip():
                    entry[key] = _scalar(value)
                    stack.append([indent, entry, None, None])
                else:
                    stack.append([indent, entry, key, entry])
                parent.append(entry)
            elif item:
                parent.append(_scalar(item))
            continue

        match = re.match(r"^([A-Za-z_][\w\-.]*):\s*(.*)$", stripped)
        if not match:
            continue
        key, value = match.group(1), match.group(2)
        if not isinstance(parent, dict):
            continue
        if value.strip() == "":
            # Pendiente: la primera linea hija decide lista o diccionario.
            level[2], level[3] = key, parent
            parent[key] = {}
        else:
            parent[key] = _scalar(value)

    return root


def strip_code(body: str) -> str:
    """Fuera bloques de codigo: no cuentan como contenido ni como enlaces."""
    return re.sub(r"```.*?```", "", body, flags=re.DOTALL)


def paragraphs(body: str) -> list:
    out = []
    for block in strip_code(body).split("\n\n"):
        block = block.strip()
        if not block or block.startswith(("#", "|", ">", "!", "---")):
            continue
        out.append(block)
    return out


# --------------------------------------------------------------------------
# el auditor
# --------------------------------------------------------------------------

class Report:
    def __init__(self, name: str):
        self.name = name
        self.errors: list = []
        self.warns: list = []
        self.notes: list = []

    def error(self, code: str, msg: str, fix: str = "") -> None:
        self.errors.append({"code": code, "message": msg, "fix": fix})

    def warn(self, code: str, msg: str, fix: str = "") -> None:
        self.warns.append({"code": code, "message": msg, "fix": fix})

    def note(self, code: str, msg: str, fix: str = "") -> None:
        self.notes.append({"code": code, "message": msg, "fix": fix})

    def as_dict(self) -> dict:
        return {"file": self.name, "errors": self.errors,
                "warnings": self.warns, "notes": self.notes,
                "score": self.score()}

    def score(self) -> int:
        """0-100. Cada error pesa 12, cada warn 4, cada nota 1. No es una nota
        academica, es un orden de trabajo: arregla primero lo que mas resta."""
        return max(0, 100 - 12 * len(self.errors) - 4 * len(self.warns)
                   - 1 * len(self.notes))


def host_of(url: str) -> str:
    match = re.match(r"^https?://([^/:?#]+)", url, re.IGNORECASE)
    host = match.group(1).lower() if match else ""
    return host[4:] if host.startswith("www.") else host


def is_internal(url: str, profile: dict) -> bool:
    """Relativo, o absoluto hacia uno de los dominios del sitio.

    Un subdominio cuenta como propio: app.ejemplo.com es interno si el sitio es
    ejemplo.com. Las paginas de conversion cuentan siempre como internas aunque
    vivan en otro dominio, porque son el destino que se quiere medir."""
    if not re.match(r"^https?://", url, re.IGNORECASE):
        return True
    if any(m in url for m in profile.get("money_pages", [])):
        return True
    host = host_of(url)
    for site in profile.get("sites", []):
        site = site.lower().removeprefix("www.")
        if host == site or host.endswith("." + site):
            return True
    return False


CONFIG_NAME = "pengu-seo.json"

# Git Bash reescribe cualquier argumento que empiece por "/" como ruta de
# Windows antes de pasarlo a Python: "/pricing" llega como
# "C:/Program Files/Git/pricing". Nada falla, simplemente ningun enlace
# coincide y E-NO-CTA marca errores falsos. Se deshace aqui.
MSYS_MANGLED = re.compile(r"^[A-Za-z]:[/\\].*?[/\\]Git[/\\](.*)$")


def unmangle(value: str) -> str:
    match = MSYS_MANGLED.match(value or "")
    return "/" + match.group(1).replace("\\", "/") if match else value



def find_config(start: Path) -> Path | None:
    """Busca pengu-seo.json desde la carpeta auditada hacia arriba."""
    here = start if start.is_dir() else start.parent
    for folder in [here, *here.parents]:
        candidate = folder / CONFIG_NAME
        if candidate.is_file():
            return candidate
    return None


def audit_file(path: Path, profile: dict, site_root: Path | None,
               known_urls: set, url_prefix: str = "/blog") -> Report:
    report = Report(path.name)
    text = path.read_text(encoding="utf-8", errors="replace")
    meta, body = parse_frontmatter(text)
    if not meta:
        report.error("E-FRONTMATTER", "Sin frontmatter YAML legible.",
                     "El archivo tiene que abrir con --- y cerrar con ---.")
        return report

    clean_body = strip_code(body)
    plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean_body)
    words = [w for w in re.findall(r"[\wáéíóúñü]+", plain, re.IGNORECASE)]
    word_count = len(words)

    title = first_present(meta, profile["title"]) or ""
    description = first_present(meta, profile["description"]) or ""
    keyword = first_present(meta, profile["keyword"]) or ""
    slug = first_present(meta, profile["slug"]) or path.stem
    fkw = fold(keyword)

    # --- keyword ---------------------------------------------------------
    if not keyword:
        report.error("E-KEYWORD", "Sin focus_keyword.",
                     "Sin keyword objetivo no hay nada que auditar ni que medir "
                     "despues en Search Console.")
    elif re.search(r"[,;:!?¿¡]", keyword):
        report.warn("W-KEYWORD-PUNT",
                    f"La keyword '{keyword}' lleva puntuacion.",
                    "La comparacion es literal: una coma en el titulo rompe la "
                    "coincidencia. Elegi la keyword sin puntuacion.")

    # --- titulo ----------------------------------------------------------
    if not title:
        report.error("E-TITLE", "Sin titulo.", "")
    else:
        if len(title) > TITLE_MAX:
            report.warn("W-TITLE-LONG",
                        f"Titulo de {len(title)} caracteres, el maximo util es "
                        f"{TITLE_MAX}.",
                        "Google lo corta y pierdes la parte final, que suele ser "
                        "donde esta el gancho.")
        elif len(title) < TITLE_MIN:
            report.warn("W-TITLE-SHORT",
                        f"Titulo de {len(title)} caracteres, corto.",
                        f"Tenes hasta {TITLE_MAX}, usalos: es espacio gratis "
                        "para keywords y para el gancho.")
        if fkw and fkw not in fold(title):
            report.error("E-TITLE-KW",
                         f"La keyword '{keyword}' no esta completa en el titulo.",
                         "Tiene que aparecer entera, no en partes sueltas.")
        elif fkw and fold(title).find(fkw) > TITLE_KEYWORD_HEAD:
            report.note("N-TITLE-KW-POS",
                        "La keyword aparece tarde en el titulo.",
                        f"Movela a los primeros {TITLE_KEYWORD_HEAD} caracteres.")

    # --- descripcion -----------------------------------------------------
    if not description:
        report.error("E-DESC", "Sin meta description.",
                     "Google la inventa a partir del cuerpo y casi siempre "
                     "elige peor que vos.")
    else:
        if not (DESC_MIN <= len(description) <= DESC_MAX):
            report.warn("W-DESC-LEN",
                        f"Descripcion de {len(description)} caracteres, fuera de "
                        f"{DESC_MIN}-{DESC_MAX}.",
                        f"El punto dulce es {DESC_IDEAL}.")
        if fkw and fkw not in fold(description):
            report.warn("W-DESC-KW",
                        f"La keyword '{keyword}' no esta en la descripcion.",
                        "Google la resalta en negrita en los resultados, sube el CTR.")

    # --- primer parrafo ---------------------------------------------------
    paras = paragraphs(body)
    if not paras:
        report.error("E-EMPTY", "Cuerpo vacio.", "")
    else:
        # Las primeras palabras del cuerpo, sea prosa o una caja de puntos
        # clave. Mirar solo el primer parrafo daba un falso positivo cuando el
        # renderizador antepone "Lo esencial", que es un patron correcto: esa
        # lista tambien es la respuesta, y en forma extraible.
        opening = fold(" ".join(" ".join(paras).split()[:FIRST_PARAGRAPH_WORDS]))
        if fkw and fkw not in opening:
            report.warn("W-FIRST-P",
                        "La keyword no aparece en el primer parrafo.",
                        "Es la senal mas barata que existe y la primera que lee "
                        "un modelo de lenguaje al decidir si citarte.")
        for opener in FLUFF_OPENERS:
            if opening.startswith(fold(opener)):
                report.warn("W-FLUFF",
                            f"El post abre con relleno: '{opener}...'",
                            "Responde en la primera linea. El contexto va despues, "
                            "si va.")
                break

    # --- encabezados ------------------------------------------------------
    h1 = re.findall(r"^#\s+(.+)$", clean_body, re.MULTILINE)
    h2 = re.findall(r"^##\s+(.+)$", clean_body, re.MULTILINE)
    h3 = re.findall(r"^###\s+(.+)$", clean_body, re.MULTILINE)

    if h1 and not profile["body_h1_allowed"]:
        report.error("E-H1", f"Hay {len(h1)} H1 en el cuerpo.",
                     "El H1 lo pone la plantilla desde el titulo. Dos H1 "
                     "confunden la jerarquia. Bajalos a ##.")
    if len(h2) < H2_MIN:
        report.error("E-H2-FEW", f"Solo {len(h2)} H2.",
                     f"Minimo {H2_MIN}. Sin estructura no hay fragmentos que "
                     "un buscador pueda extraer.")
    elif len(h2) > H2_MAX:
        report.note("N-H2-MANY", f"{len(h2)} H2, muchos.",
                    f"Por encima de {H2_MAX} el articulo pierde foco.")
    if fkw and h2 and not any(fkw in fold(x) for x in h2):
        report.warn("W-H2-KW",
                    f"Ningun H2 contiene '{keyword}' completa.",
                    "El chequeo busca la cadena entera. 'Sobre que materiales "
                    "funciona' no vale para 'que es dtf textil'.")
    if h3 and h2:
        pos_h2 = clean_body.find("\n## ")
        pos_h3 = clean_body.find("\n### ")
        if pos_h3 != -1 and (pos_h2 == -1 or pos_h3 < pos_h2):
            report.warn("W-H3-ORPHAN", "Hay un H3 antes del primer H2.",
                        "Un H3 sin H2 padre rompe la jerarquia.")

    # --- extension y densidad --------------------------------------------
    if word_count < WORDS_ERROR:
        report.error("E-THIN", f"{word_count} palabras.",
                     f"Por debajo de {WORDS_ERROR} Google lo trata como "
                     "contenido delgado.")
    elif word_count < WORDS_WARN:
        report.warn("W-SHORT", f"{word_count} palabras.",
                    f"Apunta a {WORDS_IDEAL} para una guia que compita.")

    if fkw and word_count:
        hits = fold(plain).count(fkw)
        density = hits / max(1, word_count)
        if density > DENSITY_MAX:
            report.warn("W-STUFF",
                        f"La keyword aparece {hits} veces, densidad "
                        f"{density:.1%}.",
                        "Por encima del 2,5% se lee como relleno. Usa sinonimos.")
        elif hits == 0:
            report.error("E-KW-ABSENT",
                         f"La keyword '{keyword}' no aparece en el cuerpo.", "")

    # --- estilo -----------------------------------------------------------
    if "—" in text or "–" in text:
        lines = [i + 1 for i, l in enumerate(text.split("\n"))
                 if "—" in l or "–" in l]
        report.error("E-DASH",
                     f"Guiones largos o cortos en las lineas {lines[:8]}.",
                     "Sustituilos por comas, dos puntos o punto. Es el rastro "
                     "de IA mas facil de detectar.")
    low_text = fold(text)
    for marker in AI_MARKERS:
        if fold(marker) in low_text:
            report.error("E-AI-MARKER", f"Marcador sin limpiar: '{marker}'.",
                         "Borralo antes de publicar.")

    # --- extraccion para buscadores de IA --------------------------------
    if not any(fold(cue) in low_text for cue in SEMANTIC_CUES):
        report.warn("W-NO-CUE", "Sin senales semanticas.",
                    "Anadi una seccion 'Errores comunes' y un cierre que abra "
                    "con 'En resumen:'. Es lo que un modelo levanta para citarte.")
    if not re.search(r"^\s*([-*]|\d+\.)\s+", clean_body, re.MULTILINE) \
            and "|" not in clean_body:
        report.warn("W-NO-STRUCT", "Sin listas ni tablas.",
                    "Un muro de parrafos no da fragmentos extraibles.")

    faq_meta = first_present(meta, profile["faq"]) or []
    has_visible_faq = bool(re.search(
        r"^##\s*.*(pregunta|faq|frequently asked)", clean_body,
        re.MULTILINE | re.IGNORECASE))
    question_heading = any("?" in x for x in h2 + h3)
    if not faq_meta and not question_heading and not has_visible_faq:
        report.warn("W-NO-QA", "Sin FAQ ni encabezados en pregunta.",
                    "Las preguntas son lo que alimenta los fragmentos "
                    "destacados y las respuestas de IA.")
    if faq_meta and profile["faq_needs_visible"] and not has_visible_faq:
        report.error("E-FAQ-INVISIBLE",
                     "Hay FAQ en el frontmatter pero ninguna seccion visible.",
                     "La plantilla emite FAQPage JSON-LD con contenido que el "
                     "usuario no ve. Google lo trata como marcado enganoso. "
                     "O escribis la seccion o quitas el FAQ del frontmatter.")
    if isinstance(faq_meta, list):
        for entry in faq_meta:
            if isinstance(entry, dict):
                answer = str(entry.get("answer") or entry.get("respuesta") or "")
                if re.search(r"\[[^\]]+\]\([^)]+\)", answer):
                    report.error("E-FAQ-LINK",
                                 "Enlace markdown dentro de una respuesta de FAQ.",
                                 "Rompe el parseo del YAML. Texto plano.")

    # --- enlaces ----------------------------------------------------------
    # El "(?<!!)" es lo que separa un enlace de una imagen. Sin el, cada
    # ![alt](/ruta.png) cuenta como enlace interno e infla la cuenta.
    body_links = re.findall(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)[^)]*\)", clean_body)
    meta_links = first_present(meta, profile["internal_links"]) or []
    meta_link_urls = [x.get("url", "") for x in meta_links
                      if isinstance(x, dict)]

    internal, external = [], []
    for anchor, url in body_links:
        if url.startswith("#"):
            continue
        if is_internal(url, profile):
            internal.append((anchor, url))
        else:
            external.append((anchor, url))

    total_internal = len(internal) + len(meta_link_urls)
    if total_internal == 0:
        report.error("E-NO-INTERNAL", "Sin enlaces internos.",
                     "Una pagina sin enlaces internos no reparte autoridad ni "
                     "retiene al lector.")
    elif total_internal < INTERNAL_MIN:
        report.warn("W-FEW-INTERNAL",
                    f"{total_internal} enlaces internos, minimo {INTERNAL_MIN}.", "")
    elif total_internal > INTERNAL_MAX:
        report.note("N-MANY-INTERNAL", f"{total_internal} enlaces internos.",
                    "Por encima de 12 diluyen el valor de cada uno.")

    if profile["money_pages"]:
        all_urls = " ".join(u for _, u in body_links) + " " + \
                   " ".join(meta_link_urls)
        if not any(m in all_urls for m in profile["money_pages"]):
            report.error("E-NO-CTA",
                         "Ningun enlace a una pagina de conversion.",
                         "El lector termina el articulo y solo puede irse a otro "
                         "articulo. Enlaza a "
                         + ", ".join(profile["money_pages"][:3]) + ".")

    # Las fuentes pueden venir en el cuerpo o declaradas en el frontmatter,
    # que es como el plugin de WordPress renderiza la seccion "Fuentes".
    declared_sources = first_present(meta, profile["sources"]) or []
    if not external and not declared_sources:
        report.warn("W-NO-CITE", "Sin ninguna cita externa.",
                    "Citar fuentes reales es senal de E-E-A-T y es lo que hace "
                    "que un modelo te trate como fuente y no como opinion.")

    anchors: dict[str, int] = {}
    for anchor, _ in body_links:
        key = fold(anchor)
        anchors[key] = anchors.get(key, 0) + 1
    for anchor, count in anchors.items():
        if count > ANCHOR_REPEAT_MAX:
            report.note("N-ANCHOR-REPEAT",
                        f"El anchor '{anchor}' se repite {count} veces.",
                        "Varia el texto del enlace.")
    for anchor, _ in body_links:
        if re.match(r"^https?://", anchor) or fold(anchor) in (
                "aqui", "aca", "click aqui", "here", "click here", "leer mas",
                "read more", "este enlace"):
            report.note("N-ANCHOR-WEAK", f"Anchor sin valor: '{anchor}'.",
                        "El anchor describe el destino, no la accion.")

    # El anchor declarado tiene que existir literalmente en el cuerpo. Si no
    # esta, el inyector no tiene donde colocarlo y el enlace nunca aparece:
    # el post se publica sin error y con menos enlaces de los que creias.
    for link in meta_links:
        if not isinstance(link, dict):
            continue
        anchor = link.get("anchor", "")
        if anchor and fold(anchor) not in fold(plain):
            report.error("E-ANCHOR-MISSING",
                         f"El anchor '{anchor}' no aparece en el cuerpo.",
                         "El inyector busca ese texto literal para convertirlo "
                         "en enlace. O lo escribis en el cuerpo, o cambias el "
                         "anchor por una frase que si este.")

    # Un enlace por bloque: el inyector del plugin de WordPress salta cualquier
    # parrafo que ya tenga un enlace, asi que el segundo anchor se pierde.
    if meta_links:
        for para in paras:
            found = [x for x in meta_links if isinstance(x, dict)
                     and fold(x.get("anchor", "")) in fold(para)]
            if len(found) > 1:
                names = ", ".join(f"'{x['anchor']}'" for x in found)
                report.error("E-LINK-COLLISION",
                             f"Dos anchors en el mismo parrafo: {names}.",
                             "El inyector salta el bloque que ya tiene un enlace "
                             "y el segundo desaparece sin avisar. Separalos en "
                             "parrafos distintos.")
                break

    # --- imagenes ---------------------------------------------------------
    hero = first_present(meta, profile["hero"])
    hero_alt = first_present(meta, profile["hero_alt"])
    # Cuando la portada se referencia por attachment_id, el alt vive en la
    # biblioteca de medios de WordPress, no en el frontmatter. Exigirlo aqui
    # seria un falso positivo en todos los posts del plugin.
    hero_is_attachment = isinstance(hero, int) or (
        isinstance(hero, str) and hero.isdigit())
    if not hero:
        report.warn("W-NO-HERO", "Sin imagen destacada.",
                    "Es lo que se ve al compartir el enlace.")
    elif not hero_alt and not hero_is_attachment:
        report.error("E-HERO-ALT", "La imagen destacada no tiene alt.", "")
    elif not hero_alt and hero_is_attachment:
        report.note("N-HERO-ALT-MEDIA",
                    "El alt de la portada vive en la biblioteca de medios.",
                    "Verifica ahi que lo tenga: desde aqui no se puede.")
    if hero and site_root and isinstance(hero, str) and hero.startswith("/"):
        target = site_root / "public" / hero.lstrip("/")
        if not target.exists():
            report.error("E-HERO-MISSING",
                         f"La imagen destacada no existe: {hero}",
                         f"Buscada en {target}.")

    for alt, src in re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", clean_body):
        if not alt.strip():
            report.error("E-IMG-ALT", f"Imagen sin alt: {src}",
                         "El alt es obligatorio, para accesibilidad y para "
                         "busqueda de imagenes.")
        elif fkw and fold(alt) == fkw:
            report.note("N-IMG-ALT-STUFF", f"El alt es solo la keyword: '{alt}'.",
                        "Describi la imagen, no repitas la keyword.")
        if site_root and src.startswith("/"):
            if not (site_root / "public" / src.lstrip("/")).exists():
                report.error("E-IMG-MISSING", f"Imagen inexistente: {src}", "")

    # --- URL --------------------------------------------------------------
    if isinstance(slug, str):
        if len(slug) > URL_MAX:
            report.note("N-URL-LONG", f"Slug de {len(slug)} caracteres.",
                        f"Manteneló bajo {URL_MAX}.")
        if slug.count("/") > URL_DIRS_MAX:
            report.note("N-URL-DEEP", f"El slug tiene {slug.count('/')} niveles.",
                        f"Maximo {URL_DIRS_MAX} directorios.")
        if fkw:
            slug_tokens = {t for t in slug.replace("/", "-").split("-")
                           if t and t not in STOP_URL}
            kw_tokens = {t for t in fkw.split() if t not in STOP_URL}
            if kw_tokens and not (slug_tokens & kw_tokens):
                report.warn("W-URL-KW",
                            f"El slug '{slug}' no comparte ninguna palabra con "
                            f"la keyword.",
                            "La URL sale en los resultados y una URL clara sube "
                            "el CTR.")
        if re.search(r"[A-Z_]|%20", slug):
            report.warn("W-URL-CHARS", f"Slug con mayusculas o guion bajo: {slug}",
                        "Minusculas y guiones normales.")

    # --- frescura y autoria ----------------------------------------------
    if not first_present(meta, profile["updated"]):
        report.note("N-NO-UPDATED", "Sin fecha de actualizacion.",
                    "Sin dateModified, cada revision que hagas es invisible "
                    "para Google y para los buscadores de IA.")
    author = meta.get("author") or meta.get("byline")
    if not author:
        report.warn("W-NO-AUTHOR", "Sin autor.",
                    "La autoria es la parte mas barata del E-E-A-T.")
    elif isinstance(author, dict) and not (author.get("url") or author.get("bio")):
        report.note("N-AUTHOR-THIN", "El autor no tiene url ni bio.",
                    "Un Person sin enlace no es una entidad verificable.")

    # --- enlaces internos que apuntan a nada ------------------------------
    # Solo se comprueban los enlaces que apuntan al propio blog. Las rutas
    # comerciales del sitio (/pricing, /contacto) no estan en esta carpeta y
    # marcarlas como rotas seria ruido que hace ignorar el informe entero.
    if known_urls and url_prefix:
        for anchor, url in internal:
            path_only = url.split("#")[0].split("?")[0].rstrip("/")
            if path_only.startswith(url_prefix.rstrip("/") + "/") \
                    and path_only not in known_urls:
                report.warn("W-LINK-404",
                            f"Enlace a un post que no existe: {url}",
                            f"Anchor '{anchor}'. O el slug cambio o el post "
                            "nunca se publico.")

    return report


# --------------------------------------------------------------------------

def collect_known_urls(content_dir: Path, prefix: str) -> set:
    urls = set()
    for path in content_dir.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")[:3000]
        match = re.search(r'^slug:\s*["\']?([^"\'\n]+)', text, re.MULTILINE)
        slug = match.group(1).strip() if match else path.stem
        urls.add(f"{prefix.rstrip('/')}/{slug}")
    return urls


def render(reports: list, strict: bool) -> str:
    lines = []
    total_e = sum(len(r.errors) for r in reports)
    total_w = sum(len(r.warns) for r in reports)
    total_n = sum(len(r.notes) for r in reports)

    for report in sorted(reports, key=lambda r: r.score()):
        head = "OK " if not report.errors and not report.warns else "!! "
        lines.append(f"{head}{report.name}  [{report.score()}/100]")
        for item in report.errors:
            lines.append(f"   ERROR  {item['code']}  {item['message']}")
            if item["fix"]:
                lines.append(f"          -> {item['fix']}")
        for item in report.warns:
            lines.append(f"   WARN   {item['code']}  {item['message']}")
            if item["fix"]:
                lines.append(f"          -> {item['fix']}")
        for item in report.notes:
            lines.append(f"   nota   {item['code']}  {item['message']}")
        lines.append("")

    lines.append("=" * 62)
    lines.append(f"{len(reports)} archivos | {total_e} errores | "
                 f"{total_w} avisos | {total_n} notas")
    if reports:
        avg = sum(r.score() for r in reports) / len(reports)
        lines.append(f"Puntaje medio: {avg:.0f}/100")
    verdict = "FALLA" if total_e or (strict and total_w) else "PASA"
    lines.append(f"Resultado: {verdict}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Auditor on-page ejecutable.")
    ap.add_argument("target", help="archivo .md o carpeta")
    ap.add_argument("--profile", choices=sorted(PROFILES), default="canonical")
    ap.add_argument("--site-root", help="raiz del sitio, para verificar imagenes")
    ap.add_argument("--url-prefix", default="/blog",
                    help="prefijo de las URLs del blog, para detectar enlaces rotos")
    ap.add_argument("--json", help="ruta del informe JSON")
    ap.add_argument("--strict", action="store_true",
                    help="los avisos tambien hacen fallar")
    ap.add_argument("--site", action="append", default=[], metavar="DOMINIO",
                    help="dominio propio; los enlaces a el cuentan como internos. Repetible")
    ap.add_argument("--money-page", action="append", default=[], metavar="RUTA",
                    help="pagina de conversion, por ejemplo /pricing. Repetible")
    ap.add_argument("--config", help=f"ruta de {CONFIG_NAME}; si no, se busca hacia arriba")
    args = ap.parse_args()

    target = Path(args.target)
    if not target.exists():
        print(f"No existe: {target}")
        sys.exit(1)

    files = sorted(target.rglob("*.md")) if target.is_dir() else [target]
    if not files:
        print(f"Sin archivos .md en {target}")
        sys.exit(1)

    config_path = Path(args.config) if args.config else find_config(target.resolve())
    config = {}
    if config_path:
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"No se pudo leer {config_path}: {exc}")
            sys.exit(1)

    # La linea de comandos manda sobre el archivo, y el archivo sobre el perfil.
    profile = dict(PROFILES[args.profile])
    profile["sites"] = args.site or config.get("sites", [])
    profile["money_pages"] = ([unmangle(m) for m in args.money_page]
                              or config.get("money_pages")
                              or profile["money_pages"])

    site_root = Path(args.site_root) if args.site_root else None
    if not site_root and config.get("site_root") and config_path:
        site_root = (config_path.parent / config["site_root"]).resolve()
    url_prefix = config.get("url_prefix", unmangle(args.url_prefix))
    known = collect_known_urls(target, url_prefix) if target.is_dir() else set()

    if config_path:
        print(f"Configuracion: {config_path}")
    if not profile["money_pages"]:
        print("Aviso: sin money_pages, el chequeo E-NO-CTA queda apagado. "
              f"Declaralas en {CONFIG_NAME}.")
    print()

    reports = [audit_file(f, profile, site_root, known, url_prefix)
               for f in files]
    print(render(reports, args.strict))

    if args.json:
        Path(args.json).write_text(
            json.dumps({"profile": args.profile,
                        "files": [r.as_dict() for r in reports]},
                       ensure_ascii=False, indent=2), encoding="utf-8")

    failed = any(r.errors for r in reports) or \
        (args.strict and any(r.warns for r in reports))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
