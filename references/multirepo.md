# Cierre multi-repo existente, sin merge automatico

Este camino registra y verifica repos/worktrees EXISTENTES. No crea ramas,
worktrees ni merges. Es stdlib + Git local, con el mismo CLI en Hermes, Claude
Code y GPT/Codex. No instala dependencias del hub.

## Contrato minimo

1. El leader declara conscientemente la lista COMPLETA de `microservicios` en la
   feature del backlog. Cada nombre es un directorio inmediato bajo la raiz del
   proyecto (puede ser symlink al repo real). El manifiesto debe cubrir exactamente
   esa lista. Metadata heredada incompleta exige corregir la declaracion con
   autorizacion; el registro no autodetecta ni completa solo los que pasan.
2. El usuario aprueba la rama destino. Esta version minima exige el MISMO nombre
   de rama local en todos los repos. Cada checkout `repo` ya debe estar en esa
   rama; `close --to` no hace checkout en este modo.
3. Declara SHAs completos, literales, de commits reales: `base_sha` anterior a la
   feature, `source_sha` que contiene su delta completo, y `target_sha` del tip
   destino a validar. El reviewer debe comprobar que ese delta realmente satisface
   la feature: un SHA/ancestria no prueba semantica ni los AC.
4. `repo` debe resolver exactamente a `<raiz>/<microservicio>`; `worktree` es una
   ruta absoluta inscrita por Git en EL MISMO common-dir. Repos duplicados,
   clones ajenos, directorios interiores, SHAs abreviados, refs/opciones y campos
   extra se rechazan. Los symlinks se canonizan antes de comparar/deduplicar.
5. Fuente separada: `HEAD == source_sha`, incluso detached. Caso ya integrado:
   `worktree == repo`, y `source_sha` puede ser un ancestro de `target_sha`; no se
   inventa un merge. Esa fuente compartida NO cuenta como aislamiento.
6. Repos y fuentes deben estar limpios de tracked y untracked. Los artefactos
   ignorados por Git pueden permanecer: no es permiso para esconder trabajo con
   `assume-unchanged`/`skip-worktree` (ambos bloquean). No hay flag de bypass.

## Manifiesto

Esquema de ejemplo, NO evidencia de un proyecto. Sustituir los tres marcadores
SHA por `git rev-parse <commit>` reales y repetir una fila por CADA servicio:

```json
{
  "version": 1,
  "feature": "7",
  "repos": [
    {
      "microservicio": "orders",
      "repo": "/proyecto/orders",
      "worktree": "/worktrees/orders",
      "base_sha": "<SHA completo previo a la feature>",
      "source_sha": "<SHA completo de la feature>",
      "target_branch": "develop",
      "target_sha": "<SHA completo del tip develop>"
    }
  ]
}
```

## Invocaciones desde la raiz con harness/

Resolver `PY`/`H` con `entorno.py` como en SKILL.md. Los comandos son identicos
si la skill esta instalada en Hermes o enlazada desde `.claude/skills`.

```bash
$PY "$H/gate.py" check-spec --feature 7
$PY "$H/worktree.py" register --feature 7 --manifest /ruta/registro.json
```

El registro persiste solo `multi_repo` y `multi_repo_protected`, y agrega historia.
No cambia status, roles, aprobaciones, permisos de documentacion ni otras
features. Conserva una huella de las rutas protegidas de la raiz sin Git; no
puede certificar el estado anterior al primer registro. El leader debe contrastar
esa primera foto con sus respaldos y la autorizacion del usuario. No se puede
re-registrar para blanquear una diferencia posterior de esas rutas.

Antes de integrar manualmente, tomar una base REAL de CADA repo en su rama
destino, HEAD igual a `base_sha`, con el runner Go robusto:

```bash
$PY "$H/postmerge_medido.py" base --repo /proyecto/orders \
  --cmd 'go test -tags integration -count=1 -json ./...' --guardar /ruta/base-orders.json
```

Declarar SOLO las rutas de las bases; no es un recibo de PASS, no acepta comandos
ni resultados manuales. `bases-postmerge.json` debe enumerar TODOS los nombres:

```json
{"version": 1, "feature": "7", "bases": {"orders": "/ruta/base-orders.json"}}
```

Integrar externamente solo con permiso. Si cambio el tip, actualizar el mapa y
repetir `register`; review/verify del contexto anterior no sirven. `close` ejecuta
SIEMPRE la suite real sobre CADA `repo`/tip, aunque exista `mediciones_destino`.
No reemplazarlo por `postmerge.py` legacy: se conserva ese archivo heredado sin
modificar, pero su parser de texto no participa de la decision de cierre.

```bash
# Con integracion manual terminada y el manifiesto actualizado:
$PY "$H/worktree.py" register --feature 7 --manifest /ruta/registro.json
$PY "$H/gate.py" verify --feature 7
$PY "$H/revision.py" --feature 7 --briefing
# Revision INDEPENDIENTE de todos los repos, evidencia, AC y ambos SHAs;
# despues de leer el informe real:
$PY "$H/gate.py" revision --feature 7 --veredicto approved
$PY "$H/gate.py" check
$PY "$H/gate.py" close --feature 7 --status done --to develop \
  --integrated --postmerge /ruta/bases-postmerge.json --leccion <clase-existente>
```

`verify` sigue ejecutando los comandos DEL SPEC desde la raiz, sin reescribirlos.
El registro vincula ejecucion/reporte al mapa de commits, spec, evidencia y reglas;
NO demuestra que un runner generico ejecuto tests no vacios: cada AC debe usar un
comando falsable y comprobar resultados terminales, ademas de las suites destino.
Cero comandos/registro ausente no permiten cerrar con `require_verify_green`.

## Bloqueos y limites

- `close --integrated` vuelve a medir TODOS los repos, integracion por ancestria,
  target branch activa, tip exacto, fuente exacta/ya integrada y limpieza.
- Spec aprobado/fresco, evidencia por AC, review sellado/fresco/por AC, verify
  real con reporte firmado y contexto actual, y leccion existente son obligatorios
  en este modo; un recibo no los reemplaza ni permite `--leccion ninguna`.
- Se conservan los bloqueos del check global y el mapa real de aislamiento. Una
  feature no aislada no es liberada inventando `worktree: "..."`; dos fuentes
  que compartan un mismo worktree bloquean incluso si ambos mapas son completos.
- Se audita CADA commit de base..fuente y base..destino contra TODOS sus padres,
  incluidos lados de merges y cambios restaurados: un diff neto limpio no basta.
  Solo se leen nombres, excepto el PRD maestro para la excepcion generada exacta.
  Marcadores eliminados/malformados/duplicados o bytes manuales distintos bloquean.
  El fingerprint ignora SOLO el bloque generado bien formado, nunca todo el PRD;
  re-registrar no reautoriza cambios. Un registro previo al formato de fingerprint
  nuevo no se migra automaticamente ni re-sella para ocultar divergencias.

  La primera insercion autorizada distingue PRD ausente, manual sin marcadores y
  generado. Solo admite prefijo manual exacto + bloque generado + LF, sin strip
  ni conversion de saltos. El compromiso de review permanece igual, pero el
  registro/cierre captura el estado generado para rechazar su eliminacion posterior.
  El cierre lo captura dentro de su transaccion: un fallo posterior restaura la
  foto previa junto con backlog/documentos. No se recalibran otras rutas o raices.
  Symlinks/salidas no regulares no habilitan escrituras fuera del contrato.
- El cierre persiste `integraciones` con fuente y tip POR REPO y los muestra en
  SDD. No escribe un `merge_commit` global ficticio. PRD/SDD y archivo de progreso
  mantienen el contrato anterior de bloques generados; ningun cuerpo manual se
  autoriza por el registro.
- No usar `start`/`drop` para gestionar este registro. Los worktrees pertenecen a
  quien los preparo; el registro no concede permiso para recrearlos/eliminarlos.
- No hay transaccion distribuida ni bloqueo de escritores Git concurrentes.
  Detener escritores antes de registrar/revisar/cerrar; una foto no impide que
  alguien mueva una rama despues de medirla. No se publica/pushea nada.
- En un monorepo sin registro multi-repo, `close --to` conserva el merge real
  `--no-ff`. No usar ese camino en una raiz agregadora sin `.git`.

## Garantia del cierre y limites de runners

- `mediciones_destino` se PRODUCE por ejecucion real en el cierre; vincula cada
  ruta/HEAD/base/source/target, contexto spec+impl+reglas, comando fijo, Python,
  hashes del runner/helper, inventario y exits de binarios. Un PASS tipeado o un
  exit 0 sin tests no sirve. Se revalidan tips, limpieza y contexto al terminar.
- Go JSON + evidencia lateral `-exec` sin cambios. Comando fijo de suite completa:
  `go test -tags integration -count=1 -json ./...`. No hay selector `--cmd` en
  close; se limpia GOFLAGS y se desactiva GOWORK para no medir otro workspace.
  Base v2 debe coincidir en ruta/rama/base_sha/comando y ser coherente/no vacia;
  falta/corrupcion/alcance ajeno no es verde. Tests anteriores desaparecidos y
  CUALQUIER test skip en destino bloquean; paquetes sin tests pueden coexistir
  con pruebas realmente ejecutadas. Los rojos nuevos bloquean; deuda base se
  distingue de regresiones, no se anuncia como suite totalmente verde.
- Limite de confianza: codigo/comando, ejecutable Go y bases pre-merge son
  artefactos locales de confianza revisados por el leader. No hay atestacion
  criptografica del autor ni defensa contra un actor que falsifique coherentemente
  TODO el estado local/runner. Un archivo de resultados destino nunca evita
  ejecutar la suite. Conservar bases originales y sus logs/hash para auditar
  procedencia; no escribir deuda a mano. El inventario comparable es el de la
  base: no certifica AC ausentes ni descubre todos los tests esperados del producto.
- Angular22/Vitest4+Node22 tiene el contrato acotado descrito abajo. Python,
  Jest y otros protocolos no se disfrazan de Go JSON: quedan BLOQUEADOS, no
  se omiten. Sin base preintegracion genuina tambien se bloquea; no fabricar
  una base despues del merge.
- Cierre y sync protegen errores/excepciones capturables con preflight y rollback
  byte-identico de backlog, documentos, progreso e historia, tambien monorepo.
  No es una transaccion durable ante SIGKILL/corte electrico ni bloqueo concurrente.
  Si Git ya mergeo, se conserva el merge y se informa; nunca reset automatico.
  Si Atlassian fallo, se restaura el preestado LOCAL (incluidos IDs locales), pero
  puede haber efectos remotos parciales: reconciliar antes de reintentar, sin
  prometer rollback de Jira/Confluence ni repetir publicaciones a ciegas.

## Lecciones del contrato

Comparar bytes manuales, no texto normalizado; auditar commits, no solo arboles;
medir destinos antes de persistir done; restaurar todo el conjunto de salidas si
falla cualquier escritura posterior. Los controles negativos deben atravesar el
CLI y probar preestado byte-identico, no solo exit distinto de cero.

## Pruebas reproducibles

`python3 -m unittest discover -s tests -p 'test_multirepo_close.py' -v` crea tres
repos locales temporales y commits con identidad `Fixture`. Prueba el CLI real,
ancestria/integracion y controles negativos; no representa datos ni cierres del
proyecto del usuario. `HARNESS_TEST_SCRIPTS` permite ejercitar el mismo contrato
por un symlink de instalacion simulado sin modificar skills instaladas.

## Contrato frontend ADR (Angular22/Vitest4 y Node22)

Antes de integrar, sobre Git limpio y rama destino activa:

```bash
$PY "$H/postmerge_frontend.py" base --repo /proyecto/front \
  --guardar /evidencia/base-front.json --evidence /evidencia/base-front-raw.json
# Despues de integrar con permiso, para un check independiente:
$PY "$H/postmerge_frontend.py" check --repo /proyecto/front \
  --base /evidencia/base-front.json --evidence /evidencia/check-front-raw.json
```

Agregar `"front": "/evidencia/base-front.json"` al mapa `bases` del cierre,
JUNTO a los demas repos. La forma del mapa no cambia. `close` selecciona este
runner si encuentra angular.json/package.json; rechaza repos mixtos Go+frontend
antes de elegir uno. No acepta un selector de comando o runner aportado por el
proyecto, ni cambia el protocolo Go. El runner frontend no instala dependencias.

- `scripts.test` debe ser literalmente `npm run test:dist && ng test <p1> ...`,
  un `ng test` por TODOS los proyectos de angular.json, sin filtros, duplicados
  ni hooks npm de test. En ADR: storefront/admin/cafeterias/ui/api-client.
- `test:dist` es literalmente `node --test scripts/verificar-dist.test.mjs scripts/catalogo-snapshot.test.mjs`.
  Es el inventario portable oficial, NO los casos opcionales activados por
  artefactos externos DIST_* ni el test legal cross-repo fuera de ese comando.
- Cada target test es `@angular/build:unit-test`, options solo `tsConfig` y sin
  configuraciones/defaultConfiguration. Raices `projects/<nombre>`; ningun
  symlink en tests Node/fuentes Angular. Cotejar archivos esperados contra
  archivos y tests efectivamente terminados; ausencias no son curaciones.
- El runner descompone ese comando literal en los entrypoints NATIVOS con Node
  fijado (no shell/npm wrappers), agrega solo no-watch y reporters de evidencia.
  Exige Node22, Angular CLI/build22, Vitest4, lock y hashes de sus propios helpers.
  CI=1/TZ=UTC; rechaza overrides NODE_*, VITEST*, NG_BUILD_*, DIST_* y limpia el
  entorno de tests. No exportar secretos: solo PATH/HOME y variables de sistema.
- Rechaza skip/todo/only, retry/fails, vacios, duplicados, finales parciales,
  errores de suite/teardown/unhandled e incoherencia con exits nativos. Node
  usa tests planos ADR; diagnosticos con archivo (incl. only/runOnly) quedan
  fuera de contrato. No identificar errores por palabras de stdout del test.
- Base v1/protocolo propio, esquema cerrado, argv real, repo/rama/SHA/tree,
  inventario, lock/toolchain/runner y raw verificables. Debe ser ancestro del
  destino y coincidir EXACTAMENTE con base_sha al cerrar. Un homonimo de otro
  proyecto/archivo es otra identidad. Tests desaparecidos bloquean con exit2.
- CLI: 0 medicion completa sin regresiones (puede contener deuda), 1 nuevos
  rojos medidos, 2 no pudo medir. No sobrescribe bases/evidencia. Sin --evidence
  crea un JSON unico junto a la base, tambien al fallar. En cierre, conserva
  `*.close.evidence.json` junto a la base y bloquea done si falta comparabilidad.
  Bases y evidencia deben vivir FUERA del repo medido. Se conserva stderr/raw
  separado de resultados: logs de tests no son evidencia de PASS.
- El limite de confianza local es el mismo que Go: no es una atestacion contra
  falsificacion coordinada del runner y todos los JSON. Tampoco es una sandbox
  para codigo hostil. Revisar codigo, bases y procedencia antes del cierre.

`HARNESS_TEST_FRONTEND_MODULES` debe apuntar a node_modules YA instalado con
estas versiones para `python -m unittest discover -s tests`; no hay skips ni
instalaciones de rescate. Ejecutar con PATH que fije Node/Go/Git/Python, en dos
interpretes y rutas simuladas `.hermes/skills/...` y `.claude/skills/...`.
`HARNESS_TEST_FRONTEND_LOGS` conserva raw de fixtures fuera de sus temporales.

Leccion reusable: contrastar inicio/final por archivo y caso con el inventario
independiente; no contar solo un resumen JSON. Forzar allowOnly ANTES de
coleccion Vitest, porque despues normaliza only a run. Probar la decision REAL
del cierre, ademas del parser, y conservar el raw de fallos antes de limpiar.
