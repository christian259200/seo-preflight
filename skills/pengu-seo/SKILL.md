---
name: pengu-seo
description: >-
  Orquestador SEO de contenido: elige la keyword con datos reales de DataForSEO,
  escribe el post en un formato canónico, lo publica en WordPress o Next.js y lo
  audita con reglas que se ejecutan y cortan. Usa esta skill cuando el usuario
  pida un blog nuevo, keyword research, un plan de contenido, una auditoría de
  posts existentes, o pregunte qué escribir a continuación.
user-invocable: true
argument-hint: "[keywords|write|audit|plan] [tema o ruta]"
license: MIT
metadata:
  author: Christian Monge
  version: "1.2.0"
---

# Pengu SEO

Tres skills sobre un formato común. El contenido se escribe una vez y se
publica donde haga falta, y nada sale sin pasar por un validador que corre de
verdad.

## La idea de fondo

Una regla escrita se incumple, y se incumple en silencio. En la landing de
Pengu Insights, la regla "todo post enlaza a la app" estaba en `AGENTS.md`, en
`VOICE.md` y en dos skills. **45 de 50 posts publicados no la cumplían.** Nadie
lo sabía porque nada lo comprobaba.

Por eso el centro de este proyecto no es un prompt largo. Es
`pengu-audit/scripts/audit.py`, que devuelve código 1 y no deja publicar.

## Las tres skills

| Skill | Para qué | Entra | Sale |
|---|---|---|---|
| [pengu-keywords](../pengu-keywords/SKILL.md) | Decidir qué escribir | semillas | plan priorizado con clusters |
| [pengu-write](../pengu-write/SKILL.md) | Escribir y publicar | keyword + brief | post canónico y renderizado |
| [pengu-audit](../pengu-audit/SKILL.md) | Impedir que salga algo malo | carpeta de posts | errores, avisos y código de salida |

## El flujo completo

```
0. console    ->  qué muestra Google ya: casi top 10, CTR bajo, huecos
1. keywords   ->  qué keyword, con qué intención, contra qué SERP
2. brief      ->  H2, preguntas reales de la SERP, enlaces, ángulo propio
3. write      ->  post en formato canónico
4. audit      ->  tiene que dar PASA antes de seguir
5. render     ->  al formato de la plataforma destino
6. audit      ->  otra vez, con el perfil de esa plataforma
7. publicar
8. mapa       ->  cada mes, volver a las páginas en posición 4 a 20
```

El paso 0 existe porque un sitio que ya rankea no empieza de cero. Antes de
escribir nada nuevo, `gsc.py` dice qué páginas están en la posición 9 sin
clics y qué consultas ya te muestran sin que tengas página. Ese trabajo rinde
más que cualquier post nuevo, y no cuesta un solo crédito.

Los pasos 4 y 6 no son opcionales. El 6 existe porque cada plataforma rompe
cosas distintas: WordPress se traga enlaces cuando dos anchors caen en el mismo
párrafo, y Next.js emite `FAQPage` con contenido que no se ve en la página.

## Cuándo usar cada una

**"Aquí tienes mi Search Console"**, **"¿qué hago con estos datos?"** →
`pengu-keywords`, empezando por `gsc.py` y `kw_map.py`. Se mira lo que ya
pasa antes de proponer nada nuevo.

**"¿Sobre qué escribo?"** o **"buscá keywords de X"** → `pengu-keywords`.
Nunca escribas antes de mirar la SERP: la mitad de las keywords informativas
con buen volumen tienen una SERP comercial donde un artículo no entra.

**"Escribí un post sobre X"** → `pengu-write`. Si no hay keyword confirmada,
pasá primero por `pengu-keywords`.

**"Revisá el blog"**, **"¿está bien esto?"**, antes de cualquier push →
`pengu-audit`.

**"¿Qué está fallando en el sitio?"** → `pengu-audit` sobre toda la carpeta,
con `--json`, y ordená por puntaje ascendente.

## Antes de escribir nada

Leé, en este orden, lo que exista en el proyecto:

1. `BRAND.md` y `VOICE.md`, si están, mandan sobre lo que diga esta skill
2. `AGENTS.md` o `CLAUDE.md` del repositorio destino
3. [`references/estilo.md`](../pengu-write/references/estilo.md) de `pengu-write`

## Reglas que no se negocian

Están en el auditor, no solo aquí, así que no dependen de que alguien se
acuerde.

- **Sin guiones largos ni cortos.** Ni em dash ni en dash, en ninguna parte.
  Es el rastro de IA más fácil de detectar y no aporta nada que no resuelva una
  coma o un punto.
- **Sin marcadores de plantilla.** Nada de `[UNIQUE INSIGHT]` ni `[COMPLETAR]`.
- **Sin precios inventados.** Si no vas a dar el precio, no pongas un rango.
- **Toda cifra con fuente real y verificable.** Una estadística sin URL es una
  opinión con números.
- **Todo post lleva un camino de conversión.** Un artículo que solo enlaza a
  otros artículos es tráfico que no factura.
- **El H1 lo pone la plantilla.** En el cuerpo se empieza en `##`.

## Cómo se entrega una recomendación

Una lista de hallazgos no es un plan. Cada recomendación que salga de estas
skills lleva cuatro cosas, o no sale:

1. **En qué se apoya.** El dato que la sostiene: la posición en Search
   Console, el código del auditor, la SERP que se miró.
2. **Qué destraba y qué la bloquea.** Reescribir el título de una página en
   posición 9 no sirve si el canonical apunta a otra URL; eso va primero.
3. **Cómo sabremos que falló.** Un número y una fecha: "si en 21 días el CTR
   de esa consulta no pasa del 2%, el título nuevo no funcionó".
4. **Qué mirar mientras tanto.** El indicador que se ve antes que el tráfico:
   impresiones de la consulta, posición media, páginas indexadas.

El formato viene de la disciplina de falsabilidad de claude-seo: una
recomendación que no puede fallar no es una recomendación, es una opinión.

Lo que Google cambió y toca a estas reglas está, con fecha y fuente, en
[`references/google-updates.md`](references/google-updates.md). Manda sobre
cualquier consejo de las referencias que lo contradiga.

## Instalar como plugin

```
/plugin marketplace add christian259200/seo-preflight
/plugin install pengu-seo@seo-preflight
```

Trae las cuatro skills y un hook que audita cada post al guardarlo (ver
`pengu-audit`). Copiar `skills/` a `~/.claude/skills/` sigue funcionando y
no instala el hook.

## Configuración

```bash
export DATAFORSEO_LOGIN="tu-login"
export DATAFORSEO_PASSWORD="tu-password"
export PENGU_LOCATION="Nicaragua"
export PENGU_LANGUAGE="Spanish"
```

También sirve `DATA_FOR_SEO="login:password"`, que es el formato que ya usa la
landing, o `~/.config/pengu-seo/dataforseo.json`.

**Ninguna credencial se escribe en el repositorio.** Ni en un archivo de
configuración, ni dentro de una lista de permisos, ni en un comentario.

Los scripts solo usan la biblioteca estándar de Python. `pyyaml` es opcional y
mejora el parseo del frontmatter, pero nada deja de funcionar sin él.

## Formato canónico

El contrato entre las tres skills está en
[`schema/post.schema.md`](schema/post.schema.md). Hay un ejemplo completo
y verificado en [`examples/ejemplo-canonico.md`](examples/ejemplo-canonico.md),
que da 100/100 en la auditoría. Sirve de plantilla.
