---
description: Rol leader de harness-flow — escribe el spec de una feature con AC verificables y lo lleva al ritual de aprobacion del usuario.
argument-hint: <id-feature>
model: inherit
---

# harness-flow: spec (rol leader)

Escribe el spec de la feature `$ARGUMENTS[0]` ANTES de tocar codigo. Si no te dieron id,
pregunta cual, o corre `/harness-flow:estado` para listarlas.

> **Shell.** Cada llamada Bash abre un shell nuevo: `$PY` y `$H` no sobreviven,
> asi que el bootstrap va pegado a cada comando, siempre. Los bloques de abajo
> usan bash (macOS, Linux, WSL, y Windows con Git for Windows). En **Windows sin
> Git for Windows la tool Bash es PowerShell**: ahi el interprete se llama
> `python` y el prefijo equivalente es
> `python "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --powershell | Invoke-Expression`,
> invocando despues con `& $PY ...`. Detalle en `references/claude.md`.

## 0. Modelo del rol (lo elige el usuario)

Este rol corre en Claude Fable 5.2 o en Claude Opus 5.5. Lo decide el USUARIO,
una vez por feature; no lo elijas tu ni lo des por supuesto.

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/modelo.py" ver --feature $ARGUMENTS[0]
```

- **Sale con exit 3 (`sin elegir`)**: PREGUNTA en un formulario (tool
  `AskUserQuestion`), una sola pregunta con dos opciones: `Fable 5.2` (el mas
  capaz; cuesta el doble por token; esfuerzo `high`) y `Opus 5.5` (el de
  siempre; esfuerzo `xhigh`). Guarda lo que responda:

  ```bash
  eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/modelo.py" elegir --feature $ARGUMENTS[0] --modelo fable|opus
  ```

- **Ya hay una eleccion**: anunciala en una linea y no vuelvas a preguntar. Si
  el usuario pide cambiarla, corre `modelo.py elegir` de nuevo.

Despues compara lo elegido con TU sesion. Tu modelo es el que dice tu system
prompt; el esfuerzo de la sesion lo imprime el script.

- **Coinciden modelo y esfuerzo**: sigue con el paso 1.
- **No coincide alguno**: aplica la eleccion tu mismo, sin pedirle nada al
  usuario. Invoca con la tool `Skill` el comando `harness-flow:usar-opus` o
  `harness-flow:usar-fable`: fija ese modelo y su esfuerzo para el resto de
  este turno. Dilo en una linea (`Leader: Opus 5.5 / xhigh, elegido por el
  usuario`) y sigue con el paso 1. NO le pidas `/model` ni `/effort`.
- **El comando no se aplico** (tras invocarlo tu system prompt sigue en otro
  modelo, o tu host no tiene la tool `Skill`): entonces si DETENTE y pide al
  usuario `/model fable` u `/model opus` y que vuelva a invocar este comando.
  No sigas el rol en otro modelo sin decirlo.
- **Sin usuario a quien preguntar** (`claude -p`): ahi el comando de fijar
  modelo no se aplica. Usa lo ya elegido solo para decirlo: sigue con el modelo
  de la sesion y avisa en una linea si no es el elegido. Quien lanza la sesion
  fija el modelo con `--model` y `--effort`.

Por que no va fijo en el frontmatter y que hacen los demas roles:
`${CLAUDE_PLUGIN_ROOT}/references/modelos.md` ("Fable 5.2 u Opus 5.5").

## 1. Contexto antes de leer archivos a ciegas

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/contexto.py" brief --feature $ARGUMENTS[0]
```

Para consultas puntuales de estructura (quien llama a X, impacto de un cambio) usa
el MCP `codebase-memory-mcp` (`search_graph`, `trace_path`, `detect_changes`) antes de
leer archivos a ciegas.

Ese brief trae AC, reglas, la seccion **producto** (el PRD y el SDD: la `F-n`
de la feature, los objetivos `O-n`/`NO-n` y las decisiones `D-n`), lecciones,
impacto del hub, superficie de contacto del grafo y **documentos relacionados**:
rutas de `docs/` (decisiones, enmiendas, reviews de features previas del mismo
servicio, notas del usuario). Lee en el PRD la historia y los objetivos que toca
la feature, y en el SDD las decisiones que aplica; de los relacionados abre solo
los que toquen tu diseno; no barras `docs/` por tu cuenta. Si dice que el
contexto esta vencido, refresca antes de disenar:

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/contexto.py" refrescar
```

Para una pregunta puntual que el brief no cubre,
`graphify query "<pregunta>" --graph <combinado>`.

Despues, los dos que el brief no reemplaza:

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/hub.py" impacto --microservicio <proyecto>/<servicio>
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/leccion.py" list
```

Las lecciones se leen **antes** de disenar, no despues de romper algo.

## 2. Escribe el spec

`docs/spec-feature-$ARGUMENTS[0]-<slug>.md`, con `Estado: draft`, siguiendo
`${CLAUDE_PLUGIN_ROOT}/templates/spec.md`. Lo que no es negociable:

- AC numerados `AC-1`, `AC-2`, … sin saltos, en Given/When/Then o formato directo, cada uno
  verificable por un tercero (describe *que* ve o recibe el usuario, nunca *como*
  se implementa). **Redacción ASD-STE100 (Karpathy):** redacta cada AC en frases de máximo 20
  palabras, en voz activa y con una sola acción verificable por AC (ver `references/comunicacion-ste100-y-prompts.md`).
  Apunta a **2-3 AC** (tope en `rules.max_acs_por_slice`, por
  defecto 5): si necesita mas, **no infles el spec**, propon partir la historia
  en nuevas candidatas `F-n`.
- **Límites negativos explícitos:** El spec no autoriza tocar rutas protegidas
  (`docs/prd/**`, `docs/sdd.md`, `.env`) ni incorporar alcances fuera del PRD.
- Cada AC declara su **costura publica de prueba** (`[costura: endpoint|servicio|ui|integracion|manual]`
  en la linea del AC o `Costura: ...` debajo), en el nivel practico mas alto, sin
  acoplar a detalles internos ni mocks propios. Incluye `## Plan vertical` con
  hasta 5 bullets (sin codigo ni nombres de archivos) y, solo si hay una senal
  concreta en el codigo actual (algo que ya se repite), `## Sugerencias (decision
  del usuario)` ("sugiere, no decidas").
- El Contexto cita el PRD y el SDD: `cumple: O1` (o `cumple: ninguno`) y
  `decisiones que aplica: D2` (o `ninguna`). Los no-objetivos `NO-n` que roza la
  feature van a "Fuera de alcance". `approve-spec` avisa si falta la cita o si
  nombra una que el documento no declara.
- El comando de verificacion va `` `verificar: <cmd>` `` dentro del backtick o en
  una linea `Comando: `` `<cmd>` `` debajo del AC. Un AC sin comando es legitimo:
  lo verifica el reviewer a mano.
- **Los comandos apuntan al worktree de la feature**, nunca a la carpeta
  compartida del repo. Con varias features vivas, `/ruta/ms-foo` esta parado en
  la rama de quien hizo checkout ultimo: el AC mediria un arbol ajeno y da verde
  falso si el `-run` no engancha nada, o rojo falso si la rama vecina tiene otro
  codigo. Crea el worktree ANTES de sellar el spec:

  ```bash
  eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/worktree.py" start --feature $ARGUMENTS[0]
  ```
- Si la feature trae migracion numerada, **reserva el numero contra la rama de
  integracion**, no contra el worktree: cada rama ve "el siguiente libre" en un
  arbol distinto y la colision esta garantizada.

## 3. Ritual de aprobacion

Este paso es del USUARIO, no tuyo.

1. MUESTRA el spec en el chat.
2. PREGUNTA explicitamente si lo aprueba.
3. Solo con un SI explicito:

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/gate.py" approve-spec --feature $ARGUMENTS[0] --yes
```

Nunca corras eso por tu cuenta ni "para agilizar". El script se niega sin
`--yes`, y `--yes` significa que el usuario dijo que si — no que tu lo asumiste.

Tambien se niega, con la regla `require_docs_al_dia`, si el proyecto no tiene el
PRD/SDD que esa regla exige: corre antes `/harness-flow:producto prd|sdd`. No
apagues la regla para destrabarlo: si el proyecto no lleva PRD/SDD lo decide el
usuario. Un `--kind bug|task` no lo exige.

Cambiar el spec despues de aprobarlo invalida el sello (firma sha256 del cuerpo).
Eso es deliberado: hay que volver a mostrarlo y re-aprobarlo.

Si el PRD o el SDD cambian despues de aprobar el spec (`estado.py` marca "PRD
cambio desde el spec"), releelo contra el documento nuevo: si un AC deja de
valer es una enmienda (seccion 4); si sigue valiendo, muestraselo al usuario y
re-aprueba con su SI.

## 4. Enmienda: el spec ya tiene trabajo encima

Si ya existe `docs/impl-$ARGUMENTS[0].md`, `docs/review-$ARGUMENTS[0].md` o un verify, `approve-spec`
se niega a re-sellar el spec cambiado: eso es una enmienda.

1. Escribe `docs/propuesta-$ARGUMENTS[0]-enmienda-<slug>.md` desde
   `${CLAUDE_PLUGIN_ROOT}/templates/enmienda.md` (por que, cambios al spec, lo
   que NO cambia) y aplica los cambios al spec. La seccion
   `## Enmiendas posteriores a la aprobacion` la escribe el gate, no tu.
2. MUESTRA la propuesta y el spec cambiado, PREGUNTA, y solo con un SI explicito:

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/gate.py" enmienda --feature $ARGUMENTS[0] --propuesta docs/propuesta-$ARGUMENTS[0]-enmienda-<slug>.md --yes
```

Se niega si el spec cambio un AC que la propuesta no nombra: el usuario aprobo
la propuesta, no el diff. Despues, el review y el verify anteriores ya no valen
para cerrar: lanza un review nuevo (`/harness-flow:review $ARGUMENTS[0]`) y vuelve a correr
verify.
