# harness-flow

Framework de desarrollo guiado por especificación (*spec-driven development*) con **gates ejecutables determinísticos** para proyectos monorepo y multi-repo, diseñado para agentes de inteligencia artificial: [Hermes Agent](https://hermes-agent.nousresearch.com), [Claude Code](https://code.claude.com), OpenAI GPT/Codex, Google Antigravity (AGY) / Gemini CLI, Grok y Kimi Code.

Es el puerto directo del arnés original en Rust (`harness_process`) a un entorno nativo de agentes: **sin binarios que compilar por sistema operativo, sin instaladores por proyecto y con dependencias mínimas** (Python estándar, más `psycopg` opcional para el grafo Postgres compartido).

Los scripts detectan automáticamente el host y el sistema operativo (macOS, Linux y Windows). Lo único que se adapta entre agentes son los mecanismos de lanzamiento del subagente revisor y las rutas de memoria procedural.

---

## Qué hace (Capacidades Implementadas)

### 1. Flujo Estricto en 4+1 Roles & TDD Vertical
Prohíbe el desarrollo horizontal por capas y las promesas sin verificar en el chat. Cada historia se implementa como un incremento observable de punta a punta (*Vertical Slice*):

- **Rol 0: Producto (`producto.py`)**: Redacta borradores en `docs/borrador-prd.md` y `docs/borrador-sdd.md`. Aplica el cuestionario de las **4 decisiones costosas de cambiar** (multi-tenant, roles/permisos, offline/sync, multi-idioma/moneda), descompone el backlog en 10–15 candidatas verticales `F-n` con un *walking skeleton* inicial (`F-1`), y ejecuta el ritual de aprobación explícita `--yes` que sella `docs/prd/PRD-master.md` y `docs/sdd.md` como rutas protegidas.
- **Rol 1: Leader (`gate.py approve-spec`, `templates/spec.md`)**: Toma una candidata `F-n` y redacta el spec con 2 a 3 Criterios de Aceptación (AC) en formato Given/When/Then. Declara obligatoriamente la **costura pública de prueba** (`[costura: endpoint|servicio|ui|integracion|manual]`). Si el spec debe cambiar tras haber iniciado trabajo, exige una **enmienda formal** (`gate.py enmienda`) que invalida automáticamente verificaciones y reviews previos.
- **Rol 2: Implementer (`implementer.md`, `worktree.py`)**: Trabaja aislado en un `git worktree` dedicado. Aplica TDD vertical estricto (`1 test en costura pública -> Red -> código mínimo -> Green -> Refactor`) con 5 paradas XP inmediatas ante desvíos. Ofrece dos modos:
  - *Subagente delegado (por defecto)*: ejecución autónoma con amnesia deliberada y brief compacto de contexto.
  - *Modo Pair interactivo (`--pair`)*: la IA actúa como Driver y el humano como Navigator en la sesión principal, avanzando micro-ciclo a micro-ciclo con confirmación explícita.
  - Registra citas verificables `archivo:linea` en `docs/impl-<id>.md`.
- **Rol 3: Reviewer Aislado (`revisor.md`, `revision.py`)**: Subagente independiente lanzado con el briefing autocontenido de `revision.py --briefing`. Contrasta las citas contra el código real, audita la integridad de los tests (prohíbe tests tautológicos o relajar aserciones viejas) y utiliza `codebase-memory-mcp` (`search_graph`, `trace_path`) para orientarse sin modificar código. Sella formalmente desde la sesión principal (`gate.py revision --veredicto approved|changes_requested|blocked`) con un tope de 2 rondas.
- **Rol 4: Cierre (`gate.py close`)**: En monorepos ejecuta `git merge --no-ff`. En multi-repos sin `.git` valida la integración manual (`--integrated`). Archiva el progreso en `harness/progress/archive/`, sincroniza la documentación generada en `docs/prd/` y `docs/sdd.md`, ejecuta los runners post-merge medidos y valida el registro de la lección procedural en `leccion.py`.

### 2. Verificadores Post-Merge Medidos Multi-Toolchain
Los tests de feature solo miden su propio worktree; no pueden anticipar choques de integración entre ramas paralelas. El arnés mide el **delta de rojos** contra una foto tomada antes del merge:
- **Go (`postmerge_medido.py`, `postmerge_exec.py`)**: Procesa `go test -json` instrumentado con bandera `-exec`. Detecta fallos nuevos discriminados por `(paquete, test)`, abortando ante paquetes que no compilan, `panic` en `init()` o tests eliminados (exit 2).
- **Frontend / Angular / TypeScript (`postmerge_frontend.py`)**: Ejecuta suites bajo Angular 22, Vitest 4 y `node:test` mediante reporters dedicados (`frontend_vitest_reporter.mjs`, `frontend_node_reporter.mjs`).
- **Infraestructura Terraform (`postmerge_terraform.py`)**: Valida código HCL con `terraform fmt`, `terraform validate` y `terraform test`.
- *Nota:* El script antiguo `scripts/postmerge.py` ha sido completamente retirado y neutralizado para prevenir falsos verdes por parsing de regex.

### 3. Memoria Procedural Cruzada entre Agentes (`leccion.py`)
Las lecciones aprendidas son memoria del usuario, no del agente donde se descubrieron:
- Escanea y valida lecciones en todas las raíces de agentes de la máquina: `~/.hermes/skills`, `~/.claude/skills`, `~/.gemini/config/skills`, `~/.gemini/skills`, `~/.agents/skills`, `~/.codex/skills`, `~/.grok/skills` y `~/.kimi-code/skills`.
- Espejado bidireccional (`leccion.py espejar`): traslada lecciones creadas en Claude Code hacia Hermes y deja symlinks para mantenerlas sincronizadas.
- El cierre (`gate.py close --leccion <clase>`) exige que la lección exista físicamente en alguna raíz activa.

### 4. Telemetría y Monitoreo Forense de MCP (`cbm_procesos.py`, `contexto.py`)
- Monitorea el daemon de `codebase-memory-mcp` y sus trabajadores.
- Identifica y elimina procesos huérfanos reasignados a `PID 1` y archivos temporales abandonados (`*.db.stage.*`).
- Detecta sockets cortados (`->(none)`) y recupera daemons huérfanos de socket mediante `--reiniciar-daemon`. En Windows opera con *no-op* seguro para evitar falsos positivos.
- Extrae resúmenes contextuales compactos por feature combinando el backlog, objetivos del PRD, decisiones del SDD y dependencias cruzadas.

### 5. Memory Hub Postgres & Visualización en Obsidian
- **Memory Hub (`hub.py`)**: Grafo relacional multi-repo compartido entre máquinas (`graph_nodes`, `graph_edges`) sobre PostgreSQL con `psycopg`. Responde a consultas de impacto transversal antes de diseñar specs. Los servicios salen de los repos reales del proyecto (cada raíz de `harness/grafos.json`), con cualquier nombre; `derivar-graphify` retira las dependencias que ya no están en el grafo; leer no exige permiso de DDL, y `HARNESS_SIN_HUB=1` impide toda conexión.
- **Vault Obsidian (`vault.py`)**: Genera un cuadro de mando de notas interconectadas en `docs/vault/` para visualizar el backlog vivo, el estado de cada feature, specs y decisiones de arquitectura (con grafo estructural opt-in mediante `--con-grafo`).

### 6. Sincronización Remota con Atlassian (`atlassian.py`)
- Si existe `harness/atlassian.json`, sincroniza issues en Jira, subtasks por AC y páginas vivas en Confluence con el spec, la evidencia y el review formal al invocar `gate.py close --publicar-atlassian`.

### 7. Gobernanza de Stacks Tecnológicos, Context7 y Modo Pair Automático (`stack.py`)
- **Detección Dinámica y Extensible de Stacks**: Motor declarativo (`assets/stacks/<stack-id>/manifest.json`) que escanea y clasifica cualquier repositorio o microservicio según archivos base (`files_any`/`files_all`), extensiones, dependencias de `package.json`, coincidencia de contenido (`content_matches`), indicadores estructurales (`strong_indicators`) y reglas de descarte (`anti_indicators`).
  - **Catálogo Activo (10 Stacks)**:
    - *Backend & Servicios*: **Golang Hexagonal** (`golang-hexagonal`), **.NET Hexagonal** (`dotnet-hexagonal`), **Rust Hexagonal** (`rust-hexagonal`), **Spring Boot Hexagonal** (`springboot-hexagonal`), **NestJS Hexagonal** (`nestjs-hexagonal`), y **Python Data Product** (`python-dataproduct`).
    - *Web & Frontend*: **Angular Product** (`angular-product`) y **Next.js Product** (`nextjs-product`).
    - *Mobile Nativo*: **iOS SwiftUI Clean Architecture** (`ios-swiftui-clean`) y **Android Jetpack Compose Clean Architecture** (`android-compose-clean`).
  - Extensible: un stack nuevo se soporta creando `assets/stacks/<nuevo-stack>/` con su `manifest.json`, sus reglas, sus skills y su `check-architecture.py`, sin tocar código Python: la detección, la verificación, el trinquete de arquitectura, el brief y la auditoría salen del manifest. Lo único escrito a mano por stack son los planes de refactor detallados y el scaffolding (ver "Verificación Normativa").
- **Arquitectura y Paridad Total Multi-LLM**:
  - **Triple espejo de reglas**: `.claude/rules/` (Claude Code), `.agents/rules/` (OpenAI Codex, Hermes, Grok, Kimi) y `.gemini/rules/` (Google Gemini CLI, Antigravity AGY).
  - **Distribución dual de skills**: `.claude/skills/` y `.agents/skills/` bajo el estándar abierto Agent Skills (YAML frontmatter con `name` y `description`).
  - **Contrato universal en `AGENTS.md`**: Síntesis generada automáticamente que extrae las restricciones arquitectónicas de `architecture.md` (descartando frontmatters específicos) para que cualquier LLM las absorba al inicio de sesión.
  - **Neutralidad de rutas internas**: las reglas y skills de los 10 stacks (44 archivos de reglas y 153 `SKILL.md`) utilizan rutas agnósticas (`.agents/skills/` o `.claude/skills/`), eliminando cláusulas restrictivas o scripts atados a un único host.
  - **Validadores de skills auto-descubribles**: `validate-agent-skills.mjs` en los 10 stacks detecta y valida automáticamente `.agents/skills` o `.claude/skills` sin flags obligatorios.
  - **Diagnóstico Dual en `stack.py verificar`**:
    - `Multi-LLM Ready: SI / NO`: Confirma si las reglas y skills requeridas están operativas en el entorno actual.
    - `Paridad Multi-LLM: TOTAL / PARCIAL`: Informa si todas las plataformas están simultáneamente sincronizadas (`claude-code`, `openai-codex/hermes/grok/kimi`, `gemini-cli/agy`) o si se debe ejecutar `stack.py normalizar`.
- **Verificación Normativa y Refactorización Guiada**: Audita límites de arquitectura en caliente mediante verificadores AST/regex (`check-architecture.py`). Si un repositorio no cumple, `stack.py refactorizar` genera un plan de refactorización: detallado y con scaffolding del esqueleto canónico (`--scaffold`) en 6 stacks (Go, Angular, .NET, Rust, iOS y Android), y genérico —un paso por cada incumplimiento que midió el verificador— en NestJS, Next.js, Python y Spring Boot, que todavía no tienen scaffolding.
- **Context7 & Documentación Oficial (`stack.py auditar`)**: los 10 stacks declaran en su manifest la documentación oficial, el id de librería de Context7 y su escáner de dependencias. El brief, el briefing del revisor y el borrador del SDD lo entregan en el bloque `DOCUMENTACION VIGENTE` de cada stack; la consulta a Context7 (`https://mcp.context7.com/mcp`) la hace el agente con el MCP de su host, ningún script se conecta. `stack.py auditar` corre el escáner del stack (`govulncheck`, `npm audit`, `pip-audit`, `cargo audit`, `osv-scanner`, `dependencyCheckAnalyze`...) y sale con exit 0 si está limpio, exit 1 si reporta hallazgos y exit 2 si no pudo medir. El escaneo DAST (`--dast`) es informativo: no cambia el exit. Ver [`references/context7-documentacion-oficial.md`](references/context7-documentacion-oficial.md).
- **Modo Pair Interactivo Automático**: es el modo por defecto de toda feature, con stack detectado o sin él (Driver = IA, Navigator = humano, ciclos TDD con micro-reportes). `gate.py approve-spec` lo deja en el backlog al sellar el spec por primera vez y `worktree.py start` lo confirma; `gate.py close` exige su rastro, la lista de tests aprobada por el usuario (`gate.py aprobar-tests`). Se delega solo por decisión del usuario (`--delegado`) o si la sesión no tiene usuario.
- **La norma del stack llega a cada rol por la salida de un script**: el brief (leader e implementer), el briefing del revisor y el borrador del SDD (rol producto) traen el texto completo de las reglas de cada stack —front y backend, cada repo con las suyas— y el índice de sus skills con la ruta de cada `SKILL.md`. No depende de que el host las cargue ni de que estén instaladas en el repo.
- **Protocolo de Preguntas de Formulario**: La IA interviene con formularios estructurados (`ask_question` en Gemini/AGY o formulario interactivo en otros hosts) **únicamente cuando es indispensable**: decisiones de diseño no previstas, paradas de TDD tras 2 fallos consecutivos sin verde, aprobación de lista de tests y confirmación de gates.
- **Principios de Karpathy y Norma Aeroespacial ASD-STE100**: Incorpora comunicación de alta densidad sin sobre-restricción (*over-constraining*), frases de máximo 20 palabras en voz activa, diagramas Mermaid en el SDD (`producto.py aprobar` avisa si no hay ninguno), criterios AC-n atómicos y micro-reportes telegráficos de pantalla de instrumentos en Pair Mode. Ver [`references/comunicacion-ste100-y-prompts.md`](references/comunicacion-ste100-y-prompts.md) y [`docs/principios-karpathy-ste100-harness-flow.md`](docs/principios-karpathy-ste100-harness-flow.md).
- **Una sola lista de normas de ingeniería para quien escribe y para quien revisa (`scripts/normas.py`)**: las normas que salen de los libros de abajo (DDIA, Ousterhout, Fowler y GoF, CLRS, Chip Huyen, Sam Newman, McConnell, OWASP, Context7, ASD-STE100 y Orosz) viven en un registro. Cada norma dice qué deja el leader en el spec, qué hace el implementer y qué audita el revisor. `contexto.py brief` imprime las dos primeras —en modo pair y en delegado— y `revision.py --briefing` la tercera, en cualquier host: el revisor no bloquea por algo que a quien escribió el código no se le dijo. Los AC negativos se marcan `[negativo]` y `approve-spec` avisa si un spec expone un endpoint sin ninguno.
- **Filosofía de Diseño de Software de John Ousterhout**: Adopta el combate sistemático de la complejidad (*A Philosophy of Software Design*): módulos profundos (*Deep Modules*) con interfaces compactas, erradicación de la sobre-fragmentación (*classitis* y micro-funciones de 3 líneas de Clean Code), ocultamiento de información (*information hiding*), absorción de la dificultad técnica hacia abajo (*pull complexity downwards*), diseño de dos alternativas por decisión (*design it twice*) y definición de errores fuera de la existencia. Ver [`references/filosofia-diseno-ousterhout.md`](references/filosofia-diseno-ousterhout.md).
- **Patrones de Datos Confiables y Escalables (DDIA - Martin Kleppmann)**: Prevención de *dual-write* mediante Transactional Outbox atómico en la misma TX ACID, control de concurrencia optimista (OCC) con columna `version`, mutaciones de red con `Idempotency-Key` y evolución de esquemas sin downtime (*Expand-Contract*). Ver [`references/patrones-datos-ddia.md`](references/patrones-datos-ddia.md).
- **Patrones GoF y Refactorización Disciplinada (Martin Fowler & Gang of Four)**: Integra los 23 patrones clásicos de GoF en capas de Arquitectura Hexagonal (Adapter en puertos, Strategy/State en dominio, Decorator/Proxy en cross-cutting, Factory en Composition Root), combinados con la regla de los "Dos Sombreros" de Kent Beck (feature vs refactor) y el saneamiento sistemático de los 24 *Code Smells* de Fowler (*Primitive Obsession*, *Shotgun Surgery*, *Feature Envy*, *Speculative Generality*, *Middle Man*). Ver [`references/patrones-gof-y-refactoring.md`](references/patrones-gof-y-refactoring.md).
- **Algoritmos y Estructuras de Datos de Rendimiento Crítico (CLRS - Cormen, Leiserson, Rivest, Stein)**: Análisis asintótico sistemático de complejidad temporal y espacial ($O(1)$, $O(\log N)$, $O(N)$), selección rigurosa de estructuras según stack y carga (Hash Tables, B-Trees, Heaps), detección de ciclos de dependencias en backlog mediante DFS de 3 colores ($O(V+E)$), ordenación topológica con algoritmo de Kahn ($O(V+E)$) y prevención de anti-patrones de rendimiento ($O(N^2)$ por bucles anidados sin indexar, consultas $N+1$ a persistencia y reasignación de colecciones sin pre-alocación). Ver [`references/algoritmos-y-estructuras-clrs.md`](references/algoritmos-y-estructuras-clrs.md).
- **Ingeniería de Inteligencia Artificial y Modelos Fundacionales (Chip Huyen)**: Arquitectura determinista de 5 capas (Guardrail de entrada, Context Assembly con maximización de *Prompt Caching*, Model Router, Foundation Model con *Structured Outputs* / JSON Schema y Validador de salida con *Circuit Breaker*), superación de "vibe checks" mediante *Golden Datasets*, mitigación de los 3 sesgos en el paradigma *AI-as-a-Judge* (posición, verbosidad mediante ASD-STE100 y auto-benevolencia mediante revisores amnésicos aislados), defensa contra *Indirect Prompt Injections* y auto-corrección acotada (*Bounded Reflection* $\le 2$). Ver [`references/ai-engineering-chip-huyen.md`](references/ai-engineering-chip-huyen.md).
- **Arquitectura de Microservicios y Sistemas Distribuidos (Sam Newman)**: Gobierno de sistemas finamente granulados (*Building Microservices* / *Monolith to Microservices*), evaluación previa *Monolith-First*, delimitación por *Bounded Contexts*, encapsulamiento estricto *Database per Service* (prohibición total de accesos SQL cruzados), selección pragmática de estilos de comunicación (Síncrono REST/gRPC vs Asíncrono EDA / colas bajo YAGNI), resiliencia distribuida (*Circuit Breakers*, *Bulkheads*, timeouts agresivos), trazabilidad mediante *Correlation IDs* (`X-Correlation-ID`) y evolución sin rotura de contratos mediante *Expand-Contract*. Ver [`references/microservicios-sam-newman.md`](references/microservicios-sam-newman.md).
- **Ingeniería de Software Pragmática y Design Docs (Gergely Orosz)**: Principios de madurez profesional y entrega predecible (*The Software Engineer's Guidebook* / *The Pragmatic Engineer*), estándar de Design Docs / RFCs (Contexto, Goals, Non-Goals, Alternatives Considered y Out of Scope), descomposición en incrementos de 1 a 3 días, disciplina de Code Review pragmático sin *nitpicking* cosmético, pago continuo de deuda técnica mediante la regla del Boy Scout (inversión del 10%-20%) y post-mortems sin culpa (*Blameless Post-Mortems*) institucionalizados con `leccion.py`. Ver [`references/ingenieria-software-gergely-orosz.md`](references/ingenieria-software-gergely-orosz.md).
- **Design Patterns (Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides)**: Un patrón es un nombre para un problema recurrente, no una clase que la feature estrena en el primer verde. Los capítulos 1 a 6 fijan cuándo entra en el PRD, el SDD, el plan y los dos sombreros. El catálogo no genera la feature: el patrón es el blanco del refactor, cuando el eje ya es real. El catálogo de los 23 sigue en la referencia de GoF y Fowler. Ver [`references/design-patterns-gof.md`](references/design-patterns-gof.md).
- **Construcción de software (Steve McConnell, *Code Complete*)**: La construcción es el centro del trabajo. La Parte I fija el terreno del rol 0 (problema, requisitos, arquitectura con estrategia de errores y barricada en SDD), la clase de software de cada feature y las prácticas de construcción que el arnés ya eligió. La Parte II fija el diseño de clases y rutinas, la barricada defensiva y el pseudocódigo del implementer, sin sustituir el TDD de la costura. Las Partes III y IV fijan el checklist de variables, nombres, tipos y control; el layout queda en el formateador del stack. La Parte V fija calidad, revisión, pruebas, depuración, refactor y afinado medido. La Parte VI fija tamaño, control del cambio, integración por rebanadas y herramientas. La Parte VII cierra el libro: layout del formateador, comentarios de intención y hábitos de oficio. Las siete partes integradas en [`references/code-complete-mcconnell.md`](references/code-complete-mcconnell.md).
- **Seguridad en Aplicaciones Web (OWASP Top 10, OWASP CLASP y OWASP ZAP)**: Metodología *Shift-Left* integral. El PRD incorpora Casos de Abuso (*Misuse Cases*); el SDD delimita Fronteras de Confianza (*Trust Boundaries*), barricadas defensivas, cifrado seguro y mitigación anti-SSRF; los specs formalizan Criterios de Aceptación Negativos (*Negative ACs*); el implementer programa defensivamente con consultas parametrizadas y zero secrets; el revisor aislado audita severidades bloqueantes; y `stack.py auditar --dast` ejecuta análisis dinámico DAST automatizado con OWASP ZAP sobre endpoints o contratos OpenAPI. Ver [`references/seguridad-owasp-y-zap.md`](references/seguridad-owasp-y-zap.md).
- **Auto-Normalización Temprana y Prioridad Arquitectónica (Feature #0)**: En el arranque de sesión (`estado.py`) el arnés evalúa el repositorio; al aprobar un spec o arrancar una feature solo bloquea, no normaliza. Con el trinquete de arquitectura adoptado (`harness/arquitectura-base.json`) la #0 ya no se crea: lo heredado se mide y solo puede bajar (ver `references/arquitectura-heredada.md`). Sin trinquete: si faltan reglas modulares o skills, las auto-instala inmediatamente (Nivel 1). Si el código fuente tiene violaciones de arquitectura detectadas por `check-architecture.py` (Nivel 2), crea automáticamente la **Feature #0** en el backlog y bloquea todas las features de negocio (`requiere: [0]`) hasta que el código quede normalizado y en verde.

#### Comandos de Gobernanza de Stacks (`stack.py`)
```bash
# 1. Detectar stack tecnológico en repositorio o microservicio
$PY "$H/stack.py" detectar --repo <ruta>

# 2. Diagnóstico normativo y paridad multi-LLM (rules, skills, arquitectura)
$PY "$H/stack.py" verificar --repo <ruta>

# 3. Normalizar repositorio (instala .claude/, .agents/, .gemini/ y genera AGENTS.md)
$PY "$H/stack.py" normalizar --repo <ruta>

# 4. Escáner de dependencias del stack (exit 0 limpio, 1 hallazgos, 2 sin medir) y DAST informativo
$PY "$H/stack.py" auditar --repo <ruta> [--dast] [--openapi ruta/a/openapi.json]

# 5. Generar plan de refactorización vertical o scaffolding canónico
$PY "$H/stack.py" refactorizar --repo <ruta> [--scaffold]

# 6. Stacks de todo el proyecto con reglas, skills y documentación vigente (rol producto)
$PY "$H/contexto.py" stacks [--resumen]

# 7. Normas de ingeniería: tabla norma × rol, o la parte de un rol
$PY "$H/normas.py" --cuadro
$PY "$H/normas.py" --rol producto|leader|implementer|revisor [--doc prd|sdd]

# 8. Fijar o cambiar el modo de implementación de una feature
$PY "$H/worktree.py" modo --feature <id> --pair|--delegado

# 9. Leer una skill de stack o una referencia entera (lo que usa un agente delegado)
$PY "$H/stack.py" skill <nombre> --stack <stack-id> [--repo <ruta>]
$PY "$H/normas.py" --ref <id-de-norma|archivo>
```

Guía de las normas, los AC negativos y el bloque `documentation`/`security_audit` del manifest: [`references/normas-de-ingenieria.md`](references/normas-de-ingenieria.md).

---

### 8. Trinquete de Arquitectura para Código Heredado (`arquitectura.py`)
Para proyectos con mucho código anterior al arnés. En vez de bloquear todo el backlog hasta reestructurarlo (la Feature #0 como muro) o de no medir nada:
- **Mide** cuánto código vive fuera de la norma del stack (`arquitectura.py inventario`) y lo **sella como base** con el SÍ del usuario (`adoptar --yes`). Desde ahí lo heredado solo puede bajar.
- **`gate.py close` se niega** si la feature hace crecer lo heredado, si cambia un archivo heredado en más de 50 líneas sin llevarlo a la norma, o si trae violaciones del verificador que no estaban en la base. Cada feature se mide contra su propio commit base.
- **Cuota de normalización**: tras 3 features de negocio, `approve-spec` exige cerrar una `--kind normalizacion` mientras quede algo heredado.
- **Genérico**: cada stack declara su norma en el bloque `layout` de su `manifest.json`; los diez del catálogo la declaran, y la plantilla oficial de cada uno mide cero código heredado.
- Guía: [`references/arquitectura-heredada.md`](references/arquitectura-heredada.md).

### 9. Contexto por Repo, Normalización Respetuosa y Context7 en Cada Host
- **El brief y el briefing del revisor** anuncian el stack de cada repo que la feature declara y traen el **texto completo de sus reglas**, el **índice de sus skills** con la ruta de cada `SKILL.md` y su **documentación vigente** (doc oficial, id de Context7 y escáner), también para los repos que viven fuera de la raíz. El rol producto recibe lo mismo, de todo el proyecto, al crear el borrador del SDD.
- **El brief es el paquete completo de un agente delegado**: trae el protocolo de implementación (TDD vertical y las 5 paradas) y, junto a cada índice, el comando con rutas absolutas que imprime una skill del stack (`stack.py skill`) o una referencia (`normas.py --ref`). Quien delega pega el brief entero y no anexa nada.
- **Modo Pair por defecto en cualquier repo**: `gate.py approve-spec` lo registra en el backlog al sellar el spec por primera vez y `worktree.py start` lo confirma (`--delegado` para delegar), así que vale también en una raíz multi-repo que usa `worktree.py register`. La lista de tests se sella con `gate.py aprobar-tests --yes` y `close` la exige en las features en modo pair.
- **`stack.py normalizar`** solo agrega lo que falta: no reemplaza un `AGENTS.md` existente ni reinstala las skills de `rules.stack_skills_excluidas`.
- **Verificadores sin falsos positivos**: workspaces Angular con varios proyectos, servicios Go sin `internal/` (aviso) y raíces de `grafos.json` como objetos.
- **Context7** documentado para Claude Code, Codex, Gemini CLI, Antigravity, Grok y Hermes; el revisor tiene Context7 y lectura web entre sus herramientas.

## Políticas de Modelos y Reasoning Effort

El arnés gestiona el modelo y el esfuerzo cognitivo según el proveedor del agente (ver detalles en [`references/modelos.md`](references/modelos.md)):

| Host / Proveedor | Rol 0 (Producto) y Rol 1 (Leader) | Rol 2 (Implementer) | Rol 3 (Reviewer Aislado) | Rol 4 (Cierre) | Estado / Rutinas |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Claude** (Claude Code / Hermes) | `claude-fable-5-2` (`high`) o `claude-opus-5-5` (`xhigh`), a elección del usuario | `claude-sonnet-5-5` (`high` / `xhigh`) | `claude-opus-5-5` (`xhigh` / `high` seg.) | `claude-opus-5-5` (`xhigh`) | `claude-haiku-5-5` (`medium`) |
| **OpenAI GPT-6** (Codex / Hermes) | `gpt-6-astra` (`medium` / `high`) | `gpt-6-astra` o `gpt-6.1-sol` (`medium` / `high`) | `gpt-6.1-sol` (`xhigh` / `high` seg.) | `gpt-6-luna` (`medium`) | `gpt-6-luna` (`low` / `medium`) |
| **Gemini 4 Argon** (AGY / Hermes) | `gemini-4-argon` (`high`) | `gemini-4-argon` (`high` / `medium` pair) | `gemini-4-argon` (`high`, subagente `self`) | `gemini-4-argon` (`medium`) | `gemini-4-argon` o Flash (`medium`) |
| **Grok** | Modelo de sesión | Sesión (`--pair` o autónomo) | Subagente `spawn_subagent` (espera id) | Gates locales | Gates locales |
| **Kimi Code** | Sesión principal | Sesión (`--pair` o autónomo) | Subagente `Agent` (`subagent_type: revisor`) | Gates locales | Gates locales |

**Fable 5.2 u Opus 5.5.** En Producto y Leader el usuario elige el modelo en un formulario, una vez por feature (por documento en el rol producto); `scripts/modelo.py` guarda la elección en el backlog. Si la sesión no está en lo elegido, el rol lo aplica solo con `/harness-flow:usar-opus` o `/harness-flow:usar-fable`, que fijan modelo y esfuerzo por el turno, sin pedir `/model` ni `/effort`. Cierre y Revisor siguen en Opus 5.5.

---

## Instalación y Configuración por Host

La skill se distribuye como un repositorio git clonado en el directorio de skills de tu agente, sin instaladores propietarios.

> [!TIP]
> **Consejo Pro: Un solo clon compartido para múltiples agentes**  
> Si utilizas varios agentes (Claude Code, Google Antigravity/Gemini, OpenAI Codex, Hermes) en la misma máquina, no dupliques el repositorio. Clónalo una sola vez en tu ubicación preferida y crea enlaces simbólicos en un solo paso:
> ```bash
> # 1. Clonar una sola vez (ej. en Hermes o ~/.agents/skills/)
> git clone https://github.com/calpil/harness-flow.git ~/.hermes/skills/software-development/harness-flow
> 
> # 2. Enlazar hacia los demás agentes:
> ln -s ~/.hermes/skills/software-development/harness-flow ~/.claude/skills/harness-flow
> ln -s ~/.hermes/skills/software-development/harness-flow ~/.gemini/config/skills/harness-flow
> ln -s ~/.hermes/skills/software-development/harness-flow ~/.agents/skills/harness-flow
> ```
> *(En Windows usa `mklink /J` en lugar de `ln -s`).*

### 1. Hermes Agent
Clona en el perfil activo (por defecto `default`):
```bash
git clone https://github.com/calpil/harness-flow.git ~/.hermes/skills/software-development/harness-flow
```

### 2. Claude Code
Clona en las skills de Claude Code (o crea un enlace simbólico desde el clon de Hermes):
```bash
git clone https://github.com/calpil/harness-flow.git ~/.claude/skills/harness-flow
# O enlace simbólico:
ln -s ~/.hermes/skills/software-development/harness-flow ~/.claude/skills/harness-flow
```
Claude Code carga automáticamente la capa nativa declarada en `.claude-plugin/plugin.json`:
- Subagentes: `harness-flow:revisor` (Opus 5.5 con herramientas MCP habilitadas) e `harness-flow:implementer` (Sonnet 5.5).
- Comandos: `/harness-flow:estado`, `/harness-flow:producto`, `/harness-flow:spec`, `/harness-flow:implementar`, `/harness-flow:review`, `/harness-flow:cierre`, y `/harness-flow:usar-opus` / `/harness-flow:usar-fable`, que solo fijan el modelo del turno. Los argumentos se leen como `$ARGUMENTS[0]`, `$ARGUMENTS[1]`.
- `.claude/settings.json` trae permisos para trabajar dentro del repo de la skill. Un plugin no puede distribuir permisos, así que en tus proyectos cada llamada a los scripts sigue pidiendo aprobación salvo que la autorices tú.

### 3. Google Antigravity (AGY) y Gemini CLI
AGY descubre skills globales en `~/.gemini/config/skills/`, mientras que Gemini CLI lee `~/.agents/skills/`:
```bash
ln -s ~/.hermes/skills/software-development/harness-flow ~/.gemini/config/skills/harness-flow
# Para Gemini CLI / Codex:
ln -s ~/.hermes/skills/software-development/harness-flow ~/.agents/skills/harness-flow
```

### 4. OpenAI GPT / Codex CLI
Codex lee `~/.agents/skills/` y `$CODEX_HOME/skills` (`~/.codex/skills`):
```bash
git clone https://github.com/calpil/harness-flow.git ~/.agents/skills/harness-flow
```
Incluye metadata de invocación automática en `agents/openai.yaml`.

### 5. Grok y Kimi Code
- **Grok**: lee `~/.agents/skills` y `~/.grok/skills` (ver [`references/grok.md`](references/grok.md)).
- **Kimi Code**: instala como plugin desde el TUI con `/plugins install <ruta-del-clone>` o symlink en `~/.kimi-code/skills/` (manifiesto [`kimi.plugin.json`](kimi.plugin.json)).

### 6. Entornos Windows
En Windows, crea un junction de directorio sin requerir elevación de privilegios:
```cmd
mklink /J "%USERPROFILE%\.claude\skills\harness-flow" "%LOCALAPPDATA%\hermes\skills\software-development\harness-flow"
```
Recomendado: instalar **Git for Windows** para utilizar sintaxis Bash estándar. Si se ejecuta en PowerShell puro, los comandos soportan invocación nativa mediante `python <skill>\scripts\entorno.py --powershell | Invoke-Expression`.

### Instalación de Dependencias del Hub
El script `entorno.py` configura automáticamente el entorno virtual neutro `~/.harness-flow/venv` con `psycopg`:
```bash
python3 ~/.hermes/skills/software-development/harness-flow/scripts/entorno.py --instalar-deps
```

---

## Flujo Operativo en un Proyecto

### 1. Inicialización de Entorno en la Sesión
Define las variables `$H` (directorio de scripts) y `$PY` (intérprete virtual) en tu terminal:
```bash
# bash / zsh (macOS / Linux)
eval "$(python3 <ruta-skill>/scripts/entorno.py --shell)"

# PowerShell (Windows)
python <ruta-skill>\scripts\entorno.py --powershell | Invoke-Expression
```
*(En Claude Code, AGY, Codex y Grok, ejecuta el comando y el script en la misma llamada de herramienta bash/terminal).*

### 2. Arranque de Sesión
Antes de realizar cualquier acción sustantiva, consulta el panorama del proyecto:
```bash
$PY "$H/estado.py"
```

### 3. Ciclo de Vida de una Feature (Monorepo)
```bash
# 1. Crear feature vinculada a candidata F-n del PRD
$PY "$H/add.py" --name "Checkout con cupon" --prd docs/prd/PRD-master.md --candidata F-3

# 2. Iniciar worktree aislado
$PY "$H/worktree.py" start --feature 1

# 3. Redactar spec y aprobar con ritual explícito del usuario
$PY "$H/gate.py" approve-spec --feature 1 --yes

# 4. Implementar bajo TDD vertical (modo delegado o modo pair)
# En Claude Code: /harness-flow:implementar 1 --pair

# 5. Generar briefing de revisión y lanzar revisor aislado
$PY "$H/revision.py" --feature 1 --briefing
# Tras revisar el informe en docs/review-1.md, sellar veredicto:
$PY "$H/gate.py" revision --feature 1 --veredicto approved

# 6. Cierre con merge, postmerge medido y registro de lección
$PY "$H/gate.py" close --feature 1 --status done --to main --leccion checkout
```

### 4. Ciclo de Vida en Raíz Multi-Repo (sin `.git` en la raíz)
Para proyectos multi-servicio donde cada componente es un repositorio independiente:
```bash
# Registrar repositorios y worktrees involucrados
$PY "$H/worktree.py" register --feature 1 --manifest /ruta/registro.json

# Verificar criterios de aceptación y generar briefing de revisión
$PY "$H/gate.py" verify --feature 1
$PY "$H/revision.py" --feature 1 --briefing

# Sellar revisión y cerrar validando ancestría y postmerge en todos los destinos
$PY "$H/gate.py" revision --feature 1 --veredicto approved
$PY "$H/gate.py" close --feature 1 --status done --to develop \
  --integrated --postmerge /ruta/bases-postmerge.json --leccion checkout
```

---

## Estructura del Repositorio

```text
harness-flow/
├── SKILL.md                          <- Instrucciones maestras leídas por los agentes
├── README.md                         <- Documentación general de arquitectura y uso
├── .claude-plugin/plugin.json        <- Manifiesto del plugin skills-dir para Claude Code
├── .claude/settings.json             <- Permisos pre-autorizados para Claude Code
├── kimi.plugin.json                  <- Manifiesto de plugin para Kimi Code
├── agents/
│   ├── openai.yaml                   <- Metadata de invocación automática en GPT/Codex
│   ├── revisor.md                    <- Subagente revisor aislado (Opus 5.5, MCP activado)
│   └── implementer.md                <- Subagente implementador (Sonnet 5.5)
├── commands/                         <- Comandos slash para Claude Code (/harness-flow:*)
│   ├── estado.md, producto.md, spec.md, implementar.md, review.md, cierre.md
│   └── usar-opus.md, usar-fable.md   <- Fijan modelo y esfuerzo del turno (los invocan producto y spec)
├── scripts/
│   ├── entorno.py                    <- Detección multi-host, resolución de $PY y $H
│   ├── estado.py                     <- Diagnóstico global de sesión, backlog y documentos
│   ├── gate.py                       <- Orquestador determinístico de gates (exit ≠ 0)
│   ├── comun.py, bloques.py          <- Parsing de ACs, firmas, hashes y manipulación segura
│   ├── init.py, add.py               <- Inicialización de proyecto y alta de features
│   ├── producto.py                   <- Rol 0: borradores y aprobación de PRD/SDD
│   ├── documentacion.py              <- Sincronización de bloques generados en PRD/SDD
│   ├── worktree.py, multirepo.py     <- Aislamiento de ramas y verificación multi-repo
│   ├── revision.py                   <- Generación del paquete de briefing para el revisor
│   ├── postmerge_medido.py           <- Runner post-merge medido para Go (JSON/-exec)
│   ├── postmerge_exec.py             <- Instrumentación de ejecución Go
│   ├── postmerge_frontend.py         <- Runner post-merge para Angular/Vitest/Node
│   ├── frontend_vitest_reporter.mjs  <- Reporter de integración Vitest
│   ├── frontend_node_reporter.mjs    <- Reporter de integración node:test
│   ├── postmerge_terraform.py        <- Runner post-merge para HCL/Terraform
│   ├── medicion_destino.py           <- Orquestador de mediciones pre y post merge
│   ├── cierre_local.py, retiros.py   <- Lógica de integración local y control de deprecaciones
│   ├── postmerge.py                  <- Stub neutralizado (aborto con exit 2 hacia runner medido)
│   ├── cbm_procesos.py               <- Telemetría forense y gestión de procesos CBM
│   ├── contexto.py                   <- Cálculo de frescura del grafo y generación de briefs
│   ├── stack.py                      <- Detección, verificación, normalización, refactorización y auditoría de stacks
│   ├── arquitectura.py               <- Trinquete de arquitectura: inventario, base, cuota y gate de código heredado
│   ├── modelo.py                     <- Elección de Fable 5.2 u Opus 5.5 para Producto y Leader
│   ├── leccion.py                    <- Memoria procedural cruzada entre agentes de la máquina
│   ├── hub.py                        <- Integración con Memory Hub Postgres
│   ├── vault.py                      <- Generación del vault de Obsidian en docs/vault/
│   └── atlassian.py                  <- Sincronización con Jira y Confluence
├── assets/stacks/                           <- Stacks tecnológicos declarativos (manifests, rules, skills, checkers)
│   ├── golang-hexagonal/             <- Arquitectura hexagonal Go, 4 rules, 9 skills, check-architecture.py
│   ├── angular-product/              <- Angular 17+ zoneless, 6 rules, 31 skills, check-architecture.mjs
│   ├── dotnet-hexagonal/             <- Clean Architecture C# 13/.NET 10, 4 rules, 9 skills, check-architecture.py
│   ├── rust-hexagonal/               <- Clean Architecture Rust (Axum/SQLx), 4 rules, 9 skills, check-architecture.py
│   ├── nextjs-product/               <- Next.js App Router, 6 rules, 37 skills, check-architecture.py
│   ├── springboot-hexagonal/         <- Spring Boot 3 Java hexagonal, 4 rules, 15 skills, check-architecture.py
│   ├── nestjs-hexagonal/             <- NestJS TypeScript hexagonal, 4 rules, 14 skills, check-architecture.py
│   ├── python-dataproduct/           <- Python data product / FastAPI / Polars, 4 rules, 11 skills, check-architecture.py
│   ├── ios-swiftui-clean/            <- iOS SwiftUI Clean Architecture, 4 rules, 9 skills, check-architecture.py
│   └── android-compose-clean/        <- Android Jetpack Compose Clean Architecture, 4 rules, 9 skills, check-architecture.py
├── templates/                        <- Plantillas oficiales de spec, prd, sdd, enmiendas y lista de tests (modo pair)
├── docs/
│   ├── README.md                     <- Índice y guía maestra de documentación técnica
│   ├── explicacion-y-diagnostico.md  <- Informe de auditoría exhaustiva y estado de salud
│   ├── principios-karpathy-ste100-harness-flow.md <- Principios de Karpathy y norma ASD-STE100 en el arnés
│   └── memoria-tecnica-implementaciones.md <- Memoria técnica exhaustiva: un hito por cada capacidad implementada
├── references/                       <- Documentación especializada por host y subsistema
│   ├── hosts.md, modelos.md, vertical-slice.md, contexto.md, lecciones-del-arnes.md
│   ├── multirepo.md, claude.md, openai.md, grok.md, kimi.md, entorno.md
│   ├── hub.md, obsidian.md, atlassian.md, documentacion.md
│   ├── arquitectura-heredada.md      <- Trinquete: base, cuota de normalización y código anterior al arnés
│   ├── context7-documentacion-oficial.md <- Context7 MCP, documentación oficial y seguridad
│   ├── comunicacion-ste100-y-prompts.md <- Principios Karpathy, norma ASD-STE100 y micro-reportes
│   ├── patrones-datos-ddia.md        <- Patrones DDIA: Transactional Outbox, Idempotencia y OCC
│   ├── filosofia-diseno-ousterhout.md <- Filosofía de diseño Ousterhout: Deep Modules y anti-classitis
│   ├── patrones-gof-y-refactoring.md <- Patrones GoF, regla de dos sombreros y catálogo Code Smells
│   ├── design-patterns-gof.md        <- Design Patterns (Gamma et al.): capítulos 1 a 6, lectura cerrada
│   ├── algoritmos-y-estructuras-clrs.md <- Algoritmos y estructuras CLRS: complejidad, grafos y anti-patrones
│   ├── ai-engineering-chip-huyen.md  <- AI Engineering (Chip Huyen): pipeline de 5 capas, AI-as-a-judge y guardrails
│   ├── microservicios-sam-newman.md  <- Microservicios (Sam Newman): Database per Service, resiliencia y contratos
│   ├── ingenieria-software-gergely-orosz.md <- Ingeniería pragmática (Gergely Orosz): Design Docs y code reviews
│   ├── code-complete-mcconnell.md    <- Code Complete (McConnell): Partes I a VII, lectura cerrada
│   └── seguridad-owasp-y-zap.md      <- Seguridad web: OWASP Top 10, CLASP (Shift-Left) y ZAP (DAST)
└── tests/                            <- Suite exhaustiva de tests unitarios y de regresión
```

---

## Verificación y Calidad

El arnés se valida con una suite `unittest` en `tests/`. Lo que cubre, por archivo:
- Gates, sellos y enmiendas: `test_spec_acs.py`, `test_enmienda.py`, `test_evidencia_y_verify.py`, `test_review_rondas.py`, `test_close_fixes.py`.
- Flujo de documentos y rutas protegidas: `test_prd_sdd_flujo.py`, `test_producto.py`, `test_documentacion.py`.
- Runners post-merge medidos: `test_measured_runner_go.py`, `test_terraform_runner.py`, `test_frontend_runner.py`, `test_postmerge.py`.
- Hosts: `test_entorno.py`, `test_leccion_multihost.py`, `test_plugin_claude.py`, `test_indice_hermes.py`, `test_modelo.py`.
- Contexto, hub y procesos: `test_contexto.py`, `test_brief_stacks.py`, `test_hub.py`, `test_cbm_procesos.py`.
- Stacks y arquitectura: `test_stack.py`, `test_stack_adopcion.py`, `test_stack_normalizar.py`, `test_arquitectura.py`.

```bash
eval "$(python3 <skill>/scripts/entorno.py --shell)"
cd <skill> && "$PY" -m unittest discover -s tests
```

- La suite completa tarda unos 17 minutos: los runners medidos y los cierres multi-repo crean repos reales.
- `test_frontend_runner.py`, `test_retirados_frontend.py`, `test_frontend_close.py` y `test_cierre_historico.py` exigen `HARNESS_TEST_FRONTEND_MODULES`, la ruta a un `node_modules` con Angular 22 y Vitest 4. Sin ella fallan a propósito en vez de omitirse.
- Los tests no abren el Memory Hub real: `HARNESS_SIN_CONTEXTO=1` y `HARNESS_SIN_HUB=1` lo impiden.

---

## Licencia

MIT
