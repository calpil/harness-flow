---
description: Rol implementer de harness-flow — verifica el gate del spec, delega la implementacion al subagente implementer (o ejecuta en modo Pair interactivo con --pair) en el worktree de la feature y contrasta su evidencia antes del review.
argument-hint: <id-feature> [--pair]
model: claude-opus-5-5
effort: xhigh
---

# harness-flow: implementar (rol implementer)

Implementa la feature `$ARGUMENTS[0]`. Argumentos recibidos: `$ARGUMENTS` (si
incluyen `--pair`, aplica el modo Pair de la seccion 5b).

**Activación Automática de Modo Pair en Stacks Tecnológicos (Angular / Golang / .NET / Stacks Normativos):**
Si el brief (`contexto.py brief`) detecta un stack tecnológico normativo (ej. Golang Hexagonal, Angular Product, .NET Hexagonal), o si el usuario pasa `--pair` o pide modo pair, **el modo Pair interactivo se activa de forma automática**. En este modo no se delega a ciegas a un subagente sin visibilidad: tú ejecutas como **Driver** en el worktree y el usuario actúa como **Navigator**.

**Protocolo de Intervención con Preguntas de Formulario:**
El agente ejecuta los ciclos TDD verticalmente (`1 test -> Red -> código mínimo -> Green -> Refactor en verde`) emitiendo su micro-reporte continuo. **Solo interviene consultando al usuario con preguntas interactivas de formulario (`ask_question` en Gemini/AGY, o formulario estructurado de opciones en otros LLMs) cuando sea REALMENTE NECESARIO:**
1. **Decisión de arquitectura o diseño no prevista:** cuando el spec o SDD no especifica detalles críticos (ej. elección de adaptador, contrato de endpoints, nombres de eventos de dominio).
2. **Refactorización o normalización de stack:** ante decisiones de reestructuración o cambios en interfaces públicas.
3. **Las 5 paradas de `/pair`:**
   - (a) Decisión fuera del plan/spec.
   - (b) Detección de alcance no solicitado (YAGNI).
   - (c) Conflicto con tests existentes (prohibido debilitarlos).
   - (d) **Dos intentos sin llegar a verde** (detenerse y pedir guía o revertir al último verde).
   - (e) Paso que supera ~50 líneas o 3 archivos.
4. **Aprobación de la Lista de Tests y Costuras:** antes de empezar el primer ciclo.
5. **Aprobación de commits y cierre:** confirmando mensaje de commit o gates.

Para repositorios genéricos sin stack normativo detectado y sin `--pair`, se utiliza el subagente delegado tradicional `harness-flow:implementer` (ver sección 5a).

> **Shell.** Cada llamada Bash abre un shell nuevo: `$PY` y `$H` no sobreviven,
> asi que el bootstrap va pegado a cada comando, siempre. Los bloques de abajo
> usan bash (macOS, Linux, WSL, y Windows con Git for Windows). En **Windows sin
> Git for Windows la tool Bash es PowerShell**: ahi el interprete se llama
> `python` y el prefijo equivalente es
> `python "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --powershell | Invoke-Expression`,
> invocando despues con `& $PY ...`. Detalle en `references/claude.md`.

## 1. Gate del spec

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/gate.py" check-spec --feature $ARGUMENTS[0]
```

Con exit distinto de 0 no se implementa: el spec no esta aprobado o cambio
despues del sello. Vuelve a `/harness-flow:spec $ARGUMENTS[0]`.

## 2. Worktree

Si la feature aun no tiene `worktree` en `harness/feature_list.json`, crealo:

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/worktree.py" start --feature $ARGUMENTS[0]
```

Anota la ruta que imprime. En una raiz multi-repo sin `.git`, el arbol se
declara con `worktree.py register`; ver `references/multirepo.md`.

## 3. Brief

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/contexto.py" brief --feature $ARGUMENTS[0]
```

Si dice que el contexto esta vencido, refresca con `contexto.py refrescar`
antes de delegar: el implementer disena con lo que le pases.

## 4. Elige el effort

Con el spec y el brief a la vista, elige el nivel del implementer. No hace falta
que el usuario lo confirme, salvo que haya pedido otro nivel: su eleccion manda.

- `high`, por defecto: spec claro, patrones conocidos.
- `xhigh`, si el codigo tiene que resolver un riesgo concreto: contratos entre
  varios repos, migracion con perdida o irreversibilidad posible, concurrencia,
  o una leccion del brief que documenta una falla previa en esta clase de
  trabajo. Mencionarlo no basta: nombra la decision y su riesgo.

Anuncialo en una frase antes de lanzar: `Implementer: claude-sonnet-5-5 / high —
un repo, AC con comando`. Criterios completos en
`${CLAUDE_PLUGIN_ROOT}/references/modelos.md` ("Seleccion automatica").

## 5. Delega (por defecto) o ejecuta en Modo Pair (`--pair`)

### 5a. Modo delegado (por defecto, sin `--pair`)

Tool `Agent` con `subagent_type: "harness-flow:implementer"` y `effort` con el
nivel del paso 4. En el prompt, una linea de goal, la ruta del spec, la del
worktree y la salida ENTERA del paso 3:

> Implementa la feature #$ARGUMENTS[0]. Spec: `docs/spec-feature-$ARGUMENTS[0]-<slug>.md`.
> Worktree: `<ruta>`. Brief: <salida de contexto.py brief>

- **Pasa `effort`, nunca `model`.** El `effort` de la invocacion le gana al del
  frontmatter, que queda en `xhigh` como red si lo olvidas. Un `model` pisaria
  el Sonnet 5.5 del frontmatter.
- No uses un fork: arrastraria todo tu historial de diseno al implementer y le
  quitaria el foco en el spec aprobado.
- El subagente no puede preguntarle al usuario. Si vuelve con una pregunta
  sobre el spec, llevala tu al chat. Si la respuesta cambia un AC, es una
  enmienda (`/harness-flow:spec $ARGUMENTS[0]`, seccion 4), no una instruccion nueva al
  implementer.

### 5b. Modo Pair interactivo (`--pair`: Driver = IA, Navigator = humano)

Si los argumentos incluyen `--pair` (o el usuario pidio modo pair, estilo `/pair` de `hola-ai`):

1. **Revisa el plan y propone la Lista de Tests (sin escribirlos aun):**
   - No lances el subagente `implementer`: tu eres el **Driver** en el worktree y
     el usuario es el **Navigator**.
   - Contrasta el `## Plan vertical` contra el codigo del worktree (si algo ya no
     encaja, avisalo; si no hay plan, propon uno de ≤5 bullets).
   - A partir de los AC, propon **la lista de tests (solo nombres)** diciendo
     **donde** se prueba cada uno (endpoint, servicio, componente/UI, integracion;
     o **verificacion manual** si es visual) y **espera la aprobacion del usuario**.
2. **Ciclo (`1 paso = 1 test de la lista`):**
   - Escribe 1 test -> correlo y muestra que falla (**Red**) -> escribe el
     **codigo minimo** (con el valor esperado del AC, nunca calculado con la misma
     logica del codigo) -> corre los tests y muestra que pasan (**Green**).
   - Por defecto haz **1 paso y detente** con este micro-mensaje bajo norma ASD-STE100 (ver `references/comunicacion-ste100-y-prompts.md`):
     `✅ Pasa: "<nombre del test>"`
     `⚙️ Decisión: <decisión técnica adoptada en <= 20 palabras>`
     `🔍 Comprobación: <comando exacto y duración/resultado en < 5 min>`
     `❓ ¿Cambiamos algo o seguimos con "<siguiente test>"?`
   - Si el usuario dice `"haz N"` / `"avanza N"` con verbos agrupados (ej. `"haz 3: codifica, compila y testea los siguientes 3"`), ejecuta `N` ciclos completos uno
     tras otro (nunca `N` tests juntos y luego el codigo) mostrando **primero los
     tests y despues el codigo**.
3. **Detente de inmediato (incluso a mitad de un lote de `N`) ante las 5 paradas:**
   - (1) necesitas tomar una decision de diseno que no esta en el plan/spec;
   - (2) se te ocurre agregar algo que no pidieron (YAGNI);
   - (3) hacer pasar un test requeriria cambiar, saltar (`skip`) o borrar un test;
   - (4) llevas **dos intentos** sin llegar a verde;
   - (5) el paso supera **~50 lineas o toca mas de 3 archivos** (propon partirlo).
4. **Chequeo y Commits:** con toda la lista en verde, verifica con el usuario los
   AC de verificacion manual, **sugiere** refactors sin aplicarlos solo (solo en
   verde), y **sugiere el mensaje de commit** separando funcionalidad y refactor
   para commitear en el worktree con su OK y escribir `docs/impl-$ARGUMENTS[0].md`.

## 6. Contrasta la evidencia

Cuando vuelva, abre `docs/impl-$ARGUMENTS[0].md` en la raiz. Es un autoinforme:

- hay una seccion `## AC-n` por CADA AC del spec, con cita `archivo:linea`;
- las citas existen en el WORKTREE y dicen lo que la seccion afirma (abre al
  menos las de los AC sin comando de verificacion);
- el trabajo esta commiteado en la rama de la feature:

  ```bash
  git -C <worktree> status --short && git -C <worktree> log --oneline -5
  ```

Si algo no aguanta, devuelvelo al implementer (otra llamada al subagente con el
hallazgo concreto y el mismo `effort`) antes de pasar al review.

## 7. Siguiente paso

`/harness-flow:review $ARGUMENTS[0]`. El revisor es otro subagente, aislado y en Opus 5.5:
no le cuentes lo que hizo el implementer.
