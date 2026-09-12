# Lo que Google cambió y toca a estas skills

Registro con fecha. Cada entrada cita una página de Google, no un blog que la
comenta. Si una regla del auditor o un consejo de las referencias contradice
una entrada de aquí, manda la entrada. Cuando se añade una, se revisa la regla.

La idea del registro, y la disciplina de exigir fuente de Google para cada
línea, viene de `data/google-updates.json` de claude-seo (MIT).

Última revisión: 2026-09-12.

| Fecha | Qué | Fuente | Qué cambia aquí |
|---|---|---|---|
| 2026-06-29 | Guía de optimización para funciones de IA generativa. No hace falta ningún archivo nuevo, ni marcado especial, ni versión en Markdown, ni trocear el contenido, ni escribir "para la IA". **Google Search ignora `llms.txt`.** El schema no es requisito para aparecer en respuestas generativas. | developers.google.com/search/docs/fundamentals/ai-optimization-guide | `site_check.py` baja `LLMS-TXT-MISSING` a nota. `geo.md` deja de vender `llms.txt` como palanca de citas. Las reglas de extracción (párrafo autónomo, pregunta como H2, respuesta primero) siguen: son las que Google describe como "lo mismo que el SEO de siempre". |
| 2026-05-15 | Políticas de spam: el abuso de contenido a escala nombra ya "usar herramientas de IA generativa para producir muchas páginas sin aportar valor", y las transformaciones automáticas como traducir en masa. | developers.google.com/search/docs/essentials/spam-policies | Refuerza `W-AI-PHRASE`, `E-AI-MARKER` y la regla de ganancia de información de `geo.md`. Diez posts con dato propio valen más que cincuenta genéricos, y ahora además es política. |
| 2026-05-07 | **Los resultados enriquecidos de FAQ dejan de mostrarse para cualquier sitio.** Supera la restricción de 2023 a sitios de gobierno y salud. La documentación de FAQPage se retiró el 2026-06-15. | developers.google.com/search/docs/appearance/structured-data/faqpage (registro de cambios) | `FAQPage` JSON-LD no da nada en la SERP de Google. `E-FAQ-INVISIBLE` se mantiene: si la plantilla emite el schema, el contenido tiene que verse (marcado engañoso). La FAQ visible sigue valiendo por sí misma: es lo que extraen las respuestas de IA y los fragmentos destacados. No se recomienda añadir `FAQPage` nuevo por Google. |
| 2024-03-12 | INP sustituye a FID como Core Web Vital. | web.dev/blog/inp-cwv-march-12 | Cualquier referencia a FID está desactualizada. `site_check.py` no mide CWV; si se añade, es INP. |
| 2023-09-14 | `HowTo` deja de mostrarse como resultado enriquecido. | developers.google.com/search/docs/appearance/structured-data/how-to | No recomendar schema `HowTo` en ningún perfil. |

## Cómo se añade una entrada

1. Encontrar la página de Google que lo dice. Un artículo de Search Engine
   Land no vale como fuente; vale como pista para encontrar la de Google.
2. Escribir la fila con fecha, resumen de una frase, URL y qué regla cambia.
3. Cambiar la regla en el mismo commit. Una entrada sin cambio de regla es
   una nota, no una entrada.
