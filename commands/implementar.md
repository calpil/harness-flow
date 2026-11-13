---
description: Rol implementer de harness-flow — verifica el gate del spec e implementa en modo Pair automatico (por defecto: avanza solo y pregunta por formulario solo cuando hace falta) o delega al subagente implementer con --delegado, en el worktree de la feature y contrasta su evidencia antes del review.
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
repite; en modo pair, `close` exige la lista de tests sellada.

**Pair automatico: avanzas solo y preguntas solo cuando hace falta.** Ejecutas
los ciclos TDD uno tras otro (`1 test -> Red -> codigo minimo -> Green -> Refactor
en verde`) y reportas cada ciclo en una linea. No preguntas si sigues.

**Un formulario (`AskUserQuestion`, `ask_question` en AGY/Gemini, o un formulario
de opciones en otros hosts) hace falta SOLO en estos casos:**

1. **Parada (1):** una decision de diseno que el plan o el spec no trae (contrato
   de un endpoint, modelo de datos, nombre de un evento, un refactor que cambia
   una interfaz publica).
2. **Parada (3):** hacer pasar un test exige cambiar, saltar o borrar un test.
3. **Parada (4):** dos intentos sin llegar a verde. Vuelve al ultimo verde y pregunta.
4. **La lista de tests pierde algo:** quitas un test ya sellado, o un AC queda
   solo con verificacion manual sin que el spec lo declare `[costura: manual]`.
5. **Lo que sella el usuario:** una enmienda, una ficha nueva, y el cierre o la
   publicacion que el proyecto reserve.
6. **Verificacion manual:** al final, los AC que solo el usuario puede mirar.

**No preguntes** si sigues con el test siguiente, el orden o el nombre de los
tests, el mensaje de un commit, un refactor en verde dentro de los archivos de
la feature, ni como partir un paso grande. Decidelo, hazlo y reportalo.

**Como preguntar:** junta las preguntas pendientes en UN formulario, con la opcion
recomendada primero. Mientras esperas la respuesta de una feature, sigue con lo
que no depende de ella. Una enmienda es un solo formulario: lleva la propuesta
ya escrita, no preguntes antes "donde lo arreglo" y despues "apruebas".

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

### 5b. Modo Pair automatico (por defecto: la sesion implementa y avanza sola)

Es el modo de toda feature cuyo modo registrado es `pair`:

0. **Lee el brief del paso 3 antes de escribir:** las reglas del stack y el
   bloque `NORMAS DE INGENIERIA` mandan sobre tu costumbre. Por cada AC marcado
   `[negativo]`, el test de rechazo va en la lista antes que el camino feliz.
1. **Revisa el plan y escribe la lista de tests (solo nombres):**
   - Contrasta el `## Plan vertical` contra el codigo del worktree. Si algo ya no
     encaja y cambia un AC, es la parada (1). Si no hay plan, escribe uno de ≤5
     bullets y sigue.
   - A partir de los AC, escribe la lista en `docs/tests-$ARGUMENTS[0].md` desde
     `${CLAUDE_PLUGIN_ROOT}/templates/tests.md`: una linea
     `- AC-n: <nombre> [costura: ...]` por test (o `- AC-n: verificacion manual: ...`
     si el spec declara ese AC `[costura: manual]`). Sellala tu:

     ```bash
     eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/gate.py" sellar-tests --feature $ARGUMENTS[0]
     ```

   - **Muestra la lista en el chat y empieza. No esperes aprobacion.** Si el
     usuario objeta un test, corrige la lista y vuelve a sellarla.
   - Sin el sello `close` se niega. Si la lista crece mientras implementas,
     vuelve a sellarla sin preguntar. El gate se niega sin `--yes` solo si la
     lista quita un test sellado o deja un AC solo con verificacion manual que el
     spec no declara: eso se pregunta, y con el SI del usuario se repite con `--yes`.
2. **Ciclo (`1 paso = 1 test de la lista`), uno tras otro:**
   - Escribe 1 test -> correlo y comprueba que falla (**Red**) -> escribe el
     **codigo minimo** (con el valor esperado del AC, nunca calculado con la misma
     logica del codigo) -> corre los tests y comprueba que pasan (**Green**) ->
     refactor en verde dentro de los archivos de la feature.
   - Reporta cada ciclo en una linea y **sigue con el siguiente sin preguntar**
     (norma ASD-STE100, `references/comunicacion-ste100-y-prompts.md`):
     `✅ "<nombre del test>" — <decision tecnica en <= 20 palabras> (<archivo:linea>)`
   - Nunca escribas todos los tests y despues el codigo.
   - **Solo si el usuario pide "paso a paso"**, pausa tras cada ciclo con
     `❓ ¿Cambiamos algo o seguimos con "<siguiente test>"?`. Con `"haz N"` ejecuta
     `N` ciclos y vuelve a pausar.
3. **Las 5 paradas:**
   - (1) necesitas una decision de diseno que no esta en el plan/spec: **pregunta**;
   - (2) se te ocurre agregar algo que ningun AC pide: **no lo agregues**, anotalo
     como hallazgo y sigue;
   - (3) hacer pasar un test requeriria cambiar, saltar (`skip`) o borrar un test:
     **pregunta**;
   - (4) llevas **dos intentos** sin llegar a verde: vuelve al ultimo verde y **pregunta**;
   - (5) el paso supera **~50 lineas o toca mas de 3 archivos**: **partelo tu** en
     pasos mas chicos y sigue.

   **Un hallazgo no abre una ficha.** Lo que encuentres fuera de los AC se arregla
   en la rama si es de esta feature (enmienda si cambia un AC) o se anota con
   `hallazgo.py anotar [--feature <id>]`. Una ficha nueva la decide el usuario, y
   si le preguntas, la primera opcion es la enmienda (`references/hallazgos.md`).
4. **Commits:** commitea en la rama de la feature cada unidad logica en verde,
   sin pedir permiso, separando funcionalidad (`feat:`/`fix:`) y refactor
   (`refactor:`). Sigue la convencion de commits del proyecto.
5. **Cierre del rol:** con toda la lista en verde, pide al usuario en un solo
   formulario los AC de verificacion manual, y escribe `docs/impl-$ARGUMENTS[0].md`.

**Varias features en paralelo.** Si el usuario pide avanzar varias a la vez y el
host tiene subagentes, lanza un implementer por feature, cada uno en su worktree
y con su brief entero. El modo sigue siendo `pair`: cada uno escribe su lista de
tests y tu la sellas. Un subagente no puede preguntar al usuario: te devuelve la
parada. Si el spec ya la decide, respondele tu; si no, llevala al usuario, junto
con las de las otras features, en un solo formulario.

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
