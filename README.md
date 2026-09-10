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

```bash
# Windows
git clone <este-repo> "$LOCALAPPDATA/hermes/skills/software-development/harness-flow"

# macOS / Linux
git clone <este-repo> ~/.local/share/hermes/skills/software-development/harness-flow
```

Hermes la carga sola en la próxima sesión. Verifica con `/skills`.

Para el hub Postgres:

```bash
uv pip install --python "<venv de hermes>/bin/python" "psycopg[binary]"
```

Credenciales en `~/.harness-hub/.env` (fuera de todo repo):

```
DB_HOST=...
DB_PORT=25060
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_SSL_MODE=require
```

## Uso en un proyecto

Desde la raíz multi-repo (la carpeta que contiene tus microservicios):

```bash
H=~/.local/share/hermes/skills/software-development/harness-flow/scripts

python "$H/init.py" --project mi-proyecto
python "$H/add.py" --name "Checkout con cupon"
python "$H/worktree.py" start --feature 1 --repo front-app
# ... escribes el spec, el usuario lo aprueba, implementas, revisas ...
python "$H/gate.py" close --feature 1 --status done --to main --leccion checkout
```

No se copia nada al repo salvo `harness/` y `docs/`. Una instalación por proyecto
multi-repo, no por microservicio.

## Estructura

```
SKILL.md                 el proceso que sigue el agente
scripts/
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
