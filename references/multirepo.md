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
Un AC con `go test ./...` a secas falla ahi (`directory prefix . does not contain
main module`): el comando tiene que entrar al repo, p. ej.
`[ -d <svc> ] && cd <svc>; go test ./...`, que tambien sirve dentro del worktree.
El registro vincula ejecucion/reporte al mapa de commits, spec, evidencia y reglas;
NO demuestra que un runner generico ejecuto tests no vacios: cada AC debe usar un
comando falsable y comprobar resultados terminales, ademas de las suites destino.
Cero comandos/registro ausente no permiten cerrar con `require_verify_green`.

## Tests retirados por la feature

Una feature que retira codigo (un broker, un cliente, un paquete) borra tambien
los tests que solo lo certificaban, y la medicion postmerge los ve como tests
desaparecidos: bloquea, con razon, porque esa es la firma de un skip o un build
tag. La baja legitima se declara aparte y el gate la verifica. No se edita la
base ni se toma de palabra:

El MISMO archivo cubre destinos Go y frontend; cada entrada usa el formato de su
destino y mezclarlos en un microservicio (o cruzarlos entre destinos) se rechaza
ANTES de correr una sola suite:

```json
{"version": 1, "feature": "7",
 "retirados": {
   "orders": ["fixture.invalid/orders/events::TestDLQPublisher"],
   "front": [["angular:api-client", "projects/api-client/src/lib/cafeterias-api.spec.ts",
              "CafeteriasApi `me` es POST porque VINCULA, no solo consulta"],
             ["node:test", "scripts/catalogo-snapshot.test.mjs", "el snapshot trae precios"]]}}
```

```bash
$PY "$H/gate.py" close --feature 7 --status done --to develop --integrated \
  --postmerge /ruta/bases-postmerge.json --retirados /ruta/retirados.json --leccion <clase>
$PY "$H/postmerge_medido.py" check --repo /proyecto/orders --base /ruta/base-orders.json \
  --cmd 'go test -tags integration -count=1 -json ./...' \
  --retirados /ruta/retirados.json --microservicio orders
$PY "$H/postmerge_frontend.py" check --repo /proyecto/front --base /evidencia/base-front.json \
  --retirados /ruta/retirados.json --microservicio front
```

En Go se declaran tests de PRIMER nivel (`paquete::TestX`); sus subtests caen con
ellos. Cada baja bloquea el cierre salvo que:

- la base la midio y el destino ya no la mide;
- su `func TestX(` existe en `base_sha` y NO existe en `source_sha` ni en el
  destino, en el directorio del paquete (`git grep`, ciego a build tags): la
  borro la propia feature. Esconderla tras `//go:build` o un skip no es baja;
- el `review-<id>.md` sellado la nombra. Pasale al revisor la lista junto con el
  briefing: tiene que confirmar que cada test solo certificaba codigo borrado.

En FRONTEND se declara el id EXACTO que mide el runner, tal cual aparece en
`results` de la base: `["angular:<proyecto>"|"node:test", "<ruta del spec>",
"<nombre completo>"]`. El nombre completo de Angular/Vitest incluye los describe;
el de node:test es plano. Cada baja bloquea el cierre salvo que:

- la base la midio (id presente en `results`) y el destino ya no la mide;
- el spec DECLARA ese test en `base_sha` y en `source_sha` y en el destino ya no
  queda ni declarado ni ESCRITO -- o el archivo ya no existe ahi. «Declara» es
  una llamada `it`/`test` (con sus formas `x`/`f` y cualquier modificador:
  `.skip`, `.only`, `.todo`, `.each`, ...) cuyo titulo literal -- entre comillas
  simples, dobles o backticks -- es el titulo hoja. «Escrito» es el mismo titulo
  entre comillas en CUALQUIER parte del archivo, buscado como subcadena. Dejar el
  test con `.skip`/`.todo`/`xit`, renombrar solo el describe, o dejarlo escrito
  tras un wrapper no-op, un alias de `it` o `test.extend`, NO son bajas y
  bloquean;
- el review sellado DECLARA la baja (ver abajo).

El titulo hoja NO se adivina partiendo el nombre completo: sale de la MEDICION de
la base. En Angular es el `title` que reporto Vitest, ya cotejado contra el evento
del reporter; en node:test, el nombre plano. Por eso dos hojas homonimas, o una
que es sufijo de otra (`POST` y `es POST`), no colapsan.

Limites conocidos del reconocimiento en la fuente: titulos armados en runtime
(`it(nombre, ...)`), concatenados (`'a' + 'b'`) o interpolados (`` `x ${y}` ``)
no se reconocen ni como declaracion ni como escritos. Un titulo con comillas
escapadas (`it('no\'s')`, titulo real `no's`) SI se reconoce como declaracion
(el parser lo desescapa), pero la busqueda de «escrito» compara el texto sin
desescapar: si en la fuente queda escapado detras de un wrapper que no registra
el test, la baja pasa (es el mismo hueco general descrito abajo). Un comentario
que conserva la llamada si cuenta. Un `it('')` (titulo vacio) hace que el runner
se niegue a medir el repo: Vitest arma su nombre completo sin el espacio final y
el cotejo nombre completo == ancestros + titulo no se cumple (falla cerrado, no
da verde). La busqueda de «escrito» NO empareja comillas por el archivo:
es subcadena, justo para que un apostrofo suelto anterior (un comentario, una
regex) no la desincronice. El reconocimiento es a proposito generoso:
reconocer de menos en la fuente se leeria como baja legitima. La red de seguridad
es la medicion -- si el test sigue corriendo, su id sigue medido en el destino y
la baja se rechaza --, pero NO cubre un test que ya no corre y cuyo titulo
tampoco quedo escrito de forma reconocible. Ese hueco es el mismo que en Go
(renombrar `func TestX` a `func testX` tambien pasa `git grep`): lo cierra el
review leyendo el diff, no el gate.

La cita del review es una DECLARACION, no una mencion. Se exige, en UNA MISMA
linea que no sea la del sello `Revisado:`, la ruta del spec junto al titulo entre
delimitadores (`'hoja'`, `"hoja"`, `` `hoja` `` o `«hoja»`), o el nombre completo
delimitado, o el id medido entero `proyecto::archivo::nombre`. Buscar hoja y ruta
sueltas por todo el texto dejaba que una hoja corta quedara «citada» por aparecer
dentro de otra palabra (`ok` dentro de «token»), o por el propio sello. Una hoja
vacia no se puede citar: se rechaza. La ruta tiene que estar completa: `<spec>.orig`
o `<spec>x` nombran otro archivo y no cuentan (un prefijo de repo delante si vale).
El sello entero queda fuera, aunque ocupe varias lineas; ademas `gate.py revision`
rechaza saltos de linea y caracteres de control en `--por`, que es por donde se
podia inyectar una cita dentro del sello.

Esa cita prueba UNA cosa: que el revisor escribio la ruta y el titulo juntos en su
informe. No prueba que haya aprobado esa baja en particular. El formato no
distingue una mencion en contra («en `<spec>` el test 'x' ahora espera 'y'»), una
linea de `grep` pegada como evidencia, ni una hoja corta citada dentro de otro
titulo de la misma linea. Quien sella responde por el contenido; el gate solo
impide que la baja pase sin que nadie la haya escrito. Con varias bajas del mismo
spec conviene citar el id entero.

Sobrebloqueos conocidos (bloquean de mas, nunca de menos):

- `it.each`/`test.for`: el nombre medido esta formateado, asi que no es un literal
  del spec y la baja no se puede declarar;
- si dos describe del mismo archivo declaran el mismo titulo y la feature borra
  solo uno, el otro sigue declarado y bloquea;
- si el titulo sobrevive como literal por otro motivo (una asercion, una
  constante), bloquea aunque el test ya no exista.

Mover un test a otro archivo del mismo proyecto, o renombrar el spec, SI es una
baja: el id incluye la ruta, asi que el id viejo desaparece y aparece uno nuevo.
El gate no puede deducir que es el mismo test; el revisor tiene que confirmarlo.

Lo que falte sin declarar sigue bloqueando como antes, ahora con su nombre en el
mensaje (tambien en frontend). Un paquete Go entero solo puede desaparecer si
tenia tests medidos y todos se retiran. La medicion persiste por repo
`retirados`, la ruta y el sha256 del archivo, en Go y en frontend. Pruebas:
`tests/test_retirados.py` (Git y Go reales) y `tests/test_retirados_frontend.py`
(Git, Angular y Node reales).

Un verde del `check` manual NO equivale al del cierre, en Go ni en frontend:

- no exige el review, asi que no verifica ninguna cita;
- compara contra el HEAD del repo, no contra `source_sha` y el tip del destino;
- solo ata el archivo a una feature si le pasas `--feature <id>`, y nunca lo ata
  al mapa de microservicios: `--microservicio` elige la clave, no la valida
  contra el backlog.

Sirve para diagnosticar una integracion a mano. El unico gate es `close`.

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

## Cierre historico (sin base preintegracion medible)

`close --integrated --historico --yes --motivo "<texto>" ...` cierra una feature
YA integrada cuya base preintegracion no se puede medir con el contrato vigente
(por ejemplo: el `package.json`/`scripts.test` de esa epoca no cumple el runner
Angular22/Vitest4 actual, o el tiempo transcurrido hizo que otras features
renombraran/movieran/borraran tests que el gate contaria como desaparecidos sin
poder declararlos bajas de ESTA feature). Diseno completo en
`docs/diseno-arnes-cierre-historico.md` (proyecto ADR, decidido por Alan el
2026-09-26). NO es un atajo general para saltarse la comparacion contra bases:
el camino normal (`--postmerge`) sigue siendo el UNICO para features nuevas.
`--historico` y `--postmerge` son mutuamente excluyentes (todo el mapa se
cierra en un solo modo); `--historico` solo aplica junto con `--integrated
--status done`.

`--historico` exige `--yes` -- igual que `approve-spec`, el agente SOLO lo pasa
tras el SI del usuario en el chat -- y `--motivo "<texto>"` no vacio, sin
saltos de linea ni caracteres de control (misma regla que la firma de
`revision`). Se persiste en el backlog: `cierre_historico: {motivo,
autorizado_por, at}`.

Que garantiza:

- El MISMO runner del cierre normal en CADA repo del mapa (Go: comando fijo con
  evidencia `-exec`; frontend: contrato Angular22/Vitest4+Node22), pero SIN
  comparar contra una base: exige exit real 0, CERO tests en rojo (no hay deuda
  tolerada porque no hay base que la pruebe), cero skip y medicion completa.
  Cualquier rojo o skip bloquea.
- Que los tests que la PROPIA feature agrego -- declarados en `source_sha` y
  ausentes en `base_sha`, identidad `(paquete, TestX)` de primer nivel en Go
  (mismo `git grep` ciego a build tags que usa `retiros._definido`) y
  `(ruta del spec, titulo hoja)` en frontend (mismo parser de declaraciones,
  `retiros.declaraciones`) -- sigan midiendose en el destino.
- Si una feature POSTERIOR los renombro, movio o borro, se declaran en
  `--retirados` con semantica HISTORICA (distinta de la normal, que exige una
  base medida): declarados en `source_sha`, AUSENTES en `base_sha` (la misma
  identidad que usa `tests_agregados_go`/`tests_agregados_front` para decidir
  que agrego la propia feature: sin este chequeo, un test que YA existia antes
  de la feature se podia declarar como baja historica de ella aunque nunca lo
  hubiera agregado -- hallazgo P2 ronda 2, corregido) y ausentes del destino
  (ni medidos ni escritos), citados en el review sellado con el mismo formato
  de cita que las bajas normales (ver seccion "Tests retirados por la feature"
  arriba). En Go se verifica con `func TestX(` de la fuente, de la base y del
  destino (`retiros.verificar_historico`); en frontend, sin medicion de
  `source_sha` disponible (el runner no puede correr codigo de hace semanas
  con el contrato vigente), el titulo hoja se resuelve probando SUFIJOS del
  nombre completo declarado contra lo que el spec DECLARA en `source_sha`
  (`retiros.sufijos_declarados`/`retiros.verificar_frontend_historico`): debe
  resultar EXACTAMENTE un sufijo declarado, o bloquea por ambiguo, y ese mismo
  titulo hoja no puede estar ya declarado en `base_sha`.
- Si el delta `base_sha..source_sha` de un repo toca codigo que no son tests y
  la feature no agrego NINGUN test ahi, bloquea nombrando el repo (la garantia
  de tests vivos quedaria vacia: no hay nada que comprobar).
- Siguen aplicando TODAS las demas reglas del cierre integrado: spec aprobado y
  fresco, review sellado en el contexto multi-repo vigente, verify verde del
  contexto vigente, leccion existente, registro multi-repo valido (fuente
  ancestro del destino, arboles limpios, rutas protegidas). `mediciones_destino`
  persiste, por repo, `modo: "historico"`, el runner, los hashes, los
  resultados, los tests de la feature encontrados (`tests_agregados`) y las
  bajas historicas -- misma forma que el cierre normal, para que PRD/SDD y el
  vault no se rompan.

Que NO garantiza:

- No mide ni reconstruye la base preintegracion: no hay comparacion de deuda ni
  deteccion de "rojos nuevos" contra un antes real, porque ese antes no se
  puede correr con el contrato vigente. Un rojo o skip en el destino bloquea
  sin distinguir si ya estaba roto antes de la feature (no hay con que
  distinguirlo).
- La resolucion de titulo hoja por sufijos en frontend es mas debil que la
  medicion real (el cierre normal usa el `title` que reporto Vitest, cotejado
  contra el evento del reporter): si el nombre completo tiene mas de un sufijo
  que calza con un titulo declarado, bloquea por ambiguo en vez de adivinar.
  Los mismos huecos de reconocimiento de `retiros.declaraciones`/`escrito`
  (titulos armados en runtime, concatenados o interpolados) aplican igual.
- No reemplaza el registro/aislamiento multi-repo ni el resto de gates: sigue
  siendo responsabilidad del leader declarar el mapa completo y del reviewer
  confirmar que el delta satisface los AC y que cada baja historica citada es
  legitima.
- La exclusividad de `--postmerge` para features NUEVAS es un compromiso de
  PROCESO (correccion ronda 1, revision independiente 2026-09-26), igual que
  `--yes` de `approve-spec`, NO una restriccion tecnica: el gate no verifica
  antiguedad de `source_sha` ni un intento previo (fallido) de medir la base.
  Nada impide tecnicamente invocar `--historico` sobre una feature nueva con
  base perfectamente medible; quien autoriza con `--yes --motivo` responde por
  esa decision. El mensaje de `gate.py close` cuando falta `--yes` lo deja
  explicito, y `tests/test_cierre_historico.py::test_mensaje_historico_advierte_que_es_barrera_de_proceso`
  lo fija como regresion.

Pruebas: `tests/test_cierre_historico.py` (Git, Go y Angular22/Vitest4+node:test
reales; requiere `HARNESS_TEST_FRONTEND_MODULES` como el resto del contrato
frontend de esta seccion).


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
- La base graba el sha256 del propio runner (`toolchain.runner_sha256`). Cambiar
  `postmerge_frontend.py` o sus reporters deja STALE toda base anterior: hay que
  volver a medirla con HEAD en `base_sha`, antes de integrar. No se migra ni se
  reescribe una base vieja para que pase.

`HARNESS_TEST_FRONTEND_MODULES` debe apuntar a node_modules YA instalado con
estas versiones para `python -m unittest discover -s tests`; no hay skips ni
instalaciones de rescate. Ejecutar con PATH que fije Node/Go/Git/Python, en dos
interpretes y rutas simuladas `.hermes/skills/...` y `.claude/skills/...`.
`HARNESS_TEST_FRONTEND_LOGS` conserva raw de fixtures fuera de sus temporales.

Leccion reusable: contrastar inicio/final por archivo y caso con el inventario
independiente; no contar solo un resumen JSON. Forzar allowOnly ANTES de
coleccion Vitest, porque despues normaliza only a run. Probar la decision REAL
del cierre, ademas del parser, y conservar el raw de fallos antes de limpiar.
