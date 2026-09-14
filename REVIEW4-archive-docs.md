# REVIEW4 archive/docs + fix P1 GPT/Codex

Veredicto: approved

## Hallazgos bloqueantes

Ninguno.

## Verificaciones adversariales

- P1 corregido: con `HARNESS_HOST` ausente y `~/.agents/skills/harness-flow` como symlink a `~/.hermes/skills/software-development/harness-flow`, `leccion.py` detecta host GPT/Codex por la ruta no resuelta (`scripts/leccion.py:36-45`, `scripts/entorno.py:32-52`) y usa solo raices `.agents` (`scripts/leccion.py:87-104`, `scripts/leccion.py:141-156`). Smoke real en HOME temporal:
  - `python .agents/skills/harness-flow/scripts/entorno.py` -> `HARNESS_HOST  : gpt`.
  - `python .agents/skills/harness-flow/scripts/leccion.py donde` -> solo `.../home/.agents/skills`.
  - `existe solo-gpt` -> exit 0.
  - `existe solo-hermes` -> exit 1.
- No vi mezcla de raices ni scan por encima del repo root: `_raices_gpt()` corta en `git rev-parse --show-toplevel` y luego agrega solo HOME/.agents y `/etc/codex/skills` (`scripts/leccion.py:76-104`). Smoke desde `repo/a/b` encontro `.agents/skills` de `repo/a`, `repo` y HOME, no el `.agents/skills` ubicado fuera del repo; `fuera-del-repo` salio exit 1.
- No rompe deteccion Hermes/Claude: smokes con HOME temporal confirmaron que una instalacion bajo `.hermes/skills` encuentra `solo-hermes` y no `solo-claude`, y una instalacion bajo `.claude/skills` con `CLAUDECODE=1` encuentra `solo-claude` y no `solo-hermes`. Los tests existentes cubren tambien Hermes perfil y precedencia Claude (`tests/test_leccion.py:97-132`, `tests/test_leccion.py:196-217`).
- GPT/Codex explicito sigue normalizado: `python3 scripts/entorno.py --host codex` imprime `HARNESS_HOST  : gpt` (`scripts/entorno.py:25-38`, `scripts/entorno.py:170-180`).
- Casos progress/PRD/Atlassian no reabiertos: el cierre `done` archiva `current-<id>.md` y registra `progress_archive` (`scripts/gate.py:384-413`, `tests/test_progress_archive.py:69-112`); `documentacion.py sync` preserva contenido manual y actualiza solo el bloque generado (`scripts/documentacion.py:130-159`, `tests/test_documentacion.py:85-131`); el gate permite el PRD generado y bloquea edicion manual u otros archivos en `docs/prd` (`scripts/gate.py:107-180`, `tests/test_documentacion.py:149-207`); el rollback si falla Atlassian restaura backlog/progress y regenera PRD/SDD sin estado falso `done` (`scripts/gate.py:512-546`, `tests/test_gate_atlassian.py:88-102`, `tests/test_progress_archive.py:92-112`, `tests/test_documentacion.py:209-260`); Confluence embebe PRD/SDD solo si existen (`scripts/atlassian.py:111-129`, `tests/test_atlassian.py:222-239`).

## Checks ejecutados

- `python3 -m unittest discover -s tests` -> 66 tests, OK.
- `python3 -m unittest tests.test_leccion tests.test_entorno tests.test_progress_archive tests.test_documentacion tests.test_gate_atlassian tests.test_atlassian` -> 60 tests, OK.
- `python3 -m compileall -q scripts tests` -> OK.
- `git diff --check` -> OK.
- Smokes manuales descritos arriba para symlink GPT sin `HARNESS_HOST`, no-scan por encima del repo root, Hermes, Claude y `--host codex`.

## Archivos modificados por esta revision

- `REVIEW4-archive-docs.md`
