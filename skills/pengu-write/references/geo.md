# Escribir para que te citen

Optimizar para ChatGPT, Perplexity, Claude, Gemini y los AI Overviews de
Google. No es una disciplina aparte: es escribir de modo que un párrafo se
sostenga solo, fuera del artículo.

## Las dos competencias

El curso las separa bien, y la distinción cambia cómo se escribe.

**Ser LA respuesta.** Para preguntas con una respuesta objetiva correcta ("qué
es el interés compuesto"), el buscador elige un fragmento y lo muestra. Compites
por ser ese fragmento. Se gana con una definición limpia, temprana y
estructurada.

**Ser UNA DE las fuentes.** Cuando el modelo decide que hay varias respuestas
válidas, no elige un fragmento: sintetiza una respuesta nueva con pedazos de
muchas fuentes y enlaza a las que usó. Se gana teniendo algo que las otras
fuentes no tienen.

La segunda está creciendo y es donde queda el margen. Un artículo profundo con
datos propios entra en muchas respuestas sintetizadas; un artículo genérico no
entra en ninguna.

## Lo que hace que un párrafo se pueda citar

Un modelo extrae fragmentos. Si el párrafo necesita el resto del artículo para
entenderse, no se puede extraer.

**No citable:**

> Como vimos antes, esto depende mucho del caso, aunque en general suele
> convenir la primera opción que mencionamos.

**Citable:**

> La serigrafía conviene a partir de unas 25 piezas. El costo está en preparar
> la pantalla, no en imprimir, así que el precio por unidad baja rápido con la
> cantidad.

Cuatro propiedades: se entiende solo, contiene el sujeto (no "esto"), da un
número y explica el mecanismo.

Prueba rápida: copiá cualquier párrafo, pegalo fuera del artículo y leelo. Si
hay que volver a buscar contexto, reescribilo.

## Señales semánticas

Frases que marcan un párrafo como respuesta. El auditor exige al menos una:

```
en resumen          errores comunes      paso 1
punto clave         por ejemplo          en conclusión
lo más importante   la respuesta corta   en pocas palabras
```

La forma natural de cumplirlo, sin que suene forzado, es una sección "Errores
comunes al..." y un cierre que abra con "En resumen:". Las dos son buenas ideas
por sí mismas; que además sean señales es un extra.

## Ganancia de información

Es el concepto que más importa y el peor entendido.

Un modelo no cita lo que puede deducir de otras cinco fuentes. Cita **lo que
solo vos tenés**. Si tu artículo repite lo que ya dicen los tres primeros
resultados, no hay razón para incluirte.

Qué cuenta como información propia:

- Un número que sacaste de tu propia operación
- El umbral donde cambia la respuesta, medido, no estimado
- Un fallo que viste repetirse y su causa
- Una comparación que nadie hizo
- Una captura de tu propio proceso

Qué no cuenta:

- Reformular la definición de Wikipedia
- Una lista de ventajas y desventajas genéricas
- Estadísticas de otro artículo sin verificar

Regla práctica: **si podrías haber escrito el artículo sin trabajar en el
sector, no aporta nada.**

## Estructura extraíble

| Formato | Cómo se extrae |
|---|---|
| Tabla | Muy bien. Filas y columnas se leen como datos |
| Lista numerada | Muy bien para procesos |
| Pregunta como H2 con respuesta debajo | Lo mejor para respuestas directas |
| Párrafo corto que abre respondiendo | Bien |
| Párrafo largo con la conclusión al final | Mal |
| Prosa con referencias a otras secciones | No se extrae |

Una tabla de seis filas se cita mejor que los tres párrafos que dirían lo
mismo.

## Preguntas reales

Las preguntas del FAQ salen del `people_also_ask` de la SERP, que trae
`pengu-keywords`, no de la imaginación.

- Escribí la pregunta como la escribe la gente, con sus palabras
- Respondé en la primera frase, ampliá después
- De 40 a 90 palabras por respuesta: menos no dice nada, más no se extrae
- Texto plano, sin enlaces markdown dentro del YAML, que rompe el parseo

## Autoridad verificable

Lo que hace que te traten como fuente y no como opinión:

- **Autor con nombre y enlace.** Un `Person` sin URL no es una entidad
  verificable.
- **Fecha de actualización.** Sin `dateModified`, cada revisión que hagas es
  invisible.
- **Fuentes externas reales.** Enlazar a una fuente sólida no te resta tráfico,
  te sitúa en su vecindario.
- **Coherencia entre artículos.** Diez artículos sobre el mismo tema pesan más
  que cincuenta sobre temas dispersos.

## Acceso de los rastreadores

De poco sirve escribir bien si el rastreador no entra. En `robots.txt`:

```
User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-User
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /
```

`Claude-Web` y `anthropic-ai` son nombres antiguos. El actual es `ClaudeBot`.
Un `robots.txt` que solo permite los viejos deja fuera al rastreador que
importa.

Un `llms.txt` en la raíz, con la descripción del sitio y el índice de
contenidos, ayuda a que un modelo entienda de qué va el sitio sin rastrearlo
entero.

## Lo que no funciona

- Repetir la keyword. La densidad alta se lee como relleno.
- Marcado schema de contenido que no está visible en la página. Google lo
  trata como engañoso, y el auditor lo marca como error.
- Bloques de "citation capsule" o etiquetas de plantilla. Se notan.
- Publicar mucho y flojo. Diez artículos buenos superan a cincuenta genéricos,
  y además no diluyen la autoridad del dominio.
