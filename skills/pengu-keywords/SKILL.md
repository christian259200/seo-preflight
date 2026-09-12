---
name: pengu-keywords
description: >-
  Investigación de keywords con datos reales de DataForSEO: volumen, CPC,
  dificultad, intención y composición de la SERP. Prioriza por oportunidad, no
  por volumen, descarta lo que no se puede ganar todavía, agrupa en clusters y
  avisa de canibalización contra el contenido publicado. Usa esta skill cuando
  el usuario pida keyword research, pregunte sobre qué escribir, quiera un plan
  de contenido, mencione DataForSEO, volumen de búsqueda o dificultad, o
  comparta una exportación de Search Console y pregunte qué hacer con ella.
user-invocable: true
argument-hint: "[semilla] [--loc pais] [--lang idioma] [--gsc exportacion]"
license: MIT
metadata:
  author: Christian Monge
  version: "1.2.0"
---

# Pengu Keywords

Convierte semillas en un plan de contenido priorizado, con datos reales y con
las keywords que no conviene atacar marcadas como tales.

## Por qué no basta con ordenar por volumen

Un CSV ordenado por volumen es la forma más rápida de escribir diez artículos
que nunca van a rankear. Tres cosas lo explican:

**La SERP decide antes que la intención.** Si el top 10 de "termos
personalizados" son fichas de producto, un artículo de blog no entra ahí, por
bien escrito que esté. Google ya decidió qué formato quiere. Esta skill mira la
SERP real de las finalistas antes de recomendar nada.

**La dificultad se compara contra tu autoridad, no en abstracto.** Un KD de 45
es una oportunidad para un dominio consolidado y una pérdida de tiempo para uno
nuevo. El techo se fija con `--authority`.

**El volumen sin intención comercial no paga nada.** 5.000 búsquedas de "qué es
X" valen menos que 200 de "X en Managua precio" si vendés X.

## Primero Search Console, después keywords nuevas

Si el sitio ya tiene tráfico de búsqueda, lo primero no es buscar keywords:
es leer para qué te muestra Google ya. Un sitio con miles de impresiones y
una docena de clics no necesita más artículos, necesita títulos que se
cliquen y una sección nueva en las páginas que están en la posición 9.

```bash
cd skills/pengu-keywords/scripts

# 1. Qué pasa hoy: casi top 10, CTR bajo, consultas sin página, URLs duplicadas
python gsc.py exports/ --content-dir src/content/blog --brand mimarca --md informe.md

# 2. El mapa de keywords: cada post, su keyword, su posición, su fecha
python kw_map.py src/content/blog --gsc exports/ --md mapa.md
python kw_map.py src/content/blog --gsc exports/ --apply     # escribe focus_keyword donde falte

# 3. Solo entonces, keywords nuevas, con Search Console como contexto
python kw_research.py "semilla" --gsc exports/ --content-dir src/content/blog --md plan.md
```

`gsc.py` lee los ZIP que exporta la consola tal cual, en español o en inglés,
sin credenciales ni red. El detalle de cada lectura está en
[`references/search-console.md`](references/search-console.md).

Con `--gsc`, `kw_research.py` mete las consultas que ya te muestran en el pozo
y, para las que ya rankean en posición 20 o mejor, cambia la recomendación a
**actualizar la página que ya rankea**. Es el error más caro que evita:
escribir el segundo artículo sobre lo que el primero casi consigue.

## Uso

```bash
cd skills/pengu-keywords/scripts

python kw_research.py "articulos promocionales" "serigrafia" \
  --loc Nicaragua --lang Spanish \
  --authority low \
  --content-dir posts/ \
  --md plan.md --out plan.json
```

Para consultas sueltas, `dfs.py` va directo a la API:

```bash
python dfs.py volume "serigrafia managua" "camisetas personalizadas" --loc Nicaragua --lang Spanish
python dfs.py serp "que es serigrafia" --loc Nicaragua --lang Spanish
python dfs.py intent "comprar termos personalizados" --lang Spanish
python dfs.py ideas "articulos promocionales" --loc Nicaragua --limit 200
python dfs.py onpage https://example.com/que-es-serigrafia/
python dfs.py ranked example.com --limit 300 --yes --out ranked.json
python dfs.py costs
```

`serp` devuelve también `ai_overview`: si la consulta muestra un AI Overview
y a qué dominios cita. Esa lista es a quién hay que parecerse para entrar.

`ranked` devuelve keyword, URL y posición de todo lo que rankea un dominio.
Es el cruce consulta-página que la exportación de Search Console no da, y
`kw_map.py --ranked ranked.json` lo usa para elegir la keyword de cada post
con datos. Cuesta por fila, así que siempre pide `--yes`.

## Control de gasto

DataForSEO cobra por llamada. El guardarrail vive en `dfs.py` y **corta antes
de gastar**, no después:

- Límite diario. Si la llamada lo supera, sale con código 2 y no llama.
- Umbral de aprobación. Por encima de él hace falta `--yes` explícito.
- Endpoints caros que siempre piden confirmación, sin importar el umbral.
- Caché en disco con vida distinta por tipo de dato: la SERP un día, el volumen
  una semana. Repetir una consulta dentro de ese plazo no cuesta nada.

```bash
python dfs.py budget --daily 5.00 --threshold 0.25 --mode threshold
python dfs.py costs --days 30
```

Antes de una tanda grande, mirá `costs`. Después de una tanda grande, también.

Los precios por endpoint están en
[`references/costos.md`](references/costos.md).

## Cómo leer el resultado

El plan reparte las keywords en cuatro bandas:

| Banda | Qué significa |
|---|---|
| **atacar ya** | Volumen suficiente, dificultad dentro de tu techo, SERP compatible |
| **segunda ola** | Sirven, pero después de las primeras y con enlaces desde ellas |
| **cluster de apoyo** | Solas no valen. Dentro de un cluster sí |
| **descartar** | Hoy no. Puede cambiar cuando suba la autoridad |

El puntaje es **demanda × posibilidad de ganar × valor comercial**, los tres
multiplicados. Multiplicativo a propósito: si cualquiera de los tres es cero, la
keyword no sirve por mucho que brillen los otros dos. Una suma ponderada
esconde eso y por eso casi todas las herramientas recomiendan keywords
imposibles.

La columna **Qué escribir** es lo más importante de la tabla. Cuando dice
"página comercial o categoría", escribir un artículo es tirar el trabajo.
Cuando dice "actualizar la página que ya rankea", la columna **GSC** dice en
qué posición y con cuántas impresiones: se empuja esa página, no se escribe
otra. **AIO** dice si la SERP muestra un AI Overview; si sí, el artículo
necesita un párrafo de respuesta directa arriba y datos propios para entrar.

## Canibalización

Con `--content-dir` cruza contra lo que ya está publicado. Si el solapamiento
pasa del 70%, avisa:

- **90% o más**: actualizá el post existente, no escribas uno nuevo. Dos URLs
  compitiendo por lo mismo se hunden las dos.
- **entre 70 y 90%**: diferenciá el ángulo y enlazá al existente.

## Canibalización entre lo ya publicado

`cannibal.py` mira los posts publicados por pares: keyword, título y slug, y
las consultas que Search Console o `dfs.py ranked` atribuyen a cada URL.
Agrupa los que se pisan y propone qué hacer con cada par:

```bash
python cannibal.py src/content/blog --gsc exports/ --md canibalizacion.md
```

| Acción | Cuándo | Qué se hace |
|---|---|---|
| fusionar | mismo tema y misma intención, solapamiento alto | una URL absorbe a la otra, la otra redirige con 301 |
| diferenciar | mismo tema, ángulo distinto | keywords separadas, título del secundario con su ángulo, enlace cruzado |
| vigilar | comparten palabras, no intención | nada, salvo no acercarlos más |

No cambia archivos. La fusión implica redirecciones y la decide una persona.
El curso lo cuenta con un caso real: dos keywords en una página, y un salto
del puesto 9 al 2 al separarlas.

## Clusters

Devuelve pilar y satélites. El pilar cubre el término amplio, los satélites las
variantes largas.

**Un cluster sin enlaces no es un cluster, son artículos sueltos.** Cada
satélite enlaza al pilar y el pilar a todos los satélites. Si ese cableado no se
hace, el trabajo de agrupar no sirvió de nada.

## Qué hacer con el plan

1. Tomá el primer "atacar ya" cuyo **Qué escribir** diga "artículo de blog".
2. Mirá su `people_also_ask`: esas son preguntas reales, sirven de H2 y de FAQ.
3. Mirá su `serp_top3`: eso es lo que hay que superar, no igualar.
4. Pasá a [`pengu-write`](../pengu-write/SKILL.md) con la keyword, las preguntas
   y el ángulo que los tres primeros no cubren.

El criterio de selección está en
[`references/seleccion.md`](references/seleccion.md).
