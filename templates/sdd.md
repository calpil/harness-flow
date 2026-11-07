# SDD - {{PROYECTO}}

Estado: draft

<!-- Borrador del rol producto (diseno de arquitectura). Vive en
     docs/borrador-sdd.md; docs/sdd.md solo lo escribe `producto.py aprobar
     --yes` tras el SI del usuario. Las guias en comentarios HTML como este se
     reemplazan por contenido o se borran: una seccion que solo tiene guia cuenta como vacia
     y la aprobacion se niega. El bloque generado por feature lo agrega
     documentacion.py sync al cerrar cada una; no lo escribas aqui. -->

## Contexto

<!-- Que sistema existe hoy y que restricciones hereda: stack, repos,
     datos, despliegue. Cruzalo con `contexto.py estado` y `hub.py impacto`
     en vez de suponerlo. Pregunta solo si aplica alguna de las 4 decisiones
     caras de cambiar despues (no las disenes si no aplican):
       1. Multi-tenant o multi-organizacion
       2. Modelo de permisos o roles
       3. Operacion offline o sincronizacion
       4. Multi-idioma o multi-moneda -->

## Componentes

<!-- Microservicios / repos con la responsabilidad de cada uno, sus
     fronteras y los contratos entre ellos (API, eventos, tablas). El flujo,
     los datos y el pseudo-codigo de cada cambio ya estan en el PRD: aqui va
     lo que el PRD no fija, la arquitectura que los sostiene.
     Regla ASD-STE100 (Karpathy): modela la arquitectura y dependencias con
     diagramas Mermaid obligatorios (`flowchart` o `sequenceDiagram`); prohibida
     la prosa larga explicativa (> 3 líneas).
     Filosofía Ousterhout (ver `references/filosofia-diseno-ousterhout.md`): diseña
     interfaces y puertos profundos (contratos minimalistas con implementación rica internamente);
     prohibida la sobre-fragmentación (*classitis*) y capas con métodos *pass-through*.
     Patrones GoF & Fowler (ver `references/patrones-gof-y-refactoring.md`):
       - Puertos y adaptadores: usa Adapter para aislar infraestructura y permitir fakes en tests.
       - Lógica de negocio: usa Strategy / State para variar algoritmos o estados complejos.
       - Cross-cutting: usa Decorator / Proxy para Outbox, OCC, métricas y reintentos.
       - Composition Root: centraliza Factory / Builder únicamente en el arranque (`main`).
     Algoritmos y Estructuras de Datos CLRS (ver `references/algoritmos-y-estructuras-clrs.md`):
       - Estima el orden de magnitud de N (volumen en memoria, throughput req/s, concurrencia).
       - Selecciona la estructura adecuada para la carga: Hash Table O(1) amortizado para búsquedas exactas,
         Heap / Cola de Prioridad O(log N) para tareas o eventos ponderados, B-Tree O(log N) para rangos.
       - Prohibidas complejidades asintóticas accidentales O(N^2) en componentes críticos.
     Diseño simple (YAGNI & Anti-Speculative Generality): no agregues capas, repositorios, factories ni
     abstracciones "por si acaso" para un futuro hipotético. Todo patrón debe justificarse por necesidad real. -->

## Datos e integraciones

<!-- Esquemas, migraciones, colas y sistemas externos. Si hay migraciones
     numeradas, decir aqui contra que rama se reserva el numero.
     Pull Complexity Downwards (Ousterhout): la persistencia y adaptadores absorben
     la complejidad técnica (Outbox, OCC, Idempotencia); el llamador ve una API limpia y atómica.
     Patrones de Datos DDIA (Martin Kleppmann - ver `references/patrones-datos-ddia.md`):
       1. Perfil de datos: clasifica la carga (OLTP interactivo vs OLAP analítico vs Streaming).
       2. Motor de persistencia: justifica B-Tree (relacional estándar) vs LSM-Tree vs In-Memory.
       3. Prevención de Dual-Write: si el servicio persiste entidades y notifica eventos,
          especifica el Transactional Outbox (tabla outbox local en la misma TX ACID)
          en lugar de llamadas separadas a colas o APIs externas.
       4. Control de concurrencia: define Optimistic Concurrency Control (OCC) con columna `version`
          para prevenir Lost Updates sin bloqueos pesados de tabla.
       5. Evolución de esquemas: migraciones sin downtime bajo el patrón Expand-Contract.
       6. Eficiencia de acceso (CLRS): define índices B-Tree para rangos O(log N) y Hash para búsquedas O(1);
          previene explícitamente consultas N+1 mediante batching / IN queries (O(1) roundtrips). -->

## Decisiones

<!-- Principio "Design It Twice" (John Ousterhout): toda decisión D-n debe contrastar
     al menos dos alternativas de diseño radicalmente diferentes. Para decisiones algorítmicas
     o de estructuras de datos (CLRS), incluye la complejidad asintótica en el trade-off (ej. O(1) vs O(N)). Una decisión sin alternativa
     descartada no es una decisión, es una descripción. El nombre
     es para que el spec de cada feature la cite ("decisiones que aplica: D2").
     Sin `Descartada:` (o `Descartado:`) con texto, aprobar se niega.
     Formato STE100 recomendado (terna de 3 frases activas):
       - D1: Clave de idempotencia en base de datos. Descartada: cache distribuido,
         porque no sobrevive a un reinicio. Consecuencia: requiere índice único en PostgreSQL. -->

## Riesgos

<!-- Que puede romperse, como se detecta y que lo mitiga. -->
