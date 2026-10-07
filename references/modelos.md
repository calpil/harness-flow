# Modelo y esfuerzo por rol

## OpenAI en Codex y Hermes

Esta politica se aplica cuando la tarea usa modelos OpenAI, incluido el provider
`openai-codex` de Hermes. El coordinador selecciona el effort de Producto y
Leader segun la tarea; no necesita confirmacion para elegir entre `medium` y
`high`. Una eleccion explicita del usuario tiene prioridad.

| Rol | Modelo | Effort |
| --- | --- | --- |
| Coordinador | `gpt-6.1-sol` | `xhigh` |
| 0 Producto: PRD/SDD | `gpt-6-astra` | Automatico: `medium` o `high` |
| 1 Leader: spec y AC | `gpt-6-astra` | Automatico: `medium` o `high` |
| 2 Implementer | `gpt-6.1-sol` | `xhigh` |
| 3 Revisor independiente | `gpt-6.1-sol` | `xhigh` |
| 4 Cierre rutinario | Gates Python y `gpt-6-luna` para interpretar resultados | `xhigh` |
| Estado, contexto y documentacion rutinaria | `gpt-6-luna` | `xhigh` |

### Seleccion automatica para Producto y Leader

Elige por el trabajo real de **cada rol**, a partir de la peticion, el brief,
el impacto y las lecciones ya disponibles. No hace falta una auditoria nueva
para seleccionar el nivel.

- **`medium`, por defecto:** requisitos claros, patrones conocidos y cambios
  cuyo alcance y criterios de aceptacion pueden definirse sin resolver riesgos
  de los siguientes grupos.
- **`high` cuando haya un riesgo concreto que ese rol deba analizar:**
  - Arquitectura entre varios repos con cambios coordinados de contratos,
    compatibilidad o secuencia de despliegue.
  - Migraciones de datos con riesgo de perdida, irreversibilidad, backfill o
    restricciones de disponibilidad y rollback.
  - Concurrencia que exige decidir sobre consistencia, transacciones, locks,
    idempotencia, carreras o reintentos.
  - Requisitos contradictorios que exigen comparar alternativas y sus efectos.

Mencionar varios repos, una migracion o concurrencia no basta: identifica la
decision y su riesgo. Un PRD conocido puede usar `medium` aunque el SDD necesite
`high`; vuelve a evaluar al iniciar Leader. La longitud del documento o un
error transitorio del entorno no justifican subir el effort.

Antes de ejecutar el rol, informa en una frase: `Producto: gpt-6-astra / medium
— alcance conocido` o `Leader: gpt-6-astra / high — contratos entre tres
servicios`. Si el alcance cambia y aparece un riesgo nuevo, reevalua y aplica el
nivel en la siguiente invocacion; evita alternarlo en cada mensaje. Al volver a
una tarea habitual, usa de nuevo `medium`. La seleccion automatica se limita a
`medium` y `high`; otro nivel requiere una eleccion explicita del usuario.

El effort no resuelve decisiones de producto: si falta saber que comportamiento
quiere el usuario, pregunta antes de fijar el acuerdo. Las aprobaciones de
PRD/SDD, spec y enmiendas siguen el ritual del flujo.

### Aplicar el nivel elegido

Un texto en el prompt no configura el esfuerzo de razonamiento. Fija modelo y
effort en la invocacion o configuracion efectiva del rol:

- **Codex:** en subagentes, pasa el modelo y effort elegidos mediante las opciones
  nativas del host. Un agente personalizado que fija `model_reasoning_effort`
  en su TOML puede prevalecer sobre el valor del spawn: usa una configuracion
  compatible con el nivel elegido. Con `codex exec`, un override por invocacion:

  ```bash
  codex exec -m gpt-6-astra -c 'model_reasoning_effort="medium"' \
    --sandbox workspace-write -C /ruta/proyecto - < /ruta/contexto-rol.md
  ```

  Para una tarea que requiere `high`, cambia ese valor a `high`. El contexto
  debe nombrar el rol, la skill, las rutas y el entregable.
- **Hermes:** usa el perfil del rol y `--reasoning medium` o `--reasoning high`
  para esa invocacion. Por ejemplo, con un perfil Producto ya configurado:

  ```bash
  hermes -p hf-producto chat --provider openai-codex -m gpt-6-astra \
    --reasoning medium --oneshot --query-file /ruta/contexto-rol.md
  ```

  En perfiles, la clave es `agent.reasoning_effort`. `delegate_task` utiliza la
  configuracion comun de delegacion y no permite elegir modelo/effort por tarea:
  para niveles distintos usa invocaciones o perfiles del rol, o tareas Kanban
  asignadas a perfiles con la configuracion adecuada.

El proceso del rol devuelve su borrador; la sesion coordinadora presenta el
documento y recoge la aprobacion. Conserva el briefing completo del revisor.
Si el host no puede aplicar el nivel seleccionado, informa el nivel solicitado
y el efectivo conocido; no declares un cambio de effort solo por escribirlo en
el prompt ni cambies los defaults globales de otras sesiones.

Fuentes: [esfuerzo de razonamiento](https://developers.openai.com/api/docs/guides/reasoning),
[agentes Codex](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[delegacion Hermes](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation/).

## Claude 5.5

Con modelos Claude, cada rol corre en la familia 5.5. Producto, Leader, Cierre
y Estado van fijos en `xhigh`; el implementer y el revisor reciben el nivel que
elige la sesion coordinadora para cada tarea (ver "Seleccion automatica" mas
abajo). Fable queda fuera. Los IDs van completos (`claude-opus-5-5`), nunca como alias:
`opus` cambia de version cuando sale la siguiente, `best` y `default` pueden
resolver a Fable, y fuera de la API de Anthropic `haiku` es Haiku 4.5, que no
acepta esfuerzo.

| Rol | Modelo | Donde se fija en Claude Code | Por que |
| --- | --- | --- | --- |
| 0 Producto | `claude-opus-5-5` | `commands/producto.md` | Decide la arquitectura; pocos tokens, mucho peso aguas abajo |
| 1 Leader | `claude-opus-5-5` | `commands/spec.md` | Un AC mal planteado cuesta dos rondas de review o una enmienda |
| 2 Implementer | `claude-sonnet-5-5` | `agents/implementer.md` | Concentra el volumen de tokens a la mitad de precio, y no es el modelo que lo revisa |
| 3 Revisor | `claude-opus-5-5` | `agents/revisor.md` | Al menos tan capaz como quien implemento |
| 4 Cierre | `claude-opus-5-5` | `commands/cierre.md` | Merge irreversible y lectura de rojos; pocos tokens, no se ahorra ahi |
| Estado | `claude-haiku-5-5` | `commands/estado.md` | Lee y cuenta al arrancar, con el contexto aun corto |

Los tres aceptan `low` a `max`. Opus 5.5 y Haiku 5.5 arrancan en `medium` si
nadie fija el nivel: el `xhigh` va explicito en cada frontmatter.

### Seleccion automatica: implementer y revisor

La sesion coordinadora elige el effort antes de cada invocacion, sin pedir
confirmacion, dentro de esta banda. Una eleccion explicita del usuario tiene
prioridad.

| Rol | Nivel | Cuando |
| --- | --- | --- |
| Implementer | `high` | Por defecto: spec claro, patrones conocidos, sin los riesgos de abajo |
| Implementer | `xhigh` | Hay un riesgo concreto que el codigo tiene que resolver |
| Revisor | `xhigh` | Primera ronda: review completo de todos los AC |
| Revisor | `high` | Ronda de seguimiento: el briefing ya trae un sello `changes_requested` o `blocked`, y solo se verifica lo bloqueante o mayor y los AC |

Riesgos que suben al implementer a `xhigh`:

- contratos coordinados entre varios repos, con compatibilidad o secuencia de
  despliegue;
- migracion de datos con riesgo de perdida, irreversibilidad, backfill o
  rollback;
- concurrencia: consistencia, transacciones, locks, idempotencia, carreras o
  reintentos;
- una leccion aplicable del brief que documenta una falla previa en esa misma
  clase de trabajo.

Que el spec mencione varios repos, una migracion o concurrencia no basta:
identifica la decision y su riesgo. El numero de AC, la longitud del spec o un
error transitorio del entorno no justifican subir. `low`, `medium` y `max`
quedan fuera de la seleccion automatica: solo con una eleccion explicita del
usuario. El revisor nunca baja de `high`: es el gate.

Antes de lanzar, informa en una frase: `Implementer: claude-sonnet-5-5 / high —
un repo, AC con comando` o `Revisor: claude-opus-5-5 / high — ronda de
seguimiento`.

**Como se aplica.** Un texto en el prompt no cambia el esfuerzo; el nivel va en
la invocacion:

- **Claude Code:** tool `Agent` con `effort: "<nivel>"`, sin `model`.
- **Hermes:** `claude -p --agent harness-flow:<rol> --effort <nivel>`.

En los dos casos el nivel de la invocacion le gana al `effort` del frontmatter.
El frontmatter queda en `xhigh`, el tope de la banda, como red: una invocacion
que olvida pasar el nivel gasta de mas, pero no revisa ni implementa por debajo
de lo debido.

Producto, Leader y Cierre no entran en la seleccion: corren en la sesion
principal, cuyo esfuerzo el modelo no puede cambiar, y gastan pocos tokens para
lo mucho que deciden.

Comprobado el 2026-10-07 con Claude Code 2.1.293, leyendo el `effort` que
registra la transcripcion: el revisor (frontmatter `xhigh`) lanzado con la tool
`Agent` y `effort: "low"` corrio en `low` sobre `claude-opus-5-5`, y
`claude -p --agent harness-flow:revisor --effort low` y `--effort max`
corrieron en `low` y `max`.

## Claude Code

- **Subagentes** (`agents/*.md`): `model` y `effort` valen para toda la vida
  del subagente. Precedencia: el `model` y el `effort` que se pasan a la tool
  `Agent` le ganan al frontmatter. Los comandos pasan `effort` (seleccion
  automatica) y nunca `model`. No definas `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`:
  invierte esa precedencia para el modelo.
- **Comandos** (`commands/*.md`): su `model` vale **solo para ese turno**; el
  siguiente vuelve al modelo de la sesion. Por eso el implementer es un
  subagente y no un comando: implementar dura muchos turnos. El `effort` de un
  comando de plugin no esta en la tabla del manifiesto; el del subagente si.
- **Sesion**: fijala en Opus 5.5 con `xhigh` para que los turnos sin comando
  tambien lo usen. En `~/.claude/settings.json`:

  ```json
  { "model": "claude-opus-5-5", "effortLevel": "xhigh" }
  ```

  Cada cambio de modelo en la sesion principal relee el contexto sin cache
  (la cache es por modelo). Con la sesion ya en Opus, los comandos de Opus no
  cambian nada; el de estado corre al arrancar, con poco contexto.

Comprobado el 2026-10-07 con Claude Code 2.1.293: `claude -p --agent
harness-flow:implementer` corre en `claude-sonnet-5-5`, `--agent
harness-flow:revisor` en `claude-opus-5-5`, y `claude -p "/harness-flow:estado"`
reporta solo `claude-haiku-5-5` en `modelUsage`. El esfuerzo no aparece en la
salida JSON.

## Hermes con Claude 5.5

Hermes no lee `model` ni `effort` de una skill, y `delegate_task` no acepta
modelo por llamada: los hijos heredan el de la sesion, o el `delegation.model`
global. Por eso los roles se reparten asi:

| Rol | Como corre en Hermes | Credencial |
| --- | --- | --- |
| Producto, Leader, Cierre, Estado | Sesion de Hermes en `claude-opus-5-5` | API key de Console |
| Implementer | `claude -p --agent harness-flow:implementer --effort <nivel>` | Login propio de Claude Code |
| Revisor | `claude -p --agent harness-flow:revisor --effort <nivel>` | Login propio de Claude Code |

### Sesion

Lanza Hermes con el modelo solo para esta invocacion; el default global no
cambia:

```bash
hermes -m claude-opus-5-5 --provider anthropic --reasoning xhigh
```

Hermes manda `thinking: adaptive` y `output_config.effort: xhigh`
(`agent/anthropic_adapter.py`, `_thinking_kwargs`).

**Haiku no sirve en Hermes**: `_thinking_kwargs` devuelve `{}` para todo modelo
cuyo nombre contiene `haiku`, asi que Haiku 5.5 corre en `medium` sin aviso.
Estado va en la sesion de Opus. Verificado en el codigo el 2026-10-07.

### Credencial: API key, nunca el OAuth prestado

El provider `anthropic` busca, en orden: `ANTHROPIC_TOKEN` o
`CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_API_KEY`, sus propios OAuth, y por ultimo
**el login de Claude Code del Keychain** (`agent/anthropic_credentials.py`).
Ese ultimo paso es usar credenciales de una suscripcion Free/Pro/Max desde un
producto de terceros, y los terminos de Anthropic lo prohiben
(https://code.claude.com/docs/en/legal-and-compliance, "Authentication and
credential use").

1. Pon tu API key de Console como `ANTHROPIC_API_KEY` en `~/.hermes/.env`.
   No definas `ANTHROPIC_TOKEN` ni `CLAUDE_CODE_OAUTH_TOKEN`: le ganan a la key.
2. En `~/.hermes/config.yaml`, `auth.adopt_external_logins: false`. Eso tambien
   deja de tomar el login de Codex CLI: antes, comprueba que tu login de
   `openai-codex` sea propio de Hermes y no prestado.

### Implementer y revisor con `claude -p`

Hermes ejecuta el binario oficial de Claude Code, que entra con tu propio login.
Eso lo permiten los mismos terminos, y la terminal de Hermes no le pasa sus
credenciales de proveedor (`tools/env_passthrough.py`). Los topes de Pro y Max
suponen "ordinary, individual usage": no lo lances en cron ni en lotes
paralelos.

Corre los dos desde la RAIZ del proyecto y da acceso al worktree con
`--add-dir`. En `-p` no hay quien apruebe permisos: lo que no permitas se
deniega. `--allowedTools "Bash"` deja correr cualquier comando; acotalo si
prefieres. El `--effort` sale de la seleccion automatica de arriba; anuncialo antes
de lanzar.

```bash
# Implementer: el brief entra por stdin.
"$PY" "$H/contexto.py" brief --feature <id> | claude -p \
  --agent harness-flow:implementer --effort <high|xhigh> --add-dir <worktree> \
  --permission-mode acceptEdits --allowedTools "Bash" \
  "Implementa la feature #<id>. Spec: docs/spec-feature-<id>-<slug>.md. Worktree: <worktree>."

# Revisor: el briefing entero entra por stdin.
"$PY" "$H/revision.py" --feature <id> --briefing | claude -p \
  --agent harness-flow:revisor --effort <xhigh|high> --add-dir <worktree> \
  --permission-mode acceptEdits --allowedTools "Bash" \
  "Revisa la feature #<id> y escribe docs/review-<id>.md."
```

Implementar puede durar mucho mas que el timeout de la terminal: correlo en
segundo plano como indica la skill `claude-code` de Hermes. Al volver, la sesion
de Hermes hace lo mismo que en Claude Code: contrasta `docs/impl-<id>.md` contra
el worktree, lee `docs/review-<id>.md` y sella con `gate.py revision`.

Sin Claude Code instalado, el revisor vuelve a `delegate_task` y hereda el
modelo y el effort de la sesion: ahi no hay seleccion por tarea. No fijes `delegation.model` para esto: es global, y los
subagentes de tus sesiones con otro modelo tambien pasarian a cobrarse por API.
