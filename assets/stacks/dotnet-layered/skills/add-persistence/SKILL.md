---
name: add-persistence
description: Agrega o cambia persistencia en SQL Server con Dapper: migración T-SQL numerada, consultas parametrizadas, procedimientos almacenados, rowversion y pruebas de integración.
---

# Add Persistence — CALPIL .NET Layered

## Objetivo y activación
Activar cuando un cambio necesita una tabla, columna, índice, consulta o procedimiento almacenado nuevo. Garantiza que el esquema solo cambie por migración, que todo SQL sea parametrizado y que quede probado contra SQL Server real.

## Inspección obligatoria
Antes de escribir código, lee:
1. `db/migrations/`: scripts existentes y último número.
2. `src/Calpil.Template.Api/WorkItems/WorkItemRepository.cs`: patrón Dapper, `Row` privado, `DbString` y uso del procedimiento.
3. `src/Calpil.Template.Api/Platform/Database/MigrationRunner.cs`: cómo se aplican los scripts (un lote, una transacción).
4. `tests/Calpil.Template.Api.IntegrationTests/DatabaseTests.cs`: estilo de las pruebas de integración.
5. `.claude/rules/security.md`: reglas de SQL y privilegios.

## Procedimiento ejecutable
1. **Reservar el número** siguiente y crear `db/migrations/NNNN_<descripcion>.sql`. Un solo lote: sin `GO`.
2. **Escribir el DDL** con nombres explícitos de constraints (`pk_`, `ck_`, `df_`, `ix_`), `rowversion` si la fila se actualiza y un índice por cada camino de consulta con volumen.
3. **Operaciones de estado:** un procedimiento almacenado por operación, en su propio archivo, con `CREATE OR ALTER PROCEDURE`, filtro por `row_version` y `OUTPUT` de la fila resultante.
4. **Escribir el método del repositorio:** SQL en constante, parámetros por objeto anónimo, `CommandDefinition` con el `CancellationToken`, y mapeo a través del `Row` privado.
5. **Textos `varchar`:** enviarlos como `DbString { IsAnsi = true, Length = n }` para no forzar conversiones a `nvarchar`.
6. **Actualizar el fake** `InMemoryWorkItemRepository` (o el de la feature) para que cumpla el mismo contrato.
7. **Probar contra SQL Server** en `tests/Calpil.Template.Api.IntegrationTests`: ida y vuelta de cada campo, caso inexistente, concurrencia y la restricción nueva.
8. **Validar:** `make test-integration` (Apple Silicon sin Rosetta: `MSSQL_IMAGE=mcr.microsoft.com/azure-sql-edge:latest`).

## Patrón de implementación
```csharp
public async Task<WorkItem?> FindAsync(Guid id, CancellationToken cancellationToken)
{
    await using var connection = await connections.OpenAsync(cancellationToken);
    var row = await connection.QuerySingleOrDefaultAsync<Row>(new CommandDefinition(
        $"SELECT {Columns} FROM dbo.work_items WHERE id = @Id",
        new { Id = id },
        cancellationToken: cancellationToken));
    return row?.ToModel();
}
```

## Decisiones y anti-patrones
- **NO** interpolar ni concatenar valores en SQL; solo constantes del repositorio como `{Columns}`.
- **NO** editar una migración ya aplicada en algún ambiente: agregar otra.
- **NO** usar `GO`, ni varios `CREATE PROCEDURE` en un archivo.
- **NO** introducir un ORM ni `DataTable`/`DataSet`.
- **NO** dejar un `UPDATE` de estado sin control de versión ("último gana").
- **NO** dar por probado SQL nuevo solo con el fake en memoria.
- **NO** usar `SELECT *`: listar columnas con alias al nombre del `Row`.

## Verificación / Definition of Done
- La migración aplica en una base vacía; re-ejecutar el runner aplica 0.
- Prueba de integración por cada consulta nueva, incluida la rama de versión vieja si hay escritura.
- `Sql_is_never_built_by_interpolating_or_concatenating_request_values` en verde.
- El fake y el repositorio real cumplen el mismo contrato.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Nombre de la migración y objetos creados (tablas, índices, procedimientos).
2. Métodos de repositorio agregados y su SQL.
3. Pruebas de integración agregadas y su salida.
4. Si el cambio exige permisos nuevos para el login de la aplicación.
