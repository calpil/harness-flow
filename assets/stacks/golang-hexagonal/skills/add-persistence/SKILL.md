---
name: add-persistence
description: Agrega o modifica persistencia relacional en PostgreSQL utilizando pgx / database/sql con transacciones, migraciones SQL deterministas y mapeo de dominio.
---

# Add Persistence — CALPIL Golang Engineering Skill

## Objetivo y activación
Activar cuando se requiera persistir datos en PostgreSQL para una feature nueva o existente, diseñar tablas, escribir scripts de migración DDL, implementar métodos en repositorios `pgx` o gestionar transacciones de base de datos.

## Inspección obligatoria
Antes de escribir código, inspecciona:
1. `internal/<feature>/application/ports/out.go`: Contrato de persistencia exigido por la aplicación (`WorkItemRepository`).
2. `internal/platform/database/postgres.go`: Configuración del pool de conexiones `pgxpool.Pool`.
3. `internal/platform/database/migrations/`: Scripts de migración SQL existentes y su correlativo numérico.
4. `internal/<feature>/adapter/out/persistence/postgres/repository.go`: Patrón existente de consultas SQL parametrizadas.

## Procedimiento ejecutable
1. **Verificar el Puerto de Salida:** Confirmar qué métodos (`Save`, `FindByID`, `FindAll`, `Update`, `Delete`) requiere la interfaz del repositorio en `ports/out.go`.
2. **Crear Script de Migración:** En `internal/platform/database/migrations/`, crear el archivo correlativo `00X_<nombre_descriptivo>.sql` con DDL idempotente (`CREATE TABLE IF NOT EXISTS`, índices adecuados).
3. **Escribir Consultas SQL Parametrizadas:** En el repositorio de la feature, usar consultas con placeholders `$1, $2, ...` para evitar completamente inyección SQL.
4. **Mapear Filas a Entidades de Dominio:** Escanear las columnas directamente a variables y reconstruir la entidad de dominio validando tipos y estados.
5. **Manejar Errores de Base de Datos:** Traducir `pgx.ErrNoRows` a errores centinela del dominio como `ErrWorkItemNotFound`.
6. **Actualizar Adaptador En Memoria:** Asegurar que `adapter/out/persistence/inmemory/repository.go` implemente exactamente los mismos métodos para mantener la paridad en tests.
7. **Verificar Conexión y Migración:** Probar la ejecución contra PostgreSQL local o mediante tests de repositorio.

## Patrón de implementación
```go
func (r *Repository) Save(ctx context.Context, item *domain.WorkItem) error {
    query := `
        INSERT INTO work_items (id, title, description, status, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6)
    `
    _, err := r.pool.Exec(ctx, query,
        item.ID,
        item.Title,
        item.Description,
        string(item.Status),
        item.CreatedAt,
        item.UpdatedAt,
    )
    if err != nil {
        return fmt.Errorf("failed to insert work item: %w", err)
    }
    return nil
}
```

## Decisiones y anti-patrones
- **NO** usar concatenación de strings para construir queries SQL; usar siempre parámetros posicionales `$1, $2`.
- **NO** retornar errores de base de datos directos (como `pgconn.PgError`) hacia la capa de aplicación o handlers HTTP.
- **NO** crear dependencias de `pgx` o SQL dentro de `domain` o `application`.
- **NO** modificar migraciones ya aplicadas; crear siempre un nuevo archivo correlativo de migración hacia adelante.

## Verificación / Definition of Done
- Script SQL probado y verificado en `docker-compose.yml`.
- Repositorio implementa 100% de la interfaz de `ports/out.go`.
- Adaptador en memoria actualizado con paridad funcional completa.
- `go test -v ./...` ejecuta sin errores de compilación ni ejecución.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Nombre del script de migración SQL creado.
2. Métodos de repositorio añadidos o modificados.
3. Tratamiento de errores y conversiones hacia el dominio.
4. Estado de paridad con el repositorio en memoria.
