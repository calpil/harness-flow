# Hallazgos: enmienda antes que ficha

Léelo cuando encuentres algo en el código mientras trabajas en otra cosa: en un
spec, al implementar, en un review o al cerrar. También cuando `add.py` se
niegue a crear una ficha.

## La regla

Un hallazgo del código **no abre una ficha**. Cada ficha paga spec, lista de
tests, review, verify y cierre. Una constante repetida, un tipo sin un valor o
un test lento no valen ese costo: se resuelven dentro de una feature que ya
existe.

Una ficha nueva la decide el usuario, y solo cuando tiene **peso propio**:

- un comportamiento nuevo que ve el usuario del producto, o
- un riesgo de plata, datos o seguridad que no puede esperar a otra feature.

## A dónde va un hallazgo

Recorre la lista en orden y quédate con el primero que aplique.

| # | Caso | Qué haces |
| --- | --- | --- |
| 1 | Cae en la feature en curso y no cambia ningún AC | Lo arreglas en su rama y lo citas en la evidencia |
| 2 | Cae en la feature en curso y cambia un AC | Enmienda: `templates/enmienda.md` y `gate.py enmienda --yes`, con el SÍ del usuario |
| 3 | Cae en otra feature abierta, con el spec sin sellar | `hallazgo.py anotar --feature <id>`; quien escribe ese spec lo pone como AC o en el plan |
| 4 | Cae en otra feature abierta, con el spec sellado | `hallazgo.py anotar --feature <id>`; al implementarla entra como enmienda o se arregla en la rama |
| 5 | Ninguna feature abierta lo cubre | `hallazgo.py anotar` sin `--feature`: queda en el proyecto |
| 6 | Tiene peso propio | Se lo muestras al usuario. Con su SÍ: `add.py --name "..." --yes --peso "<por qué es ficha>"` |

"Cae en una feature" quiere decir que esa feature toca ese código o ese
comportamiento. Una feature cerrada no recibe hallazgos.

Los cortes de una feature grande siguen la misma regla. Partir una feature en
varias fichas es una propuesta al usuario, no un alta.

### Cuando le preguntas al usuario

La primera opción del formulario es el destino sin ficha: la enmienda o
anotarlo. La ficha es otra opción. No la recomiendes si el hallazgo cabe en una
feature abierta. Una pregunta que solo ofrece "ficha aparte: sí o no" no le da
al usuario la salida barata.

## Comandos

```bash
"$PY" "$H/hallazgo.py" anotar --feature <id> --texto "<una linea>" [--origen "review de la #191"]
"$PY" "$H/hallazgo.py" anotar --texto "<una linea>" [--microservicio <repo>]   # al proyecto
"$PY" "$H/hallazgo.py" list [--feature <id>] [--todos]
"$PY" "$H/hallazgo.py" mover --id H-3 --feature <id>      # o --sin-feature
"$PY" "$H/hallazgo.py" resolver --id H-3 --como "E-1 de la #180"
```

- `anotar` no pide `--yes`: anotar no gasta nada y no compromete trabajo.
- El texto va en una línea de hasta 400 caracteres. El detalle va en el spec o
  en la propuesta de enmienda.
- `resolver --como` dice dónde quedó: `AC-3`, `E-1 de la #180`, un commit, o
  `descartado: <motivo>`.

Los hallazgos viven en `hallazgos` de `harness/feature_list.json`, con id `H-n`.

## Quién se entera

| Dónde | Qué muestra |
| --- | --- |
| `contexto.py brief --feature <id>` | Los hallazgos de esa feature y los del proyecto que tocan sus repos, con el comando para resolverlos o traerlos |
| `estado.py` | Una línea con cuántos hay abiertos y dónde |
| `gate.py approve-spec` | Avisa los que la feature tiene anotados |
| `gate.py close --status done` | **Se niega** mientras la feature tenga hallazgos abiertos |

`close` no pierde un hallazgo: o se resolvió, o pasó a otra feature abierta, o
pasó al proyecto con `mover --sin-feature`.

El revisor no los recibe: juzga el spec contra el código.

## Cuándo `add.py` crea una ficha

| Caso | ¿Pide `--yes`? |
| --- | --- |
| Primera ficha de una candidata `F-n` del PRD | No: el usuario aprobó el PRD |
| `--kind normalizacion` con el trinquete adoptado | No: el usuario adoptó el trinquete |
| Otra ficha de una candidata que ya tiene una | Sí: es partir la feature |
| Cualquier otra feature, bug o task | Sí |

Sin `--yes`, `add.py` se niega, repite la regla y lista las features abiertas
donde el hallazgo puede caber: las que nombra `--requiere`, las que comparten
repo y, si no hay ninguna, todas las abiertas.

`--yes` va con `--peso "<por qué es ficha y no enmienda>"`: una línea con el
comportamiento nuevo o el riesgo que la justifica, o con que el usuario la
pidió. Queda escrito en la ficha (`peso`). Si no hay qué poner, no es una
ficha.

`--yes` es una barrera de proceso, igual que la de `approve-spec`: el agente lo
pasa solo cuando el usuario pidió o aprobó esa ficha.

## Observaciones de un review

Los hallazgos menores e informativos de un review van a `## Observaciones` y no
bajan el veredicto. Tampoco abren fichas. La sesión principal decide, antes de
cerrar:

- los que son de la feature y no cambian un AC, se arreglan en la rama;
- los que son de otra feature abierta, se anotan ahí;
- los demás, se anotan en el proyecto.

## Rojos nuevos tras un merge

Un rojo nuevo después de integrar es una regresión. Anótalo con `hallazgo.py
anotar` y muéstraselo al usuario: tiene peso, y la ficha de bug la decide él.
No bajes la aserción que lo detectó.

## El caso que originó la regla

ADR, 12 de noviembre de 2026. En cuatro horas y media el agente dio de alta 16
fichas (#190 a #205). Salieron de hallazgos de specs y reviews: una constante
repetida, un tipo sin un valor, un test lento, los cortes de una feature sin
arrancar. El agente preguntó por formulario, pero cada pregunta ofrecía solo la
ficha aparte, y la recomendaba. El usuario retiró siete a mano, con la nota "no
es ficha aparte; entra como enmienda".

Lo que fallaba en el arnés:

1. Ningún texto decía qué hacer con un hallazgo.
2. No había dónde dejar un hallazgo que no fuera una ficha.
3. `add.py` era el único ritual sin `--yes`, y no pedía un motivo.

## Tests

[`tests/test_hallazgos.py`](../tests/test_hallazgos.py): alta de fichas,
anotar, mover y resolver, brief, arranque de sesión, `approve-spec` y `close`.
