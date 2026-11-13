---
name: dependency-review
description: Guía para evaluar, auditar y actualizar dependencias en Cargo Workspace asegurando compatibilidad, licencias y seguridad
---

# Revisión de Dependencias en Rust

## Objetivo y activación
Esta skill se activa cuando es necesario añadir una nueva dependencia externa a Cargo, evaluar vulnerabilidades conocidas o actualizar paquetes existentes en el workspace Rust.

## Inspección obligatoria
Antes de modificar ficheros de dependencias:
- Revisar `Cargo.toml` raíz en `[workspace.dependencies]`.
- Revisar `Cargo.lock`.
- Revisar cada `Cargo.toml` en los crates miembros (`crates/*/Cargo.toml`).
- Consultar las directrices en `.agents/rules/dependencies.md` (o `.claude/rules/dependencies.md`).

## Procedimiento ejecutable
1. **Evaluar necesidad y salud del crate:** Verificar en crates.io que la dependencia sea mantenida activamente, con licencia permisiva (MIT/Apache-2.0) y sin vulnerabilidades reportadas en RustSec Advisory Database.
2. **Definir en el Workspace raíz:** Añadir la dependencia con versión semver estricta en `[workspace.dependencies]` dentro de `Cargo.toml`.
3. **Consumir en crates correspondientes:** En el `Cargo.toml` del crate que requiere la biblioteca, declarar `{ workspace = true }`.
4. **Verificar compilación limpia:** Ejecutar `cargo check --workspace` para comprobar que no existan conflictos de versiones ni features incompatibles.
5. **Auditar vulnerabilidades:** Si `cargo audit` está disponible, ejecutar `cargo audit` para escanear `Cargo.lock`.
6. **Ejecutar pruebas completas:** Correr `cargo test` para garantizar que la nueva dependencia no altera el comportamiento del sistema.

## Patrón de implementación
```toml
# En Cargo.toml raíz
[workspace.dependencies]
axum = { version = "0.8", features = ["json", "tokio"] }

# En crates/api/Cargo.toml
[dependencies]
axum = { workspace = true }
```

## Decisiones y anti-patrones
- **No duplicar versiones entre crates:** No definir versiones manuales en crates hijos; usar `{ workspace = true }`.
- **Cero dependencias sin justificación:** No incorporar crates grandes para funcionalidades que pueden resolverse con la biblioteca estándar.
- **Mantener `Cargo.lock` versionado:** Garantizar reproducibilidad en CI y entornos de despliegue.

## Verificación / Definition of Done
- Dependencia agregada en `[workspace.dependencies]`.
- Consumo estandarizado con `{ workspace = true }`.
- `cargo check --workspace` y `cargo test` exitosos.

## Contrato de entrega del agente
El agente reportará las dependencias añadidas o actualizadas, su versión, su propósito y la confirmación de compilación limpia y pruebas.
