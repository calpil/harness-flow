---
name: add-api-endpoint
description: Diseña e implementa endpoints REST versionados en ASP.NET Core MVC C# sobre puertos hexagonales, con validación de DTOs, RFC 7807 ProblemDetails y contratos OpenAPI.
---

# Add API Endpoint — CALPIL .NET Engineering Skill

## Objetivo y activación
Activar cuando el usuario o la historia requiera crear o modificar un endpoint HTTP REST en el servicio ASP.NET Core. Guía la definición de rutas, DTOs de request/response, atributos de validación, códigos de estado HTTP y mapeo hacia los casos de uso correspondientes en la capa de aplicación.

## Inspección obligatoria
Antes de escribir código, inspecciona:
1. `src/Calpil.Template.WebApi/Controllers/WorkItemsController.cs`: Convención existente de controladores MVC y rutas de API.
2. `src/Calpil.Template.WebApi/DTOs/`: Modelos de request y DataAnnotations de validación.
3. `src/Calpil.Template.Application/WorkItems/Ports/IWorkItemUseCase.cs`: Casos de uso disponibles para consumir.
4. `src/Calpil.Template.WebApi/Middlewares/GlobalExceptionMiddleware.cs`: Mapeo de excepciones hacia RFC 7807 ProblemDetails.
5. `api/openapi.yaml`: Especificación OpenAPI del servicio.

## Procedimiento ejecutable
1. **Definir el contrato HTTP:** Determinar método HTTP (GET, POST, PUT, PATCH, DELETE), ruta bajo `api/v1/...`, payload esperado y respuestas HTTP esperadas (200, 201, 204, 400, 404, 422).
2. **Crear DTOs de Request y Response:** En `Calpil.Template.WebApi/DTOs/`, declarar las clases con atributos DataAnnotations (`[Required]`, `[StringLength]`).
3. **Mapear a Comando de Aplicación:** Declarar el comando o query en `Calpil.Template.Application` y consumir el puerto de entrada `I...UseCase`.
4. **Implementar el Endpoint en el Controlador:** Crear la acción en el controlador correspondiente decorada con `[HttpPost]`, `[HttpGet]`, etc., y atributos `[ProducesResponseType]`.
5. **Alinear Respuestas de Error:** Asegurar que los errores de validación de modelo y excepciones de dominio se serialicen como RFC 7807 `application/problem+json`.
6. **Actualizar OpenAPI:** Documentar el nuevo endpoint y sus esquemas en `api/openapi.yaml`.
7. **Escribir Pruebas de Integración:** En `Calpil.Template.WebApi.Tests/Controllers/`, escribir pruebas con `WebApplicationFactory<Program>` validando casos exitosos (2xx), payloads inválidos (400) y recursos no encontrados (404).

## Patrón de implementación
```csharp
[HttpPost]
[ProducesResponseType(typeof(ResourceDto), StatusCodes.Status201Created)]
[ProducesResponseType(typeof(ProblemDetails), StatusCodes.Status400BadRequest)]
public async Task<IActionResult> Create(
    [FromBody] CreateResourceRequest request,
    CancellationToken cancellationToken)
{
    var command = new CreateResourceCommand(request.Name, request.Description);
    var result = await _useCase.CreateAsync(command, cancellationToken);

    return CreatedAtAction(nameof(GetById), new { id = result.Id }, result);
}
```

## Decisiones y anti-patrones
- **NO** colocar lógica de negocio ni sentencias SQL dentro de los métodos del controlador.
- **NO** exponer entidades de dominio (`WorkItem`) directamente en las respuestas del controlador; usar siempre DTOs de salida.
- **NO** omitir la validación de ModelState o responder errores en texto plano; usar siempre RFC 7807.
- **NO** ignorar el token de cancelación (`CancellationToken`) en las llamadas asíncronas.

## Verificación / Definition of Done
- Pruebas de integración del controlador pasando limpiamente con `dotnet test`.
- Códigos de respuesta HTTP y cabeceras `Location` conformes con REST.
- `api/openapi.yaml` actualizado reflejando el nuevo endpoint.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Método y ruta añadida o modificada.
2. DTOs creados con sus reglas de validación.
3. Pruebas de integración agregadas en `Calpil.Template.WebApi.Tests`.
4. Evidencia de paso de `dotnet test`.
