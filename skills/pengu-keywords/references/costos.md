# Costos de DataForSEO y cómo no quemarlos

Precios aproximados por llamada, en USD, cola estándar. Están codificados en el
diccionario `COST` de `dfs.py`, que es lo que usa el guardarrail para estimar
antes de llamar. El costo real que devuelve la API es el que se registra en el
ledger.

## Tabla

| Comando | Endpoint | Costo | Notas |
|---|---|---:|---|
| `serp` | `serp/google/organic/live/advanced` | $0,002 | Por 100 resultados. Incluye PAA y features |
| | `serp/google/organic/live/regular` | $0,001 | Sin features, la mitad de precio |
| `volume` | `keywords_data/google_ads/search_volume/live` | $0,05 | Por lote, hasta 1.000 keywords |
| `ideas` | `dataforseo_labs/google/keyword_ideas/live` | $0,05 | Por consulta, sin importar el límite |
| `related` | `dataforseo_labs/google/related_keywords/live` | $0,05 | |
| `difficulty` | `dataforseo_labs/google/bulk_keyword_difficulty/live` | $0,01 | Por lote. Barato, usalo |
| `intent` | `dataforseo_labs/google/search_intent/live` | $0,01 | Por lote |
| `competitors` | `dataforseo_labs/google/serp_competitors/live` | $0,05 | |
| `onpage` | `on_page/instant_pages` | $0,01 | Una URL |
| | `on_page/lighthouse/live/json` | $0,02 | Core Web Vitals |
| | `backlinks/summary/live` | $0,02 | Siempre pide confirmación |
| | `dataforseo_labs/google/ranked_keywords/live` | $0,05 | Siempre pide confirmación |

## Lo que cuesta una corrida completa

`kw_research.py` con dos semillas y ocho comprobaciones de SERP:

```
2 semillas × ideas          $0,10
1 lote de dificultad        $0,01
8 SERP                      $0,016
                            -----
                            $0,126
```

Poco más de doce centavos por un plan de contenido de un trimestre. El costo no
es el problema; el problema es repetirlo sin darse cuenta, y para eso está la
caché.

## Cómo baja el costo

**La caché es lo que más ahorra.** Vive en `~/.cache/pengu-seo/dataforseo/` con
vidas distintas por tipo de dato:

| Tipo | Vida | Por qué |
|---|---|---|
| SERP | 1 día | Se mueve a diario |
| Volumen y Labs | 7 días | El dato es mensual, no cambia en una semana |
| On-page | 6 horas | Cambia cuando cambia la página |
| Backlinks | 3 días | Se mueve despacio |

Repetir una consulta dentro de su plazo no cuesta nada y el resultado trae
`"cached": true`. Para forzar datos frescos, `--no-cache`.

**Lotes, no llamadas sueltas.** `volume` con 50 keywords cuesta lo mismo que
con una: $0,05. Cincuenta llamadas individuales cuestan $2,50. La diferencia es
de cincuenta veces y es el error más común.

**`live_regular` cuando no necesitás features.** La mitad de precio. Si solo
querés ver quién rankea, sobra.

**Filtrá antes de pedir dificultad.** `kw_research.py` descarta por volumen
mínimo antes de gastar en KD, no después.

## Configuración del presupuesto

```bash
python dfs.py budget --daily 5.00 --threshold 0.25 --mode threshold
```

| Modo | Comportamiento |
|---|---|
| `none` | Nunca pregunta. Solo para pipelines desatendidos que ya conocés |
| `threshold` | Pregunta por encima del umbral. El razonable |
| `always` | Pregunta siempre. Para aprender qué cuesta cada cosa |

Presets según el uso:

| Perfil | Diario | Umbral |
|---|---:|---:|
| Aprendiendo | $2,00 | $0,10 |
| Un sitio propio | $5,00 | $0,25 |
| Agencia con varios clientes | $25,00 | $1,00 |

El límite diario **bloquea**, no avisa: si la llamada lo supera, sale con
código 2 y no se ejecuta. Es a propósito. Un bucle mal escrito contra una API
de pago es una factura sorpresa, y el momento de descubrirlo no es a fin de mes.

## Revisar el gasto

```bash
python dfs.py costs            # los últimos 7 días
python dfs.py costs --days 30  # el mes
```

El ledger vive en `~/.config/pengu-seo/ledger.json` y guarda 60 días, con el
desglose por endpoint. Si un endpoint aparece mucho más caro de lo esperado, ahí
se ve.

## Alternativas gratis

Cuando no hay presupuesto o no hay cuenta:

| Dato | Fuente gratis | Qué se pierde |
|---|---|---|
| Qué rankea | Buscar a mano en incógnito | Nada, solo tiempo |
| Preguntas reales | People Also Ask en la SERP | Nada |
| Volumen relativo | Google Trends | El número absoluto |
| Volumen propio | Search Console | Solo tus propias keywords |
| Dificultad | Mirar quién rankea y con qué | La comparación numérica |
| Intención | Leer los títulos del top 10 | Poco |

Search Console merece mención aparte: para un sitio que ya tiene tráfico, es
mejor fuente que cualquier herramienta de pago, porque son tus datos reales y
no una estimación. Las keywords donde ya apareces en posición 8 a 20 con
impresiones son la fruta más baja que existe.
