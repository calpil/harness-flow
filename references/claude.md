# Claude Code

## Formato

La skill usa el formato comun de Agent Skills, asi que Claude Code la carga por
su `SKILL.md` sin fork. Encima, el directorio trae un
`.claude-plugin/plugin.json`: eso lo convierte ademas en un **plugin skills-dir**,
que es la unica forma de que una skill empaquete su propio subagente y sus
comandos sin instalar nada suelto en `~/.claude/agents/` ni `~/.claude/commands/`.

```
harness-flow/
  SKILL.md                  <- la skill (host-neutral, igual en los tres hosts)
  .claude-plugin/plugin.json <- solo lo lee Claude Code; Hermes y Codex lo ignoran
  agents/revisor.md         <- subagente revisor aislado
  commands/*.md             <- estado, producto, spec, review, cierre
```

Hermes, GPT/Codex y Grok no miran `.claude-plugin/` ni `commands/`, asi que la capa
nativa de Claude no rompe la neutralidad de host: son archivos inertes para ellos.

## Instalacion

Personal, disponible en cualquier proyecto:

```bash
git clone https://github.com/calpil/harness-flow.git ~/.claude/skills/harness-flow
```

Por repo, versionado con el proyecto:

```bash
git clone https://github.com/calpil/harness-flow.git .claude/skills/harness-flow
```

**Symlink**: si ya tienes el clone para Hermes, enlazalo en vez de duplicarlo.
Claude Code lee `SKILL.md` a traves del symlink y carga el plugin igual:

```bash
ln -s ~/.hermes/skills/software-development/harness-flow ~/.claude/skills/harness-flow
```

Carga en la **proxima** sesion, o ya mismo con `/reload-plugins`. Verifica:

```bash
claude plugin list          # debe listar harness-flow@skills-dir  Status: loaded
```

`claude plugin details harness-flow@skills-dir` **no** es una verificacion util:
su inventario no cuenta comandos y reporta `Agents (0)` incluso para plugins que
si los cargan. Para comprobar de verdad que el subagente y los comandos entraron,
abre una sesion nueva y mira `/agents` y la lista de skills.

## Que aporta la capa nativa

| Pieza | Nombre en la sesion | Reemplaza a |
| --- | --- | --- |
| Subagente revisor | `harness-flow:revisor` | pegar el briefing en un `general-purpose` a mano |
| `/harness-flow:estado` | arranque de sesion | recordar correr `estado.py` |
| `/harness-flow:producto` | rol producto: PRD inicial / SDD de arquitectura | leer el flujo entero del SKILL.md |
| `/harness-flow:spec` | rol leader | leer el flujo entero del SKILL.md |
| `/harness-flow:review` | rol reviewer | idem |
| `/harness-flow:cierre` | verify + base + close + postmerge | idem |

El subagente `revisor` no duplica el prompt de revision: el briefing que emite
`revision.py --feature <id> --briefing` sigue mandando. `agents/revisor.md` solo
agrega los invariantes que no dependen del spec (aislamiento, arbol correcto, no
sellar, no tocar codigo). Si los dos se contradicen, gana el script — la leccion
de "cuando existan dos versiones de un gate, la doc tiene que mandar a la buena"
aplica igual a los prompts.

## `$PY` y `$H` no sobreviven entre llamadas Bash

Esta es la diferencia operativa real con Hermes. En Claude Code **cada llamada a
la tool `Bash` abre un shell nuevo**: el directorio de trabajo persiste, las
variables de entorno no. Un `eval` en una llamada y `"$PY" "$H/gate.py"` en la
siguiente falla con `$PY` vacio, que suele leerse como "el script no existe".

Pega el `eval` al comando, en la misma llamada, siempre:

```bash
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/estado.py"
```

`${CLAUDE_PLUGIN_ROOT}` se expande en los archivos de `commands/` y `agents/` de
este plugin, y se expande al path **sin resolver** (`~/.claude/skills/harness-flow`,
no el destino del symlink). Eso es justo lo que `entorno.py` necesita.

## Windows

### Instalacion

`%USERPROFILE%\.claude\skills\harness-flow` (personal) o
`<repo>\.claude\skills\harness-flow` (por repo). El plugin skills-dir carga
igual: `.claude-plugin\plugin.json` no depende del SO.

Para compartir un solo clone con Hermes, `ln -s` no existe. Un **junction** es
la opcion practica: no pide administrador ni Modo Desarrollador, aunque solo
funciona dentro del mismo volumen.

```cmd
mklink /J "%USERPROFILE%\.claude\skills\harness-flow" ^
  "%LOCALAPPDATA%\hermes\skills\software-development\harness-flow"
```

Con Modo Desarrollador activo, un symlink real tambien sirve y cruza volumenes:

```powershell
New-Item -ItemType SymbolicLink -Force `
  -Path  "$env:USERPROFILE\.claude\skills\harness-flow" `
  -Target "$env:LOCALAPPDATA\hermes\skills\software-development\harness-flow"
```

### La tool Bash puede no ser bash

Esto es lo que mas muerde. En Windows nativo, Claude Code usa Bash **solo si
Git for Windows esta instalado**; si no lo esta, **cae a PowerShell** como shell.
Entonces el bootstrap de los comandos deja de funcionar por dos motivos a la
vez: `eval "$(...)"` no es sintaxis de PowerShell, y el interprete se llama
`python` (o `py -3`), no `python3`.

Las dos formas, equivalentes:

```bash
# bash/zsh: macOS, Linux, WSL, y Windows CON Git for Windows
eval "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --shell)" && "$PY" "$H/estado.py"
```

```powershell
# PowerShell: Windows SIN Git for Windows
python "${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py" --powershell | Invoke-Expression
& $PY "$H/estado.py"
```

`--shell` emite `export H=...`; `--powershell` emite `$H = '...'` y
`$env:HARNESS_HOST = '...'`. Por eso en PowerShell se invoca con el operador
`&`, y la asignacion no sobrevive a la llamada siguiente igual que en bash.

Las barras normales funcionan en las dos: Python acepta `/` como separador en
Windows, asi que `${CLAUDE_PLUGIN_ROOT}/scripts/entorno.py` no necesita
traducirse a backslashes.

La recomendacion sigue siendo instalar Git for Windows: deja un solo camino en
vez de dos.

### Interprete y venv

El venv neutro vive en `%USERPROFILE%\.harness-flow\venv`, y el binario esta en
`Scripts\python.exe`, no en `bin/python`. `entorno.py` ya lo resuelve por
`os.name == "nt"`; no lo armes a mano.

```powershell
python $env:USERPROFILE\.claude\skills\harness-flow\scripts\entorno.py
python $env:USERPROFILE\.claude\skills\harness-flow\scripts\entorno.py --instalar-deps
```

### Que esta verificado y que no

Las rutas, el nombre del venv y el orden de raices salen de ejercitar las ramas
Windows de `entorno.py` y `leccion.py` (`ES_WINDOWS = True`), no de suponerlas.
El comportamiento del shell sale de la documentacion oficial de Claude Code.

**Nada de esto se probo en una maquina Windows.** Si algo falla ahi, el primer
diagnostico es `entorno.py` sin flags: imprime SO, host, H, PY y si `psycopg`
esta, y sale con exit!=0 cuando no puede resolver un interprete.

## Deteccion de host

`entorno.py` devuelve `claude` por dos caminos independientes, en este orden:

1. `CLAUDECODE=1` o `CLAUDE_CONFIG_DIR` en el entorno — Claude Code los exporta
   siempre, asi que funciona aunque la skill viva fuera de `~/.claude/skills`.
2. La ruta del script bajo `<algo>/.claude/skills/<skill>/scripts`. La deteccion
   **no** hace `resolve()` a proposito: por el symlink, el archivo real esta en
   `~/.hermes/...` y resolverlo daria host `hermes`.

Forzar a mano, si hace falta:

```bash
python3 ~/.claude/skills/harness-flow/scripts/entorno.py --host claude --shell
```

## Interprete con `psycopg`

Claude Code no trae venv propio, asi que `entorno.py` usa el venv neutro
`~/.harness-flow/venv` y **no toca el python del sistema**:

```bash
python3 ~/.claude/skills/harness-flow/scripts/entorno.py                  # diagnostico
python3 ~/.claude/skills/harness-flow/scripts/entorno.py --instalar-deps  # crea el venv e instala
```

`psycopg` solo hace falta para el Memory Hub. Los gates locales corren sin el.

## Raices de lecciones

`leccion.py` busca skills en `~/.claude/skills` y despues en `.claude/skills` del
proyecto. Crear o parchear una leccion en este host es escribir
`<raiz>/<clase>/SKILL.md` con las tools de archivo — no hay equivalente de
`skill_manage`.

Si `harness-flow` entro por symlink desde `~/.claude/skills` al clone de Hermes,
las lecciones que escribas caen en `~/.claude/skills/<clase>/`, fuera del clone:
no ensucian el repo.

Eso es donde se **crean**. Al **buscar** (el gate de `close --leccion`),
`leccion.py` mira ademas las raices de los otros agentes -- Hermes, GPT/Codex,
`~/.codex/skills`, `~/.grok/skills`, `~/.kimi-code/skills` -- porque una leccion
es memoria procedural del usuario y no del CLI donde se tipeo. `leccion.py donde`
imprime primero la raiz de creacion y marca las demas como solo consulta.

### Espejo en Hermes

Buscar en Hermes no basta para que Hermes *cargue* la leccion: su agente solo
lee `~/.hermes/skills`. Con Hermes instalado, `leccion.py espejar <clase>` mueve
`~/.claude/skills/<clase>` a `~/.hermes/skills/<cat>/<clase>` (`--categoria`,
por defecto `software-development`) y deja en su lugar un symlink absoluto. La
copia fisica vive en Hermes y Claude Code la lee por el enlace: un patch desde
cualquiera de los dos llega al otro. `leccion.py donde` marca esa raiz como
espejo en vez de solo consulta.

`gate.py close --leccion <clase>` espeja solo al terminar el cierre, sin
bloquearlo nunca. No toca nada cuando:

- Hermes no esta instalado, o `HARNESS_SKILLS_DIR` fuerza una raiz unica;
- la leccion ya es un enlace (a Hermes: ya esta; a otro agente: no es suya);
- Hermes ya tiene una skill con ese nombre: avisa `[!]` y hay que fusionar a mano.

Si el symlink no se puede crear (Windows sin Modo Desarrollador), la leccion
vuelve a `~/.claude/skills` y el aviso lo dice.
