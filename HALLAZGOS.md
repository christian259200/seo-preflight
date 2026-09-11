# Hallazgos: qué encuentra esto en contenido real

Este documento existe por una razón: un auditor de SEO se juzga por lo que
encuentra, no por lo que promete. Aquí está todo lo que estas herramientas
detectaron en dos sitios en producción, con el conteo real y el motivo por el
que cada cosa importa.

Los sitios se describen sin nombrarlos. Lo que interesa es el patrón, no de
quién es el dominio.

- **Sitio A**: WordPress, 38 artículos, español, publicados con un plugin propio
- **Sitio B**: Next.js con markdown en archivos, 50 artículos, inglés

---

## Resumen

| Defecto | Sitio A | Sitio B | Severidad |
|---|---:|---:|---|
| Dos anchors en un mismo párrafo, el segundo se pierde | 20 de 31 | no aplica | error |
| Anchor declarado que no existe en el cuerpo | 4 de 7 | no aplica | error |
| Posts sin ningún camino de conversión | 0 | 29 de 50 | error |
| Sin focus keyword declarada | 0 | 50 de 50 | error |
| Guiones largos, prohibidos por escrito en tres documentos | 0 | 7 | error |
| Schema FAQPage sin FAQ visible en la página | 0 | 3 | error |
| Enlace markdown dentro del YAML, rompe el build | 0 | 2 | error |
| `BlogPosting` emitido dos veces en la misma página | todas | 0 | error |
| El único H1 de la página está en `display: none` | todas | 0 | error |
| Sin fecha de modificación en el schema | todas | todas | nota |

---

## Los que más sorprenden

### La regla escrita que nadie cumple

En el sitio B, la regla "todo artículo enlaza a la aplicación" estaba escrita en
tres documentos distintos del repositorio, incluido el archivo de contexto que
lee el agente antes de escribir.

**45 de 50 artículos publicados no la cumplían.**

Nadie lo sabía porque nada lo comprobaba. Los artículos cerraban con una sección
de "a dónde ir después" que enviaba a otros tres artículos. El lector recorría
el embudo entero y salía a más contenido.

Es el hallazgo que justifica el proyecto: una regla escrita se incumple, y se
incumple en silencio.

### El enlace que desaparece sin error

El inyector de enlaces internos salta cualquier párrafo que ya contenga un
enlace. Si dos anchors caen en el mismo bloque, **solo se inyecta el primero**.
No hay error, no hay aviso, el post se publica y tiene un enlace menos.

Un ítem de lista es un bloque. Esta línea pierde uno de los dos:

```markdown
**Se lo llevan:** bolsas de tela, bolígrafos, libretas pequeñas, llaveros.
```

20 de 31 artículos publicados tenían este defecto.

### El anchor que no existe

Variante del anterior, descubierta publicando. El frontmatter declara un anchor,
el inyector lo busca en el cuerpo y no lo encuentra porque durante la edición la
frase cambió. El enlace nunca aparece.

Apareció en 4 de los 7 artículos de la última tanda. **Dos se detectaron después
de publicar**, lo que llevó a añadir el chequeo `E-ANCHOR-MISSING`. En la misma
corrida, ese chequeo nuevo encontró los otros dos antes de publicar.

Es el mejor ejemplo de por qué un auditor tiene que ejecutarse: la regla ya
estaba documentada y aun así se incumplió cuatro veces seguidas.

### El H1 invisible

En el sitio A, cada artículo tiene exactamente un H1 y está oculto:

```html
<h1 class="title">Título del artículo</h1>      <!-- display: none -->
<h2 class="entry-title">Título del artículo</h2> <!-- este es el que se ve -->
```

La causa es una regla del propio CSS del plugin, que oculta el banner de migas
de pan para limpiar el diseño. Dentro de ese banner vive el único H1.

Google descarta el texto en `display: none`, así que en la práctica esas páginas
no tienen H1 y la jerarquía visible empieza en H2.

Este defecto no lo detecta el auditor de markdown: vive en la plantilla, no en
el contenido. Se encontró inspeccionando el DOM en el navegador. Vale la pena
decirlo, porque marca el límite de la herramienta.

### El schema duplicado

Verificado en el navegador sobre una página publicada:

```
script 1 (plugin SEO): Organization + WebSite + WebPage + Person + BlogPosting
script 2 (plugin de publicación): BlogPosting + FAQPage
```

**Dos `BlogPosting` para la misma URL.** Cada uno declara autor, fecha e imagen
por su cuenta, y si difieren en algo, Google elige y no avisa cuál.

Lo correcto es detectar que ya hay un plugin de SEO emitiendo `BlogPosting` y
publicar solo lo que falta, que en este caso es el `FAQPage`.

### El marcado que el usuario no ve

En el sitio B, tres artículos declaraban preguntas frecuentes en el frontmatter.
La plantilla las convertía en `FAQPage` JSON-LD, pero **no las renderizaba en la
página**.

Marcado estructurado que describe contenido invisible es marcado engañoso según
las guías de Google. Aquí no fue malicioso, fue una plantilla a medio hacer, y el
resultado es el mismo.

---

## Falsos positivos que hubo que corregir

Un auditor que grita de más se ignora, y un auditor ignorado no sirve para nada.
Estos aparecieron en las primeras pasadas y están corregidos.

| Falso positivo | Por qué era falso | Corrección |
|---|---|---|
| Portada sin `alt` | El `alt` vive en la biblioteca de medios cuando se referencia por `attachment_id` | Pasó a nota, no error |
| Sin citas externas | Las fuentes venían declaradas en el frontmatter, no en el cuerpo | Se cuentan las dos formas |
| 22 enlaces internos rotos | Eran imágenes: `![alt](/ruta.png)` contaba como enlace | La expresión pasó a llevar `(?<!!)` |
| Marcador de IA `as an ai` | "treat the account as an AI training system" es prosa legítima | La cadena buscada pasó a ser `as an ai language model` |
| Keyword ausente del primer párrafo | El renderizador antepone la caja de puntos clave, que también es respuesta | Se miran las primeras 120 palabras del cuerpo, no el primer bloque |

El de las imágenes es el más instructivo: no solo generaba ruido, además inflaba
la cuenta de enlaces internos, así que artículos sin enlaces reales pasaban el
chequeo.

---

## Lo que el auditor no ve

Decirlo importa tanto como la lista de hallazgos.

- **Si el contenido es bueno.** Mide forma, no fondo. Un artículo vacío pero bien
  estructurado saca 100.
- **Si las estadísticas son ciertas.** Comprueba que haya fuentes, no que digan
  lo que afirmás.
- **Defectos de plantilla.** El H1 oculto y el schema duplicado viven en el HTML
  renderizado. Para eso hay que abrir el navegador o llamar a una API de
  análisis on-page.
- **Si la keyword se puede ganar.** Eso está en la parte de investigación de
  keywords, que mira la SERP real antes de recomendar.
- **Rendimiento y Core Web Vitals.** Son del sitio, no del markdown.

---

## Lo que enseñan estos números

**Escribir la regla no basta.** Es el hallazgo central. Tres documentos decían lo
mismo y el incumplimiento fue del 90 por ciento.

**Los defectos silenciosos son los peores.** Los enlaces perdidos no producían
ningún error. El post se publicaba con menos enlaces y todo parecía correcto.

**Los ejemplos de la documentación también fallan.** El ejemplo canónico de este
repositorio no pasó su propia auditoría a la primera: la keyword era
`que es la serigrafia` y el cuerpo abría con "La serigrafía es una técnica".
La cadena completa no aparecía en ningún lado.

**Un chequeo nuevo se paga solo el mismo día.** `E-ANCHOR-MISSING` se escribió
después de que dos artículos se publicaran con enlaces faltantes. En esa misma
corrida encontró otros dos antes de que salieran.
