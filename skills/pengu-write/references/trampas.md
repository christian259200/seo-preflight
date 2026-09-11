# Trampas conocidas

Cada una costó tiempo real en producción. Están aquí para que no lo cuesten dos
veces. Las que se pueden detectar están en el auditor.

## Dos anchors en el mismo párrafo

**La más cara y la más silenciosa.**

El inyector de enlaces, tanto el del plugin de WordPress como el de
`render.py`, salta cualquier bloque que ya tenga un enlace. Si dos anchors caen
en el mismo párrafo, **solo se inyecta el primero y el segundo desaparece sin
error**.

Mal:

```markdown
Puedes revisar el catálogo y solicitar una cotización con las medidas.
```

Bien:

```markdown
Puedes revisar el catálogo por categoría para elegir el artículo.

Con las medidas y la cantidad, puedes solicitar una cotización.
```

Afectó a 8 de 15 posts en la primera tanda de un sitio en producción, y sigue apareciendo:
la auditoría actual encuentra 20 casos en 31 posts publicados. El auditor lo
marca como `E-LINK-COLLISION`. El renderizador avisa de los anchors que no pudo
colocar.

Ojo con las listas: un ítem de lista es un bloque. `**Se lo llevan:** bolsas de
tela, bolígrafos, llaveros` es un solo bloque, y si "bolsas de tela" y
"llaveros" son los dos anchors, se pierde uno.

## La keyword incompleta en el H2

El chequeo busca la **cadena entera**, no palabras sueltas.

Keyword: `que es dtf textil`

- "¿Sobre qué materiales funciona el DTF textil?" → **no cumple**
- "Qué es DTF textil y cómo funciona" → cumple

Pasa cuando se escribe rápido y el H2 sale natural pero desordenado. Es el
fallo más frecuente de todos.

## Puntuación dentro de la keyword

La comparación ignora acentos pero **no** puntuación. Si la keyword es
`banner manta o roll up` y el título dice "Banner, manta o roll up", la coma
rompe la coincidencia y el chequeo falla aunque a la vista esté bien.

Elegí keywords sin puntuación.

## Enlaces markdown dentro del YAML

Un `[texto](url)` dentro de una respuesta de FAQ en el frontmatter **rompe el
parseo del YAML** y tumba el build.

Mal:

```yaml
faq:
  - question: "¿Qué alternativas hay?"
    answer: "Puedes usar [Crayon](https://crayon.co) o Klue."
```

Las respuestas van en texto plano. `render.py` las limpia al convertir a
Next.js, pero en el canónico no deben estar. El auditor lo marca como
`E-FAQ-LINK`. Aparece en 2 de los 50 posts de la landing.

## Schema de FAQ sin FAQ visible

Si el frontmatter lleva `faqs` y la plantilla emite `FAQPage` JSON-LD, esas
preguntas **tienen que estar visibles en la página**. Marcado con contenido que
el usuario no ve es marcado engañoso según las guías de Google.

Pasa cuando la plantilla emite el schema desde el frontmatter pero no renderiza
la sección, que es exactamente lo que hace la landing de Pengu. Tres posts
afectados. El auditor lo marca como `E-FAQ-INVISIBLE` en el perfil `nextjs`.

O escribís la sección visible, o quitás el FAQ del frontmatter.

## El post que solo enlaza a otros posts

Un artículo que cierra con "Where to go next" y manda a tres artículos más es
tráfico que no factura nunca. **45 de 50 posts de la landing no tenían ni un
enlace a la aplicación**, con la regla escrita en tres documentos distintos.

Todo post lleva al menos un camino de conversión, dentro del cuerpo y no solo
al final. El auditor lo marca como `E-NO-CTA` cuando el perfil declara páginas
de conversión.

## Publicar en tandas

El alojamiento compartido limita ráfagas. En la primera tanda de 15 posts, 5
devolvieron una página HTML de error en vez de JSON. Uno de ellos ya existía, lo
que probó que no era el contenido.

Publicá de uno en uno, con pausa:

```bash
for f in posts/*.md; do python publish.py "$f"; sleep 20; done
```

## El slug del zip tiene que coincidir con la carpeta instalada

Si el paquete se arma con un nombre de carpeta distinto al de la instalación,
WordPress instala **una segunda copia al lado de la que está corriendo**. Dos
copias activas redeclaran las mismas clases y tumban el sitio.

El nombre del proyecto no es necesariamente el slug instalado. Comprobalo antes
de empaquetar.

## La caché del sitemap

Rank Math cachea `post-sitemap.xml` y **no lo invalida cuando se publica por la
API REST**. Podés tener 31 posts publicados y un sitemap que muestra 4.

Después de una tanda, limpiá la caché del sitemap a mano en los ajustes del
plugin de SEO.

## Selectores CSS compuestos que no existen

`.content-page.sidebar-position-right` exige que **las dos clases estén en el
mismo elemento**. Si el marcado real es `.content-page > .sidebar-position-right`,
el selector no coincide con nada y falla en silencio.

Verificá el marcado real en el navegador antes de escribir el selector. Adivinar
nombres de clase cuesta más que abrir el inspector.

## La consola de Windows y los acentos

`cp1252` destroza los acentos de cualquier informe. "catálogo" sale como
"cat?logo" justo cuando hay que leerlo.

Los scripts hacen `sys.stdout.reconfigure(encoding="utf-8")`. Y no reemplaces
`sys.stdout` por un `TextIOWrapper` nuevo: al recolectarse el objeto original se
cierra el buffer y el siguiente `print` lanza `ValueError: I/O operation on
closed file`.

## Los ejemplos de la documentación también fallan

El ejemplo canónico de este mismo proyecto no pasó la auditoría a la primera:
la keyword era `que es la serigrafia` y el cuerpo empezaba con "La serigrafía
es una técnica...". La cadena completa no aparecía en ningún sitio.

Si escribís un ejemplo, auditalo. Un ejemplo que no cumple sus propias reglas
enseña a incumplirlas.
