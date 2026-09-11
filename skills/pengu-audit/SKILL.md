---
name: pengu-audit
description: >-
  Auditoría on-page ejecutable de posts en markdown. Comprueba título, meta
  descripción, keyword, jerarquía de encabezados, extensión, enlaces internos y
  de conversión, imágenes, FAQ, schema, URL y estilo, con perfiles para
  WordPress y Next.js. Devuelve código 1 si hay errores, así que sirve de puerta
  antes de publicar. Usa esta skill cuando el usuario pida revisar, auditar o
  validar contenido, antes de cualquier push, o cuando pregunte qué está mal en
  su blog.
user-invocable: true
argument-hint: "[ruta] [--profile wordpress|nextjs|canonical]"
license: MIT
metadata:
  author: Christian Monge
  version: "1.0.0"
---

# Pengu Audit

Corre, encuentra y corta. Es la pieza central del proyecto.

## Por qué existe

Las reglas escritas se incumplen en silencio. Datos reales de este mismo
entorno:

| Regla | Dónde estaba escrita | Incumplimiento |
|---|---|---|
| Enlazar a la aplicación | AGENTS.md, VOICE.md y dos skills | 45 de 50 posts |
| Sin guiones largos | tres documentos | 7 posts |
| FAQ visible con su schema | guías de Google | 3 posts |
| Un enlace por párrafo | referencia de la skill | 20 de 31 posts |

Nadie lo sabía porque nada lo comprobaba. Un script que devuelve código 1 sí.

## Uso

```bash
cd skills/pengu-audit/scripts

python audit.py posts/ --profile wordpress --site example.com
python audit.py landing/src/content/blog --profile nextjs --site-root landing
python audit.py post.md --profile canonical
python audit.py posts/ --profile wordpress --json informe.json
python audit.py posts/ --profile wordpress --strict
```

Códigos de salida: `0` si pasa, `1` si hay errores. Con `--strict`, los avisos
también cortan.

Sin dependencias externas. `pyyaml` mejora el parseo del frontmatter si está
instalado, pero hay un parser propio de respaldo.

## Perfiles

Cada plataforma rompe cosas distintas, así que cada una tiene su perfil.

| Perfil | Frontmatter | Comprobaciones propias |
|---|---|---|
| `wordpress` | plugin ai-blog-bridge | Colisión de anchors, fuentes en frontmatter, portada por attachment_id |
| `nextjs` | colección markdown de Next.js | FAQ visible obligatoria, imágenes en disco |
| `canonical` | formato propio | Superset de los dos |

El perfil `nextjs` exige FAQ visible porque la plantilla típica emite el schema
desde el frontmatter sin pintar las preguntas. El chequeo de conversión aplica a
cualquier perfil en cuanto declarás `money_pages`.

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

Todo se puede pasar también por línea de comandos, y la línea de comandos manda:

```bash
python audit.py posts/ --profile wordpress --site example.com --money-page /contacto
```

Hay una plantilla en `pengu-seo.example.json`, en la raíz del repositorio.

## Qué comprueba

**Metadatos.** Título de 30 a 70 caracteres con la keyword completa, y
preferentemente en los primeros 40. Descripción de 120 a 160, ideal 140, con la
keyword. Keyword sin puntuación.

**Contenido.** Keyword completa en el primer párrafo. Sin H1 en el cuerpo. De 3
a 12 H2. La keyword entera en algún H2. Sin H3 huérfanos. Mínimo 300 palabras,
objetivo 900. Densidad por debajo del 2,5%.

**Extracción.** Al menos una señal semántica. Listas o tablas. FAQ o
encabezados en pregunta. FAQ visible si hay schema de FAQ.

**Enlaces.** De 3 a 12 internos. Al menos un camino de conversión cuando el
perfil lo declara. Al menos una cita externa, en el cuerpo o en `sources`.
Anchors repetidos como máximo dos veces. Sin anchors vacíos tipo "aquí". Un
enlace por bloque.

**Imágenes.** Portada con alt. Alt en todas las imágenes. Existencia real del
archivo con `--site-root`.

**URL.** Menos de 100 caracteres, máximo dos directorios, sin mayúsculas ni
guiones bajos, compartiendo alguna palabra con la keyword.

**Frescura y autoría.** Fecha de actualización. Autor con enlace o biografía.

**Estilo.** Sin guiones largos ni cortos, con números de línea. Sin marcadores
de plantilla. Sin aperturas de relleno.

La lista completa con umbrales está en
[`references/reglas.md`](references/reglas.md).

## Cómo leer el resultado

```
!! guia-regalos-corporativos.md  [78/100]
   ERROR  E-LINK-COLLISION  Dos anchors en el mismo párrafo: 'regalos corporativos', 'catálogo'.
          -> El inyector salta el bloque que ya tiene un enlace y el segundo
             desaparece sin avisar. Separalos en párrafos distintos.
```

**Los errores se arreglan antes de publicar.** Son cosas que rompen algo:
schema engañoso, enlaces que desaparecen, contenido delgado.

**Los avisos se arreglan cuando se pueda.** Restan pero no rompen.

**Las notas son mejoras.** Ignorarlas es una decisión válida.

El puntaje es 100 menos 12 por error, 4 por aviso y 1 por nota. No es una nota
académica, es un orden de trabajo: los archivos salen ordenados de peor a
mejor, así que se empieza por arriba.

Cada hallazgo trae `-> ` con la corrección concreta. Si no la trae, el mensaje
ya la contiene.

## Enganchar al build

Que la puerta se cierre sola:

```json
{
  "scripts": {
    "audit": "python skills/pengu-audit/scripts/audit.py src/content/blog --profile nextjs --site-root .",
    "prebuild": "npm run audit"
  }
}
```

Con eso, un post con errores no llega a producción. Es la diferencia entre una
regla y una garantía.

## Añadir una comprobación

Los umbrales son constantes al principio de `audit.py`. Cambiarlos ahí los
cambia en todos los perfiles a la vez.

Para una comprobación nueva, añadila dentro de `audit_file` con
`report.error()`, `report.warn()` o `report.note()`, con un código propio y un
mensaje que **diga cómo arreglarlo**, no solo qué está mal.

Un hallazgo sin corrección concreta se ignora, y un informe que se ignora es
peor que no tenerlo.
