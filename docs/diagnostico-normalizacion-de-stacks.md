# Diagnóstico de la normalización de stacks en dos proyectos reales

Fecha: 2026-11-12. Proyectos medidos: ADR e Innova Real Estate.

Este documento registra qué se preguntó, qué se midió, qué estaba mal en el
arnés, qué se corrigió y qué queda por hacer en cada proyecto. La descripción
del mecanismo está en
[`references/normalizacion-de-stacks.md`](../references/normalizacion-de-stacks.md)
y el detalle de la implementación en el Hito 33 de la
[`memoria técnica`](memoria-tecnica-implementaciones.md).

## 1. Qué se preguntó

1. ¿Funciona bien la normalización de front y backend?
2. El usuario observó que queda código sin la norma de arquitectura, sin skills
   y sin rules, y pidió revisar ADR e Innova Real Estate.
3. Pidió una solución para que no vuelva a pasar que `architecture.md` apunte a
   `src/app/features/**` cuando el código vive en `projects/*/src/app/`: el
   arnés debe mirar primero la ruta real, porque mañana el código puede estar
   en otra carpeta.

## 2. Cómo se midió

- Todo en solo lectura sobre los dos proyectos. No se escribió en ninguno.
- Sondas en carpetas temporales: los 10 stacks en un repo mínimo y 11 formas de
  proyecto (front con back dentro, monorepo, raíz sin declarar...).
- Sobre los proyectos: `stack.py detectar`, `verificar`, `normalizar --dry-run`,
  `arquitectura.py inventario` y comparación de cada copia instalada contra la
  plantilla.

## 3. Qué se encontró en cada proyecto

| | ADR | Innova Real Estate |
| --- | --- | --- |
| Repos que la normalización veía | 5: el front y 4 microservicios | 14: el front y 13 servicios |
| Rules, skills y `AGENTS.md` en esos repos | Completos, iguales a la plantilla | Completos, con copias viejas |
| Archivos fuera de la arquitectura del stack | 0 (eran 508 en 118 carpetas el 2026-11-10) | 1.361 en 256 carpetas |
| Trinquete de arquitectura | Adoptado; 10 features de normalización cerradas | Sin adoptar; 0 features de normalización |
| Feature #0 | No existe | Cerrada (`done`) |
| Repos del proyecto que nadie normalizaba | `adr-zitadel` (53 archivos Go) y `ms-invoice-service`, enlazados dentro de la raíz y sin declarar en `harness/grafos.json` | Ninguno |

Detalle de Real Estate:

- El front tenía `.claude/rules/architecture.md` del 2026-11-07. Sus `globs`
  eran `src/app/features/**` y `src/app/core/**`. El código vive en
  `projects/*/src/app/`. La plantilla se corrigió el 2026-11-09 y la copia no se
  actualizó.
- Los 13 servicios Go tenían `scripts/check-architecture.py` de 146 líneas. La
  plantilla tiene 285.
- `stack.py verificar` decía "Arquitectura: OK" en 12 de los 13 repos. Esos
  servicios tienen su código en `handlers/`, `routes/`, `database/`: no hay
  `internal/`, el verificador avisa que no midió los límites y sale con 0.
- Los 6 worktrees del front revisados tenían 0 rules y 0 skills: su `.gitignore`
  ignora las carpetas que empiezan con punto. El mismo día, a las 19:58, un
  agente del proyecto versionó esas carpetas (commit `4cf2af88`).

Diferencia entre los dos proyectos: ADR adoptó el trinquete y bajó de 508
archivos heredados a 0. Real Estate cerró su Feature #0 y desde entonces nada
exige bajar los 1.361.

## 4. Qué estaba mal en el arnés

| # | Falla | Efecto |
| --- | --- | --- |
| 1 | `normalizar` solo agregaba lo que faltaba | Una copia instalada no se actualizaba nunca, y nadie avisaba. El brief entregaba el texto viejo |
| 2 | Los `globs` de una regla salían de la plantilla, no del repo | Una regla podía no nombrar ni un archivo del repo |
| 3 | `verificar` traducía el exit 0 del verificador a "OK" | Código fuera de la norma con "COMPLIANT" |
| 4 | La raíz se perdía si no estaba declarada o si una subcarpeta traía un `package.json`; un repo con stack no se miraba por dentro | Repos del proyecto sin rules, sin skills y sin medir |
| 5 | Un proyecto Gradle cualquiera se detectaba como Android | Norma equivocada |
| 6 | Un repo que no versiona `.claude/` daba worktrees sin norma | El host que trabaja en el worktree no la carga |
| 7 | `estado.py` envolvía la normalización en `except Exception: pass` | Un fallo dejaba los repos sin normalizar y sin una línea que lo dijera |

## 5. Qué se corrigió

| # | Corrección | Dónde |
| --- | --- | --- |
| 1 | Una copia vieja que nadie editó se actualiza; una editada por el proyecto se conserva y se avisa; `--reemplazar` la cambia por la plantilla | `scripts/copias.py`, `stack.plan_de_copias`, `stack.normalizar_repositorio` |
| 1 | El brief y `stack.py skill` entregan la plantilla vigente cuando la copia del repo quedó vieja | `contexto._texto_regla`, `contexto._skill_md`, `stack.ruta_skill` |
| 2 | El alcance de `architecture.md` y `security.md` se calcula con el código del repo: si algún archivo queda fuera de los `globs`, se suma `**/*.<ext>`. Se mide en cada normalización | `copias.ajustar_alcance` |
| 3 | `verificar` dice cuántos archivos viven fuera de la norma, cuántos no mira el layout y qué avisó el verificador. El arranque de sesión cuenta lo heredado cuando no hay trinquete | `stack.codigo_fuera_de_la_norma`, `arquitectura.resumen`, `arquitectura.py inventario` |
| 4 | La raíz entra siempre; entra una carpeta con otro stack dentro de un repo y el segundo nivel de un monorepo. Un clon ajeno dentro de la raíz se avisa y no se toca | `stack.detectar_todos_los_destinos`, `stack.repos_sin_declarar` |
| 5 | `detection.requires_any` en el manifest. Android exige un `AndroidManifest.xml` | `stack.evaluar_stack_manifest`, `assets/stacks/android-compose-clean/manifest.json` |
| 6 | `worktree.py start`, `register` y el arranque de sesión enlazan al worktree las carpetas de rules y skills que el repo no versiona | `comun.enlazar_normativa` |
| 7 | El fallo se imprime | `scripts/estado.py` |

### Una decisión que salió de probar contra los proyectos

La primera versión reescribía las copias viejas en el arranque de sesión. En
Real Estate eso dejaba 13 checkouts con cambios sin commit, y `gate.py close`
no integra sobre un árbol con cambios: habría bloqueado todos los cierres.

Regla que quedó: el arranque de sesión actualiza solo las copias que el repo no
versiona. Las que sí versiona quedan pendientes y se avisan en una línea, con
el comando. El arnés no hace commits en los repos del usuario.

### Dos correcciones a lo que se dijo durante el diagnóstico

- Se dijo que la regla con `globs` viejos "no se activa para ningún archivo".
  En Claude Code no es así: el campo que limita una regla a unas rutas es
  `paths`, y las reglas instaladas no lo traen, así que se cargan siempre. Lo
  que sí quedaba viejo era el texto de la regla que entregaba el brief, los
  verificadores copiados y el alcance que leen los hosts que usan `globs`.
- Se reportaron 73 tests como "fallos de entorno de siempre". No lo eran. Ver
  la sección 8.

## 6. Qué queda por hacer en cada proyecto

Nada de esto lo hace el arnés solo. Son cambios en repos del usuario.

### Innova Real Estate

1. **Actualizar las copias viejas.** 14 repos (el front y 13 servicios Go)
   tienen 6 o 7 copias viejas que versionan: `architecture.md` y `security.md`
   en `.claude`, `.agents` y `.gemini`, y `scripts/check-architecture.py` en
   los servicios Go. En cada repo:

   ```bash
   "$PY" "$H/stack.py" normalizar --repo <ruta>     # y commitea el cambio
   ```

2. **Decidir si se adopta el trinquete.** Sin él nada frena los 1.361 archivos
   fuera de la norma:

   ```bash
   "$PY" "$H/arquitectura.py" inventario --detalle
   "$PY" "$H/arquitectura.py" adoptar --yes          # decisión del usuario
   ```

3. **Worktrees anteriores al commit `4cf2af88`.** Su rama no trae las rules ni
   las skills. Las reciben al rebasar sobre `develop`. Mientras tanto el brief
   les entrega la norma por la salida del script.

### ADR

1. **Actualizar las copias viejas del front.** 6 copias: `architecture.md` y
   `security.md` con el alcance ampliado a `**/*.ts`. Mismo comando.
2. **Decidir qué hacer con `adr-zitadel` y `ms-invoice-service`.** Para que el
   arnés los normalice y los mida, se declaran en `harness/grafos.json`. Hoy:
   `adr-zitadel` no tiene rules, skills ni `AGENTS.md`, y tiene 17 archivos Go
   fuera de la norma; `ms-invoice-service` pertenece a otro proyecto
   (Online-Invoice) y tiene 342.

## 7. Qué verá el usuario en el próximo arranque de sesión

| Proyecto | Líneas nuevas de `estado.py` |
| --- | --- |
| Real Estate | `[!] 14 repo(s) con copias viejas de rules, skills o validadores que versionan...` y `arquitectura: [!] 1361 archivos en 256 carpetas viven fuera de la norma del stack y nada los frena` |
| ADR | `[!] 1 repo(s) con copias viejas...` y dos líneas `[!] ... es un repo dentro del proyecto que no esta declarado en harness/grafos.json` |

El arnés se usa por un enlace (`~/.claude/skills/harness-flow`), así que el
cambio está activo para los agentes de ambos proyectos desde que se escribió.

## 8. Verificación

- `tests/test_copias.py`: 41 tests nuevos.
- Tres tests existentes cambiaron por diseño: la raíz no declarada ahora entra
  (`test_stack_adopcion`), el arreglo Android trae su manifiesto, y una
  plantilla externa puede traer copias más viejas que las de la skill
  (`test_stack`).
- Suite completa sobre el árbol de trabajo, sin el toolchain de frontend: 1.184
  tests, 1.111 pasan y 73 fallan por falta de la variable.
- Los cuatro archivos de frontend con el toolchain: 93 tests, 93 pasan.
- Entre las dos corridas pasan los 1.184. El detalle está en "Estado de
  Verificación" de la [`memoria técnica`](memoria-tecnica-implementaciones.md).

**Los 73 tests de frontend.** En todas las corridas de la sesión se reportaron
73 fallos en `test_frontend_runner`, `test_retirados_frontend`,
`test_frontend_close` y `test_cierre_historico` como un problema del entorno.
El toolchain que piden estaba instalado desde el 2026-10-01 en
`~/.harness-flow/frontend-toolchain`. Lo que faltaba era pasar su ruta:

```bash
T=~/.harness-flow/frontend-toolchain
PATH=$T/node_modules/node/bin:$PATH HARNESS_TEST_FRONTEND_MODULES=$T/node_modules \
  "$PY" -m unittest discover -s tests
```

Esos tests fallan a propósito cuando falta la variable. Un fallo así no es un
"fallo conocido": es una parte de la suite que no se midió.

## 9. Límites que quedan

- Un repo JVM sin otra señal se detecta como `springboot-hexagonal` y un repo
  Python como `python-dataproduct`, aunque use otro framework (Ktor, Django).
  Exigir la señal del framework puede dejar sin norma un repo que hoy la tiene:
  es decisión del usuario.
- Un archivo nuevo de la plantilla (una skill agregada al stack) se instala en
  el arranque de sesión aunque la carpeta esté versionada. Queda como archivo
  sin seguimiento hasta que alguien lo commitea. Ya era así antes de este
  cambio.
- Una copia distinta de la plantilla sin registro y sin historial git de la
  skill no se actualiza: se conserva y se avisa.
