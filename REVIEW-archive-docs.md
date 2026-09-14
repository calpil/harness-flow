# REVIEW archive/docs

Veredicto: changes_requested

## Hallazgos

### P1 — `documentacion.py sync` deja el arnes en rojo con la configuracion por defecto

- Referencias: `scripts/documentacion.py:152-158`, `scripts/gate.py:110-126`, `scripts/comun.py:61-68`, `SKILL.md:145`.
- Criterio afectado: (3) sincronizar `docs/prd/PRD-master.md` y `docs/sdd.md` preservando manual, y contrato documentado de que el bloque generado es una excepcion segura a `docs/prd/**`.
- Problema: `documentacion.sync()` crea/actualiza `docs/prd/PRD-master.md`, pero `_check_rutas_protegidas()` sigue fallando cualquier cambio bajo `docs/prd/**` sin distinguir el bloque generado `harness-flow:features` de ediciones manuales. En un repo con las reglas por defecto, la sincronizacion esperada convierte `gate.py check` en rojo.
- Reproduccion ejecutada en un repo temporal limpio con una feature `done`: `python3 scripts/documentacion.py sync` creo `docs/prd/PRD-master.md` y `docs/sdd.md`; luego `python3 scripts/gate.py check` salio `1` con `rutas protegidas modificadas: docs/prd/`.
- Por que los tests no lo excluyen: no hay test de `gate.py check` despues de `documentacion.sync()` ni test que verifique la excepcion de bloque generado frente a `rutas_protegidas` (`search_files` en `tests/` no encontro cobertura de `rutas_protegidas`/`docs/prd`).

## Checks pedidos

- (1) `close --status done` archiva `harness/progress/current-<id>.md` sin perderlo: cubierto y verificado en `scripts/gate.py:337-348` y `tests/test_progress_archive.py:69-82`.
- (2) si `close --publicar-atlassian` falla, se restauran backlog/current y PRD/SDD no quedan como feature `done`: cubierto en `scripts/gate.py:479-496`, `tests/test_gate_atlassian.py:88-102`, `tests/test_progress_archive.py:92-112` y `tests/test_documentacion.py:149-174`.
- (3) `documentacion.py sync` crea/actualiza PRD/SDD preservando contenido manual fuera del bloque generado: implementado en `scripts/documentacion.py:130-158` y cubierto por `tests/test_documentacion.py:85-131`; bloqueado por el hallazgo P1 de integracion con rutas protegidas.
- (4) host-neutral Hermes/Claude Code: el cambio nuevo usa Python stdlib y rutas del proyecto (`scripts/documentacion.py:1-18`, `scripts/gate.py:467-469`) sin APIs de host; no vi acoplamiento a Hermes. La documentacion usa `$PY "$H/..."`, compatible con el flujo existente.
- (5) Confluence incluye PRD/SDD si existen: implementado en `scripts/atlassian.py:111-129` y cubierto por `tests/test_atlassian.py:225-239`; tambien aplica al outbox porque `cmd_push` usa el mismo `cuerpo_confluence` en `scripts/atlassian.py:194-200`.
- (6) tests: los casos principales existen y pasan, pero falta cobertura para la interaccion `documentacion.sync()` + `gate.py check` + `rutas_protegidas`, que hoy falla.

## Verificacion ejecutada

- `python3 -m unittest discover -s tests` -> 56 tests, OK.
- `python3 -m compileall -q scripts` -> OK.
- `git diff --check` -> OK.
- Reproduccion adversarial en repo temporal: `documentacion.py sync` OK; `gate.py check` FAIL por `rutas protegidas modificadas: docs/prd/`.

## Archivos modificados por esta revision

- `REVIEW-archive-docs.md`
