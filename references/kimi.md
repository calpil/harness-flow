# Kimi Code

## Que carga Kimi

Kimi Code (2.x) descubre este `SKILL.md` como skill de usuario o de proyecto:

- `$KIMI_CODE_HOME/skills/harness-flow` (`~/.kimi-code/skills/harness-flow`)
- `~/.agents/skills/harness-flow` (el minimo comun; en la maquina de referencia,
  symlink al clone de Hermes)
- `<repo>/.kimi-code/skills/harness-flow` y `<repo>/.agents/skills/harness-flow`
- como plugin instalado: Kimi copia el directorio a
  `$KIMI_CODE_HOME/plugins/managed/harness-flow/` y corre desde ESA copia. Un
  `git pull` del clone NO actualiza el plugin: hay que reinstalar con
  `/plugins install <ruta-del-clone>` y recargar (`/reload` o sesion nueva).

`/plugins install` es slash command del TUI; no existe como subcomando `kimi`
del CLI (`kimi plugins` responde "unknown command"). Tambien se puede lanzar
desde fuera con `kimi -p "/plugins install <ruta-del-clone>"`.

Con el plugin habilitado, `agents/revisor.md` y `agents/implementer.md` quedan
registrados como agentes y la tool `Agent` acepta `subagent_type: "revisor"` e
`implementer`. El frontmatter de `revisor.md`
(`model: claude-opus-5-5`, `tools: Read, Grep, Glob, Bash, Write, WebFetch, WebSearch, mcp__codebase-memory-mcp__*, mcp__context7__*, mcp__claude_ai_Context7__*`)
y de `implementer.md` cargan sin romper: Kimi ignora `model` (campo de Claude Code)
y acepta `tools` separado por comas.

Los `commands/*.md` no se registran: usan `${CLAUDE_PLUGIN_ROOT}`, que Kimi no
expande, y `kimi.plugin.json` no declara `commands` a proposito. El flujo se
sigue desde este skill, no desde atajos.

## Host

Kimi 2.x NO exporta marca de proceso al shell (nada equivalente a
`GROK_AGENT`): la identidad es la ruta del script, sin `resolve()`.

`entorno.py` reporta `kimi` cuando, despues de un `HARNESS_HOST` explicito:

1. el script cuelga de `$KIMI_CODE_HOME/skills/` (`~/.kimi-code/skills/`);
2. el script cuelga de `$KIMI_CODE_HOME/plugins/managed/` (la copia managed);
3. el script esta bajo el directorio que diga `KIMI_CODE_HOME`, si moviste la
   raiz de datos.

Por el symlink de `~/.agents/skills` el host es `gpt`: equivalente a efectos
practicos, porque las lecciones nacen en `~/.agents/skills`, que Kimi escanea.
Lo que no debes hacer es invocar los scripts por la ruta real del clone de
Hermes (`~/.hermes/...`): el host seria `hermes` y las lecciones nacerian en
`~/.hermes/skills`, que Kimi no lee. Si el agente resuelve el symlink o
trabaja con cwd dentro del clone, fija `HARNESS_HOST=kimi`:

```bash
python3 <skill>/scripts/entorno.py --host kimi --shell
```

El interprete es el venv neutro `~/.harness-flow/venv`, el mismo de Claude y de
GPT. `psycopg` solo hace falta para el Memory Hub.

## Implementer y Modo Pair (por defecto)

**Pair es el modo por defecto de toda feature**, con stack detectado o sin él: lo deja en el
backlog `gate.py approve-spec` al sellar el spec por primera vez y `gate.py close` exige su rastro,
la lista de tests aprobada (`gate.py aprobar-tests`). `--pair` ya no hace falta para activarlo. El
modo delegado es decisión del usuario (`worktree.py modo --feature <id> --delegado`) o de una sesión
sin usuario. En los dos modos el brief (`contexto.py brief`) trae el texto de las reglas de cada
stack, el índice de sus skills y el bloque `NORMAS DE INGENIERIA`, que es la misma lista que audita
el revisor: cúmplelas aunque tu host no cargue `agents/implementer.md`. Si delegas en un
subagente, pégale el brief entero y nada más: trae el comando que imprime cada skill del stack
(`stack.py skill`) y cada referencia (`normas.py --ref`), con rutas absolutas.

En Kimi Code hay dos caminos para implementar:

1. **Modo Pair interactivo (por defecto)**: corre en la **sesión principal de Kimi**
   (Driver = Kimi, Navigator = humano). No uses subagentes aquí: Kimi interactúa
   en el TUI sobre el worktree de la feature, acuerda la lista de tests antes de
   tocar código, y avanza `1 test -> Red -> código mínimo -> Green`, pausando en
   cada micro-ciclo con el micro-mensaje (`✅ Pasa "<test>"... ¿Seguimos?`) y
   respetando las 5 paradas XP de `references/vertical-slice.md`.
2. **Modo Delegado (autónomo)**: solo si el usuario lo pidió o la sesión no tiene usuario
   (`worktree.py start --feature <id> --delegado`). Con el plugin instalado, usa la tool `Agent` con
   `subagent_type: "implementer"`, pasando el prompt con el spec, el worktree y la
   salida de `contexto.py brief`. Sin plugin, puedes correr la sesión delegada con
   `kimi -p --agent-file <skill>/agents/implementer.md`.

Al terminar la implementación (en pair o delegada) y registrar `docs/impl-<id>.md`,
pasa al Rol 3 (Revisor aislado) con amnesia limpia.

## Revisor

Con el plugin instalado: tool `Agent` con `subagent_type: "revisor"`, pegando
en `prompt` la salida entera de `revision.py --feature <id> --briefing`.

Sin plugin, en sesion nueva:

```bash
kimi -p --agent-file <skill>/agents/revisor.md "Revisa la feature #<id>: <briefing>"
```

o con un subagente generico (`coder`/`explore` via la tool `Agent`):
declarando que el rigor baja, porque sin el cuerpo de `agents/revisor.md` el
review no hereda las invariantes del arnes.

Cuando vuelva, lee `docs/review-<id>.md` y sella con `gate.py revision`, igual
que en los otros hosts.

## Lecciones

Crear sigue el host. En `kimi` la raiz es `$KIMI_CODE_HOME/skills`
(`~/.kimi-code/skills`); si no existe, `~/.agents/skills`. Nunca el
`.kimi-code/skills` de un repo (se versionaria) ni `~/.hermes/skills` (Kimi no
la escanea). `leccion.py donde` imprime la que aplica:

```bash
eval "$(python3 <skill>/scripts/entorno.py --shell)" && "$PY" "$H/leccion.py" donde
```

Escribe `<raiz>/<clase>/SKILL.md` con frontmatter `name` y `description`. No
hay `skill_manage`. Buscar, el gate de `close --leccion`, mira ademas las
raices de los otros agentes: una leccion escrita en Hermes o en Claude sigue
cerrando desde Kimi, y al reves.

## codebase-memory-mcp

`codebase-memory-mcp` (consulta estructural + reindexado tras cerrar) se instala
una vez con su `install.sh` y se auto-registra en este host si lo detecta. Detalle,
comandos y `HARNESS_SIN_CBM` en `references/contexto.md`.
