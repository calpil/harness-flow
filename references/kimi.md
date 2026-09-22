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

Con el plugin habilitado, `agents/revisor.md` queda registrado como agente y la
tool `Agent` acepta `subagent_type: "revisor"`. El frontmatter
(`model: opus`, `tools: Read, Grep, Glob, Bash, Write`) carga sin romper: Kimi
ignora `model` (campo de Claude Code) y acepta `tools` separado por comas.

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
