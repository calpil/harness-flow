# REVIEW2 archive/docs

Veredicto: approved

## Hallazgos

No encontre bloqueantes en la revision acotada. El P1 reportado en `REVIEW-archive-docs.md` queda resuelto en el comportamiento real del gate.

## Verificacion P1

### 1. `documentacion.py sync` + `gate.py check` verde con `PRD-master.md` generado

Verificado en repo temporal git limpio: `/var/folders/8s/nppx4bg950dd7jh7fkpf6zp40000gn/T/hf-review2-ehucnpv8`.

- Base commiteada sin `docs/prd/`.
- `python3 scripts/documentacion.py sync` salio 0 y creo:
  - `docs/prd/PRD-master.md`
  - `docs/sdd.md`
- `git status --porcelain` despues del sync mostro el caso que rompia antes:
  - `M harness/feature_list.json`
  - `?? docs/prd/`
  - `?? docs/sdd.md`
  - `?? harness/progress/`
- `python3 scripts/gate.py check` salio 0:
  - `[ok] 3 ruta(s) protegida(s) intactas`
  - `[ok] check limpio.`

La excepcion esta acotada en `scripts/gate.py:121-160`: solo `docs/prd/PRD-master.md`, con marcadores `harness-flow:features`, y con el contenido fuera de marcadores igual al baseline/default.

### 2. Edicion manual fuera del bloque generado queda bloqueada

En el mismo repo temporal, despues de commitear la documentacion generada como baseline, modifique el texto manual fuera de los marcadores en `docs/prd/PRD-master.md`.

- `python3 scripts/gate.py check` salio 1.
- Salida relevante:
  - `[!!] rutas protegidas modificadas: docs/prd/PRD-master.md`
  - `[!!] 1 bloqueo(s), 0 aviso(s).`

Esto esta cubierto tambien por `tests/test_documentacion.py:166-188`.

### 3. Otros archivos bajo `docs/prd/**` quedan prohibidos

Probe dos variantes:

- Con `docs/prd/` ya trackeado, agregue `docs/prd/otro.md`:
  - `python3 scripts/gate.py check` salio 1.
  - La salida nombro `docs/prd/otro.md`.
- Con `docs/prd/` aun como directorio untracked, agregue `docs/prd/otro.md` junto al PRD generado en `/var/folders/8s/nppx4bg950dd7jh7fkpf6zp40000gn/T/hf-review2-extra-untracked-mlgg5pvl`:
  - `git status --porcelain` mostro `?? docs/prd/`.
  - `python3 scripts/gate.py check` salio 1 con `rutas protegidas modificadas: docs/prd/`.

La segunda variante verifica que el caso de porcelain agregado como directorio no abre una via para colar otros archivos.

## Regresiones previas revisadas

- Archivo `current`: `tests/test_progress_archive.py:69-112` cubre que `close --status done` archiva `harness/progress/current-<id>.md`, que `blocked` lo mantiene vivo y que un fallo Atlassian lo restaura. Ejecutado en el subset dirigido: OK.
- Rollback Atlassian: `scripts/gate.py:424-426` conserva el cierre original, `scripts/gate.py:533-550` revierte status/campos/progress y resincroniza docs si `atlassian.py push` falla. Cubierto por `tests/test_gate_atlassian.py:88-102`, `tests/test_progress_archive.py:92-112` y `tests/test_documentacion.py:190-215`. Ejecutado: OK.
- PRD/SDD: `scripts/documentacion.py:149-158` sincroniza `docs/prd/PRD-master.md` y `docs/sdd.md`; `tests/test_documentacion.py:85-131` cubre creacion, idempotencia y preservacion manual fuera del bloque generado. Ejecutado: OK.
- Confluence PRD/SDD: `scripts/atlassian.py:111-129` agrega PRD/SDD al cuerpo si existen; `tests/test_atlassian.py:225-239` lo cubre. Ejecutado: OK.
- Host-neutral Hermes/Claude: el cambio nuevo usa Python stdlib y rutas del proyecto (`scripts/documentacion.py:1-18`, `scripts/gate.py:521-523`) y no introduce APIs de Hermes ni Claude. Las regresiones de entorno/lecciones siguen cubiertas por `tests/test_entorno.py` y `tests/test_leccion.py`; subset dirigido ejecutado: OK.

## Checks ejecutados

- `python3 -m unittest discover -s tests` -> 58 tests, OK.
- `python3 -m compileall -q scripts` -> OK.
- `git diff --check` -> OK.
- Subset dirigido de regresiones (`ProgressArchiveTests`, P1 en `DocumentacionTests`, rollback Atlassian, Confluence PRD/SDD, `EntornoTests`, `RaicesTests`, `PerfilesHermesTests`) -> 40 tests, OK.
- Reproducciones manuales en repos temporales git para P1 -> verdes/rojos esperados.

## Archivos modificados por esta revision

- `REVIEW2-archive-docs.md`
