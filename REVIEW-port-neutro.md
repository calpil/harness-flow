# Revision adversarial: port neutro de harness-flow (Hermes -> Hermes + Claude Code)

Rama `feat/port-neutro` en `/Users/alan/.hermes/worktrees/harness-flow-port-neutro`.
Revisor: subagente aislado. No implemente este cambio.

Suite: `python3 -m unittest discover -s tests` -> **25 tests OK** con el python
del sistema. Con un python de venv como runner, **falla 1** (ver H-02).

Veredicto: **changes_requested** (4 bloqueantes).

---

## Hallazgos

| Sev | archivo:linea | Que esta mal y por que importa |
| --- | --- | --- |
| **bloqueante** | `scripts/leccion.py:124` | `raiz.glob("*/" + clase + "/SKILL.md")` interpola `clase` sin escapar dentro de un patron glob. `buscar("*")`, `buscar("[a-z]*")` devuelven la **primera skill cualquiera**. Verificado: con `HARNESS_SKILLS_DIR=/tmp/globtest/root`, `buscar('*')` -> `/tmp/globtest/root/cat/realskill/SKILL.md` y `buscar('[a-z]*')` idem. El saneo de `leccion.py:118` solo bloquea `/`, `\`, `.`, `..` — no los metacaracteres glob. Consecuencia directa sobre el objetivo 4: `gate.py close --leccion '*'` (`scripts/gate.py:395`) **pasa el gate sin que exista ninguna leccion**. Es exactamente el falso verde que el gate existe para impedir. |
| **bloqueante** | `scripts/leccion.py:93-94` vs `scripts/leccion.py:72-77` | Regresion para el usuario que YA usa esto en Hermes con **perfiles**. En el host `hermes` el orden es `_raices_hermes()` (que arranca por `~/.hermes/skills`, linea 67) y solo despues `_raiz_propia()`. El codigo anterior (`git show HEAD:scripts/leccion.py`, bloque de `skills_root`) consultaba los `parents` de `__file__` **antes** que los candidatos del home. Verificado con un home simulado: skill instalada en `~/.hermes/profiles/trabajo/skills/.../harness-flow` con una leccion `tdd` en el perfil y otra en el default; con `HARNESS_HOST=hermes` (que es justo lo que `entorno.py --shell` exporta, `scripts/entorno.py:202`) devuelve `DEFAULT-PROFILE` en vez de `PERFIL-TRABAJO`. El usuario de perfiles lee/valida la leccion equivocada. |
| **bloqueante** | `README.md:54`, `SKILL.md:57`, `SKILL.md:60`, `SKILL.md:226` vs `scripts/entorno.py:106` | La documentacion afirma en cuatro sitios que el venv neutro vive en `~/.harness-hub/venv`. El codigo usa `~/.harness-flow/venv` (`venv_neutro()`, linea 106). Verificado en ejecucion: `entorno.venv_neutro()` -> `<home>/.harness-flow/venv`. Afirmacion de documentacion que el codigo no respalda, en la instruccion de instalacion del objetivo 5; ademas `~/.harness-hub/` es el directorio de credenciales (`README.md:65`), asi que el usuario buscara el venv donde nunca estara. |
| **bloqueante** | `tests/` (directorio completo, sin trackear) | `git status` reporta `tests/` como **untracked** y `.gitignore` no lo excluye. El cambio que se somete a revision no incluye los tests: cualquiera que haga `git diff`/PR de esta rama recibe el port **sin** su red de seguridad. Toda la evidencia de correccion del port es no-versionada. |
| **importante** | `scripts/entorno.py:184` | `--instalar-deps` solo crea el venv neutro si `py.parent.parent/pyvenv.cfg` no existe. Si el usuario de Claude Code lanza el comando desde **cualquier venv activo** (el del proyecto), `py` ya es un venv-python y `psycopg` se instala **en el venv del proyecto**, no en el neutro. Eso contradice `SKILL.md:56-57` ("en Claude Code crea un venv propio ... en vez de tocar el python del sistema") y ensucia el entorno del proyecto del usuario. El host ni siquiera se consulta en esa rama. |
| **importante** | `tests/test_entorno.py:140-147` | Falso verde que tapa H-05. El test se llama `test_instalacion_sin_venv_no_toca_python_del_sistema` pero **depende de que el runner no sea un venv**. Ejecutado con `/tmp/venvprobe/bin/python -m unittest discover -s tests` este test **FALLA**: `['/tmp/venvprobe/bin/python','-m','venv',...] not found in [...]` — se salto la creacion del venv y fue derecho a `pip install`. El test pasa por accidente del entorno del autor, no por el comportamiento. |
| **importante** | `scripts/leccion.py:35-42` vs `scripts/entorno.py:27-42` | Dos detectores de host **divergentes** en el mismo port. (a) `leccion.py:35-37` no valida `HARNESS_HOST`: con `HARNESS_HOST=Claude` (mayuscula) devuelve literalmente `"Claude"`, cae al `else` de la linea 96 y usa el orden **generic** en silencio; `entorno.py:29-30` para el mismo valor lanza `ValueError`. Verificado en ejecucion. (b) `leccion.py:38` acepta `CLAUDE_CONFIG_DIR` como senal de host claude, `entorno.py:32` no. (c) `entorno.py:35-37` detecta claude por la ruta `.claude/skills`, `leccion.py` no. Resultado: `$PY entorno.py` puede decir `hermes` y `leccion.py` resolver como `claude` en la misma maquina. |
| **importante** | `scripts/leccion.py:51` | `Path.cwd()` sin proteccion. Si el cwd fue borrado (worktree eliminado, `worktree.py` es parte de este mismo flujo), `skills_roots()` revienta con `FileNotFoundError: [Errno 2]` y un traceback crudo, no con el mensaje accionable que el resto de la funcion se esfuerza en dar (`leccion.py:106-107`). Verificado: rc=1 con traceback en `_raices_claude`. Caso borde "cwd fuera de cualquier repo/inexistente" no cubierto por ningun test. |
| **importante** | `scripts/leccion.py:92`, verificado en ejecucion | En host `claude`, `_raiz_propia()` anade la raiz de skills **de Hermes** cuando la skill esta enlazada/instalada bajo `~/.hermes`. Verificado con symlink `~/.claude/skills/harness-flow -> ~/.hermes/skills/.../harness-flow`: `leccion.py donde` lista `~/.claude/skills` **y** `~/.hermes/skills`, y `existe secreto-hermes` resuelve a la skill de Hermes. El objetivo 3 dice que en Claude Code la precedencia es personal > proyecto; no dice que se filtren skills de Hermes. `tests/test_leccion.py:72-79` prueba la direccion contraria (hermes no ve claude) pero **no** esta, que es la que falla. |
| **menor** | `tests/test_leccion.py:81-85` | Test tautologico: `test_sin_host_conocido_cae_a_la_raiz_que_contiene_esta_skill` no comprueba lo que su nombre dice. Solo asegura `raices` no vacio y `all(isinstance(r, Path))` — `skills_roots()` no puede devolver otra cosa que `Path`. Pasaria con cualquier raiz, incluida la equivocada. |
| **menor** | `tests/test_entorno.py:31` | `getattr(entorno, "host_agente", lambda: "sin soporte")` en un test cuyo objeto es precisamente ejercitar `host_agente`. El fallback enmascara "la funcion no existe" convirtiendolo en un assert de igualdad de strings; el diagnostico del fallo queda peor y el patron invita a que el test sobreviva a la desaparicion del simbolo. |
| **menor** | `scripts/entorno.py:120-122` | Si el venv neutro existe pero **no** tiene `psycopg` (instalacion a medias, `pip` interrumpido), se devuelve igual sin comprobarlo, saltandose la rama `tiene_psycopg(actual)` de la linea 124 que si habria encontrado un interprete valido. Degradacion silenciosa. |
| **menor** | `scripts/entorno.py:222` | `main()` devuelve `1` cuando falta `psycopg` aunque el propio mensaje de la linea 221 diga "gates locales disponibles". Un usuario de Claude Code que solo quiera los gates locales (sin hub Postgres) ve un exit!=0 permanente en el diagnostico. Ruido, no rotura. |
| **menor** | `README.md:127-129` | La fila `tests/` se inserto **dentro** del bloque de `scripts/`, entre `leccion.py` y `hub.py`, rompiendo el arbol: parece que `hub.py`, `vault.py` y `atlassian.py` cuelgan de `tests/`. |
| **menor** | `scripts/leccion.py:171` | `cmd_ver` reporta el fallo con `skills_root()` (una sola raiz) mientras `cmd_existe:183-188` lista **todas** las consultadas. Mensajes de error inconsistentes para el mismo tipo de fallo. |

---

## Lo que si esta bien (verificado, no asumido)

- **Objetivo 2, quoting shell**: `scripts/entorno.py:203` usa `shlex.quote` y
  `scripts/entorno.py:208` duplica la comilla simple para PowerShell. Verificado
  con un `/bin/sh` real en `tests/test_entorno.py:114-116` sobre una ruta con
  `'`, `$HOME`, backtick y comillas dobles: no hay inyeccion en ningun modo.
- **Objetivo 2, nada de shell a medias**: los `return 1` de `entorno.py:177`,
  `:192`, `:198` ocurren **antes** de imprimir cualquier `export`
  (`entorno.py:201`). Verificado: `out == ""` en los tres caminos de fallo
  (`tests/test_entorno.py:127-175`). No hay variable exportada a la mitad ni
  `[ok]` falso; `:196-198` ademas re-verifica el import tras un `pip` con exit 0,
  que es la trampa clasica.
- **Objetivo 3, override exclusivo**: `scripts/leccion.py:82-88` corta antes de
  consultar cualquier otra raiz y falla explicito si no es directorio. Correcto.
- **Objetivo 3, precedencia personal > proyecto en Claude**:
  `scripts/leccion.py:45-53` pone la personal primero. Correcto.
- **Symlinks y `/var` vs `/private/var`**: `scripts/leccion.py:102` resuelve y
  deduplica; `scripts/entorno.py:34-37` deliberadamente **no** resuelve para que
  un symlink en `.claude` no herede el host del destino. Decision correcta y
  documentada en el propio comentario.
- **HOME ausente**: `scripts/leccion.py:31` encadena `HOME` -> `USERPROFILE` ->
  `Path.home()` y trata la cadena vacia como ausente. Verificado sin `HOME` ni
  `USERPROFILE`: resuelve.
- **Rutas con espacios**: `HARNESS_VENV="<...>/mi venv"` se maneja bien
  (`tests/test_entorno.py:177-180`) y los comandos se construyen como listas, sin
  shell intermedio.

## Huecos de cobertura no cubiertos por ningun test

- **`gate.py close --leccion` no tiene ni un test** pese a ser el objetivo 4.
  Todo el objetivo se apoya indirectamente en `buscar()`, que es justo la funcion
  rota por H-01.
- **Windows**: solo se simula via `mock.patch.object(entorno, "ES_WINDOWS", True)`
  en `tests/test_entorno.py:179`. El modo `--powershell` nunca se valida contra un
  interprete PowerShell real, y `leccion._casa()` no se prueba con `USERPROFILE`
  sin `HOME`.
- **cwd inexistente / fuera de repo** (H-08), **raiz de skills sin permisos de
  lectura**, y **`CLAUDE_CONFIG_DIR` apuntando a algo inexistente**: sin cobertura.
