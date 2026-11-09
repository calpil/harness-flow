---
description: Reglas de gestión y auditoría de dependencias en Rust y Cargo Workspace
globs: ["**/Cargo.toml", "Cargo.lock"]
---

# Reglas de Dependencias en Rust

- **Workspace Dependencies Centralizadas:**
  - Todas las dependencias compartidas se declaran en `Cargo.toml` raíz bajo `[workspace.dependencies]` con versiones semver precisas.
  - Los crates miembros (`crates/*`) consumen dependencias mediante `{ workspace = true }` para evitar discrepancias de versiones o duplicación de dependencias compiladas.
- **Auditoría de Vulnerabilidades y Mantenimiento:**
  - Prohibido introducir crates no mantenidos o con licencias restrictivas.
  - Cada crate añadido debe justificar su inclusión y pertenecer a un ámbito tecnológico estándar del ecosistema Rust (e.g. `tokio`, `axum`, `sqlx`, `serde`).
- **Control de Flags y Características:**
  - Activar únicamente los features de Cargo estrictamente necesarios en cada crate (e.g. `uuid` con `v4` y `serde`, `chrono` con `serde`).
  - Mantener tiempos de compilación acotados evitando dependencias no utilizadas en producción.
- **Reproducibilidad:**
  - `Cargo.lock` debe versionarse en Git para garantizar compilaciones reproducibles e idénticas en entornos locales, CI y producción en contenedores Docker.
