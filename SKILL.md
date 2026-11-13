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

En Codex, Claude Code, AGY / Gemini y Grok las llamadas de terminal independientes no conservan
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

Muestra features abiertas, gates pendientes, edad del grafo y en que paso estan el PRD y el SDD (`prd:`/`sdd:`, mas `candidatas:` con la feature de cada `F-n`). Si hay una feature `in_progress`, retómala; no arranques otra. Si falta un documento que exige `require_docs_al_dia`, el siguiente paso es el rol 0, no un spec: `approve-spec` se negaria.

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

Cuatro roles, en orden. No los saltes. El 0 solo corre cuando el proyecto no tiene PRD/SDD aprobados o el usuario pide cambiarlos. Mientras la regla `require_docs_al_dia` los exija (por defecto `["prd", "sdd"]`; `true` = solo el PRD), `approve-spec` se niega a sellar una feature sin ellos; `--kind bug|task` no los exige. Apagarla (`false`) es decision del USUARIO, nunca del agente.

La politica de modelos depende del proveedor de la tarea. Con OpenAI en Codex o
Hermes, Producto y Leader usan `gpt-6-astra`: **la skill elige el effort segun la
tarea antes de iniciar cada rol**, `medium` como base y `high` cuando hay riesgos
concretos de arquitectura, migracion, concurrencia o requisitos contradictorios.
Indica el nivel y su motivo en una frase y aplicalo en la invocacion del rol.
Criterios, resto de roles y configuracion por host: [`references/modelos.md`](references/modelos.md).
Con Claude, **Producto y Leader corren en Fable 5.2 (`high`) o en Opus 5.5 (`xhigh`): lo
elige el USUARIO en un formulario, una vez por feature** (`$PY "$H/modelo.py" ver|elegir`);
si la sesion esta en otro modelo, el rol se detiene y pide `/model`. Cierre va fijo en
Opus 5.5 `xhigh`; **el implementer y el revisor reciben el effort que la skill elige por tarea**: implementer `high` y
`xhigh` ante un riesgo concreto; revisor `xhigh` en la primera ronda y `high` en la
de seguimiento. Se anuncia igual y se pasa en la invocacion (`effort` de la tool
`Agent`, o `claude -p --effort`).
Con Gemini 4 (`Hydrogen` / `Argon`) en AGY o Hermes, la sesion y los subagentes
corren con el nivel elegido en la sesion (`high`, p.ej. `Gemini 4 Hydrogen (High)` o
`Gemini 4 Argon (High)`); en AGY los subagentes se lanzan con `Model: "inherit"`
y `TypeName: "self"` (sin override por llamada de `effort`), y en Hermes se
anuncia el esfuerzo antes de cada rol (detalle y limite actual de
`_build_gemini_thinking_config` en [`references/modelos.md`](references/modelos.md)).

### 0. Producto — PRD inicial y SDD de arquitectura, antes del backlog

El agente NUNCA escribe `docs/prd/**` ni `docs/sdd.md`: redacta en `docs/borrador-prd.md` / `docs/borrador-sdd.md` (rutas sin proteger) y el usuario es quien aprueba. `estado.py` muestra en que paso esta cada documento.

1. `$PY "$H/producto.py" borrador --doc prd|sdd` crea el borrador desde `templates/prd.md` / `templates/sdd.md`, o desde el cuerpo manual que ya exista. No inventes requisitos: si algo falta, pregunta **una pregunta a la vez con tu respuesta sugerida** (estilo `/backlog` de `hola-ai`). El PRD cuenta una historia (antes/despues, con nombre y momento), el flujo hoy/despues, los datos y el pseudo-codigo del acuerdo; NUNCA codigo final (un bloque ```go lo rechaza). El comando imprime además los **stacks de todos los repos del proyecto**: para el SDD, con sus restricciones de arquitectura, el texto completo de sus reglas y el índice de sus skills; para el PRD, solo qué stack hay en cada repo (`$PY "$H/contexto.py" stacks` lo repite), con la documentación vigente de cada stack (Context7 y doc oficial). Imprime también el bloque **`NORMAS DE INGENIERIA`** del documento: lo que cada norma pide dejar escrito en el PRD (casos de abuso, volumen, objetivos y no-objetivos) o en el SDD (persistencia y consistencia, fronteras de confianza, estrategia de errores, versiones del stack, patrones solo con eje real). El SDD no contradice esas reglas: una decisión que se aparte va como `D-n` con su alternativa descartada. Para el SDD cruza `contexto.py estado`, `hub.py impacto` y `leccion.py list`, pregunta solo si aplica alguna de las **4 decisiones caras de cambiar** (multi-tenant/org, permisos/roles, offline/sync, multi-idioma/moneda), aplica YAGNI al resto y nombra cada decision (`- D1: ... Descartada: <opcion>, porque ...`). Las guias `<!-- -->` se reemplazan: una seccion que solo tiene guia cuenta como vacia y la aprobacion se niega.
2. **Ritual de aprobacion**, el mismo del spec: MUESTRA el borrador, PREGUNTA, y solo con el SI explicito corre `$PY "$H/producto.py" aprobar --doc prd|sdd --yes`. Copia el cuerpo a `docs/prd/PRD-master.md` / `docs/sdd.md` conservando el bloque generado, y sella `documentos.<doc>` en el backlog; `gate.py check` acepta ese cuerpo por el sello hasta que el usuario lo commitea. Sin `--yes` se niega, y tambien si una feature multi-repo registrada abierta fijo los bytes de ese documento. Si al re-aprobar hay specs abiertos aprobados contra la version anterior, los lista: el leader los revisa.
3. **Candidatas como rebanadas verticales (`Vertical Slice` / `/backlog`)**: `F-1` es un *walking skeleton* punta a punta (sin mocks). Corta cada `- F-n: nombre: resultado (cumple O1; requiere: F-m)` (10–15 candidatas maximo, una linea sin estimaciones ni detalles tecnicos) por comportamiento observable del usuario (`UI/API -> logica -> datos -> tests`), NUNCA por capa horizontal ni como historia del sistema, y usa *expand–contract* para refactors amplios. Declara bloqueos con `requiere: F-m` solo cuando una historia no tiene sentido sin otra (`producto.py` valida que existan y no formen ciclos). Cada una entra al backlog con `add.py --name "<nombre>" --prd docs/prd/PRD-master.md --candidata F-n` (que hereda sus bloqueos o recibe `--requiere`); su spec se escribe en el rol 1. Detalles en [`references/vertical-slice.md`](references/vertical-slice.md).

### 1. Leader — spec antes que código

1. Lee el backlog y `progress/current-<id>.md`. Prioriza la **frontera** (features sin bloqueos `requiere` pendientes en `estado.py`). Consulta el grafo antes de leer archivos a ciegas:
   `$PY "$H/contexto.py" brief --feature <id>` (indice compacto: AC, costuras, bloqueos, reglas, lo que el PRD/SDD
   dice de la feature —su `F-n`, objetivos `O-n`/`NO-n` y decisiones `D-n`—, lecciones,
   impacto del hub, superficie de contacto del grafo y el stack de CADA repo que la feature declara —front y backend—, con el **texto completo de sus reglas** y el **índice de sus skills** al final: los AC y el plan no las contradicen). Si el contexto esta vencido lo dice;
   refresca con `$PY "$H/contexto.py" refrescar`. Para algo puntual: `codebase-memory-mcp`
   (`search_graph`, `trace_path`) o `graphify query "<pregunta>" --graph <combinado>`.
2. Consulta impacto cross-repo: `$PY "$H/hub.py" impacto --microservicio <proyecto>/<servicio>`.
3. Revisa lecciones aplicables: `$PY "$H/leccion.py" list` **antes** de diseñar.
4. Escribe `docs/spec-feature-<id>-<slug>.md` con `Estado: draft` usando `templates/spec.md` (`add.py` ya lo crea desde ahi, estilo `/story` de `hola-ai`). Apunta a **2–3 AC** en Given/When/Then (tope en `rules.max_acs_por_slice = 5`; si necesita mas, propon al usuario partir la historia en nuevas `F-n`: los cortes entran al backlog solo con su SI, `add.py --yes --peso`), declara en cada AC su **costura publica de prueba** (`[costura: endpoint|servicio|ui|integracion|manual]` o `Costura: ...` debajo, en el nivel practico mas alto, sin acoplar a detalles internos/mocks), define `## Plan vertical` (≤5 bullets sin codigo ni nombres de archivos) y `## Sugerencias (decision del usuario)` solo si hay senal concreta en el codigo actual. El Contexto cita lo que cumple del PRD (`cumple: O1`) y las decisiones del SDD que aplica (`decisiones que aplica: D2`); `approve-spec` avisa si no cita ninguna, si excede el tamano del slice o si falta costura. **AC negativos**: todo AC que expone un endpoint o una accion con permisos lleva al menos un AC marcado `[negativo]` (sin permiso, entrada invalida, fuera de limite); `approve-spec` avisa si falta y el revisor lo marca como hallazgo mayor. Mientras el spec no esta sellado, el brief trae en el bloque **`NORMAS DE INGENIERIA`** lo que cada norma pide dejar escrito en el spec (`en el spec: ...`): idempotencia y concurrencia, esquema de salida de un LLM, version de un contrato compartido, librerias nuevas.
5. Si los comandos de AC usan rutas de worktree, crea el worktree con `$PY "$H/worktree.py" start --feature <id>` antes de sellar el spec. Esto prepara las rutas; no autoriza implementar todavía.
6. **Ritual de aprobación**: MUESTRA el spec al usuario en el chat, PREGUNTA si lo aprueba, y solo con su SÍ explícito corre:
   `$PY "$H/gate.py" approve-spec --feature <id> --yes`
   Nunca apruebes por tu cuenta. El script se niega sin `--yes`. La primera aprobación deja la feature en **modo pair** en el backlog: desde ahí `close` exige la lista de tests sellada, llegue la feature al código por `worktree.py start`, por `worktree.py register` o por un árbol armado a mano. Delegar es decisión del usuario: `$PY "$H/worktree.py" modo --feature <id> --delegado`.
   El sello guarda contra que PRD/SDD se aprobo el spec. Si despues cambian, `estado.py`,
   `gate.py check`, el brief y `close` lo avisan: el leader lo revisa; si un AC deja de valer
   es una enmienda, y si sigue valiendo se re-aprueba con el SI del usuario.

### Enmienda — cambiar un spec que ya tiene trabajo encima

Con evidencia, review o verify encima, `approve-spec` se niega a re-sellar un spec cambiado: es una **enmienda**. Escribe `docs/propuesta-<id>-enmienda-<slug>.md` desde [`templates/enmienda.md`](templates/enmienda.md), aplica los cambios al spec, MUESTRA ambos y, solo con el SÍ explícito: `$PY "$H/gate.py" enmienda --feature <id> --propuesta docs/<propuesta>.md --yes`. Se niega si cambió un AC que la propuesta no nombra; numera `E-n`, la anota en el spec, sella spec y propuesta, y deja sin valor para `close` el review y el verify anteriores.

### Hallazgos — enmienda antes que ficha

Un hallazgo del código (en un spec, al implementar, en un review, al cerrar) **no abre una ficha**: cada ficha paga spec, lista de tests, review, verify y cierre. Va, en este orden: (1) a la feature en curso que toca ese código: se arregla en su rama, y si cambia un AC es una enmienda; (2) a otra feature abierta que lo cubre: `$PY "$H/hallazgo.py" anotar --feature <id> --texto "<una línea>"`; (3) al proyecto, si ninguna lo cubre: el mismo comando sin `--feature`. El brief de cada feature muestra los suyos y los del proyecto que tocan sus repos, y `close` se niega mientras la feature tenga hallazgos abiertos (`hallazgo.py resolver --id H-n --como "<AC-n, E-n o commit>"`, o `mover`).

Una **ficha nueva la decide el usuario** y solo con peso propio: un comportamiento nuevo que ve el usuario del producto, o un riesgo de plata, datos o seguridad que no espera a otra feature. `add.py` se niega sin `--yes --peso "<por qué es ficha y no enmienda>"`, salvo la primera ficha de una candidata `F-n` del PRD y una normalización con el trinquete adoptado. Si le preguntas al usuario, la primera opción es el destino sin ficha; no recomiendes la ficha si el hallazgo cabe en una feature abierta. Partir una feature en cortes es una propuesta, no un alta. Detalle en [`references/hallazgos.md`](references/hallazgos.md).

### 2. Implementer — TDD vertical y modo Pair (por defecto)

1. Verifica el gate: `$PY "$H/gate.py" check-spec --feature <id>` (exit≠0 si no está approved o está stale; avisa bloqueos `requiere` y alertas de slice).
2. Trabaja DENTRO del worktree de la feature; si aun no existe, crealo con `$PY "$H/worktree.py" start --feature <id>`.
   Lee el brief ENTERO (`start` lo imprime; `$PY "$H/contexto.py" brief --feature <id>` lo repite) antes de escribir: trae el modo registrado, el **texto de las reglas de cada stack**, el **índice de sus skills**, la **documentación vigente** del stack (Context7 y doc oficial) y el bloque **`NORMAS DE INGENIERIA`**. Esas normas son obligatorias en modo pair y en delegado, en cualquier host: es la misma lista que audita el revisor, y su violación es hallazgo bloqueante o mayor. Si delegas en un subagente, pégale el brief completo.
   **El brief es el paquete completo de quien implementa, delegado o no.** Trae el protocolo (TDD vertical y las 5 paradas), el texto de las reglas de cada stack, el índice de sus skills y las normas de ingeniería, cada uno con el **comando que imprime el contenido** (`stack.py skill <nombre> --stack <id>`, `normas.py --ref <id>`). Esos comandos llevan el intérprete y el script con ruta absoluta: funcionan en un subagente que no tiene `$PY`/`$H` ni permiso para abrir archivos fuera del proyecto. Al delegar pega el brief ENTERO y nada más: no anexes skills ni referencias a mano, ni guardes en tu memoria que hay que anexarlas.
3. Antes de editar, orientate con `codebase-memory-mcp` (`search_graph`, `trace_path`, `detect_changes`) en vez de leer a ciegas. Indexa la raiz, no tu worktree: confirma leyendo el archivo.
4. **Bucle TDD vertical (prohibido el TDD horizontal)**: avanza **un test a la vez** (`1 test en la costura publica -> Red -> codigo minimo -> Green -> Refactor en verde`), con el valor esperado tomado del AC (nunca calculado con la misma logica que el codigo) y separando los commits funcionales de los de refactor puro. Emite micro-reportes concisos bajo norma ASD-STE100 (frases <= 20 palabras, voz activa y comprobabilidad en < 5 min; ver [`references/comunicacion-ste100-y-prompts.md`](references/comunicacion-ste100-y-prompts.md)). Las **5 paradas de `/pair`**: (a) decision de diseno no prevista en el plan/spec: **pregunta**; (b) alcance que ningun AC pide (YAGNI): **no lo agregues**, anotalo como hallazgo y sigue; (c) cambiar/saltar/borrar un test para que pase: **pregunta**; (d) **dos intentos** sin llegar a verde: vuelve al ultimo verde y **pregunta**; (e) paso que supera **~50 lineas o 3 archivos**: **partelo tu** y sigue.
5. **Dos modos de ejecucion** (detalle en [`references/vertical-slice.md`](references/vertical-slice.md)):
   - **Modo Pair automático, por defecto en cualquier repo**: no depende de que se detecte un stack ni de cómo se arme el árbol. `gate.py approve-spec` deja el modo en el backlog al sellar el spec por primera vez, `worktree.py start` lo confirma (`pair` salvo `--delegado`) y el brief lo repite. La IA implementa en la sesión principal (TDD vertical: `1 test -> Red -> código mínimo -> Green -> Refactor en verde`) y **avanza ciclo tras ciclo sin preguntar si sigue**. Antes de escribir código escribe la **lista de tests** (solo nombres y costura) en `docs/tests-<id>.md`, la sella ella misma con `$PY "$H/gate.py" sellar-tests --feature <id>`, la muestra en el chat y empieza: no espera aprobación. **`close` se niega sin ese sello fresco**: si la lista crece, se vuelve a sellar sin preguntar. El gate exige `--yes` (el SÍ del usuario) solo si la lista quita un test sellado o deja un AC solo con verificación manual que el spec no declara `[costura: manual]`.
   - **Subagente delegado (solo si el usuario lo pide con `--delegado`, o si la sesión no tiene usuario)**: `worktree.py start --delegado`, o `worktree.py modo --feature <id> --delegado` si ya estaba arrancada. No exige lista de tests: en Claude Code `/harness-flow:implementar <id>` delega en `harness-flow:implementer` (`agents/implementer.md`) y contrasta su evidencia; en Hermes con Claude Code usa `claude -p --agent harness-flow:implementer`, y con OpenAI/Gemini usa el rol segun [`references/modelos.md`](references/modelos.md).
   - **Cuándo un formulario hace falta en modo Pair**: en las paradas (a), (c) y (d); al quitar un test sellado o dejar un AC solo manual; en lo que sella el usuario (enmienda, ficha nueva, el cierre o la publicación que el proyecto reserve); y al final, para los AC de verificación manual. **No se pregunta** si se sigue con el test siguiente, el orden o el nombre de los tests, el mensaje de un commit (se commitea en la rama de la feature, funcionalidad y refactor por separado), un refactor en verde dentro de los archivos de la feature, ni cómo partir un paso. Las preguntas pendientes van juntas en **un** formulario, con la recomendada primero; mientras llega la respuesta se sigue con lo que no depende de ella. Una enmienda es un solo formulario, con la propuesta ya escrita. Si el usuario pide **"paso a paso"**, se pausa tras cada ciclo (`"haz N"` ejecuta `N` ciclos).
   - **Varias features en paralelo**: si el usuario lo pide y el host tiene subagentes, un implementer por feature, cada uno en su worktree y con su brief entero. El modo sigue siendo `pair`: cada uno escribe su lista de tests y la sesión principal la sella. Un subagente no pregunta al usuario: devuelve la parada, y la sesión principal la responde desde el spec o la lleva al usuario junto con las demás.
6. Escribe evidencia en `docs/impl-<id>.md`: una fila por AC-n citando `archivo:linea`. Commitea en la rama de la feature: el review diffea `base..HEAD`.

### 3. Reviewer — subagente aislado, veredicto sellado

El review NO lo haces tú mismo. Un revisor que recuerda haber escrito el código se aprueba solo; uno que solo ve spec + diff, no.

1. Arma el briefing: `$PY "$H/revision.py" --feature <id> --briefing`. Trae, para cualquier host, la lista completa de normas a auditar (datos, diseño, refactor, rendimiento, IA, servicios, construcción, seguridad OWASP, versiones y Context7), el texto de las reglas de cada stack y su documentación vigente: no dependas de un prompt de subagente propio de tu host para tenerlas.
2. Lanza el revisor con el subagente de tu host, pegando esa salida como contexto. Goal: "Revisa la feature #<id> y escribe docs/review-<id>.md". El subagente lee spec y código por su cuenta, no modifica nada más.
   - Hermes: con OpenAI, revisor nativo con el briefing completo y el modelo/effort de [`references/modelos.md`](references/modelos.md). Con modelos Claude y Claude Code instalado, `claude -p --agent harness-flow:revisor` con el briefing por stdin; si no, `delegate_task` con la salida en `context`.
   - Claude Code: la tool `Agent` con `subagent_type: harness-flow:revisor`, pegando la salida en el prompt.
     Ese subagente viene en la propia skill (`agents/revisor.md`); sin el, `general-purpose` sirve igual.
   - GPT/Codex: `codex exec` o el revisor/subagente disponible, pegando el briefing; si no hay aislamiento real, decláralo.
   - AGY / Gemini: `invoke_subagent` con `TypeName: "self"` (o un subagente definido con `define_subagent` y `EnableWriteTools: true`), `Model: "inherit"` y `Workspace: "inherit"`, pegando el briefing entero más "sigue el cuerpo de `<skill>/agents/revisor.md`; ignora su frontmatter". NO uses `TypeName: "research"`: es de solo lectura y no puede correr los comandos de los AC ni escribir `docs/review-<id>.md`.
   - Grok: `spawn_subagent` con `isolation: none` y el briefing entero en `prompt`, más "sigue el cuerpo de `<skill>/agents/revisor.md`; ignora su frontmatter". `background` devuelve un id al instante: espera con `get_command_or_subagent_output` antes de leer el acta o sellar. `revision.py` y `gate.py revision` corren en el mismo cwd; de ahí `find_root()` saca `docs/review-<id>.md`. Un `isolation: worktree` o un `cwd` distinto deja el acta fuera del gate. Sin `resume_from`, sin effort en la tool, sin `codex exec` ni `delegate_task`. Procedimiento en [`references/grok.md`](references/grok.md).
   NO uses un fork de la sesión como revisor: hereda tu historial y con él el sesgo que el aislamiento evita.
3. Cuando el subagente haya terminado, LEE tú `docs/review-<id>.md`. El veredicto del subagente es un autoinforme: verifica que cada fila cite `archivo:linea` real antes de sellar.
4. Sella:
   `$PY "$H/gate.py" revision --feature <id> --veredicto approved|changes_requested|blocked`
   El script estampa `Revisado: ...` con la firma entera (veredicto · fecha ISO · autor ·
   `estampado por gate.py revision`). Un `Veredicto:` o un `Revisado:` tipeado a mano NO cuenta.
5. **Criterio y tope de rondas** (regla del usuario): `approved` = cada AC cumplido y medido, sin
   hallazgos bloqueantes ni mayores; menores e info van a Observaciones y NO abren ronda ni ficha
   (se arreglan en la rama o se anotan con `hallazgo.py`). La ronda
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
| `gate.py approve-spec --feature <id> --yes` | Solo con SÍ del usuario; sella quién/cuándo y contra qué PRD/SDD, y en la primera aprobación deja la feature en modo pair. Se niega a re-sellar un spec cambiado con trabajo encima, y sin el PRD/SDD que exige `require_docs_al_dia` |
| `gate.py sellar-tests --feature <id>` | Modo pair: la sella quien implementa, sin formulario, si la lista (`docs/tests-<id>.md`) declara al menos un test por AC. Exige `--yes` (SÍ del usuario) si quita un test sellado o deja un AC solo con verificación manual que el spec no declara. `aprobar-tests` es el nombre anterior y sigue valiendo. `close` exige ese sello fresco en las features en modo pair |
| `gate.py enmienda --feature <id> --propuesta <md> --yes` | Solo con SÍ del usuario; la propuesta nombra cada AC que cambió; deja sin valor el review y el verify anteriores |
| `producto.py aprobar --doc prd\|sdd --yes` | Solo con SÍ del usuario; borrador completo y sin bloque generado; copia al destino y sella |
| `gate.py revision --feature <id> --veredicto <v>` | Review responde por CADA AC-n con `archivo:linea` |
| `gate.py close --feature <id> --status done --to <rama>` | Todas las reglas activas, y que la feature no tenga hallazgos anotados sin resolver |
| `add.py --name "<n>" --yes --peso "<por qué>"` | Solo con SÍ del usuario; una ficha nueva dice por qué no es una enmienda. Sin `--yes` entran la primera ficha de una candidata `F-n` y una normalización con trinquete |
| `hallazgo.py anotar\|list\|mover\|resolver` | Lo que se encuentra en el código va a una feature abierta o al proyecto, no a una ficha. Ver `references/hallazgos.md` |
| `postmerge_medido.py base --repo <r> --guardar <j>` | Foto medida de los rojos ANTES del merge |
| `postmerge_medido.py check --repo <r> --base <j>` | Rojos NUEVOS, build roto o tests desaparecidos (exit 2) |
| `arquitectura.py check [--feature <id>]` | Trinquete de arquitectura: lo heredado no crece; `close` lo corre solo. Ver `references/arquitectura-heredada.md` |
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

Si aparecen rojos nuevos: anota el choque (`hallazgo.py anotar`) y muestraselo al usuario, que
decide si es una ficha de bug; no bajes la asercion que lo detecto.
Al verificar el exit a mano no uses un pipe (`| tail`): te devuelve el status
del tail, no el del gate.

Reglas en `harness/feature_list.json` → `rules`: `require_spec_approved`, `require_review`, `require_leccion`, `require_verify_green`, `require_docs_al_dia` (documentos que `approve-spec` exige; un valor que no entiende hace fallar `check`, no la apaga). `stack_skills_excluidas` (`{"<stack-id>": ["<skill>", ...]}`) nombra las skills de un stack que el proyecto retiró a propósito: `stack.py normalizar` no las instala y `verificar` no las cuenta como faltantes; un valor mal formado detiene la normalización.

**Rutas protegidas**: `docs/prd/**`, `docs/sdd.md`, `docs/constitution.md`, `.env`. Son del USUARIO. Ningún agente las reescribe a mano — `documentacion.py sync` solo actualiza el bloque generado `harness-flow:features`, y `gate.py check` reporta violaciones fuera de ese contrato. La otra via, la unica que cambia el cuerpo manual del PRD o del SDD, es el sello de `producto.py aprobar --yes` (`documentos.prd|sdd`): el usuario aprobo ESE cuerpo en el chat y vale hasta que lo commitea. Sin repo git no hay commit que medir: el sello es la unica prueba para approve-spec, y check ademas acepta los bytes que un registro multi-repo ya fijo. Un cuerpo a mano y sin registrar no cuenta hasta `aprobar --yes`. Un backlog anterior conserva su lista: si no trae `docs/sdd.md`, `check` lo avisa.

## Stacks Tecnológicos de CALPIL y Extensibilidad Multi-Stack

Harness Flow integra un motor declarativo y extensible de detección y gobierno de stacks tecnológicos (`assets/stacks/<stack-id>/manifest.json`). Reconoce automáticamente la arquitectura y convenciones de cada repositorio o microservicio:
- **Golang Hexagonal (`golang-hexagonal`)**: dominio Go puro en `internal/*/domain/**` (sin frameworks/SQL), puertos de entrada/salida en `application/`, adaptadores Chi HTTP (RFC 7807) y persistencia `pgx`/in-memory, composition root en `cmd/server/main.go`, tests deterministas sin `time.Sleep` (`go test -race`).
- **Angular Product (`angular-product`)**: feature-oriented layered (`src/app/features/<feat>/(domain|application|ui|data-access)`), dominio TypeScript puro sin dependencias de `@angular`/RxJS, Signals para reactividad, componentes standalone, composition root en `app.routes.ts` y linter de límites (`check-architecture.py` / `check-architecture.mjs`).
- **.NET Hexagonal (`dotnet-hexagonal`)**: C# 13 / .NET 10 (LTS) con Clean Architecture multi-proyecto (`Domain` puro en BCL sin dependencias externas, `Application` con puertos in/out, `Infrastructure` con Dapper/ADO.NET y `Npgsql`, `WebApi` con MVC Controllers, ProblemDetails RFC 7807 y `Program.cs` como Composition Root, y tests deterministas con xUnit y `WebApplicationFactory`).
- **Rust Hexagonal (`rust-hexagonal`)**: Rust (edición 2021/2024) con Clean Architecture multi-crate o modular (`crates/domain` puro sin dependencias de red/SQLx, `crates/application` con puertos in/out y casos de uso, `crates/infrastructure` con SQLx PostgreSQL y repositorios en memoria, `crates/api` con handlers Axum, ProblemDetails RFC 7807 y `src/main.rs` como Composition Root, y tests deterministas sin `thread::sleep`).
- **Next.js Product (`nextjs-product`)**: Next.js 15+ / React 19 con Server Components por defecto, aislamiento `server-only` y App Router.
- **Spring Boot Hexagonal (`springboot-hexagonal`)**: Java 21 / Spring Boot 3.4 con dominio puro sin dependencias de Spring/JPA y ArchUnit.
- **NestJS Hexagonal (`nestjs-hexagonal`)**: TypeScript / NestJS modular con Prisma ORM y puertos desacoplados.
- **Python Data Product (`python-dataproduct`)**: Python 3.14 con FastAPI, Polars/Pydantic y adaptadores de origen/destino.
- **iOS SwiftUI Clean (`ios-swiftui-clean`)**: Swift con Clean Architecture por módulos SPM (`*Domain` puro, `*Data`, `*UI`, `*App` como Composition Root).
- **Android Compose Clean (`android-compose-clean`)**: Kotlin y Jetpack Compose con `features/*/(domain|data|presentation)` y `core`.
- **Stacks Futuros**: cualquier nuevo stack se agrega simplemente creando una carpeta `assets/stacks/<nuevo-stack>/manifest.json` con su bloque `"detection"` (indicadores de archivos, extensiones, dependencias y anti-indicadores); el motor lo detectará y normalizará de forma automática sin tocar código Python. `detection.requires_any` declara la señal propia del stack: sin ninguno de esos archivos el repo no es de ese stack (un proyecto Gradle sin `AndroidManifest.xml` no es Android). Para que su código heredado se mida (trinquete), el manifest declara además el bloque `"layout"`.

### Comandos de Stacks

| Comando | Función |
| --- | --- |
| `$PY "$H/stack.py" detectar [--repo <r>]` | Detecta el stack de la raíz o microservicios con confianza e indicadores |
| `$PY "$H/stack.py" verificar [--repo <r>]` | Audita la instalación (rules, skills, copias viejas) y la arquitectura. Dice cuánto código vive fuera de la norma y qué no midió el verificador: no da `COMPLIANT` sobre código sin medir |
| `$PY "$H/stack.py" normalizar [--repo <r>] [--reemplazar]` | Instala rules, skills, `AGENTS.md` y validadores; ajusta el alcance de las reglas a donde vive el código del repo; actualiza la copia que quedó vieja y conserva la que el proyecto editó (`--reemplazar` la cambia por la plantilla). Ver `references/normalizacion-de-stacks.md` |
| `$PY "$H/stack.py" refactorizar [--repo <r>] [--scaffold]` | Plan de refactorización: detallado y con esqueleto canónico (`--scaffold`) en Go, Angular, .NET, Rust, iOS y Android; genérico (un paso por incumplimiento medido) en NestJS, Next.js, Python y Spring Boot |
| `$PY "$H/stack.py" auditar [--repo <r>] [--dast]` | Corre el escáner de dependencias del stack y muestra su documentación oficial e id de Context7. Exit 0 limpio, 1 con hallazgos, 2 si no pudo medir. `--dast` (OWASP ZAP) es informativo |
| `$PY "$H/contexto.py" stacks [--resumen]` | Stacks de TODOS los repos del proyecto con sus restricciones, reglas, skills y documentación vigente. Es lo que recibe el rol producto |
| `$PY "$H/normas.py" --cuadro` | Tabla norma × rol; exit 1 si una celda está vacía. `--rol producto\|leader\|implementer\|revisor` imprime la parte de un rol |
| `$PY "$H/normas.py" --ref <id\|archivo>` | Imprime una referencia entera: el id de una norma (`seguridad`, `datos`...) o un archivo de `references/` (`vertical-slice`). Exit 2 si no existe |
| `$PY "$H/stack.py" skill <nombre> [--stack <id>] [--repo <r>]` | Imprime el `SKILL.md` de una skill de stack: la copia del repo si existe, si no la plantilla. Exit 2 si no existe |
| `$PY "$H/worktree.py" modo --feature <id> --pair\|--delegado` | Fija o cambia el modo de implementación. Delegar es decisión del usuario |
| `$PY "$H/stack.py" arquitectura [--repo <r>] [--stack <id>]` | Corre solo el verificador de arquitectura y sale con su exit code (2 si no pudo medir). Es el comando de los AC de una normalización |
| `$PY "$H/stack.py" stacks` | Lista los stacks tecnológicos soportados |

**Auto-Normalización Temprana y Prioridad Arquitectónica (Feature #0):** Al arrancar la sesión (`estado.py`), el arnés evalúa automáticamente el repositorio: si faltan reglas modulares o skills, las auto-instala inmediatamente (Nivel 1). Si el código fuente tiene violaciones arquitectónicas reportadas por `check-architecture.py` (Nivel 2), crea automáticamente la **Feature #0** en el backlog y bloquea todas las features de negocio (`requiere: [0]`) en `approve-spec` y `worktree.py start` hasta que el código quede normalizado. La #0 cubre **todos** los repos con violaciones: los declara en `microservicios` (de ahí saca el brief el stack y las reglas de cada uno) y su spec trae, por repo, un AC de arquitectura (`stack.py arquitectura --repo <r>`) y uno de tests con el comando del stack de ese repo. La normalización solo agrega lo que falta: no reemplaza un `AGENTS.md` que ya existe ni reinstala las skills de `rules.stack_skills_excluidas`.

**Proyecto con mucho código heredado (trinquete):** la Feature #0 como muro no escala cuando casi todo el código es anterior al arnés. `$PY "$H/arquitectura.py" inventario` mide cuánto vive fuera de la norma del stack y `adoptar --yes` (decisión del USUARIO) lo sella como base: desde ahí lo heredado solo puede bajar, el código nuevo nace dentro de la norma, un archivo heredado muy modificado se normaliza en la misma feature, y cada 3 features de negocio se exige una `--kind normalizacion`. Con la base sellada la #0 deja de bloquear. Detalle en [`references/arquitectura-heredada.md`](references/arquitectura-heredada.md).

### Actualización Continua y Seguridad: Context7 y Documentación Oficial
Para garantizar que toda implementación use versiones actualizadas, APIs no deprecadas y esté protegida contra vulnerabilidades:
- **Context7 MCP (`https://mcp.context7.com/mcp`):** consulta en tiempo real documentación versionada de librerías (`resolve-library-id`, `query-docs` o `"use context7"`).
- **Dónde contrastar, por stack:** el brief, el briefing del revisor y el borrador del SDD traen por cada stack el bloque `DOCUMENTACION VIGENTE`: documentación oficial, id de Context7 y escáner de dependencias (los 10 stacks lo declaran en su `manifest.json`). La consulta a Context7 la hace el agente con el MCP de su host; ningún script se conecta a Context7.
- **Documentación Oficial y Seguridad:** verificación de breaking changes y escaneo con `$PY "$H/stack.py" auditar --repo <ruta>`, que corre el escáner del stack (`govulncheck`, `npm audit`, `pip-audit`, `cargo audit`...) y sale con **exit 0** si está limpio, **exit 1** si reporta hallazgos y **exit 2** si no pudo medir (escáner ausente o repo sin stack): un escáner que no corrió no es un verde. Detalles completos en [`references/context7-documentacion-oficial.md`](references/context7-documentacion-oficial.md).

**El Modo Pair es el modo por defecto en cualquier repo**, con stack detectado o sin él (lo registra `gate.py approve-spec` al sellar el spec por primera vez y lo confirma `worktree.py start`). El brief y el briefing del revisor traen además el **texto completo de las reglas de cada stack** que toca la feature y el **índice de sus skills** (nombre, descripción y ruta del `SKILL.md`, que existe aunque la skill no esté instalada en el repo), para que lleguen al agente en cualquier host y en repos de cualquier ubicación. El rol producto recibe lo mismo, de todo el proyecto, al crear el borrador del SDD. Antes de una tarea que una skill del stack cubre, abre su `SKILL.md` y síguela. La IA avanza sola, ciclo tras ciclo, y **solo interviene con preguntas interactivas de formulario** (`ask_question` en AGY/Gemini o formulario Markdown en otros hosts) ante una decisión de diseño no prevista, un test que habría que cambiar o borrar, dos intentos fallidos sin verde, o lo que sella el usuario (enmienda, ficha nueva, cierre). La lista de tests la sella ella misma.

### Normas de ingeniería: una sola lista para quien escribe y para quien revisa

Las normas que salen de los libros de abajo viven en un registro (`scripts/normas.py`). Cada una dice qué deja el leader en el spec, qué hace el implementer y qué audita el revisor. `contexto.py brief` imprime las dos primeras en el bloque **`NORMAS DE INGENIERIA`** —en modo pair y en delegado, en cualquier host— y `revision.py --briefing` imprime la tercera. Salen del mismo registro: el revisor no bloquea por algo que a quien escribió el código no se le dijo, y audita lo mismo tenga o no `agents/revisor.md`. Cada norma aplica solo si el cambio toca su materia. `python3 scripts/normas.py --rol leader|implementer|revisor` las muestra sueltas.

### Filosofía de Diseño de Ousterhout y Patrones de Datos DDIA
- **A Philosophy of Software Design (John Ousterhout):** diseño guiado por módulos profundos (*Deep Modules*), erradicación de la sobre-fragmentación artificial (*classitis* y micro-funciones de 3 líneas), ocultamiento de información, absorción de complejidad técnica hacia abajo (*pull complexity downwards*), decisiones contrastadas (*design it twice*) y definición de errores fuera de la existencia. Ver [`references/filosofia-diseno-ousterhout.md`](references/filosofia-diseno-ousterhout.md).
- **Patrones de Datos Confiables (Martin Kleppmann - DDIA):** prevención de dual-write con Transactional Outbox atómico, Optimistic Concurrency Control (OCC) con versionado, Idempotency-Key en mutaciones y migraciones Expand-Contract. Ver [`references/patrones-datos-ddia.md`](references/patrones-datos-ddia.md).
- **Design Patterns (Gamma, Helm, Johnson, Vlissides):** un patrón es nombre, problema, solución y costo. Entra en un `D-n` si el eje ya es real, y en el código solo en el sombrero de refactor. El catálogo de los 23 no se copia: sigue en la referencia de GoF y Fowler. Capítulos 1 a 6 cerrados en el mismo archivo. El catálogo no genera el programa: el patrón es el blanco del refactor. Ver [`references/design-patterns-gof.md`](references/design-patterns-gof.md).
- **Code Complete (Steve McConnell):** la construcción (diseño detallado, código, depuración, integración y pruebas del desarrollador) es el centro del trabajo. El rol 0 prepara el terreno: problema en lenguaje de usuario, requisitos comprobables, arquitectura con alternativas y un 10–20 % del esfuerzo upstream. La clase de software de la feature (negocio, misión crítica, vida crítica) fija cuánto formalismo cabe. La estrategia de errores (corrección vs robustez) y la barricada defensiva quedan fijadas en el SDD. La Parte II lleva el diseño de clases y rutinas, la barricada defensiva y el pseudocódigo al implementer, sin sustituir el TDD de la costura. Las Partes III y IV son el checklist de datos y de control; el layout lo pone el formateador. La Parte V fija la calidad durante la construcción, el revisor junto al test, la depuración por hipótesis y el afinado solo con medición. La Parte VI fija el tamaño del sistema, el control del cambio, la integración por rebanadas y las herramientas que ya se usan. La Parte VII cierra el libro: el formateador manda el layout, el comentario dice el porqué, y el oficio es el hábito que los gates ya fijan. Partes I a VII cerradas en el mismo archivo. Ver [`references/code-complete-mcconnell.md`](references/code-complete-mcconnell.md).
- **Seguridad en Aplicaciones Web (OWASP Top 10, OWASP CLASP y OWASP ZAP):** enfoque *Shift-Left* integral. El PRD delimita casos de abuso (*misuse cases*); el SDD modela fronteras de confianza (*Trust Boundaries*), barricadas y mitigación de SSRF/inyecciones; los specs exigen *Negative Acceptance Criteria*; el implementer programa defensivamente con parámetros vinculados y zero hardcoded secrets; el revisor aislado audita severidades bloqueantes/mayores; y `stack.py auditar --dast` ejecuta análisis dinámico DAST con OWASP ZAP contra endpoints o contratos OpenAPI. Ver [`references/seguridad-owasp-y-zap.md`](references/seguridad-owasp-y-zap.md).

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
Si el cierre dice "cbm pendiente" (el daemon compartido no atendio), no es un fallo ni
requiere accion: el arnes lo reintenta solo. No lo reintentes a mano ni mates el daemon ni
procesos cbm a mano (`kill`, `pkill`): dejas sin cbm a las sesiones de los demas agentes. Para
procesos cbm sobrantes: `$PY "$H/contexto.py" limpiar-cbm` (avisa cuales estan en uso, cuales
sesiones tienen el enlace cortado y mata solo los huerfanos). Excepcion: si el aviso dice
"daemon vivo pero sin socket", eso NO se arregla solo; avisa a la persona usuaria y, con su
aprobacion, `$PY "$H/contexto.py" limpiar-cbm --reiniciar-daemon` (`--solo-avisar` muestra a
quien afecta). Nunca lo corras por tu cuenta: corta cbm en las sesiones conectadas.
Detalles de refresco, cobertura y fallos: [`references/contexto.md`](references/contexto.md)
y [`references/hub.md`](references/hub.md).

Las lecciones son skills reutilizables por clase de trabajo. Lee las aplicables
y patchea una existente antes de crear otra. El cierre exige que la lección
indicada exista. Hermes las crea con `skill_manage`; los demás hosts usan su raíz
nativa. Rutas y precedencia: [`references/hosts.md`](references/hosts.md).

## PRD/SDD y Obsidian

`documentacion.py sync` mantiene el bloque generado de `docs/prd/PRD-master.md`
y `docs/sdd.md`; nunca reescribas su contenido manual. El cierre `done` ejecuta
el sync. Entre medio, cada feature lleva su `F-n` (`add.py --candidata`), su spec
cita `O-n`/`D-n` y el sello del spec recuerda contra que version se aprobo. Para
la aprobación del PRD/SDD y esa trazabilidad, consulta
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
[`references/modelos.md`](references/modelos.md) (sección Gemini / AGY),
[`references/grok.md`](references/grok.md) y
[`references/kimi.md`](references/kimi.md).

Jira/Confluence solo se usa si existe `harness/atlassian.json` y el usuario
solicita publicar. No inventes el binding ni publiques por defecto; consulta
[`references/atlassian.md`](references/atlassian.md).

## Reglas duras

- Todo hallazgo relevante se escribe en `harness/progress/`. Una respuesta en el chat no reemplaza evidencia persistida.
- Un hallazgo no abre una ficha: se resuelve en una feature abierta (rama, AC o enmienda) o se anota con `hallazgo.py`. Una ficha nueva exige el SÍ del usuario y su peso (`add.py --yes --peso`).
- `gate.py verify` corre en el WORKTREE de la feature cuando existe. Si el
  worktree declarado no existe, **bloquea** en vez de caer a la raíz; sin
  worktree, avisa que mide la raíz. Un rojo o un verde sobre el árbol
  equivocado no es un veredicto sobre el código.
- **La feature sale de `rules.rama_base` (por defecto `develop`), no del HEAD del
  repo.** `worktree.py start` crea la rama desde ese SHA (aborta si una rama que
  ya existía no desciende de la base) y la registra en `base_branch`/`base_sha`;
  `revision.py` diffea contra `merge-base base HEAD`, no `HEAD~1`. `--base <rama>`
  para un caso puntual.
- **El worktree nace con las dependencias de la raíz enlazadas.** `worktree.py start`
  enlaza cada directorio de `rules.worktree_enlaces` (por defecto `node_modules`;
  `[]` lo desactiva) que exista en la raíz y falte en el worktree, y `gate.py verify`
  repara el enlace antes del primer AC. Nunca pisa lo propio del worktree; si el
  `.gitignore` no ignora el enlace (`node_modules/` con barra), lo agrega al
  `info/exclude` local. No enlaces a mano ni corras `npm install` en el worktree.
- Con features paralelas, usa worktrees independientes para los AC, reserva las migraciones contra la rama de integración y corre la suite completa de destino después de cada cierre. `verify` mide los AC del worktree, no la integración. Reglas y casos límite: [`references/multirepo.md`](references/multirepo.md).
- El cuerpo manual del PRD, el del SDD y la constitution son del USUARIO. No los reescribas; `documentacion.py sync` solo puede tocar su bloque generado `harness-flow:features`.
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
| Implementer (pair por defecto; delegado solo con `--delegado`) | sesion (pair) o `claude -p --agent` (delegado) | sesion (pair) o `Agent` (`harness-flow:implementer`, delegado) | sesion (pair) o autonomo (delegado) | sesion (pair) o `invoke_subagent` (`self`, delegado) | sesion (pair) o autonomo (delegado) | sesion (pair) o `Agent` (delegado) |
| Revisor | `claude -p --agent` o `delegate_task` | `Agent` | `codex exec` o subagente | `invoke_subagent` (`self`) | `spawn_subagent` y espera el id | `Agent` o `kimi -p` |
| Crear lección | `skill_manage` | `leccion.py donde` | `leccion.py donde` | `leccion.py donde` | `leccion.py donde` | `leccion.py donde` |
| Guía del host | [`modelos.md`](references/modelos.md) | [`claude.md`](references/claude.md) | [`openai.md`](references/openai.md) | [`modelos.md`](references/modelos.md) / [`hosts.md`](references/hosts.md) | [`grok.md`](references/grok.md) | [`kimi.md`](references/kimi.md) |

Los gates, worktrees, specs, memoria y documentación usan los mismos scripts
Python. Si no hay revisor aislado, puedes revisar localmente con
`revision.py --feature <id>`, pero declara que el aislamiento no se logró.

## Referencias (cargalas cuando hagan falta, no antes)

| Archivo | Cuando leerlo |
| --- | --- |
| [`references/vertical-slice.md`](references/vertical-slice.md) | Vertical Slice, frontera `requiere`, costuras de test, TDD vertical, 3 alarmas y modo Pair (`--pair`) |
| [`references/entorno.md`](references/entorno.md) | `entorno.py` no resuelve el interprete o el host, falta `psycopg` |
| [`references/multirepo.md`](references/multirepo.md) | raiz multi-repo sin `.git`: registro, `--integrated`, postmerge medido |
| [`references/contexto.md`](references/contexto.md) | varias raices de grafo, el parte de `refrescar`, algo del contexto no cuadra |
| [`references/lecciones-del-arnes.md`](references/lecciones-del-arnes.md) | **antes de tocar o escribir un gate** |
| [`references/hallazgos.md`](references/hallazgos.md) | encuentras algo en el código mientras trabajas en otra cosa, o `add.py` se niega a crear una ficha: enmienda antes que ficha, `hallazgo.py` |
| [`references/arquitectura-heredada.md`](references/arquitectura-heredada.md) | proyecto con mucho código anterior al arnés: trinquete, base, cuota de normalización, `arquitectura.py` |
| [`references/normalizacion-de-stacks.md`](references/normalizacion-de-stacks.md) | un repo no recibe las rules o skills de su stack, una regla no nombra el código del repo, una copia instalada quedó vieja, worktree sin normativa, `stack.py verificar` |
| [`references/normas-de-ingenieria.md`](references/normas-de-ingenieria.md) | una norma no llega a un rol, quieres agregar o cambiar una, AC negativos, bloque `documentation`/`security_audit` del manifest, exit de `stack.py auditar` |
| [`references/hosts.md`](references/hosts.md) | raíces de skills y creación de lecciones por host |
| [`references/hub.md`](references/hub.md) | esquema del hub, `derivar-graphify`, credenciales |
| [`references/obsidian.md`](references/obsidian.md) | que genera el vault, config sembrada, `--con-grafo` |
| [`references/atlassian.md`](references/atlassian.md) | mapeo a Jira/Confluence y sus comandos |
| [`references/claude.md`](references/claude.md) | Claude Code: plugin, comandos, Windows, raices de lecciones |
| [`references/modelos.md`](references/modelos.md) | modelo por proveedor y rol; seleccion de effort para OpenAI, Claude 5.5 y Gemini 4 Argon (AGY y Hermes) |
| [`references/openai.md`](references/openai.md) | GPT/Codex: instalacion, deteccion y raices |
| [`references/grok.md`](references/grok.md) | Grok: host, `spawn_subagent` y espera del revisor, lecciones en `~/.grok/skills`, vault |
| [`references/kimi.md`](references/kimi.md) | Kimi Code: host, plugin, revisor y lecciones |
| [`references/context7-documentacion-oficial.md`](references/context7-documentacion-oficial.md) | consultar Context7 MCP / docs oficiales para mantener stacks actualizados y auditar seguridad/CVEs |
| [`references/comunicacion-ste100-y-prompts.md`](references/comunicacion-ste100-y-prompts.md) | principios de Karpathy, estándar aeroespacial ASD-STE100, prompts de alta densidad y micro-reportes |
| [`references/patrones-datos-ddia.md`](references/patrones-datos-ddia.md) | patrones de datos DDIA (Transactional Outbox, Idempotency-Key, OCC, prevención de Dual-Write) |
| [`references/filosofia-diseno-ousterhout.md`](references/filosofia-diseno-ousterhout.md) | filosofía de diseño de software de John Ousterhout (Deep Modules, anti-classitis, Design It Twice) |
| [`references/patrones-gof-y-refactoring.md`](references/patrones-gof-y-refactoring.md) | patrones GoF en arquitectura hexagonal, regla de los dos sombreros de Beck/Fowler y catálogo de Code Smells |
| [`references/design-patterns-gof.md`](references/design-patterns-gof.md) | Design Patterns (Gamma et al.): cuándo entra un patrón en cada fase. El catálogo sigue en la fila de arriba. Lectura cerrada, capítulos 1 a 6 |
| [`references/algoritmos-y-estructuras-clrs.md`](references/algoritmos-y-estructuras-clrs.md) | algoritmos y estructuras CLRS: complejidad asintótica, orden topológico de features y prevención de N+1/O(N^2) |
| [`references/ai-engineering-chip-huyen.md`](references/ai-engineering-chip-huyen.md) | ingeniería de IA (Chip Huyen): arquitectura de 5 capas, structured outputs, guardrails y AI-as-a-judge |
| [`references/microservicios-sam-newman.md`](references/microservicios-sam-newman.md) | microservicios y sistemas distribuidos (Sam Newman): Database per Service, resiliencia y contratos |
| [`references/ingenieria-software-gergely-orosz.md`](references/ingenieria-software-gergely-orosz.md) | ingeniería pragmática (Gergely Orosz): estándar Design Docs / RFCs, entrega predecible y code reviews |
| [`references/code-complete-mcconnell.md`](references/code-complete-mcconnell.md) | Code Complete (McConnell): las siete partes, de los prerrequisitos al oficio. Rol 0 (estrategia de errores en SDD), spec, implementer, revisor y cierre |
| [`references/seguridad-owasp-y-zap.md`](references/seguridad-owasp-y-zap.md) | seguridad web (OWASP Top 10, CLASP y ZAP): Shift-Left, casos de abuso, barricadas, TDD negativo y DAST |
| [`references/documentacion.md`](references/documentacion.md) | rol producto (PRD inicial / SDD de arquitectura), su sello y como se sincronizan |
