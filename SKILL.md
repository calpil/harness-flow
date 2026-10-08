---
name: harness-flow
description: >-
  Gestiona features en repos con harness/feature_list.json: spec y AC aprobados,
  implementacion con evidencia, review, verify y cierre mediante gates Python.
  Tambien genera el vault Obsidian en docs/, PRD/SDD, Jira/Confluence y
  contexto de grafo y Memory Hub.
---

# Harness Flow

Proceso spec-driven para proyectos multi-repo. Puerto del arnés Rust (`harness_process`) a un agente: sin binario, sin instalador, sin compilar por SO. El proceso vive aquí; los gates son scripts Python que devuelven exit≠0.

**Host-neutral**: funciona igual en Hermes, Claude Code, GPT/Codex, AGY/Gemini, Grok y Kimi Code. Lo único que cambia son las herramientas del agente (subagente y escritura de skills); los scripts se autodetectan. Ver "Equivalencias por host".

**Idioma: responde SIEMPRE en español.** Los documentos generados van en español, sin tildes en los nombres de archivo.

## Layout

El arnés NO se copia a cada repo. Una instalación por PROYECTO (raíz multi-repo), no por microservicio:

```
~/proyectos/adr/                 <- raíz multi-repo = "proyecto" en el hub
  harness/                       <- estado del proceso (versionado)
    feature_list.json            <- backlog + rules
    grafos.json                  <- raices de graphify a combinar (opcional)
    progress/current-<id>.md     <- estado vivo por feature
    progress/archive/current-<id>.md <- progreso archivado al cerrar done
    progress/history.md          <- bitácora append-only
    atlassian.json               <- sitio/proyecto/space (NUNCA credenciales)
  docs/                          <- specs, borradores PRD/SDD, evidencia; prd/ es del usuario
  .agents/skills/                <- skills compartidas; Codex tambien admite .codex/skills
  docs/vault/                    <- notas generadas; el vault Obsidian es docs/
  graphify-out/                  <- grafo local (gitignored)
  ms-orders-service/             <- repo git propio = "microservicio"
  front-adr/
```

Credenciales del hub: `~/.harness-hub/.env` (fuera del repo, por máquina).

Los scripts viven en el directorio de esta skill y necesitan un intérprete con
las dependencias del hub (`psycopg`). Esa ruta cambia según el host, el SO y el
perfil, así que **no la hardcodees**: `entorno.py` la detecta.

```bash
# bash / zsh  (macOS, Linux)
eval "$(python3 <skill>/scripts/entorno.py --shell)"

# PowerShell (Windows)
python <skill>\scripts\entorno.py --powershell | Invoke-Expression
```

Eso define `H` (scripts), `PY` (intérprete con dependencias) y `HARNESS_HOST`
(`hermes`, `claude`, `gpt`, `gemini`, `grok` o `kimi`). A partir de ahí todos los comandos de este
documento funcionan tal cual en los tres SO y en los hosts soportados:

```bash
$PY "$H/estado.py"
```

En Codex, Claude Code y Grok las llamadas de terminal independientes no conservan
`$PY`, `$H` ni `HARNESS_HOST`. Pega el `eval` al comando, en la misma llamada.
En Codex fija el host incluso si `<skill>` es la ruta real del clone de Hermes:

```bash
eval "$(python3 <skill>/scripts/entorno.py --host codex --shell)"
"$PY" "$H/estado.py"
```

Repite ambas lineas en cada llamada, sustituyendo `estado.py` por el comando que
toque. En PowerShell repite la inicializacion con `--host codex --powershell`
y ejecuta con `& $PY`. Detalles en [`references/openai.md`](references/openai.md)
y [`references/grok.md`](references/grok.md).

Sin flags, `entorno.py` imprime un diagnóstico y sale con exit≠0 si no resuelve
un intérprete usable; `--instalar-deps` pone `psycopg` donde corresponde. Orden
de detección, `--host` y `HARNESS_PYTHON`: [`references/entorno.md`](references/entorno.md).

## Arranque de sesión

Al entrar a un proyecto con `harness/feature_list.json`, ANTES de responder nada sustantivo:

```bash
$PY "$H/estado.py"
```

Muestra features abiertas, gates pendientes y edad del grafo. Si hay una feature `in_progress`, retómala; no arranques otra.

Si dice `vault: ausente` o `vault: desactualizado` y el grafo esta fresco, regenera solo el panel de Obsidian. No relances graphify ni el hub:

```bash
$PY "$H/vault.py" build
```

Si el contexto esta vencido, `$PY "$H/contexto.py" refrescar` ya regenera ese panel. El detalle esta en "Obsidian". Grok no tiene el comando `/harness-flow:estado`: este arranque es el que sigue.

Al listar pendientes, contrasta el resumen con un conteo programatico de
`feature_list.json` por `status`. `estado.py` cuenta `todo`, `pending`,
`in_progress`, `blocked` y `review` como abiertas; solo `done` y `superseded`
como cerradas, con desglose separado. Los estados desconocidos o ausentes se
cuentan y muestran aparte: nunca calcules cierres como total menos abiertas.
No reescribas estados para cuadrar el resumen. Los gates y el aislamiento de
worktrees comprueban trabajo iniciado, no toda la cola pendiente.

## El flujo

Cuatro roles, en orden. No los saltes. El 0 solo corre cuando el proyecto no tiene PRD/SDD aprobados o el usuario pide cambiarlos.

La politica de modelos depende del proveedor de la tarea. Con OpenAI en Codex o
Hermes, Producto y Leader usan `gpt-6-astra`: **la skill elige el effort segun la
tarea antes de iniciar cada rol**, `medium` como base y `high` cuando hay riesgos
concretos de arquitectura, migracion, concurrencia o requisitos contradictorios.
Indica el nivel y su motivo en una frase y aplicalo en la invocacion del rol.
Criterios, resto de roles y configuracion por host: [`references/modelos.md`](references/modelos.md).
Con Claude 5.5, Producto, Leader y Cierre van fijos en `xhigh`; **el implementer y el
revisor reciben el effort que la skill elige por tarea**: implementer `high` y
`xhigh` ante un riesgo concreto; revisor `xhigh` en la primera ronda y `high` en la
de seguimiento. Se anuncia igual y se pasa en la invocacion (`effort` de la tool
`Agent`, o `claude -p --effort`).

### 0. Producto — PRD inicial y SDD de arquitectura, antes del backlog

El agente NUNCA escribe `docs/prd/**`: redacta en `docs/borrador-prd.md` / `docs/borrador-sdd.md` (rutas sin proteger) y el usuario es quien aprueba. `estado.py` muestra en que paso esta cada documento.

1. `$PY "$H/producto.py" borrador --doc prd|sdd` crea el borrador desde `templates/prd.md` / `templates/sdd.md`, o desde el cuerpo manual que ya exista. El PRD cuenta una historia (antes/despues, con nombre y momento), el flujo hoy/despues, los datos y el pseudo-codigo del acuerdo; NUNCA codigo final (un bloque ```go lo rechaza). Rellena cada seccion con lo que cuente el usuario; para el SDD cruza `contexto.py estado`, `hub.py impacto` y `leccion.py list`. Las guias `<!-- -->` se reemplazan: una seccion que solo tiene guia cuenta como vacia y la aprobacion se niega.
2. **Ritual de aprobacion**, el mismo del spec: MUESTRA el borrador, PREGUNTA, y solo con el SI explicito corre `$PY "$H/producto.py" aprobar --doc prd|sdd --yes`. Copia el cuerpo a `docs/prd/PRD-master.md` / `docs/sdd.md` conservando el bloque generado, y sella `documentos.<doc>` en el backlog; `gate.py check` acepta ese cuerpo por el sello hasta que el usuario lo commitea. Sin `--yes` se niega, y tambien con features multi-repo registradas abiertas (su registro fijo los bytes del PRD).
3. Cada `- F-n: nombre: resultado` de "Features candidatas" entra al backlog con `add.py --name "<nombre>" --prd docs/prd/PRD-master.md`; su spec se escribe en el rol 1.

### 1. Leader — spec antes que código

1. Lee el backlog y `progress/current-<id>.md`. Consulta el grafo antes de leer archivos a ciegas:
   `$PY "$H/contexto.py" brief --feature <id>` (indice compacto: AC, reglas, lecciones,
   impacto del hub y superficie de contacto del grafo). Si el contexto esta vencido lo dice;
   refresca con `$PY "$H/contexto.py" refrescar`. Para algo puntual: `codebase-memory-mcp`
   (`search_graph`, `trace_path`) o `graphify query "<pregunta>" --graph <combinado>`.
2. Consulta impacto cross-repo: `$PY "$H/hub.py" impacto --microservicio <proyecto>/<servicio>`.
3. Revisa lecciones aplicables: `$PY "$H/leccion.py" list` **antes** de diseñar.
4. Escribe `docs/spec-feature-<id>-<slug>.md` con `Estado: draft` usando `templates/spec.md`. Los AC-n en Given/When/Then son obligatorios.
5. Si los comandos de AC usan rutas de worktree, crea el worktree con `$PY "$H/worktree.py" start --feature <id>` antes de sellar el spec. Esto prepara las rutas; no autoriza implementar todavía.
6. **Ritual de aprobación**: MUESTRA el spec al usuario en el chat, PREGUNTA si lo aprueba, y solo con su SÍ explícito corre:
   `$PY "$H/gate.py" approve-spec --feature <id> --yes`
   Nunca apruebes por tu cuenta. El script se niega sin `--yes`.

### Enmienda — cambiar un spec que ya tiene trabajo encima

Con evidencia, review o verify encima, `approve-spec` se niega a re-sellar un spec cambiado: es una **enmienda**. Escribe `docs/propuesta-<id>-enmienda-<slug>.md` desde [`templates/enmienda.md`](templates/enmienda.md), aplica los cambios al spec, MUESTRA ambos y, solo con el SÍ explícito: `$PY "$H/gate.py" enmienda --feature <id> --propuesta docs/<propuesta>.md --yes`. Se niega si cambió un AC que la propuesta no nombra; numera `E-n`, la anota en el spec, sella spec y propuesta, y deja sin valor para `close` el review y el verify anteriores.

### 2. Implementer — evidencia por AC

1. Verifica el gate: `$PY "$H/gate.py" check-spec --feature <id>` (exit≠0 si no está approved o está stale).
2. Trabaja DENTRO del worktree de la feature; si aun no existe, crealo con `$PY "$H/worktree.py" start --feature <id>`.
3. Antes de editar, orientate con `codebase-memory-mcp` (`search_graph`, `trace_path`, `detect_changes`) en vez de leer a ciegas. Indexa la raiz, no tu worktree: confirma leyendo el archivo.
4. Escribe evidencia en `docs/impl-<id>.md`: una fila por AC-n citando `archivo:linea`. Commitea en la rama de la feature: el review diffea `base..HEAD`.

En Claude Code no implementa la sesion principal: `/harness-flow:implementar <id>` delega en el subagente `harness-flow:implementer` (`agents/implementer.md`) y contrasta su evidencia. En Hermes con modelos Claude y Claude Code instalado, `claude -p --agent harness-flow:implementer`; con OpenAI, usa el rol nativo y su configuracion en [`references/modelos.md`](references/modelos.md).

### 3. Reviewer — subagente aislado, veredicto sellado

El review NO lo haces tú mismo. Un revisor que recuerda haber escrito el código se aprueba solo; uno que solo ve spec + diff, no.

1. Arma el briefing: `$PY "$H/revision.py" --feature <id> --briefing`
2. Lanza el revisor con el subagente de tu host, pegando esa salida como contexto. Goal: "Revisa la feature #<id> y escribe docs/review-<id>.md". El subagente lee spec y código por su cuenta, no modifica nada más.
   - Hermes: con OpenAI, revisor nativo con el briefing completo y el modelo/effort de [`references/modelos.md`](references/modelos.md). Con modelos Claude y Claude Code instalado, `claude -p --agent harness-flow:revisor` con el briefing por stdin; si no, `delegate_task` con la salida en `context`.
   - Claude Code: la tool `Agent` con `subagent_type: harness-flow:revisor`, pegando la salida en el prompt.
     Ese subagente viene en la propia skill (`agents/revisor.md`); sin el, `general-purpose` sirve igual.
   - GPT/Codex: `codex exec` o el revisor/subagente disponible, pegando el briefing; si no hay aislamiento real, decláralo.
   - AGY / Gemini: `invoke_subagent` (tipo `research` o subagente definido), pegando el briefing en el prompt.
   - Grok: `spawn_subagent`. En `prompt`, el briefing entero mas "sigue el cuerpo de `<skill>/agents/revisor.md`; ignora su frontmatter". `isolation: none` (el acta queda en el worktree de la feature; `worktree` la escribiria en un worktree de Grok). No pases `resume_from`: hereda el historial. No uses `codex exec` ni `delegate_task`. Detalle en [`references/grok.md`](references/grok.md).
   NO uses un fork de la sesión como revisor: hereda tu historial y con él el sesgo que el aislamiento evita.
3. Cuando vuelva, LEE tú `docs/review-<id>.md`. El veredicto del subagente es un autoinforme: verifica que cada fila cite `archivo:linea` real antes de sellar.
4. Sella:
   `$PY "$H/gate.py" revision --feature <id> --veredicto approved|changes_requested|blocked`
   El script estampa `Revisado: ...` con la firma entera (veredicto · fecha ISO · autor ·
   `estampado por gate.py revision`). Un `Veredicto:` o un `Revisado:` tipeado a mano NO cuenta.
5. **Criterio y tope de rondas** (regla del usuario): `approved` = cada AC cumplido y medido, sin
   hallazgos bloqueantes ni mayores; menores e info van a Observaciones y NO abren ronda. La ronda
   siguiente solo verifica lo bloqueante/mayor de la anterior y los AC, sin buscar hallazgos nuevos
   (el briefing lo dice solo si ya hay un sello `changes_requested`/`blocked`). Tope: 2 rondas por
   feature; algo mayor nuevo en la segunda se escala al usuario, no abre una tercera. No le pidas
   al revisor "buscar mutantes nuevos": eso convierte cada ronda en una auditoria sin fin.

Si el subagente no está disponible, `$PY "$H/revision.py" --feature <id>` da el paquete y revisas tú — dicéndolo explícitamente, porque el rigor baja.

### 4. Cierre

Hay dos modos de cierre. En una raiz multi-repo sin `.git`, con worktrees ya
existentes, registra TODOS los microservicios y SHAs y valida una integracion
manual ya realizada; no inventes una rama o `.git` en la raiz. Contrato y
manifiesto: [`references/multirepo.md`](references/multirepo.md).

```bash
$PY "$H/worktree.py" register --feature <id> --manifest <registro.json>
# Tras la integracion externa autorizada, actualiza el registro y mide:
$PY "$H/gate.py" verify --feature <id>
$PY "$H/revision.py" --feature <id> --briefing
# Delega el review independiente, lee el acta y séllala:
$PY "$H/gate.py" revision --feature <id> --veredicto approved
$PY "$H/gate.py" close --feature <id> --status done --to <rama> \
  --integrated --postmerge /ruta/bases-postmerge.json --leccion <clase-existente>
```

`--integrated` no hace merges: comprueba repos, worktrees, limpieza, ancestria y
tips, y corre las suites completas de destino contra bases preintegracion
medidas. No acepta recibos PASS manuales ni sustituye spec, review, verify,
leccion, rutas protegidas o aislamiento. Cambiar el mapa o sus SHAs invalida
review y verify. El detalle por protocolo esta en la referencia.

En un monorepo Git sin registro multi-repo, `close` integra la rama de feature
con `git merge --no-ff` en la rama destino indicada por el usuario:

```bash
"$PY" "$H/gate.py" close --feature <id> --status done --to <rama> --leccion <clase>
# si harness/atlassian.json existe y el usuario pidio publicar remoto:
"$PY" "$H/gate.py" close --feature <id> --status done --to <rama> \
  --leccion <clase> --publicar-atlassian
```

El gate exige las reglas activas, aborta ante árbol sucio, rama ausente o
conflicto y deja el backlog intacto si falla. `done` archiva el progreso y
sincroniza PRD/SDD. Verifica el commit en la rama destino; el mensaje del script
no es evidencia de integración. Para publicar en Atlassian se requiere
`--publicar-atlassian` y el binding del proyecto.

## Gates (todos con exit≠0)

| Comando | Verifica |
| --- | --- |
| `gate.py check` | Todo el proceso; es el gate maestro |
| `gate.py check-spec --feature <id>` | Spec existe, `Estado: approved`, firma fresca |
| `gate.py approve-spec --feature <id> --yes` | Solo con SÍ del usuario; sella quién/cuándo. Se niega a re-sellar un spec cambiado con trabajo encima |
| `gate.py enmienda --feature <id> --propuesta <md> --yes` | Solo con SÍ del usuario; la propuesta nombra cada AC que cambió; deja sin valor el review y el verify anteriores |
| `producto.py aprobar --doc prd\|sdd --yes` | Solo con SÍ del usuario; borrador completo y sin bloque generado; copia al destino y sella |
| `gate.py revision --feature <id> --veredicto <v>` | Review responde por CADA AC-n con `archivo:linea` |
| `gate.py close --feature <id> --status done --to <rama>` | Todas las reglas activas |
| `postmerge_medido.py base --repo <r> --guardar <j>` | Foto medida de los rojos ANTES del merge |
| `postmerge_medido.py check --repo <r> --base <j>` | Rojos NUEVOS, build roto o tests desaparecidos (exit 2) |
| `postmerge_terraform.py base\|check ...` | Destinos Terraform (fmt, validate, `terraform test`); `close` lo despacha solo, ver `references/multirepo.md#contrato-terraform-fmt-validate-y-terraform-test` |

**Despues de cada `close ... --to <rama>`, corre `postmerge_medido.py`** (Go; en
Angular `postmerge_frontend.py`; en Terraform `postmerge_terraform.py`, que mide el
commit y no admite `--retirados`) sobre la rama destino. Los AC de una feature miden su worktree y no pueden ver los choques
entre features. El gate compara `(paquete, test)` contra la base pre-merge y solo
falla por rojos NUEVOS, asi que la deuda tolerada no lo vuelve inservible:

```bash
$PY "$H/postmerge_medido.py" base  --repo <ruta> --guardar /tmp/base-<svc>.json   # ANTES
$PY "$H/gate.py" close --feature <id> --status done --to develop --leccion <clase>
$PY "$H/postmerge_medido.py" check --repo <ruta> --base /tmp/base-<svc>.json      # DESPUES
```

`postmerge.py` (el gate viejo de regex) **no sirve como gate**: da VERDE con un
paquete que no compila, un `panic` en `init()` o tests borrados. Usa siempre la
version medida (por que, en `references/lecciones-del-arnes.md`).

Si aparecen rojos nuevos: ficha el choque, no bajes la asercion que lo detecto.
Al verificar el exit a mano no uses un pipe (`| tail`): te devuelve el status
del tail, no el del gate.

Reglas en `harness/feature_list.json` → `rules`: `require_spec_approved`, `require_review`, `require_leccion`, `require_verify_green`, `require_docs_al_dia`.

**Rutas protegidas**: `docs/prd/**`, `docs/constitution.md`, `.env`. Son del USUARIO. Ningún agente las reescribe a mano — `documentacion.py sync` solo actualiza el bloque generado `harness-flow:features`, y `gate.py check` reporta violaciones fuera de ese contrato. La otra via, la unica que cambia el cuerpo manual del PRD, es el sello de `producto.py aprobar --yes` (`documentos.prd`): el usuario aprobo ESE cuerpo en el chat y vale hasta que lo commitea.

## Contexto y memoria del proyecto

Antes de diseñar, consulta el brief y las lecciones aplicables. El grafo debe
estar fresco; si no, refresca y revisa el parte antes de confiar en él. Las
raíces de microservicios se declaran en `harness/grafos.json`, nunca se adivinan.

```bash
$PY "$H/contexto.py" estado
$PY "$H/contexto.py" brief --feature <id>
$PY "$H/contexto.py" refrescar
$PY "$H/hub.py" impacto --microservicio <proyecto>/<servicio>
$PY "$H/leccion.py" list
```

El Memory Hub y `codebase-memory-mcp` son opcionales para los gates locales.
Detalles de refresco, cobertura y fallos: [`references/contexto.md`](references/contexto.md)
y [`references/hub.md`](references/hub.md).

Las lecciones son skills reutilizables por clase de trabajo. Lee las aplicables
y patchea una existente antes de crear otra. El cierre exige que la lección
indicada exista. Hermes las crea con `skill_manage`; los demás hosts usan su raíz
nativa. Rutas y precedencia: [`references/hosts.md`](references/hosts.md).

## PRD/SDD y Obsidian

`documentacion.py sync` mantiene el bloque generado de `docs/prd/PRD-master.md`
y `docs/sdd.md`; nunca reescribas su contenido manual. El cierre `done` ejecuta
el sync. Para el flujo de aprobación del PRD/SDD, consulta
[`references/documentacion.md`](references/documentacion.md).

Abre `docs/` como vault de Obsidian. Las notas se generan en `docs/vault/` y
ningún rol las usa como evidencia o contexto de implementación. Ejecuta
`$PY "$H/vault.py" build` tras escribir spec, evidencia o review si no vas a
hacer `start` o `close` enseguida. Detalles: [`references/obsidian.md`](references/obsidian.md).

## Integraciones por host y herramientas externas

La skill es portable, pero la instalación, el shell y el revisor dependen del
host. Usa la referencia correspondiente antes de ejecutar comandos específicos:
[`references/openai.md`](references/openai.md),
[`references/claude.md`](references/claude.md),
[`references/grok.md`](references/grok.md) y
[`references/kimi.md`](references/kimi.md).

Jira/Confluence solo se usa si existe `harness/atlassian.json` y el usuario
solicita publicar. No inventes el binding ni publiques por defecto; consulta
[`references/atlassian.md`](references/atlassian.md).

## Reglas duras

- Todo hallazgo relevante se escribe en `harness/progress/`. Una respuesta en el chat no reemplaza evidencia persistida.
- `gate.py verify` corre en el WORKTREE de la feature cuando existe. Si el
  worktree declarado no existe, **bloquea** en vez de caer a la raíz; sin
  worktree, avisa que mide la raíz. Un rojo o un verde sobre el árbol
  equivocado no es un veredicto sobre el código.
- **La feature sale de `rules.rama_base` (por defecto `develop`), no del HEAD del
  repo.** `worktree.py start` crea la rama desde ese SHA (aborta si una rama que
  ya existía no desciende de la base) y la registra en `base_branch`/`base_sha`;
  `revision.py` diffea contra `merge-base base HEAD`, no `HEAD~1`. `--base <rama>`
  para un caso puntual.
- Con features paralelas, usa worktrees independientes para los AC, reserva las migraciones contra la rama de integración y corre la suite completa de destino después de cada cierre. `verify` mide los AC del worktree, no la integración. Reglas y casos límite: [`references/multirepo.md`](references/multirepo.md).
- El cuerpo manual del PRD y la constitution son del USUARIO. No los reescribas; `documentacion.py sync` solo puede tocar su bloque generado `harness-flow:features`.
- Aislamiento: una feature sin worktree bloquea a las demás sin worktree.
- No afirmes lo que no puedes comprobar. Si un gate no corrió, dilo.
- Los AC pueden declarar su comando de dos formas, ambas válidas:
  `- AC-1: ... \`verificar: pytest -q\`` o una línea `Comando: \`pytest -q\`` debajo del AC.
- La evidencia cubre un AC si la cita `archivo:linea` está en la **sección** del AC
  (encabezado `## AC-1` con la cita debajo), no necesariamente en la misma línea.
  Prosa sin cita nunca cuenta. Una **mención** del AC en medio de una frase no abre
  sección: sólo las líneas que lo **declaran** (`## AC-1`, `- AC-1:`, `| AC-1 |`).
- `verify` sólo mide los AC que declaran comando: con 12 AC y 3 comandos, un
  `3/3 en verde` **no** dice nada de los otros 9. Los lista como `NO se midieron`,
  `close` los repite como aviso, y ese hueco lo cubre la revisión.
- `close` rechaza un `last_verify` que midió otro número de AC, y un verify o un
  review sellados antes de la última enmienda: si el spec cambió después de
  medir o de revisar, hay que re-correr `verify` y lanzar un review nuevo. Como
  `approve-spec` ya no re-sella un spec con trabajo encima, la única vía para
  cambiarlo es `gate.py enmienda`, que es la que invalida lo anterior.
- `psycopg` va en el intérprete que resuelve `entorno.py` (`$PY`): un
  `ModuleNotFoundError: psycopg` en `hub.py` casi siempre es `python3` en vez de
  `$PY`. Arreglo en [`references/entorno.md`](references/entorno.md).

## Auditoría del arnés

Antes de cambiar gates, lee [`references/lecciones-del-arnes.md`](references/lecciones-del-arnes.md).
Esa referencia también describe cómo ejecutar la suite y evaluar las regresiones.

## Equivalencias por host

| Necesitas | Hermes | Claude Code | GPT/Codex | AGY / Gemini | Grok | Kimi Code |
| --- | --- | --- | --- | --- | --- | --- |
| Implementer | sesion o `claude -p --agent` | `Agent` (`harness-flow:implementer`) | sesion | sesion | sesion | sesion |
| Revisor | `claude -p --agent` o `delegate_task` | `Agent` | `codex exec` o subagente | `invoke_subagent` | `spawn_subagent` | `Agent` o `kimi -p` |
| Crear lección | `skill_manage` | `leccion.py donde` | `leccion.py donde` | `leccion.py donde` | `leccion.py donde` | `leccion.py donde` |
| Guía del host | — | [`claude.md`](references/claude.md) | [`openai.md`](references/openai.md) | `entorno.py` | [`grok.md`](references/grok.md) | [`kimi.md`](references/kimi.md) |

Los gates, worktrees, specs, memoria y documentación usan los mismos scripts
Python. Si no hay revisor aislado, puedes revisar localmente con
`revision.py --feature <id>`, pero declara que el aislamiento no se logró.

## Referencias (cargalas cuando hagan falta, no antes)

| Archivo | Cuando leerlo |
| --- | --- |
| [`references/entorno.md`](references/entorno.md) | `entorno.py` no resuelve el interprete o el host, falta `psycopg` |
| [`references/multirepo.md`](references/multirepo.md) | raiz multi-repo sin `.git`: registro, `--integrated`, postmerge medido |
| [`references/contexto.md`](references/contexto.md) | varias raices de grafo, el parte de `refrescar`, algo del contexto no cuadra |
| [`references/lecciones-del-arnes.md`](references/lecciones-del-arnes.md) | **antes de tocar o escribir un gate** |
| [`references/hosts.md`](references/hosts.md) | raíces de skills y creación de lecciones por host |
| [`references/hub.md`](references/hub.md) | esquema del hub, `derivar-graphify`, credenciales |
| [`references/obsidian.md`](references/obsidian.md) | que genera el vault, config sembrada, `--con-grafo` |
| [`references/atlassian.md`](references/atlassian.md) | mapeo a Jira/Confluence y sus comandos |
| [`references/claude.md`](references/claude.md) | Claude Code: plugin, comandos, Windows, raices de lecciones |
| [`references/modelos.md`](references/modelos.md) | modelo por proveedor y rol; seleccion automatica de effort para Producto/Leader en Codex y Hermes, y para implementer/revisor con Claude 5.5 |
| [`references/openai.md`](references/openai.md) | GPT/Codex: instalacion, deteccion y raices |
| [`references/grok.md`](references/grok.md) | Grok: host, revisor con `spawn_subagent`, lecciones en `~/.grok/skills`, vault |
| [`references/kimi.md`](references/kimi.md) | Kimi Code: host, plugin, revisor y lecciones |
| [`references/documentacion.md`](references/documentacion.md) | rol producto (PRD inicial / SDD de arquitectura), su sello y como se sincronizan |
