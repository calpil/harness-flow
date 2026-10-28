# Vertical Slice Development, TDD Incremental y Modo Pair (`hola-ai` en Harness Flow)

Esta referencia detalla cómo `harness-flow` integra las 3 skills de [`nschurmann/hola-ai`](https://github.com/nschurmann/hola-ai) (`/backlog` → `/story` → `/pair`), basadas en Extreme Programming (historias verticales, criterios de aceptación, TDD paso a paso, pair programming y diseño simple), con los gates determinísticos de `harness-flow` en todos los hosts soportados (`hermes`, `claude`, `gpt`/`codex`, `gemini`/AGY, `grok` y `kimi`).

## 1. Equivalencia directa `hola-ai` ↔ `harness-flow`

```text
hola-ai:       /backlog          →  /story                →  /pair                      →  (/code-review)
harness-flow:  Rol 0 (Producto)  →  Rol 1 (Leader: spec)  →  Rol 2 (--pair o delegado)  →  Rol 3 (Revisor) + Rol 4 (Cierre)
```

| Fase en `hola-ai` | Equivalente en `harness-flow` | Qué hace | Qué NUNCA hace |
| --- | --- | --- | --- |
| **`/backlog`** | **Rol 0: Producto** (`producto.py` / `/harness-flow:producto prd\|sdd` + `add.py`) | Convierte la idea en el PRD/SDD y en una lista corta (10–15 máx.) de candidatas verticales `F-n` de una línea con su frontera `requiere: F-m`. | Inventar requisitos sin preguntar, crear historias técnicas/por capa, estimar o escribir código final. |
| **`/story`** | **Rol 1: Leader** (`gate.py approve-spec` / `/harness-flow:spec <id>`) | Toma **una** candidata `F-n`, define 2–3 AC (tope 5) en Given/When/Then con su costura pública, un `## Plan vertical` (≤5 bullets sin código ni rutas) y `## Sugerencias (decision del usuario)` para aprobación. | Escribir código o inflar un spec con más de 5 AC (propone partir la historia en nuevas `F-n`). |
| **`/pair`** | **Rol 2: Implementer en Modo Pair** (`/harness-flow:implementar <id> --pair`) | Pair programming (Driver = IA, Navigator = humano): acuerda la **lista de tests** (solo nombres y costura) y ejecuta `1 test → Red → código mínimo → Green`, parando en cada paso con un micro-mensaje. | Editar/borrar tests para que pasen, agregar alcance no pedido, o commitear sin acuerdo del usuario en modo `--pair`. |
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

---

## 3. Rol 1 (Leader = `/story`): Costuras Públicas, Mini-Plan y "Sugiere, no decidas"

Al refinar **una sola** feature en `docs/spec-feature-<id>-<slug>.md` desde `templates/spec.md`:

1. **2 a 3 AC ideales (máximo 5 por slice):**
   - Redacta entre 2 y 3 criterios en formato Given/When/Then (hasta un tope de `rules.max_acs_por_slice = 5`). Solo describen *qué* ve o recibe el usuario, nunca *cómo* se implementa.
   - **Si necesita más criterios, no infles el spec:** propón al usuario partir la feature en nuevas candidatas `F-n` para agregarlas con `add.py`, y continúa con la primera. `gate.py check-spec` y `approve-spec` avisan con `[!]` si hay más de 5 AC.
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
- **Modo delegado (por defecto):** subagente autónomo (`harness-flow:implementer` o equivalente del host) que ejecuta los ciclos TDD verticalmente en el worktree y entrega `docs/impl-<id>.md`.
- **Modo Pair interactivo (`--pair`):** la IA actúa como **Driver** (escribe los tests y el código en el worktree) y el humano como **Navigator** (revisa, decide y da el sí o no en cada paso). Se activa con `/harness-flow:implementar <id> --pair` o pidiendo modo pair en cualquier host.

### Protocolo completo de `/pair` dentro de Harness Flow

#### Paso 1. Revisión (`1. Review`)
- Verifica el gate del spec (`$PY "$H/gate.py" check-spec --feature <id>`), asegura el worktree (`worktree.py start --feature <id>`) y lee el brief (`contexto.py brief --feature <id>`).
- Contrasta el `## Plan vertical` del spec contra el código actual del worktree. Si algo ya no encaja, díselo al usuario antes de empezar. Si el spec no tiene plan vertical, propón uno de máximo 5 bullets y espera su aprobación.

#### Paso 2. Lista de tests (`2. Test list`)
- En modo `--pair`, a partir de los AC del spec, **propón primero la lista de tests: solo los nombres, sin escribir el código de los tests todavía**.
- Indica **dónde** se prueba cada uno (`endpoint`, `servicio`, `componente/ui`, `integracion` — prefiriendo el nivel práctico más alto) y marca los que no se puedan automatizar bien (por ejemplo, visuales) como **verificación manual**.
- **Espera la aprobación del usuario** antes de iniciar el primer ciclo. (En modo subagente delegado, el implementer arma esta misma lista internamente desde los AC antes de escribir el primer test).

#### Paso 3. Ciclo (`3. Cycle`: 1 paso = 1 test de la lista)
1. Escribe **el test** (uno solo).
2. Córrelo y **muestra que falla** (**Red**).
3. Escribe el **código mínimo** que lo hace pasar. Nada que el test no exija.
4. Corre los tests y **muestra que pasan** (**Green**).

En modo `--pair`, por defecto haces **1 paso y te detienes**, enviando este micro-mensaje:

```text
✅ Pasa "<nombre del test>". <qué hice en una línea> (<archivo:línea>)
Decisión tomada: <criterio o decisión menor tomada, si hubo alguna>
¿Cambiamos algo o seguimos con "<siguiente test>"?
```

Si el usuario dice **"haz N"** / **"avanza N"**, ejecutas `N` ciclos completos (`test → código → green`, uno tras otro), **nunca "N tests y luego el código"**. En un lote de `N`, **muestra primero los tests y después el código** (los tests son lo que el Navigator más necesita revisar).

#### Las 5 paradas inmediatas (incluso a mitad de un lote de `N`)
Detente de inmediato y consulta al usuario (o al coordinador si eres subagente) si:
1. **Decisión de diseño no prevista:** necesitas tomar una decisión de diseño que no está en el plan ni en el spec.
2. **Alcance no pedido (YAGNI):** se te ocurre agregar algo que no pidieron, aunque parezca razonable.
3. **Integridad de tests:** hacer pasar un test requeriría cambiar, saltar (`skip`) o borrar un test existente.
4. **Dos intentos sin verde:** llevas **dos intentos** en el mismo paso sin llegar a verde (revierte al último estado verde antes de replantear).
5. **Tamaño del paso excesivo:** el paso supera **~50 líneas o toca más de 3 archivos** — propón partirlo en pasos más pequeños.

#### Reglas de los tests (`Test rules`)
- **Independencia del valor esperado:** el valor esperado del test sale del criterio de aceptación, **nunca calculado con la misma lógica o fórmula que el código de producción**.
- **Interfaz pública:** prueba el comportamiento a través de la costura pública declarada, nunca acoplado a detalles internos o privados.

#### Paso 4. Chequeo final (`4. Check`)
Cuando toda la lista de tests está en verde:
- En `--pair`, verifica junto con el usuario los criterios marcados como **verificación manual** (`[costura: manual]`).
- Si algo se repite o quedó desprolijo, **sugiere** el refactor; el usuario decide. **Refactoriza solo con los tests en verde y nunca mezclado con funcionalidad nueva.**
- Si se tomó una decisión que aplica a todo el proyecto, propón registrarla en una lección (`leccion.py`) o en la guía del proyecto.
- Escribe `docs/impl-<id>.md` en la raíz con una sección `## AC-n` por cada criterio citando `archivo:linea` y el comando ejecutado.
- Sugiere correr el **Rol 3 (`/harness-flow:review <id>` / `revision.py --feature <id> --briefing`)** en un subagente aislado con contexto limpio (nunca revises tu propio código).

#### Paso 5. Commits (`5. Commit`)
- **Separa siempre funcionalidad y refactor en commits distintos** (`feat:`/`fix:` vs `refactor:`).
- **En modo `--pair`:** no hagas commits silenciosos en mitad del ciclo; cuando haya un buen punto (tests en verde, unidad lógica completa), avisa al usuario y **sugiere el mensaje de commit**. Con su confirmación, commitea en la rama del worktree de la feature (requerido antes de lanzar el Rol 3 y `gate.py close`, que exigen el árbol limpio y diffean `merge-base(base, HEAD)..HEAD`).

---

## 5. Configuración Multi-LLM para el flujo completo

| Host / Proveedor | Rol 0 (`/backlog` → PRD/SDD) y Rol 1 (`/story` → Spec) | Rol 2 en Modo Pair (`--pair`) | Rol 2 Delegado (Subagente) | Rol 3 (Revisor aislado) |
| --- | --- | --- | --- | --- |
| **Claude Code** | `/harness-flow:producto`, `/harness-flow:spec` (`claude-opus-5-5`, `xhigh`) | `/harness-flow:implementar <id> --pair` en la sesión principal | `Agent(harness-flow:implementer)` (`claude-sonnet-5-5`, `high`/`xhigh`) | `/harness-flow:review <id>` → `Agent(harness-flow:revisor)` (`claude-opus-5-5`, `xhigh`/`high`) |
| **Hermes** | Sesión en `gpt-6-astra` (`medium`/`high`), `claude-opus-5-5` (`xhigh`) o `gemini-4-argon` (`high`) | Sesión interactiva de Hermes ejecutando 1 ciclo por turno | `claude -p --agent harness-flow:implementer` o perfil del rol | `claude -p --agent harness-flow:revisor` o `delegate_task` con briefing |
| **GPT / Codex** | `gpt-6-astra` (`medium`/`high`) | Sesión interactiva de Codex en el worktree | Sesión o `codex exec` (`gpt-6.1-sol`, `xhigh`) | `codex exec` / subagente aislado con briefing |
| **AGY / Gemini** | Sesión en `Gemini 4 Argon (High)` | Sesión principal de AGY pausando tras cada micro-mensaje | `invoke_subagent` (`TypeName: "self"`, `Model: "inherit"`) | `invoke_subagent` (`TypeName: "self"`, `Model: "inherit"`, `Workspace: "inherit"`) |
| **Grok** | Sesión principal de Grok | Sesión principal de Grok en el worktree | Sesión o `spawn_subagent` | `spawn_subagent` (`isolation: none`, sin `resume_from`) |
| **Kimi Code** | `/harness-flow:producto`, `/harness-flow:spec` | `/harness-flow:implementar <id> --pair` en la sesión | `Agent(implementer)` | `/harness-flow:review <id>` → `Agent(revisor)` o `kimi -p` |
