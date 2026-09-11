# harness-flow

Skill de [Hermes Agent](https://hermes-agent.nousresearch.com) que implementa un
proceso de desarrollo spec-driven para proyectos multi-repo, con gates ejecutables.

Es el puerto del arnés Rust `harness_process` a Hermes: **sin binario, sin
instalador por proyecto, sin compilar por sistema operativo**. El proceso vive en
esta skill; los gates son scripts Python que devuelven exit≠0 cuando algo falta.

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
- **Jira / Confluence**: opcional, apagado si no hay binding.

## Instalación

No hay instalador ni binario: la skill es un clone de git dentro del directorio de
skills de Hermes. Este lo escanea al iniciar la sesión y la carga por su
`SKILL.md`.

```bash
git clone https://github.com/calpil/harness-flow.git \
  ~/.hermes/skills/software-development/harness-flow
```

Esa es la ruta del perfil `default`. Si usas otro perfil, va en
`~/.hermes/profiles/<perfil>/skills/software-development/harness-flow`. En
Windows es la misma ruta bajo tu carpeta de usuario (`%USERPROFILE%\.hermes\...`).

Hermes la carga en la **próxima** sesión; verifica con `/skills`.

Luego instala la dependencia del hub Postgres en el intérprete correcto — el del
venv de Hermes, no el del sistema. El script lo detecta solo en Windows, Linux y
macOS:

```bash
python3 ~/.hermes/skills/software-development/harness-flow/scripts/entorno.py --instalar-deps
```

Sin flags, `entorno.py` imprime un diagnóstico (SO, rutas detectadas, si
`psycopg` está presente) y sale con exit≠0 si falta algo.

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

Es un clone, así que se actualiza con git. Los cambios aplican en la **siguiente**
sesión de Hermes, porque el `SKILL.md` se lee al iniciar.

```bash
cd ~/.hermes/skills/software-development/harness-flow
git pull
```

## Uso en un proyecto

Primero define `H` (scripts) y `PY` (python de Hermes) sin hardcodear rutas:

```bash
# bash / zsh
eval "$(python3 ~/.hermes/skills/software-development/harness-flow/scripts/entorno.py --shell)"

# PowerShell
python $env:USERPROFILE\.hermes\skills\software-development\harness-flow\scripts\entorno.py --powershell | Invoke-Expression
```

Después, desde la raíz multi-repo (la carpeta que contiene tus microservicios):

```bash
$PY "$H/init.py" --project mi-proyecto
$PY "$H/add.py" --name "Checkout con cupon"
$PY "$H/worktree.py" start --feature 1 --repo front-app
# ... escribes el spec, el usuario lo aprueba, implementas, revisas ...
$PY "$H/gate.py" close --feature 1 --status done --to main --leccion checkout
```

No se copia nada al repo salvo `harness/` y `docs/`. Una instalación por proyecto
multi-repo, no por microservicio.

## Estructura

```
SKILL.md                 el proceso que sigue el agente
scripts/
  entorno.py             detecta H y PY por SO (Windows/Linux/macOS)
  comun.py               rutas, backlog, firmas, parsers de AC
  init.py add.py         alta de proyecto y de features
  gate.py                TODOS los gates (exit≠0)
  worktree.py            aislamiento por feature
  revision.py            paquete de revisión (solo lectura)
  leccion.py             memoria procedural por clase de trabajo
  hub.py                 Memory Hub Postgres
  vault.py               generación del vault Obsidian
  atlassian.py           Jira / Confluence
  estado.py              panorama al entrar al proyecto
templates/               spec, evidencia, review
references/              Obsidian, Atlassian
```

## Licencia

MIT
