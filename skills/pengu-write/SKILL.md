---
name: pengu-write
description: >-
  Escribe posts de blog en un formato canónico y los renderiza al formato de
  WordPress (plugin ai-blog-bridge) o Next.js (colección markdown), inyectando
  enlaces internos, FAQ visible, puntos clave y fuentes según lo que cada
  plataforma sepa renderizar sola. Usa esta skill cuando el usuario pida
  escribir o reescribir un artículo, publicar contenido, o adaptar un post de
  una plataforma a otra.
user-invocable: true
argument-hint: "[tema o keyword] [--to wordpress|nextjs]"
license: MIT
metadata:
  author: Christian Monge
  version: "1.0.0"
---

# Pengu Write

Se escribe una vez, en formato canónico. El renderizador lo lleva a cada
plataforma añadiendo solo lo que esa plataforma no sabe hacer sola.

## Antes de escribir

1. **Confirmá la keyword.** Si no viene de
   [`pengu-keywords`](../pengu-keywords/SKILL.md), pasá por ahí. Escribir sin
   confirmar el tipo de SERP es la forma más cara de perder un día.
2. **Leé `BRAND.md` y `VOICE.md`** del proyecto destino si existen. Mandan
   sobre esta skill.
3. **Mirá el `people_also_ask`** de la SERP. Esas son las preguntas reales de
   la gente y son material directo para H2 y FAQ.
4. **Leé los tres primeros resultados.** No para copiarlos: para encontrar qué
   no dicen. Si tu artículo dice lo mismo que ellos, no hay razón para que
   Google te suba por encima.

## Escribir

Copiá [`examples/ejemplo-canonico.md`](../pengu-seo/examples/ejemplo-canonico.md) y
trabajá encima. Da 100/100 en la auditoría, así que arranca desde un formato
correcto.

El contrato de campos está en
[`schema/post.schema.md`](../pengu-seo/schema/post.schema.md).

### Estructura que funciona

Sale del curso de SEO y del material del máster, y está en
[`references/estructura.md`](references/estructura.md).

```
Párrafo 1     La respuesta, con la keyword completa dentro. Sin contexto previo
Párrafo 2     Por qué importa, en una o dos frases
Párrafo 3     Qué cubre la guía

## Keyword completa + el ángulo         <- H2 con la keyword entera
## Un aspecto concreto                   tabla o lista
## Otro aspecto
## Errores comunes al ...                <- señal semántica, y es lo más leído
## Cómo hacerlo paso a paso              <- pasos numerados
Cierre que abra con "En resumen:"        <- lo que un modelo levanta para citar
```

Entre 5 y 8 H2 propios. El renderizador de WordPress añade "Preguntas
frecuentes" y "Fuentes", así que 6 propios son 8 publicados.

### Las reglas duras

Todas están en el auditor. No hace falta recordarlas, pero entenderlas ahorra
correcciones.

| Regla | Umbral | Por qué |
|---|---|---|
| Keyword completa en el título | obligatoria | La comparación es literal, no por palabras sueltas |
| Título | 30 a 70 caracteres | Por encima Google lo corta |
| Descripción | 120 a 160, ideal 140 | El curso es explícito con el 140 |
| Keyword en el primer párrafo | obligatoria | Lo primero que se lee, humano o modelo |
| Keyword completa en un H2 | obligatoria | Es donde más falla la gente que escribe rápido |
| Sin H1 en el cuerpo | obligatoria | El H1 lo pone la plantilla |
| Extensión | 900 mínimo, 1400 objetivo | Por debajo de 300 es contenido delgado |
| Enlaces internos | 3 a 12 | Menos no reparte autoridad, más la diluye |
| Camino de conversión | al menos uno | Un post que solo enlaza a posts no factura |
| Cita externa | al menos una | E-E-A-T, y es lo que te vuelve fuente citable |
| Señal semántica | al menos una | Lo que un modelo levanta para citarte |

### La trampa de la keyword en el H2

El chequeo busca la **cadena entera**. Un H2 que diga "¿Sobre qué materiales
funciona el DTF textil?" **no** satisface la keyword `que es dtf textil`. Hay
que escribir "Qué es DTF textil y cómo funciona".

Es el fallo más frecuente y el más fácil de arreglar. El resto de trampas
conocidas están en [`references/trampas.md`](references/trampas.md).

### Estilo

En [`references/estilo.md`](references/estilo.md). Lo esencial:

- **Sin guiones largos ni cortos**, en ninguna parte del archivo.
- **Sin precios ni rangos de precio** si no los vas a sostener.
- Frases cortas, voz activa, segunda persona para el lector.
- Nada de aperturas de contexto. La respuesta va en la primera línea.
- Nada de superlativos sin prueba.
- Los números y las tablas ganan a los adjetivos.

## Renderizar

```bash
cd skills/pengu-write/scripts

python render.py post.md --to wordpress --out ../../../posts/post.md
python render.py post.md --to nextjs   --out ../landing/src/content/blog/post.md
python render.py post.md --to markdown --dry-run
```

Qué hace cada destino:

| | WordPress | Next.js |
|---|---|---|
| Enlaces internos | los inyecta el plugin | los inyecta el renderizador |
| FAQ | lo renderiza el plugin | se escribe visible en el cuerpo |
| Puntos clave | los renderiza el plugin | se escriben en el cuerpo |
| Fuentes | las renderiza el plugin | se escriben en el cuerpo |
| Índice | lo genera el plugin | lo genera la plantilla |

La asimetría no es un capricho. La plantilla de Next.js emite `FAQPage` JSON-LD
desde el frontmatter pero **no renderiza esas preguntas en la página**. Marcado
sin contenido visible es marcado engañoso según Google, así que el renderizador
escribe la sección para que coincidan.

### Enlaces sin colocar

Si el renderizador avisa de anchors sin colocar, es porque ese texto no aparece
en ningún párrafo libre. Dos causas:

- El anchor no está escrito en el cuerpo. Escribilo o quitalo de
  `internal_links`.
- Está en un párrafo que ya tiene otro enlace. **Un bloque, un enlace.** El
  segundo se pierde en silencio. Separalos en párrafos distintos.

Esta regla se replica en las dos plataformas a propósito: si solo existiera en
WordPress, el mismo post pasaría la auditoría en Next.js y perdería enlaces al
migrarlo.

## Después de escribir

```bash
python ../../pengu-audit/scripts/audit.py post.md --profile canonical
```

**Tiene que dar PASA antes de renderizar.** Después de renderizar, auditá otra
vez con el perfil de la plataforma: cada una rompe cosas distintas.

## Vídeo

Solo cuando el tema es explicativo. Para encontrar el vídeo en español más
visto y embebible sobre un tema:

```bash
YTKEY=tu-clave python scripts/fetch_videos.py "que es serigrafia"
```

Ordena por vistas reales, no por la relevancia de YouTube, y descarta los que
no se pueden embeber. La clave es de YouTube Data API v3 y se lee de la
variable de entorno, nunca del código.

## Optimizar para buscadores de IA

No es una disciplina aparte, es escribir para que un párrafo se pueda extraer
sin el resto del artículo. En
[`references/geo.md`](references/geo.md). Lo que más rinde:

- Cada H2 empieza respondiendo. El contexto va después.
- Una señal semántica por artículo, mínimo. "En resumen:", "Errores comunes",
  "Paso 1".
- Datos propios. Un modelo cita lo que no puede deducir de otras cinco fuentes.
- Fuentes reales con enlace. Sin ellas sos una opinión.
- Tablas. Se extraen mucho mejor que la prosa equivalente.
