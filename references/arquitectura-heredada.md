# Arquitectura heredada: el trinquete

Para un proyecto que adopta el arnes con mucho codigo ya escrito. Hay dos formas
malas de tratarlo:

- **El muro.** La Feature #0 bloquea todo el backlog hasta reestructurar todo.
  Garantiza el resultado, detiene el negocio y es un refactor masivo sin tests.
- **Lo progresivo sin medir.** Lo existente no se toca y lo nuevo "nace bien".
  Nada lo comprueba: lo heredado no converge y el codigo nuevo puede caer fuera
  de la norma sin que el verificador lo note.

El trinquete es la tercera: se mide cuanto codigo vive fuera de la norma, esa
medida se sella como base y desde ahi solo puede bajar. Es el mismo criterio de
`postmerge_medido.py` para los tests: fallan los rojos nuevos, no la deuda.

## Que es "heredado"

Lo declara cada stack en `assets/stacks/<id>/manifest.json`, bloque `layout`:

| Clave | Significado |
| --- | --- |
| `codigo` | Patrones de las rutas que son codigo bajo la norma |
| `excluir` | Lo que no cuenta (tests, `vendor/`) |
| `normalizado` | Rutas que ya siguen la norma del stack |
| `unidad_tras` | Opcional: la unidad es el modulo que sigue a ese segmento (`features`) |

Un archivo en `codigo`, fuera de `excluir` y fuera de `normalizado` es heredado.
Se agrupan en **unidades**: el directorio del archivo, o el modulo si el stack
declara `unidad_tras`. En los patrones `*` no cruza `/` y `**/` cruza cero o mas
directorios. Un stack sin `layout` no se mide, y los comandos lo dicen.

Los diez stacks del catalogo declaran su `layout`, y la plantilla oficial de cada
uno mide cero codigo heredado: la plantilla ES la norma, asi que un layout que la
marcara como heredada estaria mal. Un stack nuevo necesita su bloque `layout`
para entrar al trinquete; sin el, sus repos quedan fuera de la base.

## Adoptarlo

```bash
$PY "$H/arquitectura.py" inventario --detalle   # que hay fuera de la norma
$PY "$H/arquitectura.py" adoptar --yes          # solo con el SI del usuario
```

`adoptar` sella la base en `harness/arquitectura-base.json`, quita la #0 de los
`requiere` de las demas features y, si la #0 seguia abierta, la deja como una
feature de normalizacion mas: su trabajo no se pierde y ya no bloquea a nadie.
Con la base presente, `estado.py` deja de crear la #0.

Sellar la base es aceptar como deuda todo lo que hoy esta fuera de la norma. Por
eso lleva `--yes`: MUESTRA el inventario, PREGUNTA, y solo con el SI se sella.

## Que exige despues

| Regla | Donde se aplica |
| --- | --- |
| Ninguna unidad heredada gana archivos y no nacen unidades heredadas | `gate.py close` |
| Un archivo heredado que la feature cambia en mas de `rules.arquitectura_umbral_lineas` lineas (50) sale de lo heredado en esa feature | `gate.py close` |
| Las violaciones del verificador que no estaban en la base fallan | `gate.py close` |
| Tras `rules.arquitectura_cuota` (3) features de negocio aprobadas, hay que cerrar una de normalizacion mientras quede algo heredado | `gate.py approve-spec` |
| Una feature de normalizacion que no vacia ninguna unidad ni baja las violaciones no cierra | `gate.py close` |

Cada feature se mide **contra su propio commit base**, no contra la base global.
Si otra feature normalizo una unidad mientras esta seguia abierta, su rama aun
trae esos archivos: comparar contra la base global daria un rojo falso.

`bug` y `task` no gastan cuota ni se frenan. `arquitectura_cuota: 0` la apaga;
cambiar la cuota o el umbral es decision del usuario.

## El dia a dia

```bash
$PY "$H/arquitectura.py" check --feature <id>   # lo mismo que medira close
$PY "$H/arquitectura.py" siguiente              # unidades heredadas, las mas tocadas primero
$PY "$H/add.py" --kind normalizacion --name "normalizar <unidad>"
$PY "$H/arquitectura.py" check --ajustar        # aprieta la base con lo ya normalizado
```

Una feature de normalizacion es una rebanada como las demas: spec, tests de
caracterizacion en la costura publica ANTES de mover codigo, y Expand-Contract
si el cambio es ancho. Normalizar es arquitectura: no se reescriben los specs de
las features ya cerradas.

`estado.py` muestra el avance (`arquitectura: 268 unidades heredadas ...; cuota 2/3`).
`gate.py check` avisa si un checkout trae mas codigo heredado que la base; es un
aviso porque un checkout viejo no es una violacion.

## Lo que ya estaba en curso y los repos sin arbol registrado

- **Features en curso al adoptar.** `adoptar` anota las que estaban `in_progress`,
  `review` o `blocked` (`arquitectura.exentas_en_curso` en el backlog) y no les
  cambia la regla a mitad de camino: cierran sin medirse. Al cerrar cada una, la
  base absorbe lo heredado que haya agregado y la bitacora lo registra. Desde
  ahi ya no esta exenta nadie mas.
- **Repos donde la feature no registra arbol.** Si la feature solo declara el
  worktree de la raiz pero el proyecto tiene mas repos en la base, `close` mide
  esos repos por su checkout contra la base. Ahi no hay diff de la feature, asi
  que no se comprueba el umbral de lineas, y el cierre lo avisa. Para medirlos
  con exactitud, registra los arboles con `worktree.py register`
  (`references/multirepo.md`).

## Casos limite

- **Codigo que no puede seguir la norma** (generado, de un proveedor):
  `arquitectura.py eximir --repo <r> --unidad <u> --motivo '<por que>' --yes`.
- **La base nunca sube sola.** `base --yes` se niega si re-sellar la aflojaria;
  admitirlo es `base --ampliar --motivo '<por que>' --yes`.
- **Sin commit base legible** el gate falla en vez de pasar: no puede saber que
  agrego la feature.
- **Repos fuera de la raiz**: las raices salen de `harness/grafos.json`; la clave
  de cada repo en la base es su ruta relativa a la raiz, o absoluta si vive fuera.
