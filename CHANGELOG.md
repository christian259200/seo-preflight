# Cambios

## 1.2.0

Lo que un despliegue rompe se ve el mismo día, y las reglas corren al
guardar, no solo cuando alguien se acuerda de lanzar el auditor. Varias
ideas vienen de claude-seo (MIT), adaptadas a scripts sin dependencias.

### Nuevo

- `site_check.py --compare anterior.json`: deriva entre dos comprobaciones.
  Canonical distinto o ausente, `noindex` nuevo, H1, título o JSON-LD que
  desaparecen y URLs que dejan de responder 200 son críticos y devuelven
  código 1. Cada `--json` guarda una instantánea por URL, incluidos los
  tipos de schema, así que cualquier informe viejo sirve de base.
- Plugin de Claude Code: `.claude-plugin/marketplace.json` y un hook
  `PostToolUse` (`hooks/audit_on_save.py`) que audita cada `.md` con
  frontmatter al guardarlo, si hay `pengu-seo.json` hacia arriba. Con
  errores devuelve 2 y Claude ve el informe.
- `audit.py`: `W-AI-PHRASE`, muletillas de IA en inglés y español. Lista
  corta a propósito.
- `pengu-seo.json` acepta `profile`, y `audit.py` lo usa cuando no se pasa
  `--profile`. El hook no necesita argumentos.
- `pengu-seo/references/google-updates.md`: lo que Google cambió y toca a
  estas reglas, con fecha y fuente de Google en cada fila.
- `pengu-seo/SKILL.md`: formato de recomendación con dato de apoyo,
  dependencia, criterio de fallo e indicador adelantado.

### Cambiado

- `LLMS-TXT-MISSING` pasa de aviso a nota. Google Search ignora `llms.txt`
  (guía de optimización para IA generativa, 2026-06-29) y ningún buscador
  de IA ha confirmado que lo lea. `geo.md` deja de venderlo como palanca.
- Las referencias dicen que `FAQPage` ya no da resultados enriquecidos
  (2026-05-07). `E-FAQ-INVISIBLE` se mantiene: schema sin contenido visible
  sigue siendo engañoso, y la FAQ visible es lo que extraen las respuestas
  de IA.

## 1.1.0

Search Console entra al flujo. Antes las tres skills empezaban de cero, como
si el sitio no rankeara por nada, y en un sitio con 13.000 impresiones y 16
clics eso es escribir artículos nuevos mientras las páginas en posición 9
siguen sin clics.

### Nuevo

- `pengu-keywords/scripts/gsc.py`: lee las exportaciones de Search Console
  (ZIP o carpeta, español o inglés) y saca cinco cosas: páginas casi en el top
  10, páginas con CTR bajo para su posición, consultas sin página, URLs
  duplicadas y páginas en AI Overviews. Sin red, sin credenciales.
- `pengu-keywords/scripts/kw_map.py`: el mapa de keywords. Cada post, su
  keyword, posición, impresiones y fecha. Propone `focus_keyword` a los que no
  la tienen, siempre entera en el título, y `--apply` la escribe.
- `dfs.py ranked dominio`: keyword, URL y posición de todo lo que rankea un
  dominio. Es el cruce consulta-página que la exportación no da.
- `dfs.py serp` devuelve `ai_overview` (si aparece y a quién cita) y
  `featured_snippet`. Sin eso la SERP se leía incompleta.
- `kw_research.py --gsc`: las consultas que ya te muestran entran al pozo, y
  las que ya rankean en posición 20 o mejor cambian la recomendación a
  "actualizar la página que ya rankea". Columnas AIO y GSC en el informe.
- `audit.py`: `W-YEAR-STALE` (año viejo en título o descripción) y
  `N-SLUG-YEAR` (año en el slug, que no se cambia). El JSON incluye la keyword
  y el título de cada archivo, para cruzarlo con Search Console.
- `references/search-console.md` en `pengu-keywords`.
- `pengu-audit/scripts/site_check.py`: comprobación técnica del sitio
  publicado. robots.txt, sitemap, redirecciones de host, y por URL: 200 sin
  redirigir, canonical propio, sin noindex, un H1, título sin marca duplicada.
- `pengu-keywords/scripts/cannibal.py`: canibalización entre posts ya
  publicados, por pares, con propuesta de fusionar, diferenciar o vigilar.

### Corregido

- `audit.py --url-prefix` mandaba menos que `pengu-seo.json`, al revés que
  todos los demás flags.
- `smoke.py` prueba `gsc.py` y `kw_map.py` con una exportación sintética.
- `E-NO-CTA` y `W-NO-CITE` casaban las páginas de conversión por subcadena:
  un enlace a `buffer.com/pricing` contaba como conversión propia y dejaba
  de contar como cita externa. Ahora una ruta solo cuenta en enlaces propios.

## 1.0.0

Primera versión: `pengu-keywords`, `pengu-write`, `pengu-audit` y el
orquestador `pengu-seo`.
