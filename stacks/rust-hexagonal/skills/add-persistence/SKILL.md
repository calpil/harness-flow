---
name: add-persistence
description: Guía para implementar o modificar repositorios de persistencia en memoria y PostgreSQL con SQLx en Rust
---

# Implementación de Persistencia en Rust

## Objetivo y activación
Esta skill se activa cuando es necesario añadir o modificar una fuente de datos en `crates/infrastructure`, implementando puertos definidos en `crates/application` mediante adaptadores en memoria y SQLx para PostgreSQL.

## Inspección obligatoria
Antes de escribir adaptadores:
- Revisar el trait de repositorio en `crates/application/src/ports/out_ports.rs`.
- Inspeccionar `crates/infrastructure/src/persistence/inmemory.rs`.
- Inspeccionar `crates/infrastructure/src/persistence/postgres.rs`.
- Revisar migraciones SQL existentes en `migrations/`.
- Comprobar las reglas de seguridad en `.agents/rules/security.md` (o `.agents/rules/security.md (o .claude/rules/security.md)`).

## Procedimiento ejecutable
1. **Definir el contrato en Application:** Declarar o actualizar el trait `#[async_trait] pub trait EntityRepository: Send + Sync` en `crates/application/src/ports/out_ports.rs`.
2. **Implementar el adaptador en memoria:** En `crates/infrastructure/src/persistence/inmemory.rs`, usar `tokio::sync::RwLock<HashMap<Uuid, Entity>>` para operaciones thread-safe y no bloqueantes.
3. **Crear script de migración SQL:** En `migrations/{timestamp}_{name}.sql`, definir `CREATE TABLE` e índices necesarios con sintaxis idempotente (`IF NOT EXISTS`).
4. **Implementar adaptador SQLx:** En `crates/infrastructure/src/persistence/postgres.rs`, implementar el trait usando consultas parametrizadas (`sqlx::query!`, `sqlx::query_as!`), con struct de fila `FromRow` intermedio y mapeo hacia la entidad de dominio.
5. **Escribir pruebas unitarias del repositorio:** En `crates/infrastructure/tests/`, verificar las operaciones CRUD con el adaptador en memoria.
6. **Registrar en el Composition Root:** En `crates/api/src/main.rs`, permitir la selección dinámica del repositorio según la variable `USE_POSTGRES`.

## Patrón de implementación
```rust
#[async_trait]
impl WorkItemRepository for SqlxWorkItemRepository {
    async fn save(&self, item: &WorkItem) -> Result<(), String> {
        sqlx::query(
            "INSERT INTO work_items (id, title, description, status, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6)"
        )
        .bind(item.id)
        .bind(&item.title)
        .bind(&item.description)
        .bind(status_to_str(item.status))
        .bind(item.created_at)
        .bind(item.updated_at)
        .execute(&self.pool)
        .await
        .map_err(|e| e.to_string())?;
        Ok(())
    }
}
```

## Decisiones y anti-patrones
- **Cero SQL dinámico sin parámetros:** Prohibida la interpolación de variables directas en sentencias SQL.
- **Entidad intermedia Row:** La entidad de dominio nunca debe tener atributos `#[derive(FromRow)]` para no acoplarla a SQLx.
- **Concurrencia con RwLock:** En el adaptador en memoria, utilizar `RwLock` para lecturas concurrentes y escrituras exclusivas.
- **Transaccionalidad:** Agrupar operaciones compuestas bajo transacciones `pool.begin().await?`.

## Verificación / Definition of Done
- Migración SQL válida en `migrations/`.
- Adaptador en memoria verificado con pruebas en `crates/infrastructure/tests/`.
- Sin advertencias en `cargo clippy -- -D warnings`.
- `cargo test -p calpil-infrastructure` ejecutado exitosamente.

## Contrato de entrega del agente
El agente entregará el archivo de migración, la implementación del adaptador en memoria y en SQLx, y la evidencia de ejecución de pruebas.
