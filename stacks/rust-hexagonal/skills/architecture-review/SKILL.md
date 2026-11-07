---
name: architecture-review
description: Guía de auditoría y revisión de límites de arquitectura hexagonal y Clean Architecture en el workspace Rust
---

# Auditoría de Arquitectura Hexagonal en Rust

## Objetivo y activación
Esta skill se activa para auditar que el código del workspace Rust respete las fronteras arquitectónicas hexagonales, asegurando la inversión de dependencias y la pureza del dominio.

## Inspección obligatoria
Antes de emitir un veredicto de arquitectura:
- Inspeccionar `crates/domain/Cargo.toml` y verificar que no dependa de crates de transporte o persistencia.
- Inspeccionar `crates/application/Cargo.toml` y verificar que solo dependa de `crates/domain` y utilidades comunes.
- Revisar que `crates/infrastructure` implemente puertos secundarios y no sea importado por `crates/application` ni `crates/domain`.
- Revisar que `crates/api` solo consuma interfaces de `crates/application` y configure el composition root en `src/main.rs`.
- Consultar `.claude/rules/architecture.md`.

## Procedimiento ejecutable
1. **Auditar dependencias de `crates/domain`:** Comprobar que en `crates/domain/Cargo.toml` no existan referencias a `axum`, `tokio`, `sqlx`, `tower` o crates de base de datos.
2. **Revisar imports en ficheros de dominio:** Escanear archivos en `crates/domain/src/` verificando que no haya imports `use` hacia infraestructura o protocolos de red.
3. **Validar aislamiento de aplicación:** Verificar que `crates/application` solo interactúe con el exterior mediante traits en `ports/`.
4. **Comprobar mapeos de infraestructura:** Confirmar que los adaptadores en `crates/infrastructure` utilicen modelos intermedios (como `WorkItemRow`) y no contaminen el dominio.
5. **Verificar composition root:** Inspeccionar `crates/api/src/main.rs` para asegurar que sea el único lugar donde se cablean las implementaciones concretas con los servicios de aplicación.
6. **Ejecutar análisis de compilación:** Correr `cargo check --workspace` para validar que el grafo de dependencias de Cargo compile limpiamente sin dependencias circulares.

## Patrón de implementación
```text
Grafo de Dependencias Válido:
crates/api -> crates/application -> crates/domain
crates/infrastructure -> crates/application -> crates/domain
```

## Decisiones y anti-patrones
- **No acoplar dominio a frameworks:** Ningún tipo en `crates/domain` debe depender de Axum o SQLx.
- **Evitar filtración de errores de persistencia:** Los errores de infraestructura deben transformarse a errores de aplicación o dominio antes de llegar a la API.
- **Inyección por interfaces:** Los servicios de aplicación deben recibir `Arc<dyn Repository>` o genéricos acotados, nunca tipos concretos de infraestructura.

## Verificación / Definition of Done
- Comprobación de que `crates/domain` no tiene dependencias impuras.
- `cargo check --workspace` exitoso.
- Informe de revisión detallando el cumplimiento de cada capa.

## Contrato de entrega del agente
El agente entregará una matriz de cumplimiento de límites arquitectónicos por crate (Domain, Application, Infrastructure, API) indicando hallazgos o aprobando la solución.
