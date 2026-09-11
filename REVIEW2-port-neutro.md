# Revision adversarial #2: port neutro de harness-flow

Rama `feat/port-neutro` en `/Users/alan/.hermes/worktrees/harness-flow-port-neutro`.
Revisor: subagente aislado. Segunda vuelta sobre `REVIEW-port-neutro.md`.
No confie en la palabra del autor: todo lo de abajo esta ejecutado.

Suite: `HOME=/Users/alan python3 -m unittest discover -s tests` -> **31 tests OK**.
Tambien con un venv como runner (`/tmp/v/bin/python -m unittest discover -s tests`)
-> **31 OK** (el falso verde H-06 de la vuelta 1 ya no aparece).

Veredicto: **changes_requested** (0 bloqueantes nuevos, 2 importantes, 4 menores).

---

## Los 4 bloqueantes, uno por uno

### B1 glob injection -> **RESUELTO**

`scripts/leccion.py:132-141` (`nombre_valido`) + guardia en `scripts/leccion.py:146-147`.
Probado contra un arbol real con skill plana, skill con categoria intermedia y
nombre con guiones:

```sh
mkdir -p /tmp/globtest2/root/cat/realskill /tmp/globtest2/root/cat/mi-skill-con-guiones /tmp/globtest2/root/plana
cd <worktree>/scripts
for n in '*' '[a-z]*' '?ealskill' 'real*' '{realskill,x}' 'realskill' \
         'mi-skill-con-guiones' 'plana' '..' '.' 'real[s]kill' 'cat/realskill'; do
  HARNESS_SKILLS_DIR=/tmp/globtest2/root python3 -c 'import sys,leccion;print(leccion.buscar(sys.argv[1]))' "$n"
done
```

Resultado: todos los comodines -> `None`; `realskill`, `mi-skill-con-guiones` y
`plana` siguen resolviendo a su `SKILL.md`. `{a,b}` no es glob de `pathlib` y
ademas contiene caracteres que no casan con ningun nombre real, asi que no
resuelve. `cat/realskill` (separador) -> `None`, correcto segun el contrato.
No encontre metacaracter olvidado: `pathlib.Path.glob` solo interpreta
`* ? [ ]` (y `**`, cubierto por `*`), y los tres estan en `prohibidos`.
El test `tests/test_leccion.py:134-141` cubre la regresion.

### B2 regresion de perfiles Hermes -> **RESUELTO**

`scripts/leccion.py:107-110`: en host `hermes`, `_raiz_propia()` va primero.
Probado con homes simulados y `env -i` (no con mocks):

```sh
T=$(mktemp -d); mkdir -p $T/.hermes/skills/tdd $T/.hermes/profiles/trabajo/skills/tdd
# 'DEFAULT-PROFILE' en el default, 'PERFIL-TRABAJO' en el perfil,
# copia de la skill instalada bajo cada uno
env -i PATH=/usr/bin:/bin HOME=$T HARNESS_HOST=hermes python3 \
  $T/.hermes/profiles/trabajo/skills/software-development/harness-flow/scripts/leccion.py ver tdd
```

-> `PERFIL-TRABAJO` (antes daba `DEFAULT-PROFILE`).
`... donde` desde el perfil lista `profiles/trabajo/skills` y luego `.hermes/skills`.
Caso default: la copia instalada en `$T/.hermes/skills/...` -> `DEFAULT-PROFILE`
y `donde` lista solo `.hermes/skills`. Sin autodeteccion (`env -i` sin
`HARNESS_HOST`) el orden es el mismo. Cubierto por
`tests/test_leccion.py:153-166`.

### B3 documentacion que el codigo no respalda -> **NO resuelto del todo**

La ruta concreta si esta arreglada: `grep -rn "harness-hub" README.md SKILL.md`
solo devuelve `README.md:70` y `SKILL.md:32`/`SKILL.md:141`, que son el
directorio de **credenciales** (`~/.harness-hub/.env`), correcto. El venv ahora
se documenta como `~/.harness-flow/venv` en `README.md:54`, `SKILL.md:59`,
`SKILL.md:62` y `SKILL.md:228`, y coincide con `scripts/entorno.py:106`
(`entorno.venv_neutro()` -> `/Users/alan/.harness-flow/venv`).

Pero el propio arreglo introdujo **una afirmacion nueva que el codigo no
respalda** (H2-01, abajo): el orden de precedencia de interpretes documentado en
`SKILL.md:61-64` no es el que implementa `python_harness()`. Como el mandato de
B3 era "que no quede ninguna afirmacion de la doc sin respaldo", lo marco **no
resuelto**; la severidad real del residuo es *importante*, no bloqueante.

Lo demas que promete la doc SI lo verifique contra el codigo, y se cumple:

| Promesa | Donde | Verificacion |
| --- | --- | --- |
| `--hub` exige psycopg | `README.md:65`, `SKILL.md:56` | `entorno.py --hub` -> rc=1; sin flags -> rc=0 (`scripts/entorno.py:231`) |
| `--host claude\|hermes\|generic` fuerza el host | `README.md:67`, `SKILL.md:64` | `entorno.py --host claude` -> `HARNESS_HOST : claude` (`scripts/entorno.py:161,169-170`) |
| `HARNESS_PYTHON` sobrescribe el interprete | `README.md:67`, `SKILL.md:61` | `HARNESS_PYTHON=/no/existe entorno.py` -> rc=1 con mensaje (`scripts/entorno.py:112-119`) |
| `HARNESS_SKILLS_DIR` fuerza una raiz unica | `README.md:68`, `SKILL.md:172` | `HARNESS_SKILLS_DIR=/tmp/otroroot leccion.py donde` -> solo esa raiz (`scripts/leccion.py:93-99`) |
| `HARNESS_VENV` cambia el venv neutro | `SKILL.md:61` | `HARNESS_VENV=... python_harness()` lo usa (`scripts/entorno.py:106`) |
| `--shell` exporta `H`, `PY`, `HARNESS_HOST` | `SKILL.md:46` | `scripts/entorno.py:209`; ademas `HARNESS_PYTHON` (no documentado, inocuo) |
| `donde` lista raices por precedencia | `SKILL.md:171-172` | `scripts/leccion.py:222-224` |
| exit!=0 si no resuelve interprete | `README.md:64-65` | `HARNESS_PYTHON=/bin/ls entorno.py` -> rc=1 "requiere Python 3.10+" |

### B4 tests no versionados -> **RESUELTO**

```sh
git --no-pager diff --cached --stat
#  tests/test_entorno.py | 212 +++++...
#  tests/test_leccion.py | 169 +++++...
#  2 files changed, 381 insertions(+)
```

`git status --short` marca ambos como `A ` (anadidos al indice). No falta
ningun archivo: `find tests -type f` solo lista esos dos `.py` y `__pycache__/`,
que `.gitignore:1-2` excluye correctamente. La evidencia esta completa.

---

## Hallazgos nuevos (bugs introducidos por los arreglos)

| Sev | archivo:linea | Que esta mal y por que importa |
| --- | --- | --- |
| **importante** | `scripts/entorno.py:191` vs `scripts/entorno.py:166` | El arreglo de H-05 cambio la condicion de "el interprete es un venv" a `host != "hermes"`, y con eso **perdio la proteccion del Python global en host hermes**. Ejecutado de verdad: `env -i PATH=... HOME=/tmp/nohome2 HARNESS_HOST=hermes /usr/local/bin/python3` con `--instalar-deps` emite `['/usr/local/bin/python3','-m','pip','install','psycopg[binary]']` — sin crear ningun venv. Eso es exactamente lo que el `help` de la linea 166 promete que **nunca** pasa ("instala psycopg[binary] en un venv, nunca en el Python global") y lo que `SKILL.md:58-59` da por hecho. Cualquier usuario de Hermes cuyo `python_harness()` resuelva al python del sistema (sin launcher `hermes` en el PATH, sin `HERMES_HOME`, sin venv de Hermes: caso normal en una instalacion por `pipx`/Homebrew) se come un `pip install` en el interprete del SO. El arreglo tapo un agujero y abrio el simetrico. La condicion correcta necesita las dos cosas: host y "py no es un venv". |
| **importante** | `SKILL.md:61-64` vs `scripts/entorno.py:111-138` | La doc dice: "Detecta en este orden: `HARNESS_PYTHON` -> venv neutro (`HARNESS_VENV` o `~/.harness-flow/venv`) -> en host Hermes, `HERMES_PYTHON`/`HERMES_HOME`, el launcher... -> el propio interprete". El codigo hace otra cosa: `HERMES_PYTHON` se consulta en **la linea 114**, antes que el venv neutro (linea 121), y el propio interprete gana al venv neutro cuando el venv no tiene psycopg y el actual si (linea 124). Verificado: con `HARNESS_VENV` apuntando a un venv neutro existente, `HARNESS_HOST=hermes` y `HERMES_PYTHON=<sys.executable>`, `python_harness()` -> `/usr/local/bin/python3`, **no** el venv neutro que la doc pone antes. Afirmacion de documentacion que el codigo no respalda: el usuario que depura "por que `$PY` no es mi venv" sigue la doc y no cuadra. |
| **menor** | `scripts/leccion.py:37` | `sys.path.insert(0, ...)` se ejecuta en **cada** llamada a `_host()` y nunca deduplica. Verificado: tres llamadas dejan `sys.path` con tres copias identicas del directorio `scripts` al frente (`len` 6 -> 9). Como `leccion` se importa desde `gate.py:393` en procesos de larga vida no revienta nada, pero ensucia `sys.path` e implica que cualquier modulo del arbol `scripts/` sombrea a uno del stdlib/entorno para el resto del proceso. Basta con el `if ruta not in sys.path`. |
| **menor** | `scripts/leccion.py:40-48` | El `except ImportError` cubre "entorno.py ausente" pero no "entorno.py roto": si el archivo existe con un `SyntaxError` o lanza en import-time, la excepcion escapa como traceback crudo en vez de caer a la heuristica minima de las lineas 42-46, que es justo el fallback pensado para copias parciales. Ademas el orden `except ImportError` / `except ValueError` es correcto solo por casualidad de que `host_agente()` se invoca dentro del mismo `try`; un lector razonable asume que solo protege el import. |
| **menor** | `tests/test_entorno.py:162-176` | El test que deberia probar H-05 (`test_instalacion_sin_venv_no_toca_python_del_sistema`) fija `HARNESS_HOST="claude"` y por tanto **solo ejercita la rama que ya funciona**. El caso que ahora esta roto (host `hermes` + interprete del sistema, H2-01) no tiene ni un test: el `assertNotIn` de la linea 175 nunca se evalua para ese host. Falso verde de cobertura: el nombre del test promete "no toca el python del sistema" sin condicionar al host. |
| **menor** | `tests/test_entorno.py:168` | `side_effect=[False, False, True, True]` fija el numero exacto de llamadas a `tiene_psycopg`. Cualquier reordenacion futura de `python_harness()` que consulte una vez mas hace saltar `StopIteration` en vez de un fallo de asercion legible. Mock secuencial donde corresponde uno por ruta (`side_effect=lambda p: ...`, como el de la linea 138). |

## Hallazgos de la vuelta 1 confirmados como arreglados

- **H-06 (falso verde con runner de venv)**: la suite completa pasa igual con
  `python3` del sistema y con `/tmp/v/bin/python`. Ya no depende del entorno.
- **H-07 (detectores de host divergentes)**: `scripts/leccion.py:34-48` delega en
  `entorno.host_agente`. Verificado desde cwd `/` y desde un cwd borrado: el
  import funciona (usa `Path(__file__).resolve().parent`, no el cwd). Con
  `HARNESS_HOST=Claude` ahora **si** falla igual que `entorno.py`:
  `[!!] HARNESS_HOST debe ser hermes, claude o generic`, rc=1. Copia parcial sin
  `entorno.py` (`/tmp/parcial/leccion.py`): cae al fallback y funciona, rc=0.
- **H-08 (cwd borrado)**: `scripts/leccion.py:58-61` captura `OSError`.
  Verificado borrando el cwd bajo el proceso: `leccion.py donde` -> rc=0 con la
  raiz personal, sin traceback.
- **H-09 (claude colando skills de Hermes)**: `scripts/leccion.py:102-106` ya no
  suma `_raiz_propia()` en host claude, con el comentario explicando por que.
- **H-11 (tautologico)**: `tests/test_leccion.py:81-91` ahora compara contra la
  raiz esperada (`assertEqual(skills_roots()[0], raiz.resolve())`).
- **H-12 (`getattr` con fallback)**: ya no existe; `tests/test_entorno.py:31`
  llama `entorno.host_agente()` directo.
- **H-13 (venv neutro a medias)**: `scripts/entorno.py:122-125` con test real en
  `tests/test_entorno.py:130-139`. El orden de precedencia entre venv neutro e
  interprete actual es correcto **en el codigo**; lo que no cuadra es la doc (H2-02).
- **H-14 (exit!=0 sin hub)**: `scripts/entorno.py:229-231`, rc=0 sin `--hub`,
  rc=1 con `--hub`. Comprobado que **no** se volvio permisivo donde debe fallar:
  interprete inexistente y binario no-Python siguen dando rc=1 en la linea 181,
  antes de llegar al `return` de la 231.
- **H-15 (arbol del README roto)**: `README.md:120-137`, `tests/` esta ahora
  fuera del bloque de `scripts/`, al mismo nivel que `templates/`.
- **H-16 (mensajes inconsistentes)**: `scripts/leccion.py:199-201` y `:213-218`
  listan ambos todas las raices consultadas.

## Huecos que siguen sin cobertura

- `gate.py close --leccion` sigue sin un solo test end-to-end
  (`scripts/gate.py:392-399`); el objetivo 4 se apoya en `buscar()` via
  `tests/test_leccion.py:134-141`, que es mejor que nada pero no ejercita el gate.
- `--instalar-deps` en host `hermes` (ver H2-01): sin test.
- Windows sigue simulado solo con `mock.patch.object(entorno, "ES_WINDOWS", True)`
  (`tests/test_entorno.py:207`); `--powershell` nunca se valida contra un
  PowerShell real.
- Rutas con espacios: cubiertas en `HARNESS_VENV` (`tests/test_entorno.py:206`) y
  en `H` (`:110`), pero no en `HARNESS_SKILLS_DIR`.
- Raiz de skills sin permisos de lectura: sigue sin cobertura.
