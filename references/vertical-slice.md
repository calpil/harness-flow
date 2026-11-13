# Vertical Slice Development, TDD Incremental y Modo Pair (`hola-ai` en Harness Flow)

Esta referencia detalla cómo `harness-flow` integra las 3 skills de [`nschurmann/hola-ai`](https://github.com/nschurmann/hola-ai) (`/backlog` → `/story` → `/pair`), basadas en Extreme Programming (historias verticales, criterios de aceptación, TDD paso a paso, pair programming y diseño simple), con los gates determinísticos de `harness-flow` en todos los hosts soportados (`hermes`, `claude`, `gpt`/`codex`, `gemini`/AGY, `grok` y `kimi`).

## 1. Equivalencia directa `hola-ai` ↔ `harness-flow`

```text
hola-ai:       /backlog          →  /story                →  /pair                      →  (/code-review)
harness-flow:  Rol 0 (Producto)  →  Rol 1 (Leader: spec)  →  Rol 2 (pair o --delegado)  →  Rol 3 (Revisor) + Rol 4 (Cierre)
```

| Fase en `hola-ai` | Equivalente en `harness-flow` | Qué hace | Qué NUNCA hace |
| --- | --- | --- | --- |
| **`/backlog`** | **Rol 0: Producto** (`producto.py` / `/harness-flow:producto prd\|sdd` + `add.py`) | Convierte la idea en el PRD/SDD y en una lista corta (10–15 máx.) de candidatas verticales `F-n` de una línea con su frontera `requiere: F-m`. | Inventar requisitos sin preguntar, crear historias técnicas/por capa, estimar o escribir código final. |
| **`/story`** | **Rol 1: Leader** (`gate.py approve-spec` / `/harness-flow:spec <id>`) | Toma **una** candidata `F-n`, define 2–3 AC (tope 5) en Given/When/Then con su costura pública, un `## Plan vertical` (≤5 bullets sin código ni rutas) y `## Sugerencias (decision del usuario)` para aprobación. | Escribir código o inflar un spec con más de 5 AC (propone partir la historia en nuevas `F-n`). |
| **`/pair`** | **Rol 2: Implementer en Modo Pair** (`/harness-flow:implementar <id>`, pair por defecto) | Pair automático: la IA escribe y sella la **lista de tests** (solo nombres y costura) y ejecuta `1 test → Red → código mínimo → Green` ciclo tras ciclo, sin pausar. Pregunta por formulario solo en las paradas que lo piden. | Editar/borrar tests para que pasen, agregar alcance no pedido, o preguntar lo que el spec ya decide. |
| *(Review limpio)* | **Rol 3: Reviewer aislado** + **Rol 4: Cierre** (`revision.py` + `gate.py revision` + `close`) | Audita con contexto limpio cada AC (`archivo:linea`), la integridad de los tests (sin tests borrados ni valores calculados con la misma lógica del código) y sella el cierre. | Aprobarse a sí mismo desde la sesión que escribió el código. |

---

## 2. Rol 0 (Producto = `/backlog`): Conversación, 4 Decisiones Caras y Candidatas Verticales

### Protocolo de conversación (estilo `/backlog`)

1. **No inventes requisitos:** si algo no está claro en lo que cuenta el usuario, pregunta **una pregunta a la vez, proponiendo tu respuesta sugerida**.
2. **Stack y las 4 decisiones caras de cambiar:** en proyectos o módulos nuevos, acuerda el stack en el SDD y pregunta **solo si aplica** alguna de estas 4 decisiones costosas de cambiar después (solo pregunta; no las diseñes si no aplican):
   1. **Multi-tenant o multi-organización**
   2. **Modelo de permisos o roles**
   3. **Operación offline o sincronización**
   4. **Multi-idioma o multi-moneda**

   Además, en `## Decisiones` del SDD documenta las decisiones de persistencia/esquema, contratos entre servicios y concurrencia/idempotencia con su `Descartada: ...`, aplicando **YAGNI** (diseño simple, sin abstracciones "para el futuro") en todo lo demás.

### Reglas de corte en `## Features candidatas` (PRD)

1. **`F-1` es el *walking skeleton*:** la primera candidata es la historia más pequeña usable de punta a punta (sin mocks de infraestructura propia), demostrando que todas las capas conectan.
2. **Cada historia entrega valor por sí sola y corta todas las capas (`datos -> backend -> UI/API -> tests`):**
   - **Prohibido cortar por capa horizontal:** `"F-1: Configurar base de datos"`, `"F-2: Crear modelo de usuario"`, `"F-3: Hacer endpoints"`. Esa infraestructura se construye dentro de la primera historia funcional que la necesita.
   - **Prohibidas las historias técnicas:** el actor nunca es el desarrollador ni el sistema (`"Como sistema quiero..."`).
   - `producto.py aprobar --doc prd` emite aviso `[!]` si detecta candidatas con olor a capa horizontal o actor de sistema.
3. **Pocas historias (10–15 máximo), una línea por candidata:**
   - Sin criterios de aceptación, sin detalles técnicos y sin estimaciones en el PRD (eso pertenece al spec del Rol 1). Es preferible agregar candidatas después que recortar un backlog inflado.
   - `producto.py aprobar --doc prd` emite aviso `[!]` si el PRD supera `rules.max_candidatas_prd` (por defecto `15`).
4. **Frontera ejecutable (`requiere: F-n` / `Requires: #N`):**
   - Añade `(cumple O1; requiere: F-1)` **solo cuando una candidata no tiene sentido sin otra**:
     ```markdown
     - F-1: Walking skeleton de cierre de venta: registra el evento y emite acuse (cumple O1)
     - F-2: Llamada de agradecimiento en horario habil: programa llamada unica (cumple O1; requiere: F-1)
     ```
   - `producto.py` **bloquea** la aprobación si una candidata cita una `F-m` inexistente, depende de sí misma o forma un ciclo.
   - `add.py --candidata F-n` hereda los bloqueos automáticamente (o recibe `--requiere 1,2`) y `estado.py` destaca en `Siguiente paso sugerido:` la **frontera** (la primera feature sin bloqueos abiertos).
5. **Refactors amplios mediante *Expand–Contract* (Parallel Change):**
   - Si un cambio requiere migrar un contrato o esquema compartido, córtalo en pasos que nunca rompan la app: (1) *Expand* (añadir lo nuevo junto a lo viejo), (2) *Migrate* (mover consumidores), (3) *Contract* (eliminar lo viejo).
6. **Features de negocio basadas en IA o analítica predictiva (Chip Huyen - ver `references/ai-engineering-chip-huyen.md`):**
   - Prohibido cortar historias de IA por capas horizontales (*"F-1: recolectar telemetría"*, *"F-2: entrenar modelo"*, *"F-3: armar dashboard"*).
   - `F-1` es un walking skeleton predictivo completo: ingesta de telemetría de 1 activo (ej. sala de bombas) $\rightarrow$ baseline heurístico + inferencia con Structured Output $\rightarrow$ alerta observable en UI/API $\rightarrow$ test con caso del Golden Dataset.
   - Slices posteriores expanden a nuevos activos (ej. `F-2: pozos de agua y achique`, `F-3: ascensores por viajes y vibración`) o añaden el circuito de calibración (`F-4: confirmación en terreno Human-in-the-Loop`).
   - Todo slice de IA debe contemplar un fallback determinista infalible si la inferencia externa falla.

---

## 3. Rol 1 (Leader = `/story`): Costuras Públicas, Mini-Plan y "Sugiere, no decidas"

Al refinar **una sola** feature en `docs/spec-feature-<id>-<slug>.md` desde `templates/spec.md`:

1. **2 a 3 AC ideales (máximo 5 por slice):**
   - Redacta entre 2 y 3 criterios en formato Given/When/Then (hasta un tope de `rules.max_acs_por_slice = 5`). Solo describen *qué* ve o recibe el usuario, nunca *cómo* se implementa.
   - **Si necesita más criterios, no infles el spec:** propón al usuario partir la feature en nuevas candidatas `F-n`, y continúa con la primera. Los cortes entran al backlog solo con su SÍ (`add.py --yes --peso`); un corte chico va como enmienda o se anota con `hallazgo.py` (ver [`hallazgos.md`](hallazgos.md)). `gate.py check-spec` y `approve-spec` avisan con `[!]` si hay más de 5 AC.
2. **Costuras públicas de prueba (`[costura: ...]` o `Costura: ...`):**
   - Cada AC declara dónde se probará en el nivel práctico más alto:
     - `endpoint` / `api` / `http` / `grpc` / `cli`
     - `servicio` / `dominio` / `usecase` / `handler`
     - `ui` / `componente` / `pantalla`
     - `integracion` / `evento` / `cola` / `db`
     - `manual` (para criterios visuales o que no se pueden automatizar bien)
   - `gate.py` avisa con `[!]` si falta declarar costuras o si una costura se acopla a detalles internos (`mock`, `privado`, `interno`, `spy`).
3. **`## Plan vertical` (máximo 5 bullets, sin código ni nombres de archivos):**
   - Explica cómo el slice atraviesa las capas con lo mínimo que cumple los AC. Si supera 5 pasos, `gate.py` emite aviso `[!]`.
4. **`## Sugerencias (decision del usuario)` ("Sugiere, no decidas"):**
   - Si un patrón podría ayudar (composición de middlewares, extraer un componente, etc.), menciónalo en `## Sugerencias (decision del usuario)` con su porqué **únicamente si hay una señal concreta en el código actual** (por ejemplo, algo que ya se repite), nunca por adelantado. El usuario decide si entra o no antes de sellar con `approve-spec --yes`.

---

## 4. Rol 2 (Implementer = `/pair` o Subagente): Lista de Tests, Ciclo TDD y las 5 Paradas

El Rol 2 soporta dos modos:
- **Modo Pair automático (por defecto, en toda feature):** la IA escribe los tests y el código en el worktree y **avanza sola, ciclo tras ciclo**. El humano decide solo lo que es suyo: las paradas que preguntan y lo que él sella. No hay que activarlo: `gate.py approve-spec` lo registra al sellar el spec por primera vez y `/harness-flow:implementar <id>` lo sigue.
- **Modo delegado (solo si el usuario lo pide o la sesión no tiene usuario):** subagente autónomo (`harness-flow:implementer` o equivalente del host) que ejecuta los ciclos TDD verticalmente en el worktree y entrega `docs/impl-<id>.md`. Se registra con `worktree.py start --feature <id> --delegado` o `worktree.py modo --feature <id> --delegado`.

**El protocolo viaja en el brief.** `contexto.py brief --feature <id>` imprime, en cualquier modo, el resumen del protocolo de esta sección (un test a la vez y las 5 paradas) y el comando que imprime este archivo entero (`normas.py --ref vertical-slice`). Trae además las reglas de cada stack, el índice de sus skills con el comando que imprime cada una (`stack.py skill`) y las normas de ingeniería. Un agente al que se le delega con el brief pegado tiene el paquete completo: no hay que anexarle nada.

### Protocolo completo de `/pair` dentro de Harness Flow

#### Paso 1. Revisión (`1. Review`)
- Verifica el gate del spec (`$PY "$H/gate.py" check-spec --feature <id>`), asegura el worktree (`worktree.py start --feature <id>`) y lee el brief (`contexto.py brief --feature <id>`).
- Contrasta el `## Plan vertical` del spec contra el código actual del worktree. Si algo ya no encaja, díselo al usuario antes de empezar. Si el spec no tiene plan vertical, propón uno de máximo 5 bullets y espera su aprobación.

#### Paso 2. Lista de tests (`2. Test list`)
- A partir de los AC del spec, **escribe primero la lista de tests: solo los nombres, sin escribir el código de los tests todavía**, en `docs/tests-<id>.md`.
- Indica **dónde** se prueba cada uno (`endpoint`, `servicio`, `componente/ui`, `integracion` — prefiriendo el nivel práctico más alto). Un AC va como **verificación manual** solo si el spec lo declara `[costura: manual]`.
- **Séllala tú** con `gate.py sellar-tests --feature <id>`, muéstrala en el chat y empieza el primer ciclo. **No esperes aprobación.** Si el usuario objeta un test, corrige y vuelve a sellar. (En modo subagente delegado, el implementer arma esta misma lista internamente desde los AC antes de escribir el primer test).
- La lista puede crecer mientras implementas: se vuelve a sellar sin preguntar. **Quitar un test sellado, o dejar un AC solo con verificación manual que el spec no declara, lo decide el usuario**: el gate se niega sin `--yes`.

#### Paso 3. Ciclo (`3. Cycle`: 1 paso = 1 test de la lista)
1. Escribe **el test** (uno solo).
2. Córrelo y **comprueba que falla** (**Red**).
3. Escribe el **código mínimo** que lo hace pasar. Nada que el test no exija.
4. Corre los tests y **comprueba que pasan** (**Green**).
5. Refactor en verde, dentro de los archivos de la feature.

Reporta el ciclo en una línea y **sigue con el siguiente sin preguntar**:

```text
✅ "<nombre del test>" — <qué hice o qué decisión menor tomé> (<archivo:línea>)
```

**Nunca "N tests y luego el código"**: un ciclo completo por test.

**Paso a paso, solo si el usuario lo pide.** Si dice "paso a paso", pausa tras cada ciclo con `¿Cambiamos algo o seguimos con "<siguiente test>"?`. Con **"haz N"** / **"avanza N"** ejecutas `N` ciclos completos y vuelves a pausar, mostrando primero los tests y después el código.

#### Las 5 paradas
| # | Qué pasa | Qué haces |
| --- | --- | --- |
| 1 | **Decisión de diseño no prevista:** necesitas una decisión que no está en el plan ni en el spec | **Pregunta** al usuario (o a quien te delegó) |
| 2 | **Alcance no pedido (YAGNI):** se te ocurre agregar algo que ningún AC pide | **No lo agregues.** Anótalo como hallazgo (`hallazgo.py anotar`) y sigue |
| 3 | **Integridad de tests:** hacer pasar un test requeriría cambiar, saltar (`skip`) o borrar un test existente | **Pregunta** |
| 4 | **Dos intentos sin verde** en el mismo paso | Vuelve al último verde y **pregunta** |
| 5 | **Paso excesivo:** supera ~50 líneas o toca más de 3 archivos | **Pártelo tú** en pasos más chicos y sigue |

#### Reglas de los tests (`Test rules`)
- **Independencia del valor esperado:** el valor esperado del test sale del criterio de aceptación, **nunca calculado con la misma lógica o fórmula que el código de producción**.
- **Interfaz pública:** prueba el comportamiento a través de la costura pública declarada, nunca acoplado a detalles internos o privados.

#### Paso 4. Chequeo final (`4. Check`)
Cuando toda la lista de tests está en verde:
- Pide al usuario, en un solo formulario, los criterios de **verificación manual** (`[costura: manual]`).
- Si algo se repite o quedó desprolijo dentro de los archivos de la feature, **refactoriza con los tests en verde, en su propio commit**. Un refactor que cambia una interfaz pública o sale de esos archivos es una decisión de diseño: parada 1.
- Si se tomó una decisión que aplica a todo el proyecto, propón registrarla en una lección (`leccion.py`) o en la guía del proyecto.
- Escribe `docs/impl-<id>.md` en la raíz con una sección `## AC-n` por cada criterio citando `archivo:linea` y el comando ejecutado.
- Sigue con el **Rol 3 (`/harness-flow:review <id>` / `revision.py --feature <id> --briefing`)** en un subagente aislado con contexto limpio (nunca revises tu propio código).

#### Paso 5. Commits (`5. Commit`)
- **Separa siempre funcionalidad y refactor en commits distintos** (`feat:`/`fix:` vs `refactor:`).
- Commitea en la rama del worktree de la feature cada unidad lógica en verde, **sin pedir permiso**, con la convención de commits del proyecto. La rama de la feature es tuya; lo que sale de ella (merge, push, deploy) sigue las reglas del proyecto. El Rol 3 y `gate.py close` exigen el árbol limpio y diffean `merge-base(base, HEAD)..HEAD`.

---

## 5. Configuración Multi-LLM para el flujo completo

| Host / Proveedor | Rol 0 (`/backlog` → PRD/SDD) y Rol 1 (`/story` → Spec) | Rol 2 en Modo Pair (por defecto) | Rol 2 Delegado (`--delegado`) | Rol 3 (Revisor aislado) |
| --- | --- | --- | --- | --- |
| **Claude Code** | `/harness-flow:producto`, `/harness-flow:spec` (`claude-opus-5-5`, `xhigh`) | `/harness-flow:implementar <id>` en la sesión principal (pair por defecto) | `Agent(harness-flow:implementer)` (`claude-sonnet-5-5`, `high`/`xhigh`) | `/harness-flow:review <id>` → `Agent(harness-flow:revisor)` (`claude-opus-5-5`, `xhigh`/`high`) |
| **Hermes** | Sesión en `gpt-6-astra` (`medium`/`high`), `claude-opus-5-5` (`xhigh`) o `gemini-4-argon` (`high`) | Sesión interactiva de Hermes, ciclo tras ciclo sin pausar | `claude -p --agent harness-flow:implementer` o perfil del rol | `claude -p --agent harness-flow:revisor` o `delegate_task` con briefing |
| **GPT / Codex** | `gpt-6-astra` (`medium`/`high`) | Sesión interactiva de Codex en el worktree | Sesión o `codex exec` (`gpt-6.1-sol`, `xhigh`) | `codex exec` / subagente aislado con briefing |
| **AGY / Gemini** | Sesión en Gemini 4 (`Hydrogen (High)` / `Argon (High)`) | Sesión principal de AGY, ciclo tras ciclo sin pausar (`ask_question` solo en las paradas que preguntan) | `invoke_subagent` (`TypeName: "self"`, `Model: "inherit"`, `Workspace: "inherit"`) | `invoke_subagent` (`TypeName: "self"`, `Model: "inherit"`, `Workspace: "inherit"`) |
| **Grok** | Sesión principal de Grok | Sesión principal de Grok en el worktree | Sesión principal en el worktree | `spawn_subagent` y espera el id ([grok.md](grok.md)) |
| **Kimi Code** | `/harness-flow:producto`, `/harness-flow:spec` | `/harness-flow:implementar <id>` en la sesión (pair por defecto) | `Agent(implementer)` | `/harness-flow:review <id>` → `Agent(revisor)` o `kimi -p` |

---

## 6. Modo Pair Automático y Protocolo de Preguntas de Formulario

### Activación automática
- **El Modo Pair es el modo por defecto en cualquier repo**, tenga o no un stack detectado. Lo registra `gate.py approve-spec` en el backlog (`modo: pair`) al sellar el spec por primera vez, `worktree.py start` lo confirma y el brief lo repite. Así queda fijado también en una raíz multi-repo, donde el árbol se declara con `worktree.py register` y `start` no corre.
- **Se delega solo por decisión del usuario** (`worktree.py start --delegado`, o `worktree.py modo --feature <id> --delegado`) o cuando la sesión no tiene usuario (`claude -p`).
- **El rastro del modo pair es la lista de tests sellada.** Se escribe en `docs/tests-<id>.md` (plantilla `templates/tests.md`), con al menos una línea `- AC-n: <test> [costura: ...]` por AC, y la sella quien implementa con `gate.py sellar-tests --feature <id>`. `gate.py close` se niega sin ese sello, si la lista cambió después de sellarla, o si el spec ganó un AC que la lista no cubre.
- Una feature cuyo spec se selló antes de este registro no tiene `modo` y no queda sujeta al gate: puede tener el trabajo hecho. `worktree.py register` lo avisa; si aún no hay código, se fija con `worktree.py modo --feature <id> --pair`.
- **Lo que el gate comprueba y lo que no.** Comprueba que la lista cubre cada AC, que el sello está fresco y que ningún test sellado se quitó sin el SÍ del usuario. No comprueba el ritmo: eso lo ve el usuario en la sesión.

### "Pair automático": qué significa
El agente avanza solo. No pausa tras cada ciclo ni pregunta si sigue. Un formulario le cuesta al usuario una interrupción: se usa cuando la respuesta cambia lo que se construye, no para confirmar lo que el spec ya decidió.

### Cuándo un formulario hace falta

| Caso | Por qué pregunta |
| --- | --- |
| Parada 1: decisión de diseño que el plan o el spec no trae | La decisión es del usuario |
| Parada 3: pasar exige cambiar, saltar o borrar un test | Debilitar un test no lo decide quien implementa |
| Parada 4: dos intentos sin verde | Seguir a ciegas gasta más que preguntar |
| La lista quita un test sellado, o deja un AC solo manual que el spec no declara | El gate lo exige (`sellar-tests --yes`) |
| Lo que sella el usuario: enmienda, ficha nueva, y el cierre o la publicación que el proyecto reserve | Son sus rituales |
| Verificación manual, al final | Solo el usuario puede mirarlo |

### Cuándo NO hace falta

| No preguntes | Qué haces |
| --- | --- |
| Si sigues con el test siguiente | Sigues |
| Si apruebas la lista de tests | La sellas, la muestras y empiezas |
| El orden o el nombre de los tests | Los decides |
| El mensaje de un commit en la rama de la feature | Commiteas |
| Un refactor en verde dentro de los archivos de la feature | Lo aplicas en su commit |
| Cómo partir un paso grande | Lo partes |
| Algo que ningún AC pide | No lo agregas; lo anotas como hallazgo |
| Algo que el spec ya decide | Lees el spec |

### Cómo preguntar
- **Un formulario, no varios.** Junta las preguntas pendientes, también las de otras features en curso. La opción recomendada va primera.
- **No te quedes esperando.** Mientras llega la respuesta, sigue con lo que no depende de ella.
- **Una enmienda es un solo formulario.** Lleva la propuesta ya escrita (`templates/enmienda.md`). No preguntes primero "dónde lo arreglo" y después "apruebas".
- **Herramienta según el host.** En AGY / Gemini, `ask_question` con opciones y recomendación `(Recommended)`. En Claude Code, `AskUserQuestion`. En GPT/Codex, Grok, Kimi y Hermes, un formulario Markdown con opciones `[A]`, `[B]`, `[C]` y la `(Recomendada)` marcada.

### Varias features en paralelo
Si el usuario pide avanzar varias features a la vez y el host tiene subagentes, va un implementer por feature, cada uno en su worktree y con su brief entero. El modo sigue siendo `pair`: cada subagente escribe su lista de tests y la sesión principal la sella. Un subagente no puede preguntar al usuario: devuelve la parada. La sesión principal la responde desde el spec si el spec ya la decide; si no, la lleva al usuario en un solo formulario con las de las otras features.
