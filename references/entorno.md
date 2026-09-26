# Entorno: interprete, host y dependencias

`entorno.py` resuelve `H` (scripts), `PY` (interprete con dependencias) y
`HARNESS_HOST`. Este archivo es el detalle; el uso diario esta en `SKILL.md`
("Layout").

## Diagnostico

Sin flags, `entorno.py` imprime un diagnóstico (SO, host, H, PY, si `psycopg`
está) y sale con exit≠0 si no puede resolver un intérprete usable. La falta de
`psycopg` solo es error con `--hub`: quien usa nada más los gates locales no
necesita el Memory Hub. `entorno.py --instalar-deps` instala
`psycopg[binary]` en el intérprete correcto (en Claude Code crea un venv propio
en `~/.harness-flow/venv` en vez de tocar el python del sistema).

## Orden de deteccion

Detecta en este orden: `HARNESS_PYTHON` → venv neutro (`HARNESS_VENV` o
`~/.harness-flow/venv`) → en host Hermes, `HERMES_PYTHON`/`HERMES_HOME`, el
launcher `hermes` del PATH y las rutas por SO → el propio intérprete. Si nada
resuelve, exporta `HARNESS_PYTHON` a mano. `--host claude|hermes|gpt|codex|gemini|agy|grok|kimi|generic` fuerza
el host cuando la detección no aplica. `codex` se normaliza a `gpt` y `agy` a `gemini`.
Dentro de una sesion de Grok el host es `grok` aunque el script viva en el clone
de Hermes o entre por el symlink de `.agents/skills`: manda `GROK_AGENT`, no la ruta.
Codex se reconoce como `gpt` por `CODEX_THREAD_ID` o `CODEX_SESSION_ID`, tambien
desde el clone de Hermes. `HARNESS_HOST` o `--host` tienen prioridad.

## `psycopg` va en `$PY`

`psycopg` debe estar en el intérprete que resuelve `entorno.py` (`$PY`), no en el
del proyecto ni en el python del sistema. Si `hub.py` tira `ModuleNotFoundError:
psycopg`, casi siempre es que estás usando `python3` en vez de `$PY`. Diagnostica
y arregla con el mismo script, sin rutas a mano: `python3 "$H/entorno.py"` y luego
`python3 "$H/entorno.py" --instalar-deps`.
