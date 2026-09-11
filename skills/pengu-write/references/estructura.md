# Estructura de un post

La plantilla que produce artículos que rankean y que se pueden citar. No es la
única que funciona, pero es la que pasa la auditoría sin esfuerzo.

## El esqueleto

```
[frontmatter]

Párrafo 1   La respuesta, con la keyword completa dentro.
Párrafo 2   Por qué importa, una o dos frases.
Párrafo 3   Qué cubre la guía.

## [keyword completa] + ángulo
    Respuesta primero. Después el detalle.
    Tabla o lista.

## [aspecto concreto 1]
## [aspecto concreto 2]
## [comparación o cuándo no conviene]

## Errores comunes al [hacer X]
    Cinco o seis, cada uno en negrita seguido de la explicación.

## Cómo [hacerlo] paso a paso
    Pasos numerados, uno por decisión.

Cierre que abre con "En resumen:"
Enlaces de cierre, uno por párrafo.
```

## Las tres primeras frases

Es lo que más cambia el resultado y lo que peor se hace.

**Mal:**

> En el mundo actual del marketing digital, las empresas buscan constantemente
> formas de destacar. Una de las técnicas más antiguas y confiables es la
> serigrafía, que ha acompañado a la industria durante décadas.

Cincuenta palabras y el lector sigue sin saber qué es. Un modelo de lenguaje
tampoco.

**Bien:**

> Qué es la serigrafía, en una línea: una técnica de estampado que empuja tinta
> a través de una malla tensada, usando una plantilla que bloquea las zonas que
> no deben imprimirse.

Responde, contiene la keyword completa y se puede citar sola.

La prueba: **si el primer párrafo, extraído del artículo, no responde nada, hay
que reescribirlo.**

## Los H2

Entre 5 y 8 propios. El renderizador añade "Preguntas frecuentes" y "Fuentes"
en WordPress, así que 6 propios son 8 publicados.

Reglas:

- **Uno lleva la keyword completa**, la cadena entera, no palabras sueltas.
- Cada H2 abre respondiendo. El contexto va después, si va.
- Al menos uno en forma de pregunta, o un FAQ.
- Descriptivos, no ingeniosos. "Cuánto dura y de qué depende" gana a
  "La prueba del tiempo".

Los H3 solo cuelgan de un H2. Un H3 antes del primer H2 rompe la jerarquía.

## Errores comunes

Es la sección con más lectura de casi cualquier artículo, y casi nadie la
escribe. Dos razones:

1. **Es lo que la gente busca de verdad.** Nadie quiere la teoría, quiere no
   equivocarse.
2. **Es una señal semántica reconocida.** Un modelo la levanta entera cuando
   alguien pregunta qué evitar.

Formato que funciona:

```markdown
**Mandar el logo en JPG.** La separación de colores necesita un vectorial.
Un JPG hay que redibujarlo y eso son horas.
```

Frase corta en negrita con el error, y una o dos frases con la consecuencia
concreta. Cinco o seis. Si se te ocurren diez, sobran cuatro.

## Tablas

Ganan a la prosa siempre que haya tres o más cosas comparables. Se leen mejor,
se extraen mejor y se citan mejor.

Cuándo usarlas:

- Comparar opciones por criterio
- Umbrales, plazos, cantidades
- Antes y después
- Qué usar según el caso

Cuándo no: cuando hay dos filas. Eso es una frase.

Cabeceras concretas. "Rendimiento" y "Nota" valen; "Aspecto 1" no.

## El cierre

Dos partes.

**El resumen.** Empieza literalmente con "En resumen:" y da la conclusión
accionable, no un repaso. Una o dos frases.

> En resumen: por debajo de 25 piezas o con muchos colores, mirá otras
> técnicas. Por encima, y con pocos colores, no hay nada más barato.

**Los enlaces de cierre.** Uno por párrafo, siempre. Dos anchors en el mismo
párrafo significa que el segundo se pierde.

```markdown
Si el pedido es de camisetas personalizadas, la tela cambia tanto el
resultado como la técnica.

Con la cantidad y el número de colores puedes solicitar una cotización.
```

El último enlace es el de conversión. Siempre hay uno.

## Extensión

| Palabras | Veredicto |
|---:|---|
| menos de 300 | Contenido delgado, error |
| 300 a 900 | Publicable, difícil que compita |
| 900 a 1.400 | La zona normal |
| 1.400 a 2.500 | Guía que compite en serio |
| más de 2.500 | Solo si cada sección aporta |

La extensión no es un objetivo, es una consecuencia. Un artículo de 1.400
palabras con relleno pierde contra uno de 900 sin él. Pero uno de 600 casi
nunca cubre un tema entero, y eso se nota.

## Vídeo

Solo cuando el tema es explicativo o el proceso se ve mejor de lo que se lee.

- Va después de la sección que explica el concepto, no al principio
- Con una frase que diga qué aporta, no "mira este video"
- Uno por artículo

Para comparativas de precios o listados de herramientas, ninguno.

## Imágenes

- La portada es obligatoria: es lo que se ve al compartir el enlace
- Alt descriptivo, nunca la keyword repetida
- El nombre del archivo también es una oportunidad
- Diagramas y capturas por encima de fotos de banco de imágenes

Una captura real de tu propio proceso vale más que la mejor foto de stock,
porque es lo único que la competencia no puede copiar.
