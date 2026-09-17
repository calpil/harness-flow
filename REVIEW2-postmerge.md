# Revision independiente final de postmerge

Veredicto: changes_requested

## Alcance y evidencia

- Revision de los cambios pendientes sobre `main`, HEAD `a4b514f`: `SKILL.md`, `scripts/postmerge.py` y `tests/test_postmerge.py`. El reporte anterior se leyo como antecedente, no como evidencia de ejecucion de esta revision.
- Contrato evaluado: exit **0** si no aparecen rojos nuevos; **1** si aparecen; **2** si no se pudo medir. La deuda preexistente no convierte la suite en verde.
- Ejecucion local: Python **3.14.6**, Go **1.26.0**, `darwin/arm64`. Sin servicios remotos ni dependencias Go descargadas: sondas con `GOPROXY=off`, `GOSUMDB=off`, `GOTOOLCHAIN=local` y `GOWORK=off`.
- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v`: **71 tests OK**, exit 0.
- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_postmerge -v`: **5 tests OK**, exit 0.
- Compilacion en memoria con `compile(...)` de los archivos Python de `scripts/` y `tests/`: **23 archivos OK**, sin escribir bytecode. `git diff --check`: exit 0.
- Sondas adicionales: **35 invocaciones reales** de Go/CLI, con **13 discrepancias** respecto al resultado esperado, agrupadas en los cinco hallazgos siguientes. El script exploratorio captura resultados, no es una suite de aserciones: su propio exit 0 no significa aprobacion.

**Los tests verdes no permiten aprobar: hay cuatro P1 reproducidos y un P2.**

## Hallazgos

### P1-1 — Un test valido oculta un error posterior de comando o compilacion

**Lineas:** `scripts/postmerge.py:45-58`, `scripts/postmerge.py:93-103`, `scripts/postmerge.py:115-120`.

`correr()` obtiene `r.returncode`, pero nunca lo consulta; basta encontrar un `=== RUN` o un `ok` para devolver una medicion valida. Los errores de paquete/build no coinciden con `RE_FAIL`. Ademas, `main()` descarta la salida cruda que permitiria ver el error.

**Reproduccion con Go real:**

1. Modulo `example.com/measurement`, `integration/good/x_test.go` con `func TestReal(t *testing.T) {}`. Tomar base con el comando por defecto: exit 0, `rojos: []`.
2. Ejecutar `--cmd 'go test -count=1 -v ./integration/good; exit 23'`. El comando real termina **23** despues de `--- PASS: TestReal`; tanto `base` como `check` terminan **0**. `check` imprime `[ok] el merge no agrego rojos nuevos.`
3. Agregar `integration/broken/broken.go` con `package broken` y `var value = undefinedReview2Symbol`. La invocacion **por defecto**, `go test -tags integration -count=1 -v ./integration/...`, termina **1**, con `[build failed]` y `undefined: undefinedReview2Symbol`, mientras el paquete `good` pasa. Tanto `base` como `check` terminan **0** y la base invalida se guarda.
4. Confirmacion del orden solicitado: `go test -count=1 -v ./integration/good && go test -count=1 -v ./integration/broken` imprime primero el PASS y luego el error de build; el comando termina **1**, el gate **0**.

**Esperado:** exit **2** en estos casos, sin publicar una base valida ni un veredicto de ausencia de regresiones. Una parte de la suite no pudo medirse. No basta cambiarlo por `returncode != 0 -> 2`: un exit 1 de Go causado exclusivamente por tests rojos efectivamente medidos debe seguir permitiendo comparar deuda y detectar nuevos rojos.

**Cobertura que falta:** `tests/test_postmerge.py:36-38` genera stdout con Python y siempre termina 0; no prueba el estado real del proceso ni un fallo de paquete mezclado con un test valido.

### P1-2 — Tests homonimos de paquetes distintos se convierten en una sola deuda

**Lineas:** `scripts/postmerge.py:36`, `scripts/postmerge.py:47`, `scripts/postmerge.py:106-108`.

El identificador es solo el nombre extraido de `--- FAIL:`. Se pierde el paquete antes de construir el conjunto; dos tests distintos llamados `TestSame` son indistinguibles.

**Reproduccion con el comando por defecto, mismo modulo y misma base:**

1. `integration/a/x_test.go`: `func TestSame(t *testing.T) { t.Fatal("deuda anterior") }`.
2. `integration/b/x_test.go`: `func TestSame(t *testing.T) {}`.
3. `base`: exit **0**, guarda `rojos: ["TestSame"]`. `check` sin cambios: **0**, con aviso de deuda; esto es correcto.
4. Cambiar SOLO el cuerpo de `b.TestSame` a `t.Fatal("regresion nueva en b")` en la fixture.
5. Go imprime **dos** `--- FAIL: TestSame`, uno por cada paquete, y termina **1**. El gate sigue contando **un** rojo y `check` termina **0**: `[ok] el merge no agrego rojos nuevos.`

**Esperado:** exit **1** y el rojo nuevo de `example.com/homonymous/integration/b`. La identidad debe conservar al menos **paquete + nombre completo de test/subtest**. Los eventos estructurados del runner permiten conservar esa identidad sin inferirla de stdout ambiguo.

**Control de poder de deteccion:** al cambiar en la fixture el nombre de ese segundo test a `TestDifferent`, manteniendolo rojo, el gate SI termina **1** y lo lista. Por tanto, el falso verde depende especificamente de la colision de nombres, no de una sonda que no se ejecuto.

**Cobertura que falta:** `tests/test_postmerge.py:69-81` solo enfrenta nombres diferentes y no incluye contexto de paquetes.

### P1-3 — Acepta bases de otro alcance sin validar repo ni comando

**Lineas:** `scripts/postmerge.py:95-108`, `scripts/postmerge.py:111-120`.

La base guarda `repo`, pero `check` no lo compara. No guarda el comando de medicion. Cualquier lista `rojos` se usa como deuda autorizada, aunque provenga de otra ruta/modulo o de una seleccion distinta de paquetes.

**Reproducciones:**

- **Otro comando, mismo repo:** tomar base con `--cmd 'go test -count=1 -v ./integration/a'`, donde `a.TestSame` falla. Ejecutar `check` con `--cmd 'go test -count=1 -v ./integration/b'`, donde `b.TestSame` falla y nunca fue medido por la base: termina **0**, lo trata como deuda.
- **Variante independiente de nombres homonimos:** dejar `a.TestSame` rojo y hacer que `b` solo contenga `TestHealthy` verde. Con esa misma base de `a`, el `check` limitado a `b` termina **0** y afirma `[ok] se curo: TestSame`, aunque el test de `a` no cambio ni fue ejecutado. Identificar tests por paquete no basta para resolver esta variante.
- **Otra ruta y otro modulo:** pasar sin modificar el JSON generado en la fixture `homonymous` al `check --repo .../foreign`, cuyo modulo es `example.com/foreign` y tiene un `TestSame` rojo. Termina **0** con aviso de deuda. Las fixtures son repos Git temporales distintos, clonados localmente sin checkout desde el HEAD revisado; comparten historia Git, pero tienen rutas y modulos Go de medicion distintos. No se afirma haber probado historias Git inconexas.

**Esperado:** exit **2** por mediciones no comparables, antes de afirmar curaciones o ausencia de regresiones. Persistir y validar la identidad del repositorio/alcance y el comando de la suite; si se permite comparar checkouts distintos, hacerlo bajo una identidad validada, no ignorando los metadatos.

**Cobertura que falta:** `tests/test_postmerge.py:61` y `tests/test_postmerge.py:71` escriben bases a mano sin comando; no ejercitan una base real con alcance diferente.

### P1-4 — Una suite completamente omitida con skip se declara medida y cura deuda

**Lineas:** `scripts/postmerge.py:37-39`, `scripts/postmerge.py:48-56`, `scripts/postmerge.py:107-120`.

Contar `=== RUN` cuenta tambien tests que llaman inmediatamente a `t.Skip`. El `ok` del paquete tampoco prueba que exista algun test completado sin skip. No hay distincion entre inicio, omision y resultado medido.

**Reproduccion con Go real y comando por defecto:**

1. Tomar base con un unico `TestDebt` que hace `t.Fatal("deuda real antes del merge")`: exit **0**, base con `TestDebt` rojo.
2. En la fixture, reemplazar el cuerpo por `t.Skip("infraestructura no disponible")`.
3. Go imprime `=== RUN TestDebt`, `--- SKIP: TestDebt`, `PASS` y `ok ...`, y termina **0**.
4. `base` sobre esta suite totalmente omitida termina **0** y guarda `rojos: []`.
5. `check` contra la base roja original termina **0** y afirma `[ok] se curo: TestDebt`.

**Esperado:** exit **2** si todos los tests fueron omitidos; no declarar una deuda curada sin un resultado efectivo. Distinguir los finales `pass`/`fail` de `skip`, no solo detectar inicios o resumenes de paquete. Este hallazgo no exige rechazar toda suite que contenga algun skip: el caso probado tiene **cero tests no omitidos**.

**Cobertura que falta:** `tests/test_postmerge.py:83-101` solo comprueba ausencia de marcas y `[no tests to run]`, no una suite presente que omite todo por falta de infraestructura.

### P2-1 — Una base ausente o corrupta sale 1 en vez de 2

**Lineas:** `scripts/postmerge.py:105-106`, `scripts/postmerge.py:131-132`.

La lectura y decodificacion de la base no manejan errores. Con una suite real verde (`go test -count=1 -v ./integration/b` sobre `TestHealthy`):

- `check --base <archivo-inexistente>` termina **1**, con `FileNotFoundError`.
- `check --base <archivo-con-contenido-{>` termina **1**, con `JSONDecodeError`.

**Esperado:** exit **2** y diagnostico accionable: no fue posible calcular el delta. El contrato reserva exit 1 a rojos nuevos realmente medidos. Validar el archivo/esquema de la base y manejar los errores antes de emitir un veredicto.

## P1 anterior: reparado y comprobado independientemente

La correccion de `scripts/postmerge.py:39` y `scripts/postmerge.py:50-56` SI bloquea el caso reportado anteriormente:

- Modulo con un `TestReal` existente.
- `go test -count=1 -run DoesNotExist ./integration/...` termina **0** e imprime `ok ... [no tests to run]`.
- `base` y `check` con ese comando terminan **2**; no se crea el archivo de base.
- Repeticion con `-v`: mismo resultado correcto; el `PASS` global de Go no compra el verde.
- Paquete con fuentes pero sin archivos de test: Go imprime `[no test files]`; `base` y `check` terminan **2**.

Esto cierra el vector exacto anterior, no los falsos verdes restantes.

## Matriz resumida

| Escenario | Exit del gate observado | Esperado |
| --- | --- | --- |
| Base/check de suite real verde | 0 / 0 | 0 / 0 |
| Solo deuda preexistente, sin cambios | 0, anuncia deuda | 0 |
| Nuevo rojo con nombre distinto | 1, lista `TestDifferent` | 1 |
| Selector inexistente, con y sin `-v`, base/check | 2 / 2 | 2 / 2 |
| Paquete sin archivos de test, base/check | 2 / 2 | 2 / 2 |
| PASS seguido de exit 23, base/check | 0 / 0 | 2 / 2 |
| PASS y build fallido, comando por defecto, base/check | 0 / 0 | 2 / 2 |
| PASS y luego build fallido secuencial, check | 0 | 2 |
| Nuevo rojo homonimo en otro paquete | 0 | 1 |
| Base de otro comando / seleccion distinta | 0 | 2 |
| Base de otra ruta/modulo | 0 | 2 |
| Todos los tests skip, base/check | 0 / 0 | 2 / 2 |
| Base ausente / JSON invalido | 1 / 1 | 2 / 2 |

## Reproduccion sobre las fixtures conservadas

Evidencia temporal local, no parte del paquete a commitear:

- Directorio: `/var/folders/8s/nppx4bg950dd7jh7fkpf6zp40000gn/T/postmerge-review2-nnk310su/`.
- `probe.py`: construye las fixtures y registra todos los pasos antes/despues. Para repetir la bateria desde cero, copiar este script a **otro directorio temporal vacio** y ejecutarlo alli; no volver a ejecutarlo en el mismo directorio porque los clones ya existen.
- `results.json`: argumentos, cwd, exit real, stdout, stderr y esperado de cada invocacion. Los numeros del reporte se agregaron leyendo este archivo, no contando a mano.

Las siguientes comprobaciones siguen siendo repetibles contra las fixtures finales; capturar el exit del proceso directamente, sin pipes:

```sh
P=/Users/alan/.hermes/skills/software-development/harness-flow/scripts/postmerge.py
T=/var/folders/8s/nppx4bg950dd7jh7fkpf6zp40000gn/T/postmerge-review2-nnk310su
export GOPROXY=off GOSUMDB=off GOTOOLCHAIN=local GOWORK=off

# P1-1: build roto y TestReal verde; observado 0, esperado 2.
python3 "$P" check --repo "$T/measurement" --base "$T/measurement/base.json"

# P1-1: PASS real antes del fallo del comando; observado 0, esperado 2.
python3 "$P" check --repo "$T/measurement" --base "$T/measurement/base.json" \
  --cmd 'go test -count=1 -v ./integration/good; exit 23'

# P1-2: esta fixture acaba en el control TestDifferent (exit 1).
# Para el fallo homonimo, renombrar SOLO TestDifferent a TestSame en
# "$T/homonymous/integration/b/x_test.go"; despues check devuelve 0 en vez de 1.
python3 "$P" check --repo "$T/homonymous" --base "$T/homonymous/base.json"

# P1-3: a sigue rojo, pero solo se mide b y se afirma curacion; observado 0.
python3 "$P" check --repo "$T/commands" --base "$T/commands/base.json" \
  --cmd 'go test -count=1 -v ./integration/b'
python3 "$P" check --repo "$T/foreign" --base "$T/homonymous/base.json"

# P1-4: todos skip, deuda presentada como curada; observado 0, esperado 2.
python3 "$P" check --repo "$T/skipped" --base "$T/skipped/base.json"

# P2-1: observado 1 con traceback, esperado 2.
python3 "$P" check --repo "$T/commands" --base "$T/commands/missing.json" \
  --cmd 'go test -count=1 -v ./integration/b'
```

## Alcance de seguridad, portabilidad y cambios de esta revision

- `--cmd` es un comando local definido deliberadamente por el operador. No se reporta `shell=True` como inyeccion remota; no hubo entrada remota ni se probaron sistemas productivos.
- `SKILL.md:155-171` documenta base antes del merge y check despues, y advierte sobre pipes. El problema bloqueante esta en los veredictos del script, no en esa secuencia documentada.
- No se encontraron acoplamientos nuevos a una API de Hermes/Claude/Codex en este script de biblioteca estandar. Ejecucion comprobada solo en el host local indicado; no se afirma validacion en Windows/Linux ni en los tres hosts de agente.
- **Unico archivo creado en el repositorio por esta revision: `REVIEW2-postmerge.md`.** Este revisor no modifico codigo, tests ni `SKILL.md`. Los hashes SHA-256 de `scripts/postmerge.py`, `tests/test_postmerge.py` y `REVIEW-postmerge.md` permanecen identicos antes/despues.
- **Cambio concurrente detectado al cierre:** `SKILL.md` paso de SHA-256 `c6141dd01651a2f8e6fc528abb956315968679dc12f036ec0f68911e845bb9d7` a `c664bc545a1482cbe90949d1cdfb0a6f1995e926b14ee6a25fc4cfbe5a51aaae`, sin intervencion de este revisor. Se releyo el diff: agrega un parrafo de siete lineas sobre estados `pending` del backlog, ajeno a postmerge, y desplaza las referencias de documentacion. No cambio el script bajo prueba ni sus tests. Se actualizaron las citas y se repitio la suite completa: **71 tests OK**. No se reviso funcionalmente ese agregado ajeno al alcance.
- Se crearon un script de sondas, JSON de evidencia y fixtures desechables fuera del repo. Los clones de las sondas fueron locales, sin checkout y sin crear commits. La suite existente utiliza sus propios repos temporales y commits de fixture; no se hizo commit ni push en el repo revisado.
- HEAD permanece en `a4b514f`. Sin bloqueos de herramientas que impidieran completar el pase solicitado.
