# Grok

## Que carga Grok

Grok descubre este `SKILL.md` y lo expone como `/harness-flow`. No lee
`~/.hermes/skills`. Las instalaciones que si ve son:

- `~/.grok/skills/harness-flow` y `<repo>/.grok/skills/harness-flow`
- `~/.agents/skills/harness-flow` (en esta maquina, symlink al clone de Hermes)
- las de `.claude/skills` y `.cursor/skills`, si la compatibilidad esta encendida

`agents/revisor.md` no queda registrado como agente: Grok solo lista los agentes
de `~/.grok/agents/`, `.grok/agents/` o de un plugin instalado. `commands/`
tampoco entra; esos archivos son de Claude Code y usan `${CLAUDE_PLUGIN_ROOT}`.
El flujo se sigue desde este skill, no desde `/harness-flow:review`.

`.claude-plugin/plugin.json` y `kimi.plugin.json` no aplican.

## Host

`entorno.py` reporta `grok` en este orden, despues de un `HARNESS_HOST` explicito:

1. `GROK_AGENT` puesto y distinto de `0`, `false`, `off` o `no`. Lo exporta el
   proceso de Grok. Gana a la ruta: el mismo script, invocado por el symlink de
   `.agents` o por el clone en `.hermes`, sigue siendo `grok`.
2. La ruta del script bajo `.grok/skills/<skill>/scripts`, sin `resolve()`.

`0` no cuenta. Si la marca esta apagada, un symlink en `.agents/skills` vuelve
a detectarse como `gpt`.

Forzar a mano:

```bash
python3 <skill>/scripts/entorno.py --host grok --shell
```

## Shell

Cada `run_terminal_command` abre un shell nuevo. `$PY` y `$H` de una llamada
anterior no existen en la siguiente. El `eval` va pegado al comando:

```bash
eval "$(python3 <skill>/scripts/entorno.py --shell)" && "$PY" "$H/estado.py"
```

`<skill>` es la ruta por la que Grok cargo la skill (`~/.agents/skills/harness-flow`
o `~/.grok/skills/harness-flow`), no el destino resuelto del symlink. `entorno.py`
exporta `H` ya resuelto y `HARNESS_HOST=grok`.

El interprete es el venv neutro `~/.harness-flow/venv`, el mismo de Claude y de
GPT. `psycopg` solo hace falta para el Memory Hub.

## Revisor

La herramienta es `spawn_subagent`. Aislamiento de contexto: el hijo no ve el
historial de quien implemento. No hace falta un proceso `grok -p` anidado.

1. Briefing, en la misma llamada que el `eval`:

```bash
eval "$(python3 <skill>/scripts/entorno.py --shell)" && "$PY" "$H/revision.py" --feature <id> --briefing
```

2. Lanza el hijo con ese texto entero en `prompt`, mas una linea: seguir el
   cuerpo de `<skill>/agents/revisor.md` e ignorar su frontmatter. Ese bloque
   (`model: opus`, `tools: Read, Grep, Glob, Bash, Write`) es de Claude Code y
   de Kimi. En Grok las herramientas son las de la sesion (`read_file`, `grep`,
   `run_terminal_command`, `search_replace`).
3. `description`: una etiqueta corta, por ejemplo `Revisa feature <id>`.
4. `isolation: none`. `worktree` escribe `docs/review-<id>.md` en un worktree
   de Grok, y `gate.py revision` lee el de la feature.
5. No pases `resume_from`. Continua la transcripcion del hijo anterior y con
   ella el sesgo que el aislamiento evita.
6. No uses `codex exec`, `delegate_task` ni la tool `Agent` de Claude. El host
   `grok` no es `gpt` ni `hermes`. `--agent` y `--agents` no lanzan este revisor:
   `--agent` cambia el agente de toda la sesion y `--agents` solo existe en
   `grok -p`.

Cuando vuelva, lee `docs/review-<id>.md` y sella con `gate.py revision`, igual
que en los otros hosts. Si `spawn_subagent` no esta, revisa tu con
`revision.py --feature <id>` y dilo: el rigor baja.

## Lecciones

Crear sigue el host. En `grok` la raiz es una sola: `~/.grok/skills`. No el
repo (`<repo>/.grok/skills` se versionaria) y no `~/.hermes/skills` (Grok no la
escanea). `leccion.py donde` imprime esa ruta aunque el directorio todavia no
exista.

```bash
eval "$(python3 <skill>/scripts/entorno.py --shell)" && "$PY" "$H/leccion.py" donde
```

Escribe `~/.grok/skills/<clase>/SKILL.md` con frontmatter `name` y
`description`. No hay `skill_manage`.

Buscar, el gate de `close --leccion`, mira ademas las raices de los otros
agentes. Una leccion escrita en Hermes o en Claude sigue cerrando desde Grok.
Al reves igual: una leccion creada aqui en `~/.grok/skills` la encuentra el
gate desde otro host.

## Obsidian

No hay un vault distinto para Grok. `vault.py`, el refresco de `worktree.py
start` y el de `gate.py close --status done` son los mismos scripts. Grok no
carga `commands/estado.md` (ahi esta el mismo paso, para Claude): al arrancar
la sesion sigue la seccion "Arranque de sesion" y "Obsidian" de `SKILL.md`.

La nota de una leccion cita el `SKILL.md` que `leccion.py` encontro. Si se
creo en este host, esa ruta es `~/.grok/skills/<clase>/SKILL.md`. Que genera
cada nota: [`obsidian.md`](obsidian.md).
