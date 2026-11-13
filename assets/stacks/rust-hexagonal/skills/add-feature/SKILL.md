---
name: add-feature
description: Guía de implementación end-to-end de una nueva funcionalidad de negocio siguiendo arquitectura hexagonal en Rust
---

# Implementación de Funcionalidades en Rust

## Objetivo y activación
Esta skill se activa cuando se solicita una nueva característica o requerimiento de negocio en el backend Rust, guiando la implementación a través de las capas de Dominio, Aplicación, Infraestructura y API.

## Inspección obligatoria
Antes de codificar, examina:
- Modelos y errores en `crates/domain/src/`.
- Casos de uso y puertos en `crates/application/src/ports/`.
- Implementaciones de persistencia en `crates/infrastructure/src/persistence/`.
- Endpoints en `crates/api/src/handlers/`.
- Reglas de arquitectura en `.agents/rules/architecture.md` (o `.claude/rules/architecture.md`).

## Procedimiento ejecutable
1. **Modelar el dominio en `crates/domain`:** Definir entidades, enumeraciones, invariantes de validación y errores con `thiserror`. Escribir pruebas unitarias en `crates/domain`.
2. **Definir puertos y casos de uso en `crates/application`:** Crear comandos (`commands.rs`), DTOs (`dtos.rs`) y traits de entrada (`in_ports.rs`) y salida (`out_ports.rs`).
3. **Implementar el servicio de aplicación:** Orquestar el flujo en `crates/application/src/services.rs`, ejecutando reglas de dominio y coordinando repositorios y publicadores de eventos.
4. **Implementar adaptadores de infraestructura:** Implementar el puerto de repositorio tanto en memoria (`InMemoryWorkItemRepository`) como en PostgreSQL con `sqlx` (`SqlxWorkItemRepository`).
5. **Exponer la funcionalidad en la API:** Crear handlers Axum en `crates/api/src/handlers/`, conectar rutas en `lib.rs` y documentar en `api/openapi.yaml`.
6. **Verificar end-to-end:** Ejecutar la suite completa de pruebas unitarias y de integración.

## Patrón de implementación
```rust
// Invariante de dominio protegida en crates/domain
impl WorkItem {
    pub fn new(id: Uuid, title: impl Into<String>, description: Option<String>, now: DateTime<Utc>) -> Result<Self, DomainError> {
        let title = title.into();
        if title.trim().is_empty() {
            return Err(DomainError::TitleRequired);
        }
        Ok(Self { id, title: title.trim().to_string(), description: description.unwrap_or_default(), status: WorkItemStatus::Open, created_at: now, updated_at: now })
    }
}
```

## Decisiones y anti-patrones
- **No contaminar el dominio con dependencias externas:** El crate de dominio no debe conocer a Axum ni a SQLx.
- **Inmutabilidad e invariantes:** Los campos mutables deben alterarse a través de métodos de entidad que validen el estado resultante.
- **Doble adaptador de persistencia:** Siempre proveer la implementación en memoria para pruebas deterministas y la implementación en SQLx para producción.
- **Mapeo explícito DTO <-> Entidad:** La API nunca expone directamente entidades de dominio internas.

## Verificación / Definition of Done
- Pruebas unitarias de dominio pasando en `crates/domain`.
- Adaptador en memoria probado en `crates/infrastructure`.
- Pruebas de integración HTTP ejecutadas en `crates/api`.
- `cargo test` y `cargo clippy -- -D warnings` limpios.

## Contrato de entrega del agente
El agente reportará los cambios realizados por cada capa (Domain, Application, Infrastructure, API), listará los archivos modificados y confirmará la ejecución exitosa de `cargo test`.
