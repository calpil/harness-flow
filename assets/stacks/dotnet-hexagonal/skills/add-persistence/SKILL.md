---
name: add-persistence
description: Agrega o modifica persistencia relacional en PostgreSQL con Dapper / ADO.NET, consultas SQL parametrizadas, migraciones DDL y paridad en memoria.
---

# Add Persistence — CALPIL .NET Engineering Skill

## Objetivo y activación
Activar cuando se requiera persistir datos en PostgreSQL para una vertical nueva o existente, diseñar tablas relacionales, redactar scripts de migración DDL, implementar métodos en repositorios Dapper o gestionar transacciones de base de datos en C#.

## Inspección obligatoria
Antes de escribir código, inspecciona:
1. `src/Calpil.Template.Application/<Feature>/Ports/I...Repository.cs`: El contrato de persistencia exigido por la aplicación.
2. `src/Calpil.Template.Infrastructure/Persistence/Dapper/SqlConnectionFactory.cs`: Factoría de conexiones `NpgsqlConnection`.
3. `src/Calpil.Template.Infrastructure/Persistence/Dapper/Migrations/`: Scripts de migración SQL existentes y su numeración correlativa.
4. `src/Calpil.Template.Infrastructure/Persistence/InMemory/`: Repositorio en memoria correspondiente.

## Procedimiento ejecutable
1. **Verificar el Puerto del Repositorio:** Revisar los métodos definidos en `I...Repository` (`SaveAsync`, `GetByIdAsync`, `ListAsync`, `UpdateAsync`, `DeleteAsync`).
2. **Crear Script de Migración SQL:** En `Infrastructure/Persistence/Dapper/Migrations/`, crear el archivo correlativo `00X_<nombre>.sql` con sentencias idempotentes (`CREATE TABLE IF NOT EXISTS`, índices adecuados).
3. **Definir la Clase Record de Base de Datos:** En el repositorio Dapper, crear una clase interna privada que coincida con las columnas de la tabla.
4. **Escribir Consultas SQL Parametrizadas:** Usar parámetros tipados (`@Id`, `@Title`, `@Status`) con `CommandDefinition` de Dapper, pasando siempre el `CancellationToken`.
5. **Implementar Mapeo a Entidad de Dominio:** Escribir un método de mapeo estático que invoque `Entity.Hydrate(...)` para reconstruir la entidad válida de dominio.
6. **Actualizar el Repositorio InMemory:** Asegurar que `InMemory...Repository` implemente los mismos métodos para garantizar paridad funcional durante los tests.
7. **Verificar Compilación y Tests:** Ejecutar `dotnet test` para asegurar que ambos adaptadores funcionen de manera idéntica.

## Patrón de implementación
```csharp
public async Task SaveAsync(WorkItem item, CancellationToken cancellationToken = default)
{
    using var connection = _connectionFactory.CreateConnection();
    const string sql = @"
        INSERT INTO work_items (id, title, description, status, created_at, updated_at)
        VALUES (@Id, @Title, @Description, @Status, @CreatedAt, @UpdatedAt)";

    var parameters = new
    {
        Id = item.Id.Value,
        Title = item.Title,
        Description = item.Description,
        Status = (int)item.Status,
        CreatedAt = item.CreatedAt,
        UpdatedAt = item.UpdatedAt
    };

    await connection.ExecuteAsync(new CommandDefinition(sql, parameters, cancellationToken: cancellationToken));
}
```

## Decisiones y anti-patrones
- **NO** usar interpolación de strings para concatenar valores en queries SQL; usar siempre `@Parametros` de Dapper.
- **NO** filtrar excepciones de base de datos (`NpgsqlException`) sin capturarlas o contextualizarlas adecuadamente.
- **NO** introducir dependencias de Dapper o Npgsql en los proyectos `Domain` o `Application`.

## Verificación / Definition of Done
- Script de migración SQL probado y verificado.
- Repositorio Dapper implementa el 100% de la interfaz del puerto.
- Repositorio InMemory actualizado manteniendo total paridad de comportamiento.
- `dotnet test` pasa con éxito.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Script de migración SQL creado.
2. Métodos del repositorio Dapper implementados.
3. Actualizaciones aplicadas al repositorio InMemory.
4. Evidencia de compilación y pruebas.
