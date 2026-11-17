---
name: add-api-endpoint
description: Diseña e implementa un endpoint REST versionado en la API .NET layered: DTOs validados, controller delgado, lógica en el service, Problem Details y pruebas HTTP.
---

# Add API Endpoint — CALPIL .NET Layered

## Objetivo y activación
Activar cuando se pide crear o modificar un endpoint HTTP de una feature que ya existe. Cubre ruta, DTOs, validación, códigos de estado y pruebas. Si la feature no existe, usar `add-feature`; si el endpoint necesita SQL nuevo, combinar con `add-persistence`.

## Inspección obligatoria
Antes de escribir código, lee:
1. `src/Calpil.Template.Api/WorkItems/WorkItemsController.cs`: convención de rutas, atributos y respuestas.
2. `src/Calpil.Template.Api/WorkItems/WorkItemDtos.cs`: forma de los DTOs de entrada y salida.
3. `src/Calpil.Template.Api/WorkItems/WorkItemService.cs`: dónde viven las reglas y cómo se reportan errores.
4. `src/Calpil.Template.Api/Platform/AppExceptionHandler.cs`: mapeo de `ErrorKind` a status HTTP.
5. `tests/Calpil.Template.Api.Tests/WorkItems/WorkItemsApiTests.cs`: estilo de las pruebas HTTP y `AssertProblemAsync`.

## Procedimiento ejecutable
1. **Definir el contrato:** método, ruta bajo `api/v1/<recurso>`, cuerpo, parámetros y cada respuesta posible (2xx, 400, 404, 409).
2. **Escribir primero la prueba HTTP** en `WorkItemsApiTests` (o la clase de la feature): camino feliz y cada error. Debe fallar antes de implementar.
3. **Crear los DTOs** como `sealed record` en `<Feature>Dtos.cs`: `[Required]`, `[StringLength]`, `[Range]`; propiedades de entrada anulables para distinguir ausente de vacío.
4. **Agregar el método al service** con la regla de negocio; lanzar `AppException` con un `code` nuevo y estable si aparece un error nuevo.
5. **Agregar la acción al controller:** atributo HTTP, `[ProducesResponseType<T>]` por respuesta, `CancellationToken`, y conversión a `*Response`.
6. **Probar el service** en `WorkItemServiceTests` con `InMemoryWorkItemRepository` para cada rama.
7. **Verificar el contrato generado:** `GET /openapi/v1.json` debe listar la ruta (prueba en `PlatformApiTests`).
8. **Validar:** `dotnet test tests/Calpil.Template.Api.Tests` y, si hubo SQL nuevo, `make test-integration`.

## Patrón de implementación
```csharp
[HttpPatch("{id}/status")]
[ProducesResponseType<WorkItemResponse>(StatusCodes.Status200OK)]
[ProducesResponseType<ProblemDetails>(StatusCodes.Status409Conflict, "application/problem+json")]
public async Task<IActionResult> ChangeStatus(Guid id, [FromBody] ChangeStatusRequest request, CancellationToken cancellationToken)
{
    var item = await service.ChangeStatusAsync(id, request.TargetStatus!.Value, cancellationToken);
    return Ok(WorkItemResponse.From(item));
}
```

## Decisiones y anti-patrones
- **NO** poner reglas de negocio, `try/catch` de errores de negocio ni SQL en el controller.
- **NO** inyectar `I*Repository` en un controller: `LayeringTests` lo rechaza.
- **NO** devolver el modelo interno ni exponer `Version`; siempre un `*Response`.
- **NO** usar `[Produces("application/json")]` a nivel de clase: fuerza `application/json` también en los errores.
- **NO** construir respuestas de error a mano (`BadRequest("texto")`): lanzar `AppException` o dejar actuar la validación automática.
- **NO** restringir el id con `{id:guid}`: un id malformado debe ser 400, no 404.

## Verificación / Definition of Done
- Pruebas HTTP nuevas en verde, incluidos los casos de error con `application/problem+json`.
- `201` con cabecera `Location` cuando se crea un recurso.
- `LayeringTests` en verde sin cambios en la propia prueba.
- La ruta aparece en `/openapi/v1.json`.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Método y ruta agregados o modificados, con sus códigos de respuesta.
2. DTOs creados y sus reglas de validación.
3. `code` de cada `AppException` nueva.
4. Pruebas agregadas y salida de `dotnet test`.
