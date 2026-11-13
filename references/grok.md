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

## Implementer y Modo Pair (por defecto)

**Pair es el modo por defecto de toda feature**, con stack detectado o sin él: lo deja en el
backlog `gate.py approve-spec` al sellar el spec por primera vez y `gate.py close` exige su rastro,
la lista de tests sellada (`gate.py sellar-tests`, que corre quien implementa). `--pair` ya no hace falta para activarlo. El
modo delegado es decisión del usuario (`worktree.py modo --feature <id> --delegado`) o de una sesión
sin usuario. En los dos modos el brief (`contexto.py brief`) trae el texto de las reglas de cada
stack, el índice de sus skills y el bloque `NORMAS DE INGENIERIA`, que es la misma lista que audita
el revisor: cúmplelas aunque tu host no cargue `agents/implementer.md`. Si delegas en un
subagente, pégale el brief entero y nada más: trae el comando que imprime cada skill del stack
(`stack.py skill`) y cada referencia (`normas.py --ref`), con rutas absolutas.

En Grok el Rol 2 se divide según la modalidad:

1. **Modo Pair automático (por defecto)**: corre en la **sesión principal de Grok**.
   Grok utiliza `run_terminal_command`, `write` y `search_replace` directamente
   en el worktree de la feature (`worktree.py start --feature <id>`), escribe la
   lista de tests, la sella (`gate.py sellar-tests`), la muestra y ejecuta
   `1 test -> Red -> código mínimo -> Green` ciclo tras ciclo, sin pausar ni
   preguntar si sigue. Pregunta con un formulario Markdown solo en las paradas
   que lo piden (`references/vertical-slice.md`, sección 6). Pausa tras cada
   ciclo solo si el usuario pide "paso a paso". Usa `spawn_subagent` para
   implementar solo si el usuario pide varias features en paralelo.
2. **Modo Delegado (autónomo)**: solo si el usuario lo pidió o la sesión no tiene
   usuario. Regístralo (`worktree.py start --feature <id> --delegado`); Grok ejecuta
   la implementación en el worktree hasta dejar la unidad en verde y el acta
   `docs/impl-<id>.md`, siguiendo las reglas y normas de la salida de `contexto.py brief`.

Una vez concluida la implementación y commiteado el trabajo en la rama de la
feature, se pasa al Rol 3 (Revisor), donde **ahí sí** es obligatorio el subagente
amnésico vía `spawn_subagent`.

## Revisor

La herramienta es `spawn_subagent`. El hijo arranca sin el historial de quien
implemento. No hace falta un proceso `grok -p` anidado.

1. Briefing, en la misma llamada que el `eval`, desde el cwd donde despues
   correras el gate:

```bash
eval "$(python3 <skill>/scripts/entorno.py --shell)" && "$PY" "$H/revision.py" --feature <id> --briefing
```

`find_root()` sube desde ese cwd hasta el primer `harness/feature_list.json`.
El acta es `<esa raiz>/docs/review-<id>.md`. El codigo que hay que citar es el
arbol que el briefing nombra (el worktree de la feature). No cambies de
directorio entre este comando, la espera y `gate.py revision`: el gate vuelve
a resolver la raiz desde su cwd.

2. Lanza el hijo con ese texto entero en `prompt`, mas una linea: seguir el
   cuerpo de `<skill>/agents/revisor.md` e ignorar su frontmatter (`model`,
   `effort`, `tools`: son de Claude Code y de Kimi). En Grok escribe el acta
   con las herramientas de la sesion: `read_file`, `grep`,
   `run_terminal_command`, `search_replace` y `write`.
3. `description`: una etiqueta corta, por ejemplo `Revisa feature <id>`.
4. `isolation: none`. Comparte el cwd del paso 1. `cwd` solo para repetir
   ese mismo directorio; es excluyente con `isolation: worktree`. Un worktree
   de Grok, o un `cwd` en el worktree de la feature mientras el gate corre en
   otra raiz, deja el acta donde `gate.py revision` no la lee.
5. Deja `background` en `true`. La llamada devuelve un id y el hijo sigue.
   Antes de abrir el acta o de sellar, espera con
   `get_command_or_subagent_output` y ese id en `task_ids`. Un review pasa de
   10 minutos: pon `timeout_ms` largo (tope 3600000) y, si sigue en curso,
   espera otra vez. `background: false` corta la espera a los 10 minutos y el
   hijo continua; para saber que termino sigue haciendo falta
   `get_command_or_subagent_output`.
6. No pases `resume_from`. Continua la transcripcion del hijo anterior y con
   ella el sesgo que el aislamiento evita.
7. `spawn_subagent` no acepta modelo ni effort: el hijo usa los de la sesion.
   No uses `codex exec`, `delegate_task` ni la tool `Agent` de Claude.
   `--agent` cambia el agente de toda la sesion y `--agents` solo existe en
   `grok -p`.

Con el hijo terminado, lee `docs/review-<id>.md` desde el mismo cwd y sella
con `gate.py revision`. Si `spawn_subagent` no esta, revisa tu con
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

## codebase-memory-mcp

`codebase-memory-mcp` (consulta estructural + reindexado tras cerrar) se instala
una vez con su `install.sh` y se auto-registra en este host si lo detecta. Detalle,
comandos y `HARNESS_SIN_CBM` en `references/contexto.md`.
