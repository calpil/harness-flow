---
name: add-api-client
description: Agrega una llamada a la API REST o un cliente HTTP tipado nuevo al portal .NET MVC: interfaz, contrato, traducción de Problem Details, registro y pruebas con handler de prueba.
---

# Add API Client — CALPIL .NET MVC

## Objetivo y activación
Activar cuando el portal necesita un dato u operación de la API que todavía no consume. Es la única vía para que entren datos al portal: aquí se define el contrato y cómo se traduce cada respuesta.

## Inspección obligatoria
Antes de escribir código, lee:
1. `src/Calpil.Template.Web/Services/IWorkItemsApi.cs`: forma de la interfaz que usan los controllers.
2. `src/Calpil.Template.Web/Services/WorkItemsApiClient.cs`: envío, lectura y traducción de errores.
3. `src/Calpil.Template.Web/Services/WorkItemsApiModels.cs`: contrato, `ApiProblem`, `ApiResult<T>` y `ApiUnavailableException`.
4. `src/Calpil.Template.Web/Services/ApiOptions.cs`: registro del cliente tipado y sus handlers.
5. `tests/Calpil.Template.Web.Tests/WorkItemsApiClientTests.cs` y `tests/Calpil.Template.Web.Tests/FakeWorkItemsApi.cs`.
6. El contrato publicado por la API (`/openapi/v1.json` en su ambiente de desarrollo).

## Procedimiento ejecutable
1. **Leer el contrato real de la API** para la operación: ruta, cuerpo, respuesta y cada error con su `type`.
2. **Agregar el método a la interfaz** (o crear `I<Recurso>Api`): lecturas devuelven el dato o `null` ante 404; escrituras devuelven `ApiResult<T>`.
3. **Escribir las pruebas del cliente** con el `StubHandler`: URL y cuerpo enviados, lectura del éxito, cada error esperado, error inesperado, red caída y cuerpo ilegible.
4. **Implementar en el cliente tipado:** rutas relativas a `BaseAddress`, valores de ruta y consulta formateados con cultura invariante, `CancellationToken` en toda llamada.
5. **Traducir respuestas:** 400, 404 y 409 a `ApiProblem`; cualquier otro status, falla de red o timeout a `ApiUnavailableException`.
6. **Actualizar `FakeWorkItemsApi`** (o crear el fake del recurso) con el mismo contrato.
7. **Si es un cliente nuevo:** registrarlo con `AddHttpClient<I, T>` con `BaseAddress`, timeout y `CorrelationIdHandler`, y llamarlo desde `Program.cs`.
8. **Validar:** `dotnet test tests/Calpil.Template.Web.Tests`.

## Patrón de implementación
```csharp
public async Task<WorkItemDto?> FindAsync(Guid id, CancellationToken cancellationToken)
{
    using var request = new HttpRequestMessage(HttpMethod.Get, $"{BasePath}/{id}");
    using var response = await SendAsync(request, cancellationToken);
    if (response.StatusCode == HttpStatusCode.NotFound)
    {
        return null;
    }

    if (!response.IsSuccessStatusCode)
    {
        throw Unexpected(response);
    }

    return await ReadAsync<WorkItemDto>(response, cancellationToken);
}
```

## Decisiones y anti-patrones
- **NO** usar `HttpClient` desde un controller ni crear clientes con `new HttpClient()`.
- **NO** dejar `EnsureSuccessStatusCode()` como único manejo de errores: pierde el Problem Details.
- **NO** tragar errores devolviendo listas vacías o valores por defecto cuando la API falla.
- **NO** reintentar automáticamente POST o PATCH.
- **NO** poner URLs absolutas ni el host de la API en el código: viene de `API_BASE_URL`.
- **NO** incluir en excepciones o logs el cuerpo de la respuesta ni cabeceras con credenciales.

## Verificación / Definition of Done
- Pruebas del cliente para éxito, cada error esperado y cada falla inesperada.
- El fake y el cliente real cumplen la misma interfaz y semántica.
- El `X-Correlation-ID` se sigue propagando (prueba existente en verde).
- `ArchitectureTests` en verde.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Operación de la API consumida (método y ruta).
2. Método agregado a la interfaz y qué devuelve en cada caso.
3. Cambios en el fake.
4. Pruebas agregadas y salida de `dotnet test`.
