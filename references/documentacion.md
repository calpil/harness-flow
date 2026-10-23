# Documentacion PRD / SDD

## Objetivo

Los dos documentos viven en `docs/` y tienen dos capas:

- el **cuerpo manual**: la prosa de producto (PRD) o de arquitectura (SDD). Es
  del USUARIO. El rol producto la redacta como borrador y el usuario la aprueba;
- el **bloque generado** `harness-flow:features`, que `documentacion.py sync`
  mantiene desde las features `status=done`. Deterministico y host-neutral.

Ningun agente escribe `docs/prd/**` ni `docs/sdd.md` a mano: son rutas
protegidas y `gate.py check` las marca en rojo.

## Archivos

| Archivo | Cuerpo manual | Bloque generado |
| --- | --- | --- |
| `docs/borrador-prd.md` | borrador del PRD (sin proteger) | nunca |
| `docs/borrador-sdd.md` | borrador del SDD (sin proteger) | nunca |
| `docs/prd/PRD-master.md` | PRD aprobado (protegido) | features cerradas, su candidata `F-n` y sus AC |
| `docs/sdd.md` | SDD aprobado (protegido) | microservicios, rama, merge, evidencia, review, progreso archivado, Jira/Confluence |

## Rol producto: PRD inicial y SDD de arquitectura

Corre ANTES de que existan features, o cuando el usuario pide cambiar el
documento. `estado.py` muestra en que paso esta cada uno (`prd:` / `sdd:`).

```bash
$PY "$H/producto.py" borrador --doc prd|sdd        # crea docs/borrador-<doc>.md
$PY "$H/producto.py" aprobar  --doc prd|sdd --yes  # solo tras el SI del usuario
$PY "$H/producto.py" estado                        # lo mismo que muestra estado.py
```

`borrador` copia `templates/prd.md` o `templates/sdd.md` con el nombre del
proyecto, o, si el destino ya tiene un cuerpo manual del usuario, lo reabre como
borrador (`Estado: draft`, sin el bloque generado ni el sello viejo). El
encabezado por defecto que inventa el generador no cuenta como cuerpo manual.
Si el borrador ya existe, no lo toca.

El agente rellena el borrador con las tools de archivo. Las guias `<!-- -->`
de la plantilla se reemplazan o se borran.

### Anatomia del PRD

Sigue «Escribe tu maldito PRD»: un PRD cuenta una historia y raya la cancha de
lo que hay que construir. **Contiene** la historia (antes y despues), hoy ->
manana, las tablas y entidades a tocar, pseudo-codigo y la explicacion de los
cambios. **Nunca contiene** codigo final, la implementacion exacta, pantallas
terminadas ni configuracion: si el razonamiento esta bien en papel, el codigo
es la parte facil; si esta mal, ningun codigo lo arregla. El tamano lo decide
el cambio: un ajuste cabe en una pagina, una funcionalidad en 3-8, una grande
en 10 o mas. Un producto grande no se parte en otros archivos PRD: el ritual
solo sella `docs/prd/PRD-master.md`. Cada "Feature candidata" es una linea
`F-n` de ese maestro; entra al backlog y su spec, con AC, cuenta la historia
de esa candidata.

Secciones, en este orden, y lo que `aprobar` exige de cada una:

| Parte | Que lleva | Exige |
| --- | --- | --- |
| Encabezado | `Estado`, `Dueño`, `Creado`, `Alcance` (que toca y que NO toca) | `Alcance:` con contenido |
| `## Resumen` | el antes y el despues en dos lineas | `Hoy:` y `Despues:` con contenido |
| `## La historia` | quien es el usuario, como lo usa, cual es el dolor, que quiere vivir; con nombre y momento, sin tecnicismos | `Antes:` y `Despues:` con contenido |
| `## Objetivos y no-objetivos` | con nombre, para citarlos ("cumple O2"); los no-objetivos frenan el "ya que estamos" | al menos un `- O1:` y un `- NO1:` |
| `## Como funciona hoy y como va a funcionar` | el flujo dibujado dos veces, reusando lo que existe | contenido |
| `## Los datos` | disparador, entidades y tablas tocadas, interruptor, candado | contenido |
| `## Pseudo-codigo: el acuerdo` | que lo dispara, que lo frena, que promete; en palabras | contenido |
| `## Features candidatas` | una linea por candidata: `- F-n: nombre: resultado (cumple O1)` | al menos una `F-n` |

`Despues:`/`Después:`, `**Antes:**` en negrita y la etiqueta sola con el parrafo
debajo valen igual. Un titulo `##` con tilde o mayusculas es la misma seccion
(`## Pseudo-código` cuenta como `## Pseudo-codigo`). Un bloque cercado con lenguaje (` ```go `, ` ```sql `,
` ```ts `...) en cualquier parte es codigo final y se niega; ` ``` ` pelado o
` ```text ` es pseudo-codigo y pasa. El validador mide estructura, no calidad:
que la historia convenza lo decide el usuario en el ritual.

- SDD: Contexto, Componentes, Datos e integraciones, Decisiones, Riesgos, cada
  una con contenido, y al menos una decision con nombre (`- D1: ...`). Cada
  `D-n` nombra la opcion descartada (`Descartada: cache, porque ...`;
  `Descartado:` vale igual, con o sin tilde). Sin eso `aprobar` se niega: una
  decision sin alternativa no es una decision. El spec de cada feature cita
  las que aplica. El flujo, los datos y el pseudo-codigo de cada cambio ya
  viven en el PRD; el SDD fija la arquitectura que los sostiene.

`aprobar --yes` es el mismo ritual del spec: se muestra el borrador en el chat,
se pregunta, y solo con el SI explicito se corre. Se niega, sin escribir nada:

- sin `--yes`;
- con una seccion ausente o que solo tiene guia (nombra cual), o una parte del
  PRD sin lo que exige la tabla de arriba (Alcance, Hoy/Despues, Antes/Despues,
  O-n/NO-n, F-n), o un SDD sin ninguna `D-n`;
- con codigo final en el PRD (un bloque cercado con lenguaje);
- si el borrador trae el bloque `harness-flow:features` (lo mantiene el sync);
- si el destino tiene marcadores malformados (no se pisa a ciegas);
- si hay features multi-repo **registradas** abiertas cuyo registro fijo los
  bytes de ese destino (era ruta protegida al registrar): nada los reautoriza,
  ni re-registrar. Se cierran primero, o se aprueba el documento antes de
  registrar.

Cuando aprueba: pone `Estado: approved` y la linea `Aprobado: <quien> · <fecha>
· sellado por producto.py aprobar --yes` en el cuerpo, lo copia al destino
conservando el bloque generado que ya tuviera (bytes exactos), guarda el sello
en `documentos.<doc>` de `harness/feature_list.json` (autor, fecha, origen,
destino, fingerprint del destino y sha256 del borrador), anota la bitacora y
deja el borrador tambien como `approved`. Todo dentro de la transaccion de
cierre local: un fallo restaura backlog, destino y bitacora a sus bytes previos.
Para el PRD imprime ademas el `add.py --name "<nombre>" --prd
docs/prd/PRD-master.md --candidata F-n` de cada `F-n`. Si hay features abiertas
con un spec aprobado contra la version anterior del documento, las lista.

## El sello y el gate de rutas protegidas

`gate.py check` acepta `docs/prd/PRD-master.md` o `docs/sdd.md` distinto de HEAD
por dos vias, y solo dos:

1. la de siempre: los bytes manuales son identicos a HEAD y solo cambio el bloque
   generado bien formado (o es su primera insercion sobre el encabezado que
   inventa `documentacion.py`, `# PRD maestro` o `# SDD`);
2. el sello: los bytes actuales dan el mismo fingerprint que guardo `aprobar
   --yes` en `documentos.prd|sdd`, o son su primera insercion del bloque generado.

El sello no autoriza otros archivos bajo `docs/prd/`, ni una edicion posterior
del cuerpo (vuelve el rojo), ni un fingerprint que no corresponda. El usuario
commitea el documento cuando quiere; a partir de ahi manda HEAD y el sello queda
como historia. El agente no lo commitea. El registro multi-repo
(`multi_repo_protected`) mantiene su contrato aparte y no lee el sello.

`docs/sdd.md` entro a `rutas_protegidas` por defecto despues que el PRD. Un
backlog creado antes conserva su lista (un registro multi-repo abierto fijo esas
rutas, asi que no se migra sola): `gate.py check` avisa con `[i]` y el usuario
lo agrega cuando no haya registros abiertos.

## El PRD/SDD en el resto del flujo

El rol producto los escribe y el cierre les agrega el bloque generado. Entre
medio, cada rol los usa asi:

| Paso | Que hace con el PRD/SDD |
| --- | --- |
| `init.py`, `estado.py` | mandan al rol producto antes que a `add.py` si falta un documento exigido; `estado.py` muestra `candidatas:` (que `F-n` tiene feature y en que estado) |
| `add.py --candidata F-n` | valida que la `F-n` exista en el PRD, la guarda en la feature (`prd_candidata`) y crea el spec desde el bloque de `templates/spec.md` con el PRD y la linea de la candidata en el Contexto |
| `contexto.py brief` | seccion `producto`: estado de cada documento, la linea `F-n` de la feature, objetivos `O-n`/`NO-n` y decisiones `D-n`. El briefing del revisor la omite: el revisor juzga spec contra codigo |
| `gate.py approve-spec` | con `require_docs_al_dia`, se niega sin los documentos exigidos; avisa si el spec no cita `O-n`/`D-n` o cita uno inexistente; guarda en `docs_base` la huella del cuerpo de cada documento |
| `estado.py`, `gate.py check`, brief, `close` | avisan cuando el PRD/SDD cambio desde que se aprobo el spec de una feature abierta |
| `close --status done` | el sync escribe la candidata `F-n` de cada feature cerrada en el bloque del PRD |

### `require_docs_al_dia`

| Valor | Exige a `approve-spec` |
| --- | --- |
| `["prd", "sdd"]` (por defecto en un backlog nuevo) | PRD y SDD |
| `true` (lo que escribian los backlogs viejos, cuando la regla no hacia nada) | solo el PRD |
| `["prd"]` / `["sdd"]` | ese documento |
| `false` | nada |

Un documento cuenta si su destino tiene cuerpo manual y ese cuerpo esta
probado: sello vigente de `aprobar --yes`, o commit del usuario sin cambios
encima. Un PRD que un agente puso ahi sin el ritual no cuenta. Sin repo git
no hay commit que medir, asi que el sello es la unica prueba para `approve-spec`,
`estado.py` y `add.py`. `gate.py check` ademas acepta los bytes que un registro
multi-repo ya fijo: sin git, ese registro es el commit de esas rutas. Un cuerpo
escrito a mano y sin registrar se reabre con `producto.py borrador` y se sella. Solo se exige a
`kind: feature`; `bug` y `task` no nacen de un PRD. Un valor que la regla no
entiende hace fallar `approve-spec` y `gate.py check` en vez de apagarse. Apagarla
es decision del usuario: el agente no edita `rules` para destrabar un spec.

### Citas y cambios despues del spec

El Contexto del spec cita lo que la feature cumple (`cumple: O1`) y las
decisiones que aplica (`decisiones que aplica: D2`); `cumple: ninguno` y
`decisiones que aplica: ninguna` lo dicen a proposito. `approve-spec` solo
avisa: el validador mide estructura y la cita correcta la decide el usuario.

La huella de `docs_base` ignora el bloque generado (cambia en cada cierre) y las
lineas `Estado:`/`Aprobado:` (re-aprobar el mismo texto no es un cambio de
producto). Si el cuerpo cambia, el spec habla de otro documento: el leader lo
revisa y, si un AC deja de valer, es una enmienda; si sigue valiendo, se
re-aprueba con el SI del usuario, lo que actualiza la huella.

`estado.py` distingue: sin documento, borrador sin aprobar, aprobado (autor y
fecha), borrador cambiado despues de aprobar (re-aprobar), destino cambiado
despues del sello, y manual del usuario sin sello (un PRD escrito a mano, valido
igual: `producto.py borrador` lo reabre si hace falta cambiarlo).

## Sync del bloque generado

```bash
$PY "$H/documentacion.py" sync
```

`gate.py close --status done` lo ejecuta dentro del cierre provisional. Cualquier
fallo local restaura backlog, documentos, progreso, historia y outbox a sus bytes
previos; no genera documentos nuevos para aparentar rollback. Si Git ya mergeo,
se conserva y se informa. Atlassian puede tener efectos remotos parciales: la
restauracion local no los deshace; reconciliar antes de reintentar. Se requiere
un escritor exclusivo; no hay garantia durable ante SIGKILL/corte electrico.

### Contrato de edicion

El usuario conserva todo contenido manual fuera del bloque generado:

```markdown
<!-- harness-flow:features:start -->
...
<!-- harness-flow:features:end -->
```

El script crea el bloque si falta por completo, reemplaza solo ese bloque si
existe y conserva bytes manuales exactos (incluidos CRLF/espacios). Un marcador
parcial, duplicado o invertido bloquea; no se repara silenciosamente. El gate y
el registro multi-repo comparten esa excepcion exacta mediante `bloques.py`.
No toca `.env`, `docs/constitution.md` ni secciones manuales del PRD.

## Relacion con Confluence

`atlassian.py push --feature <id>` embebe `docs/prd/PRD-master.md` y `docs/sdd.md`
en la pagina Confluence de la feature cuando esos archivos existen (cuerpo
manual y bloque generado). Sin token, el mismo cuerpo queda como intent
`confluence-upsert` en `harness/outbox/`.
