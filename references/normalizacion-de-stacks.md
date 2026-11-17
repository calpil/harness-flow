# Normalización de stacks: qué repos, qué alcance y qué copias

Léelo cuando un repo del proyecto no reciba las rules o las skills de su stack,
cuando una regla no nombre el código del repo, cuando una copia instalada quede
distinta de la plantilla o cuando `stack.py verificar` diga algo que no esperas.

## Stacks soportados

Cada uno vive en `assets/stacks/<stack-id>/` (manifest, `rules/`, `skills/` y validadores). Lo que exige cada uno:

- **Golang Hexagonal (`golang-hexagonal`)**: dominio Go puro en `internal/*/domain/**` (sin frameworks/SQL), puertos de entrada/salida en `application/`, adaptadores Chi HTTP (RFC 7807) y persistencia `pgx`/in-memory, composition root en `cmd/server/main.go`, tests deterministas sin `time.Sleep` (`go test -race`).
- **Angular Product (`angular-product`)**: feature-oriented layered (`src/app/features/<feat>/(domain|application|ui|data-access)`), dominio TypeScript puro sin dependencias de `@angular`/RxJS, Signals para reactividad, componentes standalone, composition root en `app.routes.ts` y linter de límites (`check-architecture.py` / `check-architecture.mjs`).
- **.NET Hexagonal (`dotnet-hexagonal`)**: C# 13 / .NET 10 (LTS) con Clean Architecture multi-proyecto (`Domain` puro en BCL sin dependencias externas, `Application` con puertos in/out, `Infrastructure` con Dapper/ADO.NET y `Npgsql`, `WebApi` con MVC Controllers, ProblemDetails RFC 7807 y `Program.cs` como Composition Root, y tests deterministas con xUnit y `WebApplicationFactory`).
- **.NET Layered API (`dotnet-layered`)**: C# / .NET 10, API REST con ASP.NET Core controllers en un solo proyecto. Una carpeta por feature y una clase por capa (`Controller → Service → Repository`); `Platform/` es transversal. SQL Server con Dapper y `Microsoft.Data.SqlClient`, sin ORM; SQL siempre parametrizado, operaciones de estado por procedimiento almacenado con `rowversion` y migraciones T-SQL en `db/migrations/`. Problem Details RFC 9457, `Program.cs` como Composition Root y tests deterministas con xUnit y `TimeProvider`.
- **.NET MVC Web Portal (`dotnet-mvc`)**: C# / .NET 10, portal web ASP.NET Core MVC con vistas Razor y Bootstrap 5. El portal presenta y captura: no tiene base de datos ni reglas de negocio, y todo dato entra y sale por una interfaz `I*Api` (cliente HTTP tipado). Controllers delgados, vistas sin `@inject`, `Html.Raw` ni código en línea (CSP `default-src 'self'`), sesión con cookie + OpenID Connect y todo cambio de estado por POST con antiforgery.
- **Rust Hexagonal (`rust-hexagonal`)**: Rust (edición 2021/2024) con Clean Architecture multi-crate o modular (`crates/domain` puro sin dependencias de red/SQLx, `crates/application` con puertos in/out y casos de uso, `crates/infrastructure` con SQLx PostgreSQL y repositorios en memoria, `crates/api` con handlers Axum, ProblemDetails RFC 7807 y `src/main.rs` como Composition Root, y tests deterministas sin `thread::sleep`).
- **Next.js Product (`nextjs-product`)**: Next.js 15+ / React 19 con Server Components por defecto, aislamiento `server-only` y App Router.
- **Spring Boot Hexagonal (`springboot-hexagonal`)**: Java 21 / Spring Boot 3.4 con dominio puro sin dependencias de Spring/JPA y ArchUnit.
- **NestJS Hexagonal (`nestjs-hexagonal`)**: TypeScript / NestJS modular con Prisma ORM y puertos desacoplados.
- **Python Data Product (`python-dataproduct`)**: Python 3.14 con FastAPI, Polars/Pydantic y adaptadores de origen/destino.
- **iOS SwiftUI Clean (`ios-swiftui-clean`)**: Swift con Clean Architecture por módulos SPM (`*Domain` puro, `*Data`, `*UI`, `*App` como Composition Root).
- **Android Compose Clean (`android-compose-clean`)**: Kotlin y Jetpack Compose con `features/*/(domain|data|presentation)` y `core`.
- **Stacks Futuros**: cualquier nuevo stack se agrega simplemente creando una carpeta `assets/stacks/<nuevo-stack>/manifest.json` con su bloque `"detection"` (indicadores de archivos, extensiones, dependencias y anti-indicadores); el motor lo detectará y normalizará de forma automática sin tocar código Python. `detection.requires_any` declara la señal propia del stack: sin ninguno de esos archivos el repo no es de ese stack (un proyecto Gradle sin `AndroidManifest.xml` no es Android). Para que su código heredado se mida (trinquete), el manifest declara además el bloque `"layout"`.
- **Varios stacks del mismo lenguaje**: el puntaje no alcanza para decidir, porque el stack general suma en cualquier repo de su lenguaje. El stack específico declara tres cosas. `requires_any`: su señal propia. `anti_indicators`: lo que lo descarta. `supersedes`: el id del stack general al que desplaza cuando ambos califican. Así se reparten los tres stacks .NET: con vistas Razor (`Views/_ViewImports.cshtml`) el repo es `dotnet-mvc`; con un proyecto `*Api` que tiene `Program.cs`, o con repositorios en carpetas de feature, es `dotnet-layered`; con proyectos `*Domain`, `*Application` o `*Infrastructure` es `dotnet-hexagonal`, aunque sirva vistas. Un repo .NET sin ninguna de esas señales queda en `dotnet-hexagonal`, como antes. Un repo con las dos señales (API y vistas en la misma solución, o un MVC con repositorios) no es ninguno de los dos: también queda en `dotnet-hexagonal`. Los stacks unidos por `supersedes` son una familia: dentro de un repo, la carpeta de un proyecto que mirada sola califica para otro stack de la familia (`Acme.Api/` en una solución con los proyectos en la raíz) no es otro destino; la gobierna la norma del repo. Un empate de puntaje lo decide el id, en orden alfabético.

## Qué hace y qué no

`stack.py normalizar` instala en cada repo la norma de su stack: rules, skills,
`AGENTS.md` y validadores. No mueve código. El código que vive fuera de la
arquitectura del stack se mide con `arquitectura.py` y se corrige con features
de normalización (ver [`arquitectura-heredada.md`](arquitectura-heredada.md)).

| Parte | Quién la hace | Cuándo |
| --- | --- | --- |
| Instalar rules, skills, `AGENTS.md` y validadores | `stack.py normalizar` | En cada arranque de sesión (`estado.py`) y a mano |
| Ajustar el alcance de las reglas al código real | `stack.py normalizar` | En cada normalización |
| Actualizar una copia que quedó vieja | `stack.py normalizar` | Ver "Copias viejas" |
| Decir cuánto código vive fuera de la norma | `stack.py verificar`, `estado.py`, `arquitectura.py inventario` | Siempre |
| Llevar el código a la norma | Features `--kind normalizacion` | Decisión del usuario |

## Qué repos se normalizan

`stack.detectar_todos_los_destinos` da la lista. La usan la normalización, la
Feature #0, el trinquete y el brief.

- **La raíz del arnés.** Entra siempre que tenga stack, esté o no declarada en
  `harness/grafos.json`.
- **Las raíces de `harness/grafos.json`.**
- **Lo que cuelga de una carpeta sin stack.** Sus repos (`ms-*`, `frontend/` y
  `backend/`). Si ninguno tiene stack, los del nivel siguiente (`apps/web`,
  `apps/api`).
- **Una carpeta con otro stack dentro de un repo.** `api/` en Go dentro de un
  front, o `web/` en Angular dentro de un servicio.

No entran:

- **Una carpeta del mismo stack sin `.git` propio.** `tools/go.mod` dentro de un
  servicio Go es parte del servicio.
- **Un clon propio dentro de un repo.** Un servicio clonado o enlazado dentro de
  la raíz es otro repo. El arnés no escribe en él ni lo mide. Lo lista con
  `[!]` en el arranque de sesión y en `stack.py detectar`. Para normalizarlo:
  decláralo en `harness/grafos.json`, o corre `stack.py normalizar --repo <ruta>`.

Detección: un stack puede declarar `detection.requires_any` en su manifest. Si
ninguno de esos archivos existe, el repo no es de ese stack. Android lo usa: un
proyecto Gradle sin `AndroidManifest.xml` no es Android.

## El alcance de una regla sale del código del repo

Las plantillas traen `globs` con el layout canónico (`src/app/features/**`,
`internal/**`). Un repo cuyo código vive en otra ruta quedaba con una regla que
no lo nombraba. Caso medido: la regla apuntaba a `src/app/features/**` y el
código vivía en `projects/*/src/app/`.

`normalizar` mira primero dónde vive el código:

1. Toma los archivos versionados del repo con la extensión de código del stack
   (sale de `layout.codigo` del manifest: `go`, `ts`, `py`...).
2. Deja fuera lo de terceros (`node_modules`, `vendor`, `dist`...), las carpetas
   ocultas y los validadores que instala el arnés.
3. Compara con los `globs` de la plantilla. Si todo el código cabe, la regla se
   instala igual a la plantilla, byte a byte.
4. Si algún archivo queda fuera, agrega `**/*.<ext>` a los `globs` de ese repo.
   Los de la plantilla se conservan.

Se repite en cada normalización. Si mañana el código se muda a otra carpeta,
`verificar` reporta la regla como copia vieja y `normalizar` la corrige.

Aplica a las reglas que deben nombrar todo el código: `architecture.md` y
`security.md`. Un stack puede declarar otra lista en
`normative.rules_cubren_codigo`.

En Claude Code el campo que limita una regla a unas rutas es `paths`, no
`globs`: las reglas instaladas se cargan siempre. `globs` es el alcance que
leen los hosts que lo usan y el que declara la regla a quien la lee.

## Copias viejas y copias del proyecto

Una copia distinta de la plantilla puede ser dos cosas:

| Estado | Qué es | Qué hace `normalizar` |
| --- | --- | --- |
| Vieja | Una versión anterior que nadie editó | La actualiza |
| Modificada | El proyecto la editó | La conserva y lo avisa |

Lo distingue con dos pruebas, en este orden:

1. **El registro de lo instalado.** `<git-dir>/harness-flow-copias.json` guarda
   la huella de cada copia que el arnés dejó. Vive dentro de `.git`: no se
   versiona y no ensucia el árbol. Una copia con la huella del registro no la
   editó nadie.
2. **El historial git de la plantilla.** Una copia igual a una versión anterior
   de la plantilla no la editó nadie. Sirve para lo instalado antes de que
   existiera el registro.

Sin ninguna de las dos pruebas la copia no se toca. Pasa cuando la skill no es
un clon git y no hay registro.

- `stack.py normalizar --repo <r> --reemplazar` cambia por la plantilla también
  las copias modificadas. Es decisión del usuario.
- `stack.py verificar` reporta las viejas como hallazgo (`Copias
  desactualizadas`) y las modificadas como advertencia.
- Un `AGENTS.md` que el arnés no generó no se reemplaza nunca.

### En el arranque de sesión no se reescribe lo que el repo versiona

`gate.py close` no integra sobre un checkout con cambios sin commit. Por eso
`estado.py` actualiza solo las copias viejas que el repo no versiona. Las que sí
versiona quedan pendientes, y el arranque lo dice en una línea `[!]` con los
repos afectados. Para actualizarlas:

```bash
"$PY" "$H/stack.py" normalizar --repo <ruta>     # y commitea el cambio
```

Mientras tanto nadie lee la copia vieja por el arnés: el brief y `stack.py
skill` entregan la plantilla vigente cuando la copia del repo quedó vieja. La
copia que el proyecto editó sí se entrega: su edición manda.

### Una carpeta nueva de la plantilla aparece sin seguimiento

Cuando la skill suma una carpeta de normativa (`.gemini/skills/` junto a
`.claude/skills/` y `.agents/skills/`), el arranque la instala en TODOS los
repos, y en los que versionan las otras queda como `??`. No es trabajo de otra
sesión ni basura: es la normativa nueva sin commitear.

1. Confirma el origen: fecha de la carpeta (la del arranque) y
   `git log -S'<carpeta>' -- scripts/` en el clone de la skill.
2. Mira cómo trata cada repo a las carpetas hermanas: `git ls-files | grep
   '^\.(claude|agents|gemini)/'` y el `.gitignore` (un front puede ignorar `.gemini/*`
   salvo `!.gemini/rules/`).
3. Pregunta en el formulario, con la recomendada primero: versionar como las
   demás (recomendado), ignorarla en `.gitignore`, o borrarla (vuelve en el
   arranque siguiente: no es arreglo). Pregunta también si se normaliza completo
   (actualiza las copias viejas) y cuándo (después de los cierres en curso).
4. Versionar = `stack.py normalizar --repo <r>` y un commit por repo en la rama
   base; en un repo que habilita carpeta por carpeta, suma la línea `!` que
   falta. Fuera de la rama de una feature y después de los merges en curso, para
   no mezclar normativa con el delta de una feature ni mover la base medida.
5. Mide lo que el commit cambia. Normalizar completo no solo suma la carpeta:
   actualiza las reglas viejas y el validador versionado
   (`scripts/check-architecture.py`). Antes de tocar N repos:
   - `stack.py normalizar --repo <r> --dry-run` en todos y lee las acciones; si
     el dry-run cambia algo más que carpetas nuevas, dilo en el formulario
     antes de elegir el momento.
   - Un repo piloto primero; después el resto uno por uno con un script que
     aborta ante: repo fuera de la rama base o con cambios versionados;
     `git status --porcelain` que, tras normalizar, nombre una ruta que no sea
     normativa (`.claude/`, `.agents/`, `.gemini/`, validadores, `AGENTS.md`);
     o un `postmerge_medido.py check` de la suite unitaria que no quede igual
     que su `base` tomada antes (`--cmd 'go test -count=1 -json ./...'`).
   - Corre la copia del validador antes y después. Una plantilla nueva trae
     reglas nuevas: el mismo código puede pasar de exit 0 a exit 1. No es una
     regresión del código (esas violaciones son las que ya registra la base del
     trinquete), pero rompe a quien ejecute esa copia: busca su nombre en
     Makefile, CI, hooks y tests antes de commitear, y cuéntaselo al usuario.
   - En el repo que no versiona el validador (usa el de la skill) solo cambian
     reglas: comprueba que el verificador de la skill siga dando lo mismo.

## Grok, en el rol y no en el commit

`stack.py normalizar` no escribe `.grok/`. Grok carga `.grok/rules/` y
`.grok/skills/` de la sesión, y no entra a un repo hermano. Por eso el brief,
el briefing del revisor y el borrador del SDD copian ahí las rules y skills de
los stacks de ese rol (front y backend), con nombre `<stack>--<nombre>`. Van a
`info/exclude`. El PRD no las copia. Contrato completo:
[`grok-sesion-stacks.md`](grok-sesion-stacks.md).

## Worktrees

`normalizar` instala en el checkout principal. Un repo que no versiona esas
carpetas (un `.gitignore` con `.*`) daba worktrees sin rules ni skills.

`worktree.py start`, `worktree.py register` y el arranque de sesión enlazan al
worktree `.claude/rules`, `.claude/skills`, `.agents/rules`, `.agents/skills`,
`.gemini/rules` y `.gemini/skills` desde el checkout principal. Solo enlazan una
carpeta que el repo no versiona y que falta en el worktree. Una carpeta
versionada la trae la rama.

## `stack.py verificar` no da un OK sin medir

| Línea | Cuándo |
| --- | --- |
| `✅ COMPLIANT` | Instalación completa, sin violaciones, sin código fuera de la norma y sin avisos del verificador |
| `⚠️ INSTALACION CONFORME; ARQUITECTURA CON PENDIENTES` | Hay código fuera de la norma, o el verificador avisó que no midió algo |
| `❌ NON-COMPLIANT` | Falta instalar algo, hay copias viejas o el verificador encontró violaciones |

- `N archivos en M carpetas viven fuera de la norma`: código dentro del alcance
  del layout y fuera de su estructura. Es el mismo número de `arquitectura.py
  inventario`.
- `N archivos de código quedan fuera del alcance del layout`: tienen extensión
  de código y el layout no los mira (una librería en `projects/ui/src/lib`).
  No cuentan como dentro ni como fuera de la norma. `inventario --detalle` los
  lista por carpeta.
- Los avisos del verificador (`NO se midieron`) se muestran. Antes se perdían al
  traducir su exit 0 a un "OK".

El exit de `verificar` no cambió: 0 si la instalación y el verificador están
bien, 1 si no.

Sin trinquete adoptado, el arranque de sesión dice cuánto código vive fuera de
la norma: `arquitectura: [!] N archivos en M carpetas viven fuera de la norma
del stack y nada los frena`. Adoptarlo es decisión del usuario.

## Qué está garantizado y qué no

- **Garantizado**: cada repo de la lista recibe la norma de su stack; las reglas
  que cubren el código nombran todo el código del repo; una copia vieja se
  actualiza o se reporta; ningún "OK" tapa código fuera de la norma.
- **No garantizado**: que el código cumpla la arquitectura. Eso lo mide el
  trinquete y lo corrigen las features de normalización.
- **Límite conocido**: un repo JVM sin otra señal se detecta como
  `springboot-hexagonal`, y un repo Python como `python-dataproduct`, aunque use
  otro framework.

## Tests

[`tests/test_copias.py`](../tests/test_copias.py): alcance de las reglas, copias
viejas y modificadas, repos del proyecto, `verificar` y worktrees.
