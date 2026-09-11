# Cambios

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

### Corregido

- `audit.py --url-prefix` mandaba menos que `pengu-seo.json`, al revés que
  todos los demás flags.
- `smoke.py` prueba `gsc.py` y `kw_map.py` con una exportación sintética.

## 1.0.0

Primera versión: `pengu-keywords`, `pengu-write`, `pengu-audit` y el
orquestador `pengu-seo`.
