# harness-flow

Skill para [Hermes Agent](https://hermes-agent.nousresearch.com),
[Claude Code](https://code.claude.com) y OpenAI GPT/Codex que implementa un proceso de desarrollo
spec-driven para proyectos multi-repo, con gates ejecutables.

Es el puerto del arnés Rust `harness_process` a un agente: **sin binario, sin
instalador por proyecto, sin compilar por sistema operativo**. El proceso vive en
esta skill; los gates son scripts Python que devuelven exit≠0 cuando algo falta.

Los scripts son stdlib puro (salvo `psycopg` para el hub Postgres) y detectan el
host solos; lo único que cambia entre Hermes, Claude Code y GPT/Codex son las herramientas
del agente para lanzar el subagente revisor y escribir lecciones.

## Qué hace

- **Flujo en tres roles**: leader escribe el spec, implementer deja evidencia por
  criterio de aceptación, reviewer sella un veredicto. En ese orden.
- **Gates reales**: no puedes implementar sin spec aprobado por el usuario, ni
  cerrar sin evidencia que cite `archivo:linea` por cada AC, ni sellar un review
  que no responda por todos los AC. Los scripts se niegan con exit≠0.
- **Memory Hub Postgres**: grafo multi-repo compartido entre máquinas
  (`graph_nodes` / `graph_edges`). Responde "¿quién se rompe si toco esto?".
- **Vault Obsidian**: `docs/vault/` generado desde el grafo y los documentos del
  proceso, versionado con el repo.
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

**OpenAI GPT/Codex** (personal, disponible en todos tus proyectos; para repo usa
`<repo>/.agents/skills/harness-flow`). ChatGPT/Codex detecta cambios de skills
automaticamente; si no aparece, reinicia Codex/ChatGPT:

```bash
git clone https://github.com/calpil/harness-flow.git \
  ~/.agents/skills/harness-flow
```

En Windows son las mismas rutas bajo `%USERPROFILE%`.

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

Sin flags, `entorno.py` imprime un diagnóstico (SO, host detectado, rutas, si
`psycopg` está presente) y sale con exit≠0 si no puede resolver un intérprete
usable. La falta de `psycopg` solo es error con `--hub`, porque los gates
locales funcionan sin el Memory Hub. Si la detección no
acierta, `--host claude|hermes|gpt|codex|generic` la fuerza, y `HARNESS_PYTHON` /
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

Después, desde la raíz multi-repo (la carpeta que contiene tus microservicios):

```bash
$PY "$H/init.py" --project mi-proyecto
$PY "$H/add.py" --name "Checkout con cupon"
$PY "$H/worktree.py" start --feature 1 --repo front-app
# ... escribes el spec, el usuario lo aprueba, implementas, revisas ...
$PY "$H/gate.py" close --feature 1 --status done --to main --leccion checkout
$PY "$H/documentacion.py" sync        # opcional; close done lo corre automaticamente
```

`close --status done` archiva `harness/progress/current-<id>.md` en
`harness/progress/archive/` y sincroniza `docs/prd/PRD-master.md` +
`docs/sdd.md` con las features implementadas. Los bloques manuales fuera de los
marcadores `harness-flow:features` no se tocan.

No se copia nada al repo salvo `harness/` y `docs/`. Una instalación por proyecto
multi-repo, no por microservicio.

## Estructura

```
SKILL.md                 el proceso que sigue el agente
agents/openai.yaml       metadata para invocacion automatica en GPT/Codex
scripts/
  entorno.py             detecta host, H y PY por SO (Windows/Linux/macOS)
  comun.py               rutas, backlog, firmas, parsers de AC
  init.py add.py         alta de proyecto y de features
  gate.py                TODOS los gates (exit≠0)
  documentacion.py       PRD/SDD generados desde features cerradas
  worktree.py            aislamiento por feature
  revision.py            paquete de revisión (solo lectura)
  leccion.py             memoria procedural por clase de trabajo
  hub.py                 Memory Hub Postgres
  vault.py               generación del vault Obsidian
  atlassian.py           Jira / Confluence
  estado.py              panorama al entrar al proyecto
tests/                   regresiones del port neutro
templates/               spec, evidencia, review
references/              Obsidian, Atlassian
```

## Licencia

MIT
