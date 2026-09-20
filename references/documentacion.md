# Documentacion PRD / SDD

## Objetivo

Los dos documentos viven en `docs/` y tienen dos capas:

- el **cuerpo manual**: la prosa de producto (PRD) o de arquitectura (SDD). Es
  del USUARIO. El rol producto la redacta como borrador y el usuario la aprueba;
- el **bloque generado** `harness-flow:features`, que `documentacion.py sync`
  mantiene desde las features `status=done`. Deterministico y host-neutral.

Ningun agente escribe `docs/prd/**` a mano: es ruta protegida y `gate.py check`
lo marca en rojo.

## Archivos

| Archivo | Cuerpo manual | Bloque generado |
| --- | --- | --- |
| `docs/borrador-prd.md` | borrador del PRD (sin proteger) | nunca |
| `docs/borrador-sdd.md` | borrador del SDD (sin proteger) | nunca |
| `docs/prd/PRD-master.md` | PRD aprobado (protegido) | features cerradas y sus AC |
| `docs/sdd.md` | SDD aprobado | microservicios, rama, merge, evidencia, review, progreso archivado, Jira/Confluence |

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
en 10 o mas, y un producto nuevo son varios PRDs anidados. En este arnes cada
"Feature candidata" es uno de esos PRDs anidados: entra al backlog y su spec,
con AC, cuenta su propia historia.

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
| `## Features candidatas` | los PRDs anidados: `- F-n: nombre: resultado (cumple O1)` | al menos una `F-n` |

`Despues:`/`Después:`, `**Antes:**` en negrita y la etiqueta sola con el parrafo
debajo valen igual. Un bloque cercado con lenguaje (` ```go `, ` ```sql `,
` ```ts `...) en cualquier parte es codigo final y se niega; ` ``` ` pelado o
` ```text ` es pseudo-codigo y pasa. El validador mide estructura, no calidad:
que la historia convenza lo decide el usuario en el ritual.

- SDD: Contexto, Componentes, Datos e integraciones, Decisiones, Riesgos, cada
  una con contenido. El flujo, los datos y el pseudo-codigo de cada cambio ya
  viven en el PRD; el SDD fija la arquitectura que los sostiene.

`aprobar --yes` es el mismo ritual del spec: se muestra el borrador en el chat,
se pregunta, y solo con el SI explicito se corre. Se niega, sin escribir nada:

- sin `--yes`;
- con una seccion ausente o que solo tiene guia (nombra cual), o una parte del
  PRD sin lo que exige la tabla de arriba (Alcance, Hoy/Despues, Antes/Despues,
  O-n/NO-n, F-n);
- con codigo final en el PRD (un bloque cercado con lenguaje);
- si el borrador trae el bloque `harness-flow:features` (lo mantiene el sync);
- si el destino tiene marcadores malformados (no se pisa a ciegas);
- para el PRD, si hay features multi-repo **registradas** abiertas: su registro
  fijo los bytes manuales del PRD y nada lo reautoriza, ni re-registrar. Se
  cierran primero, o se aprueba el PRD antes de registrar.

Cuando aprueba: pone `Estado: approved` y la linea `Aprobado: <quien> · <fecha>
· sellado por producto.py aprobar --yes` en el cuerpo, lo copia al destino
conservando el bloque generado que ya tuviera (bytes exactos), guarda el sello
en `documentos.<doc>` de `harness/feature_list.json` (autor, fecha, origen,
destino, fingerprint del destino y sha256 del borrador), anota la bitacora y
deja el borrador tambien como `approved`. Todo dentro de la transaccion de
cierre local: un fallo restaura backlog, destino y bitacora a sus bytes previos.
Para el PRD imprime ademas el `add.py --name "<nombre>" --prd
docs/prd/PRD-master.md` de cada `F-n`.

## El sello y el gate de rutas protegidas

`gate.py check` acepta `docs/prd/PRD-master.md` distinto de HEAD por dos vias, y
solo dos:

1. la de siempre: los bytes manuales son identicos a HEAD y solo cambio el bloque
   generado bien formado (o es su primera insercion sobre el prefijo por defecto);
2. el sello: los bytes actuales dan el mismo fingerprint que guardo `aprobar
   --yes` en `documentos.prd`, o son su primera insercion del bloque generado.

El sello no autoriza otros archivos bajo `docs/prd/`, ni una edicion posterior
del cuerpo (vuelve el rojo), ni un fingerprint que no corresponda. El usuario
commitea el PRD cuando quiere; a partir de ahi manda HEAD y el sello queda como
historia. El agente no lo commitea. El registro multi-repo (`multi_repo_protected`)
mantiene su contrato aparte y no lee el sello.

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
