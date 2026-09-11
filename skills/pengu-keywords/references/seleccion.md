# Cómo se elige una keyword

El criterio que aplica `kw_research.py`, explicado para poder discutirlo o
ajustarlo. Sale del curso de SEO, del material del máster y de lo que ha
funcionado y fallado en producción.

## El puntaje

```
oportunidad = demanda × posibilidad_de_ganar × valor_comercial × 100
```

Los tres factores se multiplican, no se suman. La diferencia importa: con una
suma ponderada, una keyword de 50.000 búsquedas y dificultad 85 sale
recomendada porque el volumen arrastra. Multiplicando, la dificultad la hunde,
que es lo correcto.

### Demanda

```
demanda = min(1, log10(volumen + 1) / 4)
```

Escala logarítmica porque la utilidad del volumen no es lineal. Pasar de 10 a
100 búsquedas cambia el negocio. Pasar de 10.000 a 100.000 casi nunca, porque a
ese nivel ya no vas a ganar la posición.

Volumen cero no se descarta: dentro de un cluster, las variantes sin volumen
medible traen tráfico que ninguna herramienta reporta. Pero solas no valen, y
por eso pesan 0,05.

### Posibilidad de ganar

Depende de la dificultad contra tu techo de autoridad:

| Autoridad | Techo de KD | Cuándo aplica |
|---|---|---|
| `low` | 30 | Dominio nuevo, menos de un año, pocos enlaces |
| `medium` | 50 | Dominio establecido, algo de autoridad temática |
| `high` | 70 | Marca reconocida en su sector |

Por encima del techo la keyword no se descarta, se penaliza y se etiqueta "no
la ataques todavía". La diferencia importa: sigue en la lista para cuando la
autoridad suba.

Ante la duda, elegí el nivel más bajo. Sobreestimar la autoridad propia es el
error más caro del keyword research, porque el costo no se ve hasta seis meses
después.

### Valor comercial

Parte de la intención:

| Intención | Peso | Por qué |
|---|---|---|
| Transaccional | 1,00 | Está listo para comprar |
| Comercial | 0,85 | Está comparando, todavía se puede influir |
| Informacional | 0,55 | Trae tráfico, factura poco directamente |
| Navegacional | 0,30 | Busca una marca concreta, casi siempre otra |

Y se ajusta con el CPC. **Un CPC alto es la señal más honesta que existe**:
significa que hay empresas pagando dinero real por ese clic, mes tras mes.
Ninguna métrica de dificultad dice tanto sobre si una keyword da dinero.

CPC igual a cero en una keyword informacional resta: nadie puja porque nadie
vende ahí.

## Las tres puertas

Antes del puntaje hay tres comprobaciones que pueden anular todo lo demás.

### 1. Tipo de SERP

Es la más importante y la que casi nadie hace.

Se clasifica en tres:

- **Comercial**: dominan features de compra (shopping, product, local pack) y
  hay dos o menos resultados de blog. Aquí un artículo no entra. Hace falta una
  página de producto o de categoría.
- **Informativa**: cinco o más resultados de blog en el top 10. Vía libre.
- **Mixta**: hay sitio para las dos cosas. Suele ser la mejor oportunidad,
  porque una página comercial con contenido de verdad gana a las dos.

Cuando la SERP es comercial y la intención parece informacional, la
posibilidad de ganar se multiplica por 0,35. La keyword sigue en la lista, pero
etiquetada como página comercial.

**Esta puerta sola evita más trabajo perdido que todo el resto junto.**

### 2. Canibalización

Solapamiento de tokens de contenido contra lo publicado:

- 90% o más: es el mismo artículo. Actualizá el existente.
- 70 a 90%: se van a pisar. Diferenciá el ángulo o enlazá.
- menos de 70%: son distintos.

Dos URLs propias compitiendo por la misma intención no suman, se restan: los
enlaces se reparten, Google elige una y suele elegir la peor.

### 3. Volumen mínimo

Por defecto 10. Por debajo, solo entra si forma parte de un cluster con un
pilar que sí tiene volumen.

## Qué escribir según lo que salga

| SERP | Intención | Qué escribir |
|---|---|---|
| comercial | cualquiera | Página de producto o categoría |
| mixta | cualquiera | Página comercial con bloque de contenido real |
| informativa | transaccional | Página comercial |
| informativa | comercial | Comparativa o listado honesto |
| informativa | informacional | Artículo de blog |

## Lo que esta skill no mide

Decirlo importa tanto como el resto.

- **Autoridad del dominio**, se declara a mano. Un valor real necesita datos de
  backlinks, que se cobran aparte.
- **Estacionalidad**. El campo `trend` de `dfs.py volume` trae doce meses,
  pero el puntaje no lo usa. Míralo a mano en categorías con temporada, como
  regalos de fin de año.
- **Marca contra genérico**. Una keyword con marca ajena en el top 10 tiene un
  techo real más bajo que el que dice su KD.
- **Rentabilidad**. La skill no sabe cuánto te deja cada venta. Una keyword de
  200 búsquedas puede valer más que una de 5.000 si el ticket lo justifica.

## Ritmo recomendado

1. Corré el research una vez por trimestre, no cada semana. Los datos de
   volumen son mensuales y no cambian tanto.
2. Trabajá un cluster completo antes de abrir otro. Medio cluster no rankea.
3. Guardá el JSON con fecha. Comparar dos corridas separadas por meses dice más
   sobre tu mercado que cualquier informe suelto.
