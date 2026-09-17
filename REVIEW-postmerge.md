# REVIEW postmerge.py

Veredicto: changes_requested

## Hallazgos

### P1 - El gate acepta un selector que no ejecuto ningun test si Go imprime `ok ... [no tests to run]`

- Referencias: `scripts/postmerge.py:47`, `scripts/postmerge.py:49`, `scripts/postmerge.py:50`, `scripts/postmerge.py:54`; cobertura actual incompleta en `tests/test_postmerge.py:83`.
- Contrato violado: el gate debe salir 2 cuando la suite no corrio o no hay evidencia positiva de ejecucion. El propio comentario dice que `no tests to run` no es verde, pero la condicion solo rechaza `corridos == 0 and oks == 0`; una linea `ok <paquete> ... [no tests to run]` cuenta como evidencia aunque hayan corrido cero tests.
- Reproduccion real con Go 1.26.0: en un modulo con `TestReal`, `go test -run DoesNotExist ./...` imprime `ok  	example.com/empty	0.463s [no tests to run]` y sale 0. Ejecutando `postmerge.py base --cmd 'go test -run DoesNotExist ./...'` sobre ese repo, el script reporta `0 '=== RUN', 1 paquete(s) ok, 0 rojo(s) top-level`, guarda base vacia y sale 0.
- Por que los tests verdes no lo excluyen: `tests/test_postmerge.py:83` simula solo `no tests to run\n` sin la linea `ok ... [no tests to run]` que emite Go en el caso real de selector vacio. Esa prueba cubre ausencia total de evidencia, no suite presente-pero-vacia.

## Verificaciones ejecutadas

- `python3 -m unittest tests.test_postmerge -v` -> 4 tests OK.
- `python3 -m unittest discover -s tests -v` -> 70 tests OK.
- `python3 -m compileall -q scripts tests` -> OK.
- `git diff --check` -> OK.
- Smoke manual con salida simulada:
  - base guarda rojos preexistentes -> exit 0, JSON con `TestViejo`.
  - check pasa con deuda preexistente sin nuevos -> exit 0.
  - check falla con rojo nuevo -> exit 1, lista `TestNuevo`.
  - salida sin `=== RUN` ni `ok <paquete>` -> exit 2.
  - salida realista `ok example.com/pkg ... [no tests to run]` -> exit 0; este es el hallazgo.
- Smoke real Go: `go test -run DoesNotExist ./...` genera `ok ... [no tests to run]`; `postmerge.py` lo acepta como base valida con cero tests ejecutados.

## Seguridad y portabilidad

- Sin hallazgos bloqueantes adicionales. `--cmd` se ejecuta con `shell=True`, pero es una herramienta local cuyo usuario define deliberadamente el comando de la suite; no se alimenta de entrada remota. Conviene mantenerlo tratado como comando confiable y evitar interpolar datos no confiables.
- La documentacion de `SKILL.md` sobre usar `postmerge.py` despues de `close`, comparar rojos nuevos y no usar pipes para verificar exit code coincide con el comportamiento esperado. No vi mentira material en el SKILL; el problema esta en una rama no cubierta del detector.

## Archivos modificados por esta revision

- `REVIEW-postmerge.md`
