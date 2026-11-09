---
name: write-tests
description: Diseña e implementa pruebas unitarias, de servicios de aplicación y de integración HTTP en .NET con xUnit y WebApplicationFactory.
---

# Write Tests — CALPIL .NET Engineering Skill

## Objetivo y activación
Activar cuando se implemente nueva funcionalidad, se corrija un defecto o se requiera incrementar la cobertura de pruebas en la solución .NET. Guía la escritura de pruebas unitarias puras para el dominio, pruebas de use cases con fakes y pruebas de endpoints con `WebApplicationFactory`.

## Inspección obligatoria
Antes de escribir pruebas, inspecciona:
1. `tests/Calpil.Template.Domain.Tests/WorkItems/WorkItemTests.cs`: Patrón de pruebas de invariantes de dominio.
2. `tests/Calpil.Template.Application.Tests/WorkItems/WorkItemServiceTests.cs`: Patrón de pruebas con fakes en memoria para use cases.
3. `tests/Calpil.Template.WebApi.Tests/Controllers/WorkItemsControllerTests.cs`: Patrón de pruebas de integración con `WebApplicationFactory<Program>`.

## Procedimiento ejecutable
1. **Identificar la Capa de la Prueba:** Clasificar si la necesidad corresponde a una prueba de entidad (`Domain.Tests`), de caso de uso (`Application.Tests`) o de controlador HTTP (`WebApi.Tests`).
2. **Escribir Pruebas de Dominio:** En `Domain.Tests`, probar exhaustivamente constructores, validaciones de argumentos y transiciones de estado válidas e inválidas.
3. **Escribir Pruebas de Use Case con Fakes:** En `Application.Tests`, probar la orquestación instanciando el servicio con implementaciones fake de `IWorkItemRepository` y `IDateTimeProvider`. Evitar mocks frágiles.
4. **Escribir Pruebas de Integración WebApi:** En `WebApi.Tests`, utilizar `HttpClient` derivado de `WebApplicationFactory<Program>` para validar status codes (201, 200, 400, 404, 422), encabezados `Location` y respuestas RFC 7807 `application/problem+json`.
5. **Verificar Cabeceras de Trazabilidad:** Confirmar que las respuestas HTTP incluyan la cabecera `X-Correlation-ID`.
6. **Ejecutar la Suite Completa:** Correr `dotnet test` asegurando que todos los proyectos de pruebas pasen al 100%.

## Patrón de implementación
```csharp
[Fact]
public async Task Create_WithValidData_Returns201CreatedAndLocationHeader()
{
    var request = new CreateWorkItemRequest
    {
        Title = "API Integration Test",
        Description = "Ensuring ASP.NET Core MVC works end to end"
    };

    var response = await _client.PostAsJsonAsync("/api/v1/work-items", request);

    Assert.Equal(HttpStatusCode.Created, response.StatusCode);
    Assert.NotNull(response.Headers.Location);
    Assert.True(response.Headers.Contains("X-Correlation-ID"));
}
```

## Decisiones y anti-patrones
- **NO** utilizar `Thread.Sleep` ni esperas basadas en tiempo para sincronizar pruebas asíncronas.
- **NO** depender de una base de datos PostgreSQL real levantada en el host para ejecutar los tests de integración estándar.
- **NO** deshabilitar tests con `[Fact(Skip = "...")]` sin autorización y justificación documentada.

## Verificación / Definition of Done
- Todas las pruebas pasan limpiamente con `dotnet test`.
- Cobertura de la nueva lógica agregada verificada.
- Tiempos de ejecución rápidos y deterministas.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Archivos de prueba agregados o modificados.
2. Escenarios cubiertos (casos de éxito, validación y errores de negocio).
3. Evidencia de paso de `dotnet test`.
