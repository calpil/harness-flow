# Gemini (Antigravity / AGY y Gemini CLI)

Esta guía separa con claridad **Antigravity (AGY)** y **Gemini CLI**, ambos resueltos como `HARNESS_HOST=gemini` por `entorno.py`.

## 1. AGY vs Gemini CLI: diferencias reales

| Capacidad | Antigravity (AGY) | Gemini CLI (`gemini`) |
| --- | --- | --- |
| **Descoberta global de `harness-flow`** | `~/.gemini/config/skills/harness-flow` (y `~/.gemini/skills/`) | `~/.gemini/skills/harness-flow` y `~/.agents/skills/harness-flow` |
| **Contrato en la raíz del repo** | `AGENTS.md` y `GEMINI.md` | `GEMINI.md` por defecto (importa `@./AGENTS.md`; o `contextFileName` en `.gemini/settings.json`) |
| **Rules y skills de stack** | `.agents/rules/*.md` (`trigger: always_on`) y `.agents/skills/` | `.gemini/rules/*.md` y `.gemini/skills/` |
| **Presupuesto de reglas nativas** | `defaultRulesBudget`: 20 000 tokens y 24 KB por archivo (lo excedente pasa a puntero) | Depende de la ventana de contexto y `GEMINI.md` |
| **Formularios en Modo Pair** | Herramienta nativa `ask_question` con recomendación `(Recommended)` | Formulario estructurado Markdown (`[A]`, `[B]`, `[C]`, `(Recomendada)`) |
| **Subagente aislado (Rol 3 / `--delegado`)** | `invoke_subagent(TypeName="self", Model="inherit", Workspace="inherit")` o `swarm(action="add", model=...)` | `gemini -m gemini-4-argon -p "<prompt>"` (sesión nueva sin historial) |
| **Context7 MCP** | Lazy-loaded en `~/.gemini/config/mcp_config.json` (`serverUrl`); se invoca vía `call_mcp_tool` | Directo en `~/.gemini/settings.json` (`httpUrl`); tools `resolve-library-id` / `query-docs` |
| **Raíz de lecciones (`leccion.py donde`)** | `~/.gemini/config/skills`, luego `~/.gemini/skills` y `~/.agents/skills` | `~/.gemini/skills` y `~/.agents/skills` |

`commands/` y `agents/*.md` frontmatter (`model`, `effort`, `tools`) son de Claude Code / Kimi. En AGY y Gemini CLI el flujo se sigue desde `SKILL.md` y los scripts Python; al lanzar un subagente se le indica seguir el **cuerpo** de `<skill>/agents/revisor.md` (o `implementer.md`) ignorando su frontmatter.

## 2. Detección de host y shell

`entorno.py` detecta `HARNESS_HOST=gemini` en este orden (tras `--host` o `HARNESS_HOST` explícito):

1. Variables de entorno `ANTIGRAVITY_AGENT`, `ANTIGRAVITY_CLI_ALIAS`, `GEMINI_CLI` o `GEMINI_AGENT` activas.
2. Ruta del script bajo `.gemini/config/skills/` o `.gemini/skills/` (sin `resolve()`).

Cada llamada de terminal en AGY y Gemini CLI abre un subshell nuevo (`$PY`, `$H` y `HARNESS_HOST` no persisten entre llamadas). Pega siempre el `eval` en la misma llamada:

```bash
eval "$(python3 <skill>/scripts/entorno.py --shell)" && "$PY" "$H/estado.py"
```

El intérprete resuelto es el venv neutro `~/.harness-flow/venv` (con `psycopg` para Memory Hub).

## 3. Política de modelos Gemini 4 por rol

Asignación obligatoria de modelos Gemini 4:

| Rol | Modelo | ID / Effort | En AGY | En Gemini CLI |
| --- | --- | --- | --- | --- |
| **0 Producto (PRD/SDD)** | **Gemini 4 Carbon (High)** | `gemini-4-carbon` · `high` | Sesión principal en `Gemini 4 Carbon (High)` | `gemini -m gemini-4-carbon` |
| **1 Leader (Spec y AC)** | **Gemini 4 Carbon (High)** | `gemini-4-carbon` · `high` | Sesión principal en `Gemini 4 Carbon (High)` | `gemini -m gemini-4-carbon` |
| **2 Implementer (Pair / Delegado)** | **Gemini 4 Argon (High)** | `gemini-4-argon` · `high` | Sesión principal en `Gemini 4 Argon (High)` (pair); si delegas: ver trampa `inherit` abajo | `gemini -m gemini-4-argon` |
| **3 Revisor aislado** | **Gemini 4 Argon (High)** | `gemini-4-argon` · `high` | `invoke_subagent("self", Model="inherit")` tras confirmar sesión en `Argon High`, o `swarm(action="add", model="Gemini 4 Argon (High)")` | `gemini -m gemini-4-argon -p ...` |
| **4 Cierre** | **Gemini 4 Hydrogen** | `gemini-4-hydrogen` · `medium`/`high` | Gates Python + sesión en `Gemini 4 Hydrogen` | `gemini -m gemini-4-hydrogen` |
| **Estado y rutinas** | **Gemini 4 Hydrogen** | `gemini-4-hydrogen` · `low`/`medium` | Gates Python + sesión en `Gemini 4 Hydrogen` | `gemini -m gemini-4-hydrogen` |

Consulta programática desde cualquier sesión:

```bash
eval "$(python3 <skill>/scripts/entorno.py --shell)" && "$PY" "$H/modelo.py" gemini --todos
eval "$(python3 <skill>/scripts/entorno.py --shell)" && "$PY" "$H/modelo.py" gemini --rol revisor
```

Además, cuando `HARNESS_HOST=gemini`, los propios scripts recuerdan el modelo correspondiente en cada transición:
- `estado.py` → `Gemini 4 Hydrogen` (+ mapa rápido de los 3 modelos).
- `producto.py borrador --doc prd|sdd` → `Gemini 4 Carbon (High)`.
- `contexto.py brief --feature <id>` → `Gemini 4 Carbon (High)` mientras el spec no esté sellado (Rol 1 Leader), y `Gemini 4 Argon (High)` una vez sellado (Rol 2 Implementer).
- `revision.py --feature <id> --briefing` → `Gemini 4 Argon (High)`.

### Trampa de `Model: "inherit"` en AGY y cómo evitarla

En AGY, `invoke_subagent` solo admite `Model: "inherit" | "pro" | "flash" | "flash_lite"` (no acepta el nombre exacto `Gemini 4 Argon (High)` ni un parámetro `effort`). Si tu sesión corrió el Rol 0/1 en **`Gemini 4 Carbon (High)`** y lanzas un subagente Implementer o Revisor con `Model: "inherit"` sin cambiar antes de modelo, el subagente heredará **Carbon High** (o **Hydrogen** si vienes de Cierre) en lugar de **Argon High**.

Dos salidas limpias en AGY:
1. **Cambiar el modelo de la sesión** a `Gemini 4 Argon (High)` antes del Rol 2 (Pair / Delegado) y del Rol 3 (Revisor), y usar `invoke_subagent(TypeName="self", Model="inherit", Workspace="inherit")`.
2. **Fijar el modelo por worker con `swarm`** si coordinas desde otro modelo: `swarm(action="add", name="revisor-<id>", model="Gemini 4 Argon (High)", workspace="inherit", brief="<briefing completo + seguir cuerpo de agents/revisor.md>")`.

## 4. Carga automática de `rules` y `skills` (front + backend) en la sesión

### Por qué hacía falta sincronización de sesión (`scripts/gemini_sesion.py`)

AGY descubre `.agents/rules/*.md` y `.agents/skills/*/SKILL.md` subiendo desde el workspace hasta `.git`; Gemini CLI hace lo mismo con `.gemini/` y `GEMINI.md`. Ninguno camina hacia repos hermanos fuera del workspace: si abres la sesión en el front (`angular-product`, `nextjs-product`) y el backend (`golang-hexagonal`, `dotnet-hexagonal`, etc.) vive en un repo hermano declarado en `harness/grafos.json`, el disco de la sesión no tenía las skills ni rules del backend.

### Cómo lo resuelve `harness-flow` en Gemini

1. **En el disco permanente (`stack.py normalizar`)**: instala `.claude/`, `.agents/`, `.gemini/`, `AGENTS.md` y `GEMINI.md` (que importa `@./AGENTS.md` para Gemini CLI) y enlaza la normativa en worktrees abiertos (`estado.py` y `worktree.py`). Nunca reemplaza un `AGENTS.md` o `GEMINI.md` creado por el usuario.
2. **En el brief inicial del Leader (`contexto.py brief`)**: si la feature aún está en spec draft (`todo`/`pending`, sin `last_spec_sig`, sin `worktree` y sin `microservicios` declarados), carga **todos los stacks normativos del proyecto** (front + backend), aunque la raíz sea un stack de frontend. Cuando el spec se aprueba o la feature pasa a `in_progress`, carga exactamente los repos de la feature.
3. **Publicación dinámica de sesión (`scripts/gemini_sesion.py`)**: cuando `HARNESS_HOST=gemini`, `contexto.py brief`, `revision.py --briefing` y `producto.py borrador --doc sdd` (y `contexto.py stacks` sin `--resumen`) publican en `.agents/` y `.gemini/` de la raíz, los repos de la feature y sus worktrees:
   - `rules/harness-flow-sesion.md` (con `trigger: always_on`, rol activo, stacks y modelo Gemini 4).
   - `rules/<stack>--<regla>.md` (con `trigger: always_on`) y `skills/<stack>--<skill>/SKILL.md`.
   - **Deduplicación para cuidar `defaultRulesBudget` (20k tokens / 24 KB en AGY):** si un destino ya tiene instalada y vigente la copia nativa sin prefijo de su propio stack, no duplica esas reglas ni skills en ese destino; solo agrega las de los stacks hermanos y las que falten o estén viejas.
   - **Git siempre limpio:** las rutas de sesión (`*--*` y `harness-flow-sesion.md` bajo `.agents/` y `.gemini/`) se excluyen en `.git/info/exclude`, así que `git status` y `gate.py close` nunca ven cambios sucios.
   - **Qué no se toca:** nunca borra rules/skills creadas por el usuario ni copias de `stack.py normalizar`; tampoco escribe a través de carpetas symlinkeadas por `enlazar_normativa` en worktrees.
   - El PRD (`producto.py borrador --doc prd`) no publica archivos de sesión (solo imprime el resumen de stacks).

## 5. Modo Pair Automático y formularios

- **Pair es el modo por defecto en cualquier repo** (lo sella `gate.py approve-spec`, lo confirma `worktree.py start`, y `gate.py close` exige `docs/tests-<id>.md` sellada por `gate.py sellar-tests`). No hace falta ningún flag `--pair`.
- En **AGY**: todas las paradas que preguntan (paradas 1, 3 y 4; enmienda; ficha nueva; cierre) van en **un** formulario usando `ask_question` con la recomendación `(Recommended)` primera.
- En **Gemini CLI**: usa un formulario estructurado Markdown (`[A]`, `[B]`, `[C]` con `(Recomendada)`).
- El protocolo completo, las 13 normas (`scripts/normas.py`, incluidos Feedback Loop/Feature Map, Agent Evals y Guardrails), el texto de las reglas y el índice de skills llegan por la salida del brief en ambos clientes.

## 6. Revisor aislado (Rol 3)

### En AGY
1. Confirma que la sesión está en **`Gemini 4 Argon (High)`** (o usa `swarm` fijando `model: "Gemini 4 Argon (High)"`).
2. Genera el briefing:
   ```bash
   eval "$(python3 <skill>/scripts/entorno.py --shell)" && "$PY" "$H/revision.py" --feature <id> --briefing
   ```
3. Lanza `invoke_subagent` con `TypeName: "self"`, `Model: "inherit"`, `Workspace: "inherit"`, pegando el briefing entero + `"sigue el cuerpo de <skill>/agents/revisor.md; ignora su frontmatter"`.
   - **Nunca uses `TypeName: "research"`** (es solo lectura: no puede correr comandos de AC ni escribir `docs/review-<id>.md`).
   - **Nunca uses un fork** de la sesión (hereda tu historial y rompe el aislamiento).
4. Lee `docs/review-<id>.md`, verifica citas `archivo:linea` y sella con `gate.py revision --feature <id> --veredicto ...`.

### En Gemini CLI
1. Genera el briefing a un archivo temporal (puede superar 60 KB):
   ```bash
   eval "$(python3 <skill>/scripts/entorno.py --shell)" && "$PY" "$H/revision.py" --feature <id> --briefing > /tmp/briefing-<id>.md
   ```
2. Ejecuta una instancia nueva sin historial en **`gemini-4-argon`** desde la raíz del proyecto (para que `docs/review-<id>.md` quede donde `gate.py revision` lo lee):
   ```bash
   gemini -m gemini-4-argon -p "Revisa la feature #<id> siguiendo el cuerpo de <skill>/agents/revisor.md (ignora su frontmatter) y el briefing en /tmp/briefing-<id>.md. Escribe docs/review-<id>.md y no modifiques codigo."
   ```
3. Verifica `docs/review-<id>.md` y sella con `gate.py revision`.

## 7. Context7 MCP

- **En AGY (`~/.gemini/config/mcp_config.json`)**:
  ```json
  { "mcpServers": { "context7": { "serverUrl": "https://mcp.context7.com/mcp" } } }
  ```
  Context7 se expone como MCP **lazy-loaded**: lee primero el schema en `<appDataDir>/mcp/context7/<toolName>.json` y llama `call_mcp_tool(ServerName="context7", ToolName="query-docs"|"resolve-library-id", Arguments=...)`. El bloque `DOCUMENTACION VIGENTE` del brief y del briefing te da el `library_id` exacto de cada stack y recuerda esta llamada cuando `HARNESS_HOST=gemini`.
- **En Gemini CLI (`~/.gemini/settings.json`)**:
  ```json
  { "mcpServers": { "context7": { "httpUrl": "https://mcp.context7.com/mcp" } } }
  ```
  Invoca directamente `resolve-library-id` y `query-docs`.

## 8. Lecciones, Obsidian y `codebase-memory-mcp`

- **Lecciones**: consulta `leccion.py donde` (`~/.gemini/config/skills` en AGY; `~/.gemini/skills` o `~/.agents/skills` en Gemini CLI) y escribe `<raiz>/<clase>/SKILL.md`.
- **Obsidian**: `vault.py build` y los hooks automáticos de `start`/`close` funcionan igual en ambos clientes.
- **`codebase-memory-mcp`**: si trabajas con varios proyectos en paralelo en AGY/Gemini CLI y el daemon compartido en `/tmp` da conflictos, usa `cbm_proyecto.py --harness-config-mcp` y `--harness-activar` ([contexto.md](contexto.md)).
