---
description: Rol implementer de harness-flow — verifica el gate del spec e implementa en modo Pair (por defecto, con la lista de tests aprobada por el usuario) o delega al subagente implementer con --delegado, en el worktree de la feature y contrasta su evidencia antes del review.
argument-hint: <id-feature> [--delegado]
model: claude-opus-5-5
effort: xhigh
---

# harness-flow: implementar (rol implementer)

Implementa la feature `$ARGUMENTS[0]`. Argumentos recibidos: `$ARGUMENTS`.

**El modo es Pair, siempre, salvo que el usuario pida delegar.** No depende de
que el repo tenga un stack detectado. Solo se delega al subagente si los
argumentos traen `--delegado`, si el usuario lo pide, o si la sesion no tiene
usuario (`claude -p`). El modo queda en el backlog desde que el usuario aprueba
el spec (`gate.py approve-spec`), `worktree.py start` lo confirma y el brief lo
repite; en modo pair, `close` exige la lista de tests aprobada.

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

Con `--delegado` implementa el subagente `harness-flow:implementer` (sección 5a).

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

Si la feature aun no tiene `worktree` en `harness/feature_list.json`, crealo.
Agrega `--delegado` SOLO si el usuario pidio delegar:

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/worktree.py" start --feature $ARGUMENTS[0]
```

`start` registra el modo (`pair` por defecto) y lo imprime. Si la feature ya
estaba arrancada y el usuario cambia de idea:

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/worktree.py" modo --feature $ARGUMENTS[0] --delegado
```

Anota la ruta que imprime. En una raiz multi-repo sin `.git`, el arbol se
declara con `worktree.py register`; ver `references/multirepo.md`. `register`
no cambia el modo: vale el que quedo al aprobar el spec. Si avisa que la
feature no tiene modo (spec sellado antes de que se registrara) y aun no hay
codigo, fijalo con `worktree.py modo --feature $ARGUMENTS[0] --pair`.

## 3. Brief

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/contexto.py" brief --feature $ARGUMENTS[0]
```

Si dice que el contexto esta vencido, refresca con `contexto.py refrescar`
antes de seguir. El brief trae el modo registrado y, al final, el **texto
completo de las reglas de cada stack** que toca la feature y el **indice de sus
skills** (nombre, descripcion y ruta del `SKILL.md`). Las reglas son
obligatorias, las tengas cargadas por otra via o no. Antes de una tarea que una
skill del stack cubre, abre su `SKILL.md` en la ruta del indice y siguela: la
ruta existe aunque la skill no este instalada en el repo.

Trae tambien el bloque **`NORMAS DE INGENIERIA`** (datos, diseno, refactor,
rendimiento, IA, servicios, construccion, seguridad, versiones y Context7) y, por
cada stack, su **`DOCUMENTACION VIGENTE`**. Es la misma lista que audita el
revisor: cumplela en modo pair y en delegado. Cada norma aplica solo si el
cambio toca su materia; su violacion es hallazgo bloqueante o mayor.

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

## 5. Modo Pair (por defecto) o delegado (`--delegado`)

### 5a. Modo delegado (solo con `--delegado` o sin usuario)

Tool `Agent` con `subagent_type: "harness-flow:implementer"` y `effort` con el
nivel del paso 4. En el prompt, una linea de goal, la ruta del spec, la del
worktree y la salida ENTERA del paso 3:

> Implementa la feature #$ARGUMENTS[0]. Spec: `docs/spec-feature-$ARGUMENTS[0]-<slug>.md`.
> Worktree: `<ruta>`. Brief: <salida de contexto.py brief>

- **El brief es el paquete completo.** Trae el protocolo, las reglas de cada stack, el
  indice de sus skills y las normas, cada uno con el comando que imprime su contenido
  (`stack.py skill ...`, `normas.py --ref ...`), con rutas absolutas. No anexes skills
  ni referencias a mano: el subagente las lee con esos comandos.
- **Pasa `effort`, nunca `model`.** El `effort` de la invocacion le gana al del
  frontmatter, que queda en `xhigh` como red si lo olvidas. Un `model` pisaria
  el Sonnet 5.5 del frontmatter.
- No uses un fork: arrastraria todo tu historial de diseno al implementer y le
  quitaria el foco en el spec aprobado.
- El subagente no puede preguntarle al usuario. Si vuelve con una pregunta
  sobre el spec, llevala tu al chat. Si la respuesta cambia un AC, es una
  enmienda (`/harness-flow:spec $ARGUMENTS[0]`, seccion 4), no una instruccion nueva al
  implementer.

### 5b. Modo Pair interactivo (por defecto: Driver = IA, Navigator = humano)

Es el modo de toda feature cuyo modo registrado es `pair` (estilo `/pair` de `hola-ai`):

0. **Lee el brief del paso 3 antes de proponer nada:** las reglas del stack y el
   bloque `NORMAS DE INGENIERIA` mandan sobre tu costumbre. Por cada AC marcado
   `[negativo]`, el test de rechazo va en la lista antes que el camino feliz.
1. **Revisa el plan y propone la Lista de Tests (sin escribirlos aun):**
   - No lances el subagente `implementer`: tu eres el **Driver** en el worktree y
     el usuario es el **Navigator**.
   - Contrasta el `## Plan vertical` contra el codigo del worktree (si algo ya no
     encaja, avisalo; si no hay plan, propon uno de ≤5 bullets).
   - A partir de los AC, escribe **la lista de tests (solo nombres)** en
     `docs/tests-$ARGUMENTS[0].md` desde `${CLAUDE_PLUGIN_ROOT}/templates/tests.md`: una linea
     `- AC-n: <nombre> [costura: ...]` por test (o `- AC-n: verificacion manual: ...`
     si es visual). MUESTRALA, PREGUNTA, y solo con el SI del usuario:

     ```bash
     eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/gate.py" aprobar-tests --feature $ARGUMENTS[0] --yes
     ```

     Sin ese sello `close` se niega. Si la lista cambia mientras implementas
     (un test nuevo, uno que sobra), vuelve a mostrarla y a sellarla.
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

   **Un hallazgo no abre una ficha.** Lo que encuentres fuera de los AC se arregla
   en la rama si es de esta feature (enmienda si cambia un AC) o se anota con
   `hallazgo.py anotar [--feature <id>]`. Una ficha nueva la decide el usuario, y
   si le preguntas, la primera opcion es la enmienda (`references/hallazgos.md`).
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
