# harness-flow

Skill para [Hermes Agent](https://hermes-agent.nousresearch.com),
[Claude Code](https://code.claude.com), OpenAI GPT/Codex y Grok que implementa un proceso de desarrollo
spec-driven para proyectos multi-repo, con gates ejecutables.

Es el puerto del arnés Rust `harness_process` a un agente: **sin binario, sin
instalador por proyecto, sin compilar por sistema operativo**. El proceso vive en
esta skill; los gates son scripts Python que devuelven exit≠0 cuando algo falta.

Los scripts son stdlib puro (salvo `psycopg` para el hub Postgres) y detectan el
host solos; lo único que cambia entre Hermes, Claude Code, GPT/Codex y Grok son las herramientas
del agente para lanzar el subagente revisor y escribir lecciones.

## Qué hace

- **Flujo en cuatro roles**: producto redacta el PRD inicial / SDD de arquitectura
  (solo al arrancar o cuando cambian), leader escribe el spec, implementer deja
  evidencia por criterio de aceptación, reviewer sella un veredicto. En ese orden.
- **Gates reales**: no puedes implementar sin spec aprobado por el usuario, ni
  cerrar sin evidencia que cite `archivo:linea` por cada AC, ni sellar un review
  que no responda por todos los AC. Los scripts se niegan con exit≠0.
- **Memory Hub Postgres**: grafo multi-repo compartido entre máquinas
  (`graph_nodes` / `graph_edges`). Responde "¿quién se rompe si toco esto?".
- **Vault Obsidian**: notas en `docs/vault/` generadas desde los documentos del
  proceso, versionadas con el repo; se abre `docs/` como vault. Es un panel para
  ti: ningun rol lo lee. Los nodos del grafo son opt-in (`vault.py build
  --con-grafo`): una nota por nodo ahoga el vault en cada refresco.
- **PRD inicial / SDD de arquitectura**: `producto.py borrador` redacta en
  `docs/borrador-<doc>.md` (sin proteger) y `producto.py aprobar --yes`, solo con
  el SÍ del usuario, copia el cuerpo a su destino y lo sella; `gate.py check`
  reconoce el sello. Ningún agente escribe `docs/prd/**` a mano. El PRD sigue
  la anatomía historia → objetivos → flujo → datos → pseudo-código, y `aprobar`
  se niega si trae código final.
- **PRD / SDD generados**: `documentacion.py sync` crea o actualiza
  `docs/prd/PRD-master.md` y `docs/sdd.md` desde las features cerradas,
  preservando el contenido manual fuera del bloque generado.
- **Jira / Confluence**: opcional, apagado si no hay binding. `atlassian.py push`
  crea/actualiza la issue Jira, subtasks por AC y una pagina Confluence con
  PRD/SDD, spec, evidencia y review; `gate.py close --publicar-atlassian` lo dispara al
  cerrar.

## Instalación

No hay instalador ni binario: la skill es un clone de git dentro del directorio
de skills de tu agente, que lo escanea y la carga por su `SKILL.md`.

**Hermes** (perfil `default`; con otro perfil va bajo
`~/.hermes/profiles/<perfil>/skills/`). Se carga en la **próxima** sesión;
verifica con `/skills`:

```bash
git clone https://github.com/calpil/harness-flow.git \
  ~/.hermes/skills/software-development/harness-flow
```

**Claude Code** (personal, disponible en todos tus proyectos; para una sola
repo usa `<repo>/.claude/skills/harness-flow`). Verifica con `/skills`:

```bash
git clone https://github.com/calpil/harness-flow.git \
  ~/.claude/skills/harness-flow
```

Si ya tienes el clone para Hermes, enlazalo en vez de duplicarlo — Claude Code
lee la skill a traves del symlink:

```bash
ln -s ~/.hermes/skills/software-development/harness-flow \
  ~/.claude/skills/harness-flow
```

**Grok** lee `~/.agents/skills` y `~/.grok/skills` (tambien `.claude/skills` y
`.cursor/skills` si esa compatibilidad esta encendida). No lee `~/.hermes/skills`.
Con el clone de Hermes, un symlink basta:

```bash
ln -s ~/.hermes/skills/software-development/harness-flow \
  ~/.agents/skills/harness-flow
```

En una sesion de Grok `entorno.py` reporta host `grok` (`GROK_AGENT`), aunque
el script resuelva al clone. El revisor es `spawn_subagent` y las lecciones se
escriben en `~/.grok/skills`. Ver [`references/grok.md`](references/grok.md).

**Otros CLIs** (Gemini CLI, Kimi Code) leen el mismo `SKILL.md`. Gemini carga
`~/.agents/skills`. `leccion.py` busca lecciones tambien en `~/.codex/skills`,
`~/.grok/skills` y `~/.kimi-code/skills`.

Kimi Code ademas puede instalar el repo como plugin (`/plugins install
<ruta-del-clone>`, manifiesto `kimi.plugin.json`): registra el agente `revisor`
para la tool Agent (`subagent_type: "revisor"`). El plugin corre desde una
copia en `$KIMI_CODE_HOME/plugins/managed/`, asi que tras un `git pull` del
clone hay que reinstalarlo.

Ademas de la skill, Claude Code carga la capa nativa que trae el repo
(`.claude-plugin/plugin.json`): el subagente revisor `harness-flow:revisor` y los
comandos `/harness-flow:estado`, `:spec`, `:review` y `:cierre`. Comprueba con
`claude plugin list` que aparezca `harness-flow@skills-dir` como `loaded`. Los
otros hosts ignoran esos archivos. Ver [`references/claude.md`](references/claude.md).

**OpenAI GPT/Codex** (personal, disponible en todos tus proyectos; para repo usa
`<repo>/.agents/skills/harness-flow`). Codex tambien lee `$CODEX_HOME/skills`
(`~/.codex/skills`), que es donde instala su propio tooling. ChatGPT/Codex
detecta cambios de skills automaticamente; si no aparece, reinicia
Codex/ChatGPT:

```bash
git clone https://github.com/calpil/harness-flow.git \
  ~/.agents/skills/harness-flow
```

### Windows

No son "las mismas rutas bajo `%USERPROFILE%`": Hermes busca primero en
`%LOCALAPPDATA%`, y el enlace entre hosts no se hace con `ln -s`.

**Claude Code** (PowerShell):

```powershell
git clone https://github.com/calpil/harness-flow.git `
  $env:USERPROFILE\.claude\skills\harness-flow
```

**Hermes**. La raiz que mira primero es `%LOCALAPPDATA%\hermes\skills`; tambien
acepta `%USERPROFILE%\.hermes\skills`, y `HERMES_SKILLS_DIR` gana sobre ambas:

```powershell
git clone https://github.com/calpil/harness-flow.git `
  $env:LOCALAPPDATA\hermes\skills\software-development\harness-flow
```

**GPT/Codex**: `$env:USERPROFILE\.agents\skills\harness-flow`.

**Compartir un solo clone entre hosts.** `ln -s` no existe en Windows. Un
*junction* es la opcion practica porque no pide permisos de administrador ni
Modo Desarrollador (solo sirve para directorios en el mismo volumen):

```cmd
mklink /J "%USERPROFILE%\.claude\skills\harness-flow" ^
  "%LOCALAPPDATA%\hermes\skills\software-development\harness-flow"
```

Con Modo Desarrollador activo tambien sirve un symlink real, que si cruza
volumenes:

```powershell
New-Item -ItemType SymbolicLink -Force `
  -Path  "$env:USERPROFILE\.claude\skills\harness-flow" `
  -Target "$env:LOCALAPPDATA\hermes\skills\software-development\harness-flow"
```

**Instala Git for Windows.** Sin el, Claude Code no usa Bash y cae a PowerShell
como shell, donde `eval "$(...)"` no existe y el interprete se llama `python`,
no `python3`. Los comandos `/harness-flow:*` traen las dos formas; cual usar lo
explica [`references/claude.md`](references/claude.md).

El venv neutro queda en `%USERPROFILE%\.harness-flow\venv`, con el interprete
en `Scripts\python.exe` (no `bin/python`). `entorno.py` lo resuelve solo.


Luego instala la dependencia del hub Postgres en el intérprete correcto. El
script lo detecta solo en Windows, Linux y macOS (en Claude Code crea un venv
propio en `~/.harness-flow/venv` en vez de tocar el python del sistema):

```bash
# Hermes
python3 ~/.hermes/skills/software-development/harness-flow/scripts/entorno.py --instalar-deps
# Claude Code
python3 ~/.claude/skills/harness-flow/scripts/entorno.py --instalar-deps
# GPT/Codex
python3 ~/.agents/skills/harness-flow/scripts/entorno.py --instalar-deps
```

En Windows el interprete se llama `python` (o `py -3`), no `python3`:

```powershell
python $env:USERPROFILE\.claude\skills\harness-flow\scripts\entorno.py --instalar-deps
```

Sin flags, `entorno.py` imprime un diagnóstico (SO, host detectado, rutas, si
`psycopg` está presente) y sale con exit≠0 si no puede resolver un intérprete
usable. La falta de `psycopg` solo es error con `--hub`, porque los gates
locales funcionan sin el Memory Hub. Si la detección no
acierta, `--host claude|hermes|gpt|codex|gemini|agy|grok|generic` la fuerza, y `HARNESS_PYTHON` /
`HARNESS_SKILLS_DIR` sobrescriben intérprete y raíz de skills.

Credenciales en `~/.harness-hub/.env` (fuera de todo repo, por máquina):

```
DB_HOST=...
DB_PORT=25060
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_SSL_MODE=require
```

## Actualización

Es un clone, así que se actualiza con git. Los cambios aplican en la
**siguiente** sesión, porque el `SKILL.md` se lee al iniciar.

```bash
cd ~/.hermes/skills/software-development/harness-flow   # o ~/.claude/skills/harness-flow
git pull
```

## Uso en un proyecto

Primero define `H` (scripts), `PY` (intérprete con dependencias) y
`HARNESS_HOST` sin hardcodear rutas — sustituye `<skill>` por el directorio
donde clonaste:

```bash
# bash / zsh
eval "$(python3 <skill>/scripts/entorno.py --shell)"

# PowerShell
python <skill>\scripts\entorno.py --powershell | Invoke-Expression
```

En Codex, Claude Code y Grok repite la inicializacion y el comando en la misma
llamada de terminal: las variables no sobreviven a llamadas independientes.
En Codex agrega `--host codex` a `entorno.py`, incluso al usar el clone de
Hermes. Ejemplo completo en [`references/openai.md`](references/openai.md).

En un monorepo, desde su raiz Git:

```bash
$PY "$H/init.py" --project mi-proyecto
$PY "$H/add.py" --name "Checkout con cupon"
$PY "$H/worktree.py" start --feature 1
# ... escribes el spec, el usuario lo aprueba, implementas, revisas ...
$PY "$H/gate.py" close --feature 1 --status done --to main --leccion checkout
$PY "$H/documentacion.py" sync        # opcional; close done lo corre automaticamente
```

En una raiz multi-repo SIN `.git`, con repos/worktrees existentes, no usar ese
merge legacy. Declarar el mapa completo y SHAs reales segun
[`references/multirepo.md`](references/multirepo.md):

```bash
$PY "$H/worktree.py" register --feature 1 --manifest /ruta/registro.json
# Integracion MANUAL autorizada, registro del tip final, verify y review fresco:
$PY "$H/gate.py" verify --feature 1
$PY "$H/revision.py" --feature 1 --briefing
# Delegar review independiente; leerlo y sellarlo antes del close.
$PY "$H/gate.py" revision --feature 1 --veredicto approved
$PY "$H/gate.py" close --feature 1 --status done --to develop \
  --integrated --postmerge /ruta/bases-postmerge.json --leccion <clase-existente>
```

No crea ramas ni worktrees, ni instala nada; `--integrated` comprueba integracion
ya realizada por ancestria, limpieza y tips exactos por repo. Guarda fuentes/tips
en `integraciones` y SDD, sin un merge global ficticio. El registro no autoriza
roles ni ediciones protegidas y no elimina bloqueos de otras features. Los mismos
comandos funcionan por symlink desde `.claude/skills`. El cierre exige el mapa de
bases reales `--postmerge` y ejecuta Go JSON/-exec o Angular22/Vitest4+Node22 de ADR
en TODOS los tips destino antes de done; no admite recibos manuales ni exit0 sin
pruebas. Protocolos ajenos permanecen bloqueados (no hay comandos genericos).
El `postmerge.py` heredado se conserva; `postmerge_medido.py` y el nuevo CLI
`postmerge_frontend.py` respaldan este cierre. Contrato, comandos para bases,
procedencia, evidencia durable y limites: `references/multirepo.md`.

`close --status done` archiva `harness/progress/current-<id>.md` en
`harness/progress/archive/` y sincroniza `docs/prd/PRD-master.md` +
`docs/sdd.md` con las features implementadas. Los bloques manuales fuera de los
marcadores `harness-flow:features` no se tocan.

No se copia nada al repo salvo `harness/` y `docs/`. Una instalación por proyecto
multi-repo, no por microservicio.

## Estructura

```
SKILL.md                 el proceso que sigue el agente
.claude-plugin/          manifiesto del plugin skills-dir (solo Claude Code)
kimi.plugin.json         manifiesto de plugin para Kimi Code (skill + agente revisor)
agents/openai.yaml       metadata para invocacion automatica en GPT/Codex
agents/revisor.md        subagente revisor (Claude Code y Kimi lo registran; Grok lee el cuerpo)
commands/                atajos /harness-flow:... (solo Claude Code)
scripts/
  entorno.py             detecta host, H y PY por SO (Windows/Linux/macOS)
  comun.py               rutas, backlog, firmas, parsers de AC
  init.py add.py         alta de proyecto y de features
  gate.py                TODOS los gates (exit≠0)
  producto.py            rol producto: borrador y aprobacion del PRD inicial / SDD
  documentacion.py       PRD/SDD generados desde features cerradas
  worktree.py            aislamiento por feature
  multirepo.py           validacion estricta de repos/fuentes/destinos existentes
  revision.py            paquete de revisión (solo lectura)
  leccion.py             memoria procedural por clase de trabajo
  hub.py                 Memory Hub Postgres
  vault.py               generación del vault Obsidian
  atlassian.py           Jira / Confluence
  estado.py              panorama al entrar al proyecto
tests/                   regresiones del port neutro
templates/               spec, evidencia, review, prd, sdd
references/              Claude Code, OpenAI, Grok, Obsidian, Atlassian, multirepo
```

## Licencia

MIT
