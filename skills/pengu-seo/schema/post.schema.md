# Formato canónico de un post

El contrato entre las tres skills. Se escribe una vez en este formato y
`render.py` lo lleva a cada plataforma.

Es un superset: contiene todo lo que WordPress y Next.js necesitan, más lo que
haría falta para un CMS nuevo. Los campos que el destino no entiende se ignoran,
no se pierden.

## Campos

### Obligatorios

| Campo | Tipo | Notas |
|---|---|---|
| `title` | texto | De 30 a 70 caracteres, con la keyword completa |
| `slug` | texto | Minúsculas y guiones, menos de 100 caracteres |
| `focus_keyword` | texto | Sin puntuación. La comparación es literal |
| `description` | texto | De 120 a 160 caracteres, ideal 140, con la keyword |

### Recomendados

| Campo | Tipo | Notas |
|---|---|---|
| `meta_title` | texto | Si el título de la página y el de la SERP difieren |
| `excerpt` | texto | Resumen corto para tarjetas. Distinto de la descripción |
| `date` | fecha ISO | Publicación |
| `updated` | fecha ISO | Se convierte en `dateModified`. Sin esto, las revisiones son invisibles |
| `status` | `publish` o `draft` | En Next.js se traduce a `draft: true/false` |
| `categories` | lista | Textos o `{title, slug}` |
| `tags` | lista | Solo texto |
| `toc` | booleano | Índice |

### Autoría

```yaml
byline:
  name: "Christian Monge"
  url: https://www.linkedin.com/in/...
  bio: "Una frase que explique por qué esta persona sabe del tema."
```

La `url` importa: un `Person` sin enlace no es una entidad verificable.

### Portada

```yaml
hero:
  path: /blog/mi-slug/hero.png
  alt: "Descripción real de lo que se ve, no la keyword repetida"
```

En WordPress también sirve `attachment_id` si la imagen ya está subida. En ese
caso el alt vive en la biblioteca de medios.

### Puntos clave

```yaml
key_takeaways:
  - "Cada punto se sostiene solo, fuera del artículo."
  - "De tres a cinco. Más deja de ser un resumen."
```

WordPress los renderiza en una caja. En Next.js `render.py` los escribe como una
sección visible.

### Enlaces internos

```yaml
internal_links:
  - anchor: "vinil textil"
    url: https://ejemplo.com/que-es-el-vinil-textil/
    title: "Qué es el vinil textil"
```

El `anchor` **tiene que aparecer literalmente en el cuerpo**, en un párrafo que
no tenga ya otro enlace. Si no, se pierde en silencio en WordPress y
`render.py` avisa al convertir.

De tres a doce. Al menos uno lleva a una página de conversión.

### FAQ

```yaml
faq:
  - question: "¿A partir de cuántas piezas conviene?"
    answer: "Alrededor de 25. El costo está en preparar la pantalla, no en imprimir."
```

- Preguntas sacadas del `people_also_ask` real, no inventadas
- Respuestas de 40 a 90 palabras
- **Texto plano.** Un enlace markdown aquí rompe el parseo del YAML
- Se emiten como `FAQPage` JSON-LD y se escriben visibles en la página

### Fuentes

```yaml
sources:
  - title: "Screen printing, Encyclopaedia Britannica"
    url: https://www.britannica.com/technology/screen-printing
```

Al menos una. Verificá que el dato esté realmente ahí antes de publicar.

### Vídeo

```yaml
video:
  url: https://www.youtube.com/watch?v=XXXX
  title: "Qué muestra el vídeo"
```

Solo cuando el tema es explicativo. Uno por artículo.

### Tooltips

```yaml
tooltips:
  https://www.ama.org/: "American Marketing Association"
```

Específico de WordPress. Añade `title` a los enlaces externos.

## El cuerpo

Markdown, empezando en `##`. **Nunca un `#`**: el H1 lo pone la plantilla desde
el título.

No escribas a mano el índice, la sección de FAQ, la de fuentes ni la caja de
puntos clave. Salen del frontmatter, y escribirlos dos veces los desincroniza.

## Ejemplo completo

[`examples/ejemplo-canonico.md`](../examples/ejemplo-canonico.md), verificado
con 100/100 en la auditoría. Sirve de plantilla.

## Qué hace cada destino

| Campo | WordPress | Next.js |
|---|---|---|
| `title` | `title` | `title` y `seo.metaTitle` |
| `description` | `description` | `seo.metaDescription` |
| `focus_keyword` | `focus_keyword` | `focus_keyword` |
| `hero` | `featured_image` | `mainImage` |
| `byline` | `byline` | `author` con imagen por defecto |
| `date` | `date` | `publishedAt` en ISO con Z |
| `updated` | `updated` | `updatedAt` |
| `status` | `status` | `draft` invertido |
| `key_takeaways` | frontmatter, lo pinta el plugin | sección visible en el cuerpo |
| `internal_links` | frontmatter, los inyecta el plugin | inyectados en el cuerpo |
| `faq` | frontmatter, lo pinta el plugin | `faqs` para el JSON-LD **y** sección visible |
| `sources` | frontmatter, lo pinta el plugin | sección visible en el cuerpo |

La asimetría refleja lo que cada plataforma sabe hacer sola. WordPress tiene un
plugin que renderiza; la plantilla de Next.js no, así que el renderizador
escribe en el cuerpo lo que allá es automático.

## Añadir una plataforma

1. Escribí `to_<plataforma>(meta, body, lang)` en `render.py`, devolviendo
   `(frontmatter, cuerpo, enlaces_sin_colocar)`.
2. Añadí el perfil en `PROFILES` de `audit.py`, mapeando dónde vive cada campo
   y declarando `money_pages` y `faq_needs_visible`.
3. Registrá el nombre en el `--to` del argparse.

Lo que decide el trabajo es una pregunta: **¿qué renderiza la plataforma sola y
qué hay que escribir en el cuerpo?** Todo lo que no renderice sola, lo escribe
el adaptador.
