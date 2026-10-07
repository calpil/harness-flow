---
description: Rol implementer de harness-flow — verifica el gate del spec, delega la implementacion al subagente implementer en el worktree de la feature y contrasta su evidencia antes del review.
argument-hint: <id-feature>
model: claude-opus-5-5
effort: xhigh
---

# harness-flow: implementar (rol implementer)

Implementa la feature `$1`. **El codigo no lo escribes tu**: lo escribe el
subagente `harness-flow:implementer` (Sonnet 5.5, effort por tarea, ver
`${CLAUDE_PLUGIN_ROOT}/references/modelos.md`). Tu orquestas, contrastas su
evidencia y llevas al usuario lo que el spec no resuelve.

> **Shell.** Cada llamada Bash abre un shell nuevo: `$PY` y `$H` no sobreviven,
> asi que el bootstrap va pegado a cada comando, siempre. Los bloques de abajo
> usan bash (macOS, Linux, WSL, y Windows con Git for Windows). En **Windows sin
> Git for Windows la tool Bash es PowerShell**: ahi el interprete se llama
> `python` y el prefijo equivalente es
> `python "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --powershell | Invoke-Expression`,
> invocando despues con `& $PY ...`. Detalle en `references/claude.md`.

## 1. Gate del spec

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/gate.py" check-spec --feature $1
```

Con exit distinto de 0 no se implementa: el spec no esta aprobado o cambio
despues del sello. Vuelve a `/harness-flow:spec $1`.

## 2. Worktree

Si la feature aun no tiene `worktree` en `harness/feature_list.json`, crealo:

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/worktree.py" start --feature $1
```

Anota la ruta que imprime. En una raiz multi-repo sin `.git`, el arbol se
declara con `worktree.py register`; ver `references/multirepo.md`.

## 3. Brief

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/contexto.py" brief --feature $1
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

## 5. Delega

Tool `Agent` con `subagent_type: "harness-flow:implementer"` y `effort` con el
nivel del paso 4. En el prompt, una linea de goal, la ruta del spec, la del
worktree y la salida ENTERA del paso 3:

> Implementa la feature #$1. Spec: `docs/spec-feature-$1-<slug>.md`.
> Worktree: `<ruta>`. Brief: <salida de contexto.py brief>

- **Pasa `effort`, nunca `model`.** El `effort` de la invocacion le gana al del
  frontmatter, que queda en `xhigh` como red si lo olvidas. Un `model` pisaria
  el Sonnet 5.5 del frontmatter.
- No uses un fork: arrastraria todo tu historial de diseno al implementer y le
  quitaria el foco en el spec aprobado.
- El subagente no puede preguntarle al usuario. Si vuelve con una pregunta
  sobre el spec, llevala tu al chat. Si la respuesta cambia un AC, es una
  enmienda (`/harness-flow:spec $1`, seccion 4), no una instruccion nueva al
  implementer.

## 6. Contrasta la evidencia

Cuando vuelva, abre `docs/impl-$1.md` en la raiz. Es un autoinforme:

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

`/harness-flow:review $1`. El revisor es otro subagente, aislado y en Opus 5.5:
no le cuentes lo que hizo el implementer.
