# Search Console antes que keywords nuevas

Search Console es la única fuente que dice para qué te muestra Google de
verdad. Todo lo demás (volúmenes, dificultad, ideas) es una estimación sobre
lo que podría pasar. Por eso el orden de trabajo es este y no al revés:

1. Leer lo que ya pasa (`gsc.py`).
2. Empujar lo que ya casi funciona (`kw_map.py`, posiciones 4 a 20).
3. Solo entonces buscar keywords nuevas (`kw_research.py --gsc`).

Un sitio con 13.000 impresiones y 16 clics no necesita más artículos.
Necesita títulos que se cliquen y tres secciones nuevas en las páginas que ya
están en la posición 9.

## Cómo exportar

En Search Console, con la propiedad abierta:

| Informe | Menú | Qué trae |
|---|---|---|
| Rendimiento en resultados de búsqueda | Rendimiento > Resultados de búsqueda > Exportar > Descargar CSV | Consultas, Páginas, Países, Dispositivos, Gráfico |
| Rendimiento en funciones de IA | Rendimiento > Funciones de IA > Exportar | Páginas e impresiones en AI Overviews y AI Mode |
| Indexación | Indexación > Páginas > Exportar | Motivos por los que una URL no se indexa |

Los ZIP se pasan tal cual, sin descomprimir. Los nombres de archivo en español
o en inglés se reconocen igual.

**Para cruzar consulta con página**, que la exportación global no hace:
filtrar por página en la consola (Página > Es exactamente > la URL) y exportar
solo esa. O `dfs.py ranked dominio`, que devuelve keyword, URL y posición del
índice de DataForSEO para todo el dominio de una vez.

## Las cinco lecturas de gsc.py

### Casi en el top 10

Páginas en posición 4 a 20 con impresiones. El curso lo llama "la página que
ya rankea": añadir una sección con la consulta literal como H2, tres enlaces
internos desde posts relacionados, y un título mejor. Google ya decidió que la
página vale para esa consulta; solo falta convencerlo de que vale más que las
diez de arriba.

Se ordenan por `impresiones / (posición - 3)`: muchas impresiones y cerca del
top 10 primero.

### CTR bajo para su posición

Google ya la muestra en el top 12 y nadie clica. Eso no es un problema de
contenido, es un problema de snippet. Se compara con una curva de CTR
esperada por posición (orientativa, redondeada hacia abajo para B2B) y se
listan las que quedan por debajo de la mitad. La columna "clics que faltan" es
el coste real de no tocar el título.

Lo que sube el CTR, según el curso: beneficio antes que característica,
"tú", un número, un año, algo nuevo o distinto en el titular.

### Consultas sin página

Búsquedas con impresiones que ningún post cubre, cruzadas contra el título,
la keyword y el slug de cada post en `--content-dir`. Si menos de un tercio de
las palabras de la consulta aparecen en algún post, es un hueco.

Con `--brand` se apartan las búsquedas de marca, que no son oportunidad.

"Cubiertas a medias" son las que tocan un post pero no con esas palabras: un
H2 con la consulta literal suele bastar.

### URLs duplicadas

La misma ruta con www y sin www, o en http, o en otro subdominio. Cada
variante recibe impresiones por su cuenta y la posición se reparte. Casi
siempre es una redirección que llegó tarde: Google indexó la variante mala
antes de que existiera el 301. Se arregla verificando la redirección y el
canonical, y pidiendo reindexación de la buena.

### AI Overviews e indexación

Si están las exportaciones, lista las páginas que aparecen en funciones de IA
con su cuota, y los motivos de no indexación con el número de páginas.

## El mapa de keywords

`kw_map.py` es la hoja que el curso manda tener: cada post, su keyword, dónde
rankea y cuándo se tocó por última vez. Se vuelve a ella cada mes.

Para los posts sin `focus_keyword` propone una, y la propuesta siempre está
entera en el título o en el meta título, porque es lo que exige el auditor. El
orden:

1. La consulta de `dfs.py ranked` que apunta a esa URL y está en el título.
2. La consulta de Search Console con más impresiones que está en el título.
3. El tramo más largo del título cuyas palabras de contenido están en el slug.
4. El título limpio de números, años, paréntesis y marca.

`--apply` escribe `focus_keyword` solo donde falta. No toca los que ya la
tienen y no toca borradores.

## Búsqueda de keywords con contexto

`kw_research.py --gsc exports/` mete las consultas de Search Console en el
pozo y, para cada keyword que ya te muestra en posición 20 o mejor, cambia la
recomendación a "actualizar la página que ya rankea" en vez de proponer un
post nuevo. Es el error más caro que evita: escribir el segundo artículo sobre
lo que el primero casi consigue.
