# REVIEW3 archive/docs + GPT/Codex

Veredicto: changes_requested

## Hallazgos bloqueantes

### P1 - `leccion.py` no autodetecta GPT/Codex cuando `harness-flow` entra por symlink desde `.agents/skills`

- Referencias: `scripts/leccion.py:35-42`, `scripts/leccion.py:120-124`, `scripts/leccion.py:139-153`, `references/openai.md:46-47`, `SKILL.md:230`, `tests/test_leccion.py:83-94`.
- Contrato violado: el alcance pide soporte automatico GPT/OpenAI Codex y que con symlink desde `.agents/skills` no se mezclen skills de Hermes. La documentacion tambien promete que el symlink desde `.agents/skills` al clone de Hermes no agrega raices de Hermes.
- Causa: `_host()` importa `entorno` desde `Path(__file__).resolve().parent`; al ejecutar `leccion.py` via symlink `.agents/skills/harness-flow -> ~/.hermes/skills/.../harness-flow`, ese `resolve()` hace que `entorno.__file__` quede bajo `.hermes/skills`, no bajo `.agents/skills`. Entonces `host_agente()` detecta `hermes` en vez de `gpt`. Como `host == "hermes"`, `skills_roots()` agrega `_raiz_propia()`/raices Hermes y no las raices GPT.
- Reproduccion ejecutada en tmp con HOME aislado: copie `scripts/` a `HOME/.hermes/skills/software-development/harness-flow`, cree `HOME/.agents/skills/harness-flow` como symlink a esa ruta, agregue una skill `solo-gpt` bajo `.agents/skills` y una `solo-hermes` bajo `.hermes/skills/cat`. Sin `HARNESS_HOST`, `python .agents/skills/harness-flow/scripts/leccion.py donde` imprimio solo `.../.hermes/skills`; `existe solo-gpt` salio 1 y `existe solo-hermes` salio 0.
- Por que los tests no lo cubren: `tests/test_leccion.py:83-94` fuerza `HARNESS_HOST="gpt"`, por lo que salta la autodeteccion que falla. Ese test prueba el workaround manual, no el caso automatico requerido.

## Verificaciones sin hallazgo material

- `scripts/entorno.py` si detecta host `gpt` desde una instalacion real en `.agents/skills`, acepta `HARNESS_HOST=gpt` y normaliza `HARNESS_HOST=codex` a `gpt` (`scripts/entorno.py:25-42`, `scripts/entorno.py:170-180`). Reproduccion CLI: auto/gpt/codex imprimieron `HARNESS_HOST  : gpt`.
- Con `HARNESS_HOST=codex`, `leccion.py` normaliza a `gpt` y encuentra skills en `.agents/skills` del repo; tambien hay test para no subir por encima del repo root (`tests/test_leccion.py:65-81`).
- `agents/openai.yaml` es YAML valido y deja `policy.allow_implicit_invocation: true` (`agents/openai.yaml:1-7`). Validado con `ruby -ryaml`.
- La documentacion de rutas OpenAI coincide con la documentacion oficial consultada: Codex escanea `.agents/skills` desde CWD hasta repo root, `$HOME/.agents/skills` y `/etc/codex/skills`, y `agents/openai.yaml` controla `allow_implicit_invocation`.
- No vi reapertura en los casos previamente revisados: archivo `current`/`archive` (`scripts/gate.py:391-415`, `tests/test_progress_archive.py:69-112`), rollback Atlassian de backlog/progress/docs (`scripts/gate.py:523-546`, `tests/test_gate_atlassian.py:88-102`, `tests/test_documentacion.py:209-260`), PRD/SDD (`scripts/documentacion.py:149-158`, `tests/test_documentacion.py:85-131`), gate de rutas protegidas (`scripts/gate.py:131-180`, `tests/test_documentacion.py:149-207`) y Confluence PRD/SDD (`scripts/atlassian.py:111-129`, `tests/test_atlassian.py:225-239`).
- Los cambios no introducen dependencias de herramientas de Hermes/Claude en los scripts Python; las diferencias de host quedan en documentacion/instrucciones.

## Checks ejecutados

- `python3 -m unittest discover -s tests` -> 66 tests, OK.
- `python3 -m compileall -q scripts tests` -> OK.
- `git diff --check` -> OK.
- `python3 scripts/entorno.py` -> OK; diagnostico local sale 0 aun sin `psycopg` porque no se pidio `--hub`.
- `ruby -ryaml -e 'YAML.load_file("agents/openai.yaml")...'` -> OK.
- Reproducciones manuales GPT/Codex y symlink descritas arriba.

## Archivos modificados por esta revision

- `REVIEW3-archive-docs.md`
