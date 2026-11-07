---
description: Reglas de pruebas unitarias, de integración y testing determinista en Rust
globs: ["tests/**", "**/*test*.rs"]
---

# Reglas de Pruebas en Rust

- **Pruebas Unitarias de Dominio:**
  - `crates/domain` debe verificarse con pruebas unitarias exhaustivas sin mocks ni dependencias de red o disco.
  - Comprobar invariantes de negocio, transiciones de estado válidas e inválidas, y validaciones de datos (`cannot_create_with_empty_title`, `change_status_transitions`).
- **Pruebas con Fakes en Memoria (Testing Determinista):**
  - Probar servicios de aplicación y repositorios utilizando el adaptador en memoria `InMemoryWorkItemRepository`.
  - No depender de instancias reales de bases de datos para pruebas rápidas de regresión en CI/CD local.
- **Pruebas de Integración de API HTTP:**
  - `crates/api/tests/api_tests.rs` debe verificar la integración completa de endpoints Axum invocando `app.oneshot(...)` con `tower::ServiceExt`.
  - Validar códigos de respuesta HTTP (`200 OK`, `201 Created`, `400 Bad Request`, `404 Not Found`).
  - Validar cabeceras `Location`, `Content-Type: application/problem+json` y `x-correlation-id`.
- **Ejecución y Verificación Continua:**
  - Antes de cualquier commit, deben ejecutarse y pasar con 0 fallos: `cargo test` y `cargo clippy -- -D warnings`.
