---
name: pengu-audit
description: >-
  Auditoría on-page ejecutable de posts en markdown. Comprueba título, meta
  descripción, keyword, jerarquía de encabezados, extensión, enlaces internos y
  de conversión, imágenes, FAQ, schema, URL y estilo, con perfiles para
  WordPress y Next.js. Devuelve código 1 si hay errores, así que sirve de puerta
  antes de publicar. Usa esta skill cuando el usuario pida revisar, auditar o
  validar contenido, antes de cualquier push, o cuando pregunte qué está mal en
  su blog.
user-invocable: true
argument-hint: "[ruta] [--profile wordpress|nextjs|canonical]"
license: MIT
metadata:
  author: Christian Monge
  version: "1.2.0"
---

# Pengu Audit

Corre, encuentra y corta. Es la pieza central del proyecto.

## Por qué existe

Las reglas escritas se incumplen en silencio. Datos reales de este mismo
entorno:

| Regla | Dónde estaba escrita | Incumplimiento |
|---|---|---|
| Enlazar a la aplicación | AGENTS.md, VOICE.md y dos skills | 45 de 50 posts |
| Sin guiones largos | tres documentos | 7 posts |
| FAQ visible con su schema | guías de Google | 3 posts |
| Un enlace por párrafo | referencia de la skill | 20 de 31 posts |

Nadie lo sabía porque nada lo comprobaba. Un script que devuelve código 1 sí.

## Uso

```bash
cd skills/pengu-audit/scripts

python audit.py posts/ --profile wordpress --site example.com
python audit.py landing/src/content/blog --profile nextjs --site-root landing
python audit.py post.md --profile canonical
python audit.py posts/ --profile wordpress --json informe.json
python audit.py posts/ --profile wordpress --strict
```

Códigos de salida: `0` si pasa, `1` si hay errores. Con `--strict`, los avisos
también cortan.

Sin dependencias externas. `pyyaml` mejora el parseo del frontmatter si está
instalado, pero hay un parser propio de respaldo.

## El sitio publicado: site_check.py

El auditor de markdown no ve la plantilla. Un canonical que apunta a otra
URL, un H1 vacío, una redirección que llegó tarde o un sitemap con URLs que
devuelven 308 solo se ven pidiendo la página. `site_check.py` la pide.

```bash
python site_check.py https://www.example.com --md sitio.md
python site_check.py https://www.example.com --only /blog/ --limit 60
```

Lee robots.txt y el sitemap (o índice de sitemaps), comprueba que las
variantes del host (sin www, http) redirigen a la canónica en un salto, y
para cada URL del sitemap: responde 200 sin redirigir, canonical
autorreferente, sin noindex, un solo H1 con texto, título y descripción en
rango, sin marca duplicada en el título, sin saltos de H1 a H3. Solo
biblioteca estándar, con retardo entre peticiones. Código de salida 1 si hay
errores.

Lo que encontró la primera vez en un sitio real: cuatro páginas con la marca
dos veces en el título porque la plantilla ya la añadía, un guion largo en
robots.txt, y dieciocho rutas que Search Console tenía indexadas con y sin
www aunque la redirección ya existía.

### Deriva: qué cambió desde la última vez

Un despliegue que rompe el SEO se nota cuando cae el tráfico, semanas
después. Con dos informes se nota el mismo día:

```bash
python site_check.py https://www.example.com --json lunes.json
# ... un despliegue después ...
python site_check.py https://www.example.com --json martes.json --compare lunes.json
```

Compara URL por URL lo que el script ya mide y lo clasifica:

| Nivel | Qué | Por qué |
|---|---|---|
| crítico | canonical distinto o ausente, `noindex` nuevo, H1 o `<title>` que desaparecen, JSON-LD que desaparece, URL que deja de responder 200 | Tumba tráfico en días. Código de salida 1 |
| aviso | texto del título, de la descripción o del H1 cambiado, URL que salió del sitemap | A veces es intencional. Vigilar el CTR dos semanas |
| info | H2 distintos, schema nuevo o de otro tipo, URL nueva | Para saber que pasó |

Cada informe `--json` guarda una instantánea por URL (estado, título,
descripción, canonical, robots, H1, H2, tipos de JSON-LD), así que
cualquier informe viejo sirve de base. Las reglas y los niveles vienen de
la práctica de seo-drift en claude-seo (MIT), recortadas a lo que este
script mide sin API de pago.

## Auditar al guardar

Instalado como plugin, un hook `PostToolUse` corre `audit.py` sobre cada
`.md` con frontmatter que Claude edite o cree, si hay un `pengu-seo.json`
hacia arriba. Con errores, el hook devuelve 2 y Claude ve el informe para
corregirlo antes de seguir; los avisos se muestran y no cortan. Un README
o una nota sin frontmatter no se auditan.

Sin plugin, el mismo hook se declara a mano en `~/.claude/settings.json`;
el encabezado de [`hooks/audit_on_save.py`](../../hooks/audit_on_save.py)
trae el bloque. El perfil sale de `pengu-seo.json` (`"profile": "nextjs"`),
así que el hook no necesita argumentos.

## Perfiles

Cada plataforma rompe cosas distintas, así que cada una tiene su perfil.

| Perfil | Frontmatter | Comprobaciones propias |
|---|---|---|
| `wordpress` | plugin ai-blog-bridge | Colisión de anchors, fuentes en frontmatter, portada por attachment_id |
| `nextjs` | colección markdown de Next.js | FAQ visible obligatoria, imágenes en disco |
| `canonical` | formato propio | Superset de los dos |

El perfil `nextjs` exige FAQ visible porque la plantilla típica emite el schema
desde el frontmatter sin pintar las preguntas. El chequeo de conversión aplica a
cualquier perfil en cuanto declarás `money_pages`.

## Configuración por sitio

Lo que cambia de un sitio a otro no está en el código. Va en un `pengu-seo.json`
en la raíz del proyecto, y el auditor lo busca desde la carpeta auditada hacia
arriba:

```json
{
  "sites": ["example.com"],
  "money_pages": ["/pricing", "/contact", "app.example.com"],
  "url_prefix": "/blog",
  "site_root": ".",
  "profile": "nextjs"
}
```

| Campo | Para qué |
|---|---|
| `profile` | Perfil por defecto (`wordpress`, `nextjs`, `canonical`). `--profile` manda si se pasa |
| `sites` | Dominios propios. Un enlace absoluto a ellos, o a un subdominio, cuenta como interno |
| `money_pages` | Páginas de conversión. Sin esto, `E-NO-CTA` queda apagado y el auditor lo avisa |
| `url_prefix` | Prefijo del blog, para detectar enlaces a posts que no existen |
| `site_root` | Raíz del sitio, para comprobar que las imágenes existen en disco |

Todo se puede pasar también por línea de comandos, y la línea de comandos manda:

```bash
python audit.py posts/ --profile wordpress --site example.com --money-page /contacto
```

Hay una plantilla en `pengu-seo.example.json`, en la raíz del repositorio.

## Qué comprueba

**Metadatos.** Título de 30 a 70 caracteres con la keyword completa, y
preferentemente en los primeros 40. Descripción de 120 a 160, ideal 140, con la
keyword. Keyword sin puntuación.

**Contenido.** Keyword completa en el primer párrafo. Sin H1 en el cuerpo. De 3
a 12 H2. La keyword entera en algún H2. Sin H3 huérfanos. Mínimo 300 palabras,
objetivo 900. Densidad por debajo del 2,5%.

**Extracción.** Al menos una señal semántica. Listas o tablas. FAQ o
encabezados en pregunta. FAQ visible si hay schema de FAQ.

**Enlaces.** De 3 a 12 internos. Al menos un camino de conversión cuando el
perfil lo declara. Al menos una cita externa, en el cuerpo o en `sources`.
Anchors repetidos como máximo dos veces. Sin anchors vacíos tipo "aquí". Un
enlace por bloque.

**Imágenes.** Portada con alt. Alt en todas las imágenes. Existencia real del
archivo con `--site-root`.

**URL.** Menos de 100 caracteres, máximo dos directorios, sin mayúsculas ni
guiones bajos, compartiendo alguna palabra con la keyword.

**Frescura y autoría.** Fecha de actualización. Ningún año anterior al actual
en el título o la descripción. Autor con enlace o biografía.

**Estilo.** Sin guiones largos ni cortos, con números de línea. Sin marcadores
de plantilla. Sin aperturas de relleno.

La lista completa con umbrales está en
[`references/reglas.md`](references/reglas.md).

## Cómo leer el resultado

```
!! guia-regalos-corporativos.md  [78/100]
   ERROR  E-LINK-COLLISION  Dos anchors en el mismo párrafo: 'regalos corporativos', 'catálogo'.
          -> El inyector salta el bloque que ya tiene un enlace y el segundo
             desaparece sin avisar. Separalos en párrafos distintos.
```

**Los errores se arreglan antes de publicar.** Son cosas que rompen algo:
schema engañoso, enlaces que desaparecen, contenido delgado.

**Los avisos se arreglan cuando se pueda.** Restan pero no rompen.

**Las notas son mejoras.** Ignorarlas es una decisión válida.

El puntaje es 100 menos 12 por error, 4 por aviso y 1 por nota. No es una nota
académica, es un orden de trabajo: los archivos salen ordenados de peor a
mejor, así que se empieza por arriba.

Cada hallazgo trae `-> ` con la corrección concreta. Si no la trae, el mensaje
ya la contiene.

## Enganchar al build

Que la puerta se cierre sola:

```json
{
  "scripts": {
    "audit": "python skills/pengu-audit/scripts/audit.py src/content/blog --profile nextjs --site-root .",
    "prebuild": "npm run audit"
  }
}
```

Con eso, un post con errores no llega a producción. Es la diferencia entre una
regla y una garantía.

## Códigos de site_check.py

| Código | Nivel | Qué significa |
|---|---|---|
| `ROBOTS-MISSING` / `ROBOTS-BLOCKS-ALL` | ERROR | Sin robots.txt, o bloquea todo |
| `ROBOTS-NO-SITEMAP` / `ROBOTS-DASH` | aviso | Sin línea Sitemap, guion largo |
| `HOST-NO-REDIRECT` | ERROR | Una variante del host no llega a la canónica |
| `HOST-CHAIN` / `HOST-TEMP-REDIRECT` | aviso | Más de un salto, o 302 |
| `SITEMAP-MISSING` / `SITEMAP-DUPLICATE` | ERROR / aviso | |
| `URL-STATUS` / `SITEMAP-REDIRECT` | ERROR | La URL del sitemap no responde 200 directa |
| `NOINDEX-IN-SITEMAP` / `CANONICAL-OTHER` | ERROR | Señales contradictorias |
| `H1-MISSING` / `H1-MULTIPLE` / `H1-EMPTY` | ERROR | Un H1 con texto por página |
| `TITLE-DOUBLE-BRAND` | ERROR | La plantilla ya añade la marca |
| `TITLE-LONG` / `TITLE-SHORT` / `DESC-MISSING` / `H2-MISSING` | aviso | |
| `HEADING-SKIP` / `DESC-LEN` / `SITEMAP-NO-LASTMOD` | nota | |

## Añadir una comprobación

Los umbrales son constantes al principio de `audit.py`. Cambiarlos ahí los
cambia en todos los perfiles a la vez.

Para una comprobación nueva, añadila dentro de `audit_file` con
`report.error()`, `report.warn()` o `report.note()`, con un código propio y un
mensaje que **diga cómo arreglarlo**, no solo qué está mal.

Un hallazgo sin corrección concreta se ignora, y un informe que se ignora es
peor que no tenerlo.
