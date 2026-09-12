# seo-preflight

Tres skills de Claude Code, publicadas como `pengu-keywords`, `pengu-write` y
`pengu-audit`, más el orquestador `pengu-seo`.

Investigación de keywords con datos reales, redacción multiplataforma y
auditoría on-page que se ejecuta y corta. Tres skills sobre un formato de post
común.

## El problema que resuelve

Las reglas escritas se incumplen en silencio.

En la landing de Pengu Insights, la regla "todo post enlaza a la aplicación"
estaba escrita en `AGENTS.md`, en `VOICE.md` y en dos skills distintas. Al
medirlo: **45 de 50 posts publicados no la cumplían.** Nadie lo sabía porque
nada lo comprobaba.

Este proyecto no es una colección de prompts mejores. Es un validador que
devuelve código 1, más las dos skills que lo alimentan.

## Las tres skills

| Skill | Para qué |
|---|---|
| **pengu-keywords** | Decide qué escribir. Lee Search Console primero (casi top 10, CTR bajo, consultas sin página), mantiene el mapa de keywords, y después DataForSEO con control de gasto, priorización por oportunidad, clusters y aviso de canibalización |
| **pengu-write** | Escribe en formato canónico y renderiza a WordPress o Next.js |
| **pengu-audit** | Impide que salga algo malo. 40 comprobaciones, tres perfiles, código de salida |

## Instalar

```bash
git clone https://github.com/christian259200/seo-preflight.git
cp -r seo-preflight/skills/* ~/.claude/skills/
```

Las cuatro carpetas de `skills/` tienen que quedar como hermanas dentro de
`~/.claude/skills/`: se enlazan entre sí con rutas relativas.

En Windows, un enlace de directorio evita tener que volver a copiar cada vez que
actualizás el repo:

```powershell
foreach ($s in "pengu-seo","pengu-keywords","pengu-write","pengu-audit") {
  New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\$s" -Target "$PWD\seo-preflight\skills\$s"
}
```

O como plugin, que además instala el hook que audita cada post al guardarlo:

```
/plugin marketplace add christian259200/seo-preflight
/plugin install pengu-seo@seo-preflight
```

Requisitos: Python 3.9 o superior. **Solo biblioteca estándar.** `pyyaml` es
opcional y mejora el parseo del frontmatter.

Para la parte de datos:

```bash
export DATAFORSEO_LOGIN="tu-login"
export DATAFORSEO_PASSWORD="tu-password"
export PENGU_LOCATION="Nicaragua"
export PENGU_LANGUAGE="Spanish"
```

También acepta `DATA_FOR_SEO="login:password"` o
`~/.config/pengu-seo/dataforseo.json`.

**Ninguna credencial va en el repositorio.** Ni en un archivo de configuración,
ni dentro de una lista de permisos de una herramienta, ni en un comentario. Un
token en un repositorio privado sigue siendo un token filtrado: lo ve cada
colaborador, queda en cada clon y sobrevive en el historial aunque borres la
línea.

## El flujo

```bash
# 0. Qué muestra Google ya. Sin red, sin créditos: solo la exportación de Search Console
python skills/pengu-keywords/scripts/gsc.py exports/ --content-dir posts/ --md informe.md
python skills/pengu-keywords/scripts/kw_map.py posts/ --gsc exports/ --md mapa.md

# 1. Qué escribir
python skills/pengu-keywords/scripts/kw_research.py "articulos promocionales" \
  --loc Nicaragua --lang Spanish --authority low \
  --content-dir posts/ --md plan.md

# 2. Escribir, partiendo del ejemplo
cp skills/pengu-seo/examples/ejemplo-canonico.md posts/nuevo.md

# 3. Auditar antes de nada
python skills/pengu-audit/scripts/audit.py posts/nuevo.md --profile canonical

# 4. Renderizar al destino
python skills/pengu-write/scripts/render.py posts/nuevo.md --to wordpress --out publicar/nuevo.md

# 5. Auditar otra vez, con el perfil de esa plataforma
python skills/pengu-audit/scripts/audit.py publicar/nuevo.md --profile wordpress
```

El paso 5 existe porque cada plataforma rompe cosas distintas. El paso 0
existe porque un sitio que ya rankea no empieza de cero: en el sitio B de
abajo, 13.600 impresiones daban 16 clics, y nueve páginas estaban entre la
posición 4 y la 20. Ese trabajo rinde más que cualquier post nuevo.

## Qué encuentra el auditor

Contra 81 posts publicados de dos sitios reales:

| Hallazgo | Casos |
|---|---|
| Dos anchors en el mismo párrafo, el segundo se pierde | 20 de 31 |
| Posts sin ningún camino de conversión | 29 de 50 |
| Guiones largos, prohibidos en tres documentos | 7 |
| Schema `FAQPage` sin FAQ visible en la página | 3 |
| Enlace markdown dentro del YAML, rompe el build | 2 |
| Páginas en el top 12 con CTR por debajo de la mitad de lo esperado | 5 de 9 |
| Rutas indexadas por duplicado (con y sin www) | 18 |

Todos verificados a mano antes de darlos por buenos. El detalle completo, con
los falsos positivos que hubo que corregir y lo que el auditor no ve, está en
[HALLAZGOS.md](HALLAZGOS.md).

## Configuración por sitio

Lo que cambia de un sitio a otro no está en el código. Va en un `pengu-seo.json`
en la raíz del proyecto, y el auditor lo busca desde la carpeta auditada hacia
arriba:

```json
{
  "sites": ["example.com"],
  "money_pages": ["/pricing", "/contact", "app.example.com"],
  "url_prefix": "/blog",
  "site_root": "."
}
```

| Campo | Para qué |
|---|---|
| `sites` | Dominios propios. Un enlace absoluto a ellos, o a un subdominio, cuenta como interno |
| `money_pages` | Páginas de conversión. Sin esto, `E-NO-CTA` queda apagado y el auditor lo avisa |
| `url_prefix` | Prefijo del blog, para detectar enlaces a posts que no existen |
| `site_root` | Raíz del sitio, para comprobar que las imágenes existen en disco |

Todo se puede pasar también por línea de comandos, y la línea de comandos manda.
En Git Bash, las rutas que empiezan por `/` se convierten en rutas de Windows
antes de llegar al script; el auditor lo detecta y lo deshace, pero el archivo de
configuración evita el problema de raíz:

```bash
python audit.py posts/ --profile wordpress --site example.com --money-page /contacto
```

Hay una plantilla en `pengu-seo.example.json`, en la raíz.

## Control de gasto

DataForSEO cobra por llamada. El guardarrail **corta antes de gastar**:

```bash
python skills/pengu-keywords/scripts/dfs.py budget --daily 5.00 --threshold 0.25
python skills/pengu-keywords/scripts/dfs.py costs --days 30
```

Si una llamada supera el límite diario, sale con código 2 y no se ejecuta. Un
bucle mal escrito contra una API de pago es una factura sorpresa, y el momento
de descubrirlo no es a fin de mes.

Hay caché en disco con vida distinta por tipo de dato: la SERP un día, el
volumen una semana. Repetir una consulta dentro de ese plazo no cuesta nada.

Un plan de contenido completo, con dos semillas y ocho comprobaciones de SERP,
cuesta unos 13 centavos.

## Enganchar al build

```json
{
  "scripts": {
    "audit": "python skills/pengu-audit/scripts/audit.py src/content/blog --profile nextjs --site-root .",
    "prebuild": "npm run audit"
  }
}
```

Un post con errores no llega a producción. Es la diferencia entre una regla y
una garantía.

## De dónde salen los umbrales

- Un curso de SEO en video, 11.430 líneas de transcripción: título de 70
  caracteres, descripción de 140, URLs bajo 100 caracteres con uno o dos
  directorios, long tail como camino para sitios nuevos, Search Console como
  fuente primaria.
- Material de SEO y SEM de un máster en marketing: link building como campaña,
  disciplina de intención, concordancia de keywords.
- Producción real: cada trampa documentada en
  `skills/pengu-write/references/trampas.md` costó tiempo antes de estar ahí.

## El sitio publicado, y qué cambió desde ayer

El auditor de markdown no ve la plantilla. `site_check.py` pide cada URL del
sitemap y comprueba robots, redirecciones de host, canonical, noindex, H1,
título y JSON-LD. Con dos informes, dice qué cambió y cuánto importa:

```bash
python skills/pengu-audit/scripts/site_check.py https://www.example.com --json lunes.json
python skills/pengu-audit/scripts/site_check.py https://www.example.com --json martes.json --compare lunes.json
```

Un canonical que cambió, un `noindex` nuevo o un H1 que desapareció salen
como críticos y devuelven código 1. Un despliegue que rompe el SEO se ve el
mismo día, no cuando cae el tráfico.

## Auditar al guardar

Instalado como plugin, un hook `PostToolUse` corre el auditor sobre cada
post que Claude edite. Con errores, Claude ve el informe y lo corrige antes
de seguir. Es la misma idea que el `prebuild`, una capa antes: la regla no
espera al build, corre al guardar.

## Lo que Google cambió

Cada regla que depende de Google tiene fecha y fuente en
[`skills/pengu-seo/references/google-updates.md`](skills/pengu-seo/references/google-updates.md).
Dos que cambiaron consejos de aquí: Google Search ignora `llms.txt`
(2026-06-29) y los resultados enriquecidos de FAQ se retiraron para todos
los sitios (2026-05-07).

## Comprobar que todo funciona

```bash
python smoke.py
```

No toca la red ni gasta un centavo. Comprueba que las cuatro herramientas
arrancan, que el parser de YAML de respaldo coincide con pyyaml, que el ejemplo
canónico saca 100/100 y que renderizarlo a los tres destinos lo sigue sacando.
Sale con código 1 si algo falla, así que sirve en CI.

## Añadir una plataforma

Está en [`schema/post.schema.md`](skills/pengu-seo/schema/post.schema.md). Son tres pasos, y la
pregunta que decide el trabajo es qué renderiza esa plataforma sola.

## Ideas prestadas

La deriva entre dos comprobaciones, el hook que audita al guardar, el
registro de cambios de Google con fuente obligatoria y el formato de
recomendación falsable vienen de
[claude-seo](https://github.com/AgriciDaniel/claude-seo) (MIT), recortados a
lo que cabe en scripts de biblioteca estándar. Parte de la lista de
muletillas de IA viene del catálogo de limpieza de Wikipedia y del mismo
proyecto.

## Licencia

MIT.
