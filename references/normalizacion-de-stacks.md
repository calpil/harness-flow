# Normalización de stacks: qué repos, qué alcance y qué copias

Léelo cuando un repo del proyecto no reciba las rules o las skills de su stack,
cuando una regla no nombre el código del repo, cuando una copia instalada quede
distinta de la plantilla o cuando `stack.py verificar` diga algo que no esperas.

## Qué hace y qué no

`stack.py normalizar` instala en cada repo la norma de su stack: rules, skills,
`AGENTS.md` y validadores. No mueve código. El código que vive fuera de la
arquitectura del stack se mide con `arquitectura.py` y se corrige con features
de normalización (ver [`arquitectura-heredada.md`](arquitectura-heredada.md)).

| Parte | Quién la hace | Cuándo |
| --- | --- | --- |
| Instalar rules, skills, `AGENTS.md` y validadores | `stack.py normalizar` | En cada arranque de sesión (`estado.py`) y a mano |
| Ajustar el alcance de las reglas al código real | `stack.py normalizar` | En cada normalización |
| Actualizar una copia que quedó vieja | `stack.py normalizar` | Ver "Copias viejas" |
| Decir cuánto código vive fuera de la norma | `stack.py verificar`, `estado.py`, `arquitectura.py inventario` | Siempre |
| Llevar el código a la norma | Features `--kind normalizacion` | Decisión del usuario |

## Qué repos se normalizan

`stack.detectar_todos_los_destinos` da la lista. La usan la normalización, la
Feature #0, el trinquete y el brief.

- **La raíz del arnés.** Entra siempre que tenga stack, esté o no declarada en
  `harness/grafos.json`.
- **Las raíces de `harness/grafos.json`.**
- **Lo que cuelga de una carpeta sin stack.** Sus repos (`ms-*`, `frontend/` y
  `backend/`). Si ninguno tiene stack, los del nivel siguiente (`apps/web`,
  `apps/api`).
- **Una carpeta con otro stack dentro de un repo.** `api/` en Go dentro de un
  front, o `web/` en Angular dentro de un servicio.

No entran:

- **Una carpeta del mismo stack sin `.git` propio.** `tools/go.mod` dentro de un
  servicio Go es parte del servicio.
- **Un clon propio dentro de un repo.** Un servicio clonado o enlazado dentro de
  la raíz es otro repo. El arnés no escribe en él ni lo mide. Lo lista con
  `[!]` en el arranque de sesión y en `stack.py detectar`. Para normalizarlo:
  decláralo en `harness/grafos.json`, o corre `stack.py normalizar --repo <ruta>`.

Detección: un stack puede declarar `detection.requires_any` en su manifest. Si
ninguno de esos archivos existe, el repo no es de ese stack. Android lo usa: un
proyecto Gradle sin `AndroidManifest.xml` no es Android.

## El alcance de una regla sale del código del repo

Las plantillas traen `globs` con el layout canónico (`src/app/features/**`,
`internal/**`). Un repo cuyo código vive en otra ruta quedaba con una regla que
no lo nombraba. Caso medido: la regla apuntaba a `src/app/features/**` y el
código vivía en `projects/*/src/app/`.

`normalizar` mira primero dónde vive el código:

1. Toma los archivos versionados del repo con la extensión de código del stack
   (sale de `layout.codigo` del manifest: `go`, `ts`, `py`...).
2. Deja fuera lo de terceros (`node_modules`, `vendor`, `dist`...), las carpetas
   ocultas y los validadores que instala el arnés.
3. Compara con los `globs` de la plantilla. Si todo el código cabe, la regla se
   instala igual a la plantilla, byte a byte.
4. Si algún archivo queda fuera, agrega `**/*.<ext>` a los `globs` de ese repo.
   Los de la plantilla se conservan.

Se repite en cada normalización. Si mañana el código se muda a otra carpeta,
`verificar` reporta la regla como copia vieja y `normalizar` la corrige.

Aplica a las reglas que deben nombrar todo el código: `architecture.md` y
`security.md`. Un stack puede declarar otra lista en
`normative.rules_cubren_codigo`.

En Claude Code el campo que limita una regla a unas rutas es `paths`, no
`globs`: las reglas instaladas se cargan siempre. `globs` es el alcance que
leen los hosts que lo usan y el que declara la regla a quien la lee.

## Copias viejas y copias del proyecto

Una copia distinta de la plantilla puede ser dos cosas:

| Estado | Qué es | Qué hace `normalizar` |
| --- | --- | --- |
| Vieja | Una versión anterior que nadie editó | La actualiza |
| Modificada | El proyecto la editó | La conserva y lo avisa |

Lo distingue con dos pruebas, en este orden:

1. **El registro de lo instalado.** `<git-dir>/harness-flow-copias.json` guarda
   la huella de cada copia que el arnés dejó. Vive dentro de `.git`: no se
   versiona y no ensucia el árbol. Una copia con la huella del registro no la
   editó nadie.
2. **El historial git de la plantilla.** Una copia igual a una versión anterior
   de la plantilla no la editó nadie. Sirve para lo instalado antes de que
   existiera el registro.

Sin ninguna de las dos pruebas la copia no se toca. Pasa cuando la skill no es
un clon git y no hay registro.

- `stack.py normalizar --repo <r> --reemplazar` cambia por la plantilla también
  las copias modificadas. Es decisión del usuario.
- `stack.py verificar` reporta las viejas como hallazgo (`Copias
  desactualizadas`) y las modificadas como advertencia.
- Un `AGENTS.md` que el arnés no generó no se reemplaza nunca.

### En el arranque de sesión no se reescribe lo que el repo versiona

`gate.py close` no integra sobre un checkout con cambios sin commit. Por eso
`estado.py` actualiza solo las copias viejas que el repo no versiona. Las que sí
versiona quedan pendientes, y el arranque lo dice en una línea `[!]` con los
repos afectados. Para actualizarlas:

```bash
"$PY" "$H/stack.py" normalizar --repo <ruta>     # y commitea el cambio
```

Mientras tanto nadie lee la copia vieja por el arnés: el brief y `stack.py
skill` entregan la plantilla vigente cuando la copia del repo quedó vieja. La
copia que el proyecto editó sí se entrega: su edición manda.

## Worktrees

`normalizar` instala en el checkout principal. Un repo que no versiona esas
carpetas (un `.gitignore` con `.*`) daba worktrees sin rules ni skills.

`worktree.py start`, `worktree.py register` y el arranque de sesión enlazan al
worktree `.claude/rules`, `.claude/skills`, `.agents/rules`, `.agents/skills` y
`.gemini/rules` desde el checkout principal. Solo enlazan una carpeta que el
repo no versiona y que falta en el worktree. Una carpeta versionada la trae la
rama.

## `stack.py verificar` no da un OK sin medir

| Línea | Cuándo |
| --- | --- |
| `✅ COMPLIANT` | Instalación completa, sin violaciones, sin código fuera de la norma y sin avisos del verificador |
| `⚠️ INSTALACION CONFORME; ARQUITECTURA CON PENDIENTES` | Hay código fuera de la norma, o el verificador avisó que no midió algo |
| `❌ NON-COMPLIANT` | Falta instalar algo, hay copias viejas o el verificador encontró violaciones |

- `N archivos en M carpetas viven fuera de la norma`: código dentro del alcance
  del layout y fuera de su estructura. Es el mismo número de `arquitectura.py
  inventario`.
- `N archivos de código quedan fuera del alcance del layout`: tienen extensión
  de código y el layout no los mira (una librería en `projects/ui/src/lib`).
  No cuentan como dentro ni como fuera de la norma. `inventario --detalle` los
  lista por carpeta.
- Los avisos del verificador (`NO se midieron`) se muestran. Antes se perdían al
  traducir su exit 0 a un "OK".

El exit de `verificar` no cambió: 0 si la instalación y el verificador están
bien, 1 si no.

Sin trinquete adoptado, el arranque de sesión dice cuánto código vive fuera de
la norma: `arquitectura: [!] N archivos en M carpetas viven fuera de la norma
del stack y nada los frena`. Adoptarlo es decisión del usuario.

## Qué está garantizado y qué no

- **Garantizado**: cada repo de la lista recibe la norma de su stack; las reglas
  que cubren el código nombran todo el código del repo; una copia vieja se
  actualiza o se reporta; ningún "OK" tapa código fuera de la norma.
- **No garantizado**: que el código cumpla la arquitectura. Eso lo mide el
  trinquete y lo corrigen las features de normalización.
- **Límite conocido**: un repo JVM sin otra señal se detecta como
  `springboot-hexagonal`, y un repo Python como `python-dataproduct`, aunque use
  otro framework.

## Tests

[`tests/test_copias.py`](../tests/test_copias.py): alcance de las reglas, copias
viejas y modificadas, repos del proyecto, `verificar` y worktrees.
