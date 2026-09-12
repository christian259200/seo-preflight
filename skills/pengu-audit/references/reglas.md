# Las reglas, una por una

Todo lo que comprueba `audit.py`, con el umbral, la severidad y el motivo. Los
umbrales son constantes al principio del script.

## Severidades

| Nivel | Peso | Criterio |
|---|---:|---|
| ERROR | -12 | Rompe algo: schema engañoso, enlaces perdidos, contenido delgado |
| WARN | -4 | Resta posiciones o conversión, no rompe nada |
| nota | -1 | Mejora. Ignorarla es una decisión válida |

## Keyword

| Código | Nivel | Umbral | Motivo |
|---|---|---|---|
| `E-KEYWORD` | ERROR | obligatoria | Sin keyword no hay nada que auditar ni que medir después |
| `W-KEYWORD-PUNT` | WARN | sin puntuación | La comparación es literal: una coma en el título rompe la coincidencia |
| `E-KW-ABSENT` | ERROR | aparece en el cuerpo | Si no está, el artículo no trata de lo que dice tratar |
| `W-STUFF` | WARN | densidad < 2,5% | Por encima se lee como relleno |

La comparación **ignora acentos** (`que es serigrafia` encuentra
`qué es serigrafía`) pero **no ignora puntuación**.

## Título

| Código | Nivel | Umbral | Motivo |
|---|---|---|---|
| `E-TITLE` | ERROR | existe | |
| `W-TITLE-LONG` | WARN | máximo 70 | El curso es explícito: por encima Google corta |
| `W-TITLE-SHORT` | WARN | mínimo 30 | Espacio gratis desperdiciado |
| `E-TITLE-KW` | ERROR | keyword completa | La cadena entera, no palabras sueltas |
| `N-TITLE-KW-POS` | nota | en los primeros 40 | Lo primero pesa más |

## Descripción

| Código | Nivel | Umbral | Motivo |
|---|---|---|---|
| `E-DESC` | ERROR | existe | Google la inventa y casi siempre elige peor |
| `W-DESC-LEN` | WARN | de 120 a 160, ideal 140 | 140 es lo que se muestra |
| `W-DESC-KW` | WARN | contiene la keyword | Google la resalta en negrita, sube el CTR |

## Contenido

| Código | Nivel | Umbral | Motivo |
|---|---|---|---|
| `E-EMPTY` | ERROR | cuerpo no vacío | |
| `W-FIRST-P` | WARN | keyword en el primer párrafo | La señal más barata que existe |
| `W-FLUFF` | WARN | sin aperturas de relleno | El primer párrafo es lo que se cita |
| `E-THIN` | ERROR | mínimo 300 palabras | Por debajo es contenido delgado |
| `W-SHORT` | WARN | objetivo 900, ideal 1.400 | |

## Encabezados

| Código | Nivel | Umbral | Motivo |
|---|---|---|---|
| `E-H1` | ERROR | ningún H1 en el cuerpo | El H1 lo pone la plantilla. Dos rompen la jerarquía |
| `E-H2-FEW` | ERROR | mínimo 3 H2 | Sin estructura no hay fragmentos extraíbles |
| `N-H2-MANY` | nota | máximo 12 H2 | Por encima el artículo pierde foco |
| `W-H2-KW` | WARN | keyword completa en un H2 | El fallo más frecuente al escribir rápido |
| `W-H3-ORPHAN` | WARN | ningún H3 antes del primer H2 | |

## Extracción

| Código | Nivel | Umbral | Motivo |
|---|---|---|---|
| `W-NO-CUE` | WARN | al menos una señal semántica | Lo que un modelo levanta para citarte |
| `W-NO-STRUCT` | WARN | una lista o una tabla | Un muro de párrafos no da fragmentos |
| `W-NO-QA` | WARN | FAQ o encabezado en pregunta | Alimenta fragmentos destacados |
| `E-FAQ-INVISIBLE` | ERROR | FAQ visible si hay schema | Marcado sin contenido visible es engañoso |
| `E-FAQ-LINK` | ERROR | respuestas en texto plano | Un enlace markdown rompe el YAML |

Señales reconocidas: `en resumen`, `en resumidas cuentas`, `lo más importante`,
`punto clave`, `paso 1`, `errores comunes`, `por ejemplo`, `en conclusión`,
`en pocas palabras`, `la respuesta corta`, `dicho de otro modo`, más sus
equivalentes en inglés.

Desde el 2026-05-07 Google no muestra resultados enriquecidos de FAQ para
ningún sitio, así que `FAQPage` JSON-LD ya no da nada en la SERP. La regla
no cambia: si la plantilla emite el schema, el contenido tiene que verse. Y
la FAQ visible vale por sí misma, porque es lo que extraen los fragmentos
destacados y las respuestas de IA. Registro con fuentes en
[`google-updates.md`](../../pengu-seo/references/google-updates.md).

`E-FAQ-INVISIBLE` solo aplica cuando el perfil declara
`faq_needs_visible: true`, que hoy es únicamente `nextjs`. En WordPress el
plugin renderiza el FAQ desde el frontmatter, así que el contenido siempre es
visible.

## Enlaces

| Código | Nivel | Umbral | Motivo |
|---|---|---|---|
| `E-NO-INTERNAL` | ERROR | al menos uno | Sin enlaces no reparte autoridad |
| `W-FEW-INTERNAL` | WARN | mínimo 3 | |
| `N-MANY-INTERNAL` | nota | máximo 12 | Más de doce diluyen el valor de cada uno |
| `E-NO-CTA` | ERROR | un camino de conversión | Un post que solo enlaza a posts no factura |
| `W-NO-CITE` | WARN | una cita externa | E-E-A-T, y te vuelve fuente citable |
| `N-ANCHOR-REPEAT` | nota | máximo 2 veces | |
| `N-ANCHOR-WEAK` | nota | sin "aquí", "leer más" | El anchor describe el destino |
| `E-LINK-COLLISION` | ERROR | un enlace por bloque | El segundo anchor se pierde en silencio |
| `W-LINK-404` | WARN | el post destino existe | Solo comprueba rutas del propio blog |

`E-NO-CTA` solo aplica cuando hay `money_pages` declaradas, en `pengu-seo.json`
o con `--money-page`. Sin ellas el auditor avisa al principio del informe de
que el chequeo está apagado, en vez de callarlo.

Un enlace cuenta como interno si es relativo, si apunta a uno de los `sites`
declarados o a un subdominio suyo, o si su host es una página de conversión
declarada por dominio (`app.example.com`). Una página de conversión declarada
por ruta (`/pricing`) solo cuenta en enlaces propios: `buffer.com/pricing` es
una cita externa, no tu página de precios.

Las imágenes **no** cuentan como enlaces. La expresión usa `(?<!!)` para
distinguir `[texto](url)` de `![alt](url)`; sin eso, cada imagen inflaba la
cuenta de enlaces internos y aparecía como enlace roto.

## Imágenes

| Código | Nivel | Umbral | Motivo |
|---|---|---|---|
| `W-NO-HERO` | WARN | portada presente | Es lo que se ve al compartir |
| `E-HERO-ALT` | ERROR | portada con alt | |
| `N-HERO-ALT-MEDIA` | nota | portada por attachment_id | El alt vive en la biblioteca de WordPress |
| `E-HERO-MISSING` | ERROR | el archivo existe | Requiere `--site-root` |
| `E-IMG-ALT` | ERROR | alt en toda imagen | Accesibilidad y búsqueda de imágenes |
| `N-IMG-ALT-STUFF` | nota | el alt no es solo la keyword | Describí la imagen |
| `E-IMG-MISSING` | ERROR | el archivo existe | Requiere `--site-root` |

## URL

| Código | Nivel | Umbral | Motivo |
|---|---|---|---|
| `N-URL-LONG` | nota | menos de 100 caracteres | Regla explícita del curso |
| `N-URL-DEEP` | nota | máximo 2 directorios | Regla explícita del curso |
| `W-URL-KW` | WARN | comparte palabra con la keyword | La URL sale en los resultados y sube el CTR |
| `W-URL-CHARS` | WARN | sin mayúsculas ni guion bajo | |

## Frescura y autoría

| Código | Nivel | Umbral | Motivo |
|---|---|---|---|
| `N-NO-UPDATED` | nota | fecha de actualización | Sin `dateModified` las revisiones son invisibles |
| `W-YEAR-STALE` | WARN | ningún año anterior al actual en título o descripción | Un año viejo en la SERP hunde el CTR aunque rankees |
| `N-SLUG-YEAR` | nota | año en el slug | No se cambia el slug; la próxima vez, sin año en la URL |
| `W-NO-AUTHOR` | WARN | autor presente | La parte más barata del E-E-A-T |
| `N-AUTHOR-THIN` | nota | autor con url o bio | Un Person sin enlace no es entidad verificable |

## Estilo

| Código | Nivel | Umbral | Motivo |
|---|---|---|---|
| `E-DASH` | ERROR | ningún guion largo ni corto | El rastro de IA más fácil de detectar |
| `E-AI-MARKER` | ERROR | sin marcadores de plantilla | |
| `W-AI-PHRASE` | WARN | sin muletillas de IA | Lo que un lector reconoce primero como texto generado |

`W-AI-PHRASE` busca una lista corta de frases que ningún redactor usa
hablando ("delve into", "tapestry of", "cabe destacar que", "un sinfín
de", "al siguiente nivel"). Es corta a propósito: cada entrada tiene que ser
rara en prosa humana, o el aviso se vuelve ruido. La lista está en
`AI_PHRASES`, en `audit.py`.

`E-DASH` da los números de línea. La comprobación cubre el archivo entero,
frontmatter incluido.

Los marcadores buscados son `[UNIQUE INSIGHT]`, `[CITATION CAPSULE]`,
`[PERSONAL EXPERIENCE]`, `[insert `, `[todo`, `[placeholder`, `lorem ipsum`,
`as an ai language model`, `as an ai assistant`, `como modelo de lenguaje`,
`como asistente de ia`, `[completar` y `tbd]`.

La cadena es `as an ai language model`, no `as an ai`: "treat the account as an
AI training system" es prosa legítima en un blog sobre inteligencia artificial,
y marcarla sería un falso positivo.

## Lo que no comprueba

Decirlo importa. El auditor no sabe nada de:

- **Si el contenido es bueno.** Mide forma, no fondo. Un artículo vacío bien
  estructurado saca 100.
- **Si las estadísticas son ciertas.** Comprueba que haya fuentes, no que
  digan lo que decís. Eso se verifica abriendo cada enlace.
- **Canibalización.** Está en `pengu-keywords`, que compara contra el contenido
  publicado.
- **Rendimiento y Core Web Vitals.** Es del sitio, no del markdown.
- **Si la keyword se puede ganar.** Está en `pengu-keywords`.

Un 100/100 significa que no hay defectos mecánicos. No significa que el
artículo merezca rankear.
