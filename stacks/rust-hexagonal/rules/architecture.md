---
description: Protección de límites de arquitectura hexagonal y Clean Architecture en Rust
globs: ["crates/**", "tests/**"]
---

# Reglas de Arquitectura Hexagonal en Rust

- **Crate Domain (`crates/domain/**`):**
  - Núcleo puro de dominio. Depende únicamente de tipos estándar y primitivas indispensables (`chrono`, `uuid`, `serde`, `thiserror`).
  - Prohibido importar dependencias de red, transporte web (`axum`, `tower`), pools de persistencia (`sqlx`) o I/O del sistema operativo.
  - Entidades con invariantes protegidas mediante constructores de validación (`WorkItem::new`), métodos de mutación (`change_status`) y tipos de error de dominio bien tipados (`DomainError`).
- **Crate Application (`crates/application/**`):**
  - Define casos de uso (`ports/in_ports.rs`), puertos de salida secundarios (`ports/out_ports.rs`), comandos, queries y DTOs de transferencia.
  - Solo depende de `crates/domain` y `async_trait`. Prohibido depender de `crates/infrastructure` o `crates/api`.
- **Crate Infrastructure (`crates/infrastructure/**`):**
  - Implementa los puertos secundarios definidos en `crates/application` (adaptador en memoria `InMemoryWorkItemRepository`, adaptador PostgreSQL con `sqlx`, `LoggingEventPublisher`, `SystemClock`).
  - Mapeo bidireccional estricto entre modelos de fila/tabla (`WorkItemRow`) y entidades de dominio (`WorkItem::hydrate`).
  - Prohibido importar dependencias de transporte HTTP (`axum`).
- **Crate API y Composition Root (`crates/api/**`):**
  - Implementa los adaptadores primarios que exponen endpoints HTTP con Axum.
  - Serializa errores de dominio y aplicación a RFC 7807 `application/problem+json`.
  - `src/main.rs` es el composition root exclusivo donde se leen las variables de entorno, se instancian los adaptadores de infraestructura y se inyectan en los servicios de aplicación.
