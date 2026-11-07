---
name: security-review
description: Revisa vulnerabilidades de seguridad, inyección SQL en Dapper, manejo de secretos, cabeceras HTTP y respuestas RFC 7807 en .NET / C#.
---

# Security Review — CALPIL .NET Engineering Skill

## Objetivo y activación
Activar antes de cualquier pase a producción o cuando se modifiquen endpoints, consultas SQL, autenticación o configuración para auditar que el backend .NET cumpla con las políticas de seguridad de CALPIL.

## Inspección obligatoria
Antes de emitir el reporte, inspecciona:
1. `src/Calpil.Template.Infrastructure/Persistence/Dapper/`: Todas las consultas SQL para descartar concatenación no segura.
2. `src/Calpil.Template.WebApi/appsettings*.json`: Ausencia de secretos o credenciales hardcodeadas.
3. `src/Calpil.Template.WebApi/Program.cs`: Cabeceras de seguridad y configuración de middleware.
4. `src/Calpil.Template.WebApi/Middlewares/GlobalExceptionMiddleware.cs`: Ocultamiento de stack traces en errores 500.

## Procedimiento ejecutable
1. **Auditoría de Inyección SQL en Dapper:** Inspeccionar cada sentencia `ExecuteAsync`, `QueryAsync` y `QuerySingleOrDefaultAsync`. Verificar que todas utilicen parámetros nombrados (`@Id`, `@Title`) y `CommandDefinition`. Prohibir `$""` o `+` en SQL.
2. **Auditoría de Secretos y Configuración:** Comprobar que `appsettings.json` solo contenga placeholders para desarrollo local y que `.env` esté en `.gitignore`.
3. **Revisión de Cabeceras HTTP:** Verificar la presencia de cabeceras de endurecimiento en `Program.cs`: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`.
4. **Verificación de Correlación y Logs:** Confirmar que `CorrelationIdMiddleware` capture o genere `X-Correlation-ID` y lo asigne a `context.TraceIdentifier` sin registrar datos personales (PII) en los logs.
5. **Revisión de Respuestas de Error:** Comprobar que en ambientes de producción los errores no controlados emitan RFC 7807 genérico con el ID de correlación y nunca el stack trace interno.
6. **Verificación de Contenedor Docker:** Asegurar que el `Dockerfile` ejecute la aplicación bajo un usuario sin privilegios `appuser`.

## Patrón de implementación
```csharp
// Consulta Dapper segura contra inyección SQL
const string sql = @"
    SELECT id, title, description, status, created_at AS CreatedAt, updated_at AS UpdatedAt
    FROM work_items
    WHERE id = @Id";

var record = await connection.QuerySingleOrDefaultAsync<WorkItemRecord>(
    new CommandDefinition(sql, new { Id = id.Value }, cancellationToken: cancellationToken));
```

## Decisiones y anti-patrones
- **NO** imprimir contraseñas o tokens en los logs estructurados con `ILogger`.
- **NO** exponer mensajes de excepción de base de datos directos hacia el cliente API.
- **NO** correr el contenedor Docker como `root`.

## Verificación / Definition of Done
- 0 consultas SQL vulnerables a inyección.
- 0 secretos o contraseñas hardcodeadas.
- Cabeceras de seguridad aplicadas en cada respuesta.
- Dockerfile con usuario `appuser`.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Resumen de áreas de seguridad auditadas.
2. Vulnerabilidades o hallazgos detectados y su nivel de severidad.
3. Acciones correctivas aplicadas.
4. Veredicto final de seguridad.
