---
name: write-tests
description: Escribe pruebas xUnit deterministas para el portal .NET MVC: páginas con WebApplicationFactory, sesión, formularios con antiforgery, cliente HTTP con handler de prueba y arquitectura.
---

# Write Tests — CALPIL .NET MVC

## Objetivo y activación
Activar cuando se pide agregar o mejorar pruebas, o como parte de cualquier cambio de comportamiento del portal. Decide el nivel de cada prueba y asegura que cada una pueda fallar.

## Inspección obligatoria
Antes de escribir código, lee:
1. `.claude/rules/testing.md`: reglas del stack.
2. `tests/Calpil.Template.Web.Tests/WebFactory.cs`: host de prueba, autenticación de prueba y `PostFormAsync`.
3. `tests/Calpil.Template.Web.Tests/FakeWorkItemsApi.cs`: cómo sembrar datos y forzar respuestas de la API.
4. `tests/Calpil.Template.Web.Tests/WorkItemsPagesTests.cs`, `AccessAndPlatformTests.cs` y `WorkItemsApiClientTests.cs`.
5. El código bajo prueba, completo.

## Procedimiento ejecutable
1. **Elegir el nivel:** lo que ve la persona → prueba de página; sesión, cabeceras o rutas → `AccessAndPlatformTests`; traducción de respuestas de la API → pruebas del cliente; validación de configuración → `OptionsTests`.
2. **Enumerar los casos:** éxito, cada rechazo de la API (400, 404, 409), API caída, sin sesión y, en formularios, sin token.
3. **Preparar el estado** sembrando el fake (`Seed`, `NextProblem`, `Unavailable`) en la propia prueba.
4. **Actuar como el navegador:** `GetStringAsync` para páginas y `WebFactory.PostFormAsync` para formularios.
5. **Afirmar sobre lo observable:** status, redirección, texto visible, llamadas registradas en `Api.Calls`. No afirmar sobre clases CSS salvo que sean el comportamiento.
6. **Comprobar que la prueba falla:** romper a propósito el comportamiento, ver el rojo y restaurar.
7. **Ejecutar** el filtro de la prueba y luego el proyecto completo.

## Patrón de implementación
```csharp
[Fact]
public async Task ChangeStatus_calls_the_api_and_confirms_on_the_details_page()
{
    var item = _factory.Api.Seed("Avanzar");

    var response = await WebFactory.PostFormAsync(
        _client, $"/work-items/{item.Id}", $"/work-items/{item.Id}/status", ("targetStatus", "InProgress"));

    Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
    Assert.Contains($"status:{item.Id}:InProgress", _factory.Api.Calls);
}
```

## Decisiones y anti-patrones
- **NO** llamar a una API, proveedor de identidad o servicio real desde una prueba.
- **NO** enviar formularios sin pasar por la página que entrega el token antiforgery.
- **NO** desactivar antiforgery o la autorización en el host de prueba para simplificar.
- **NO** compartir una `WebFactory` entre clases ni depender del orden de ejecución.
- **NO** usar `Thread.Sleep` ni `Task.Delay`.
- **NO** marcar pruebas con `Skip` ni borrar aserciones para llegar a verde.

## Verificación / Definition of Done
- Cada rama nueva del código tiene al menos una prueba que la ejercita.
- Se comprobó que cada prueba nueva falla al romper el comportamiento.
- `dotnet test tests/Calpil.Template.Web.Tests` en verde.
- Sin warnings de compilación en el proyecto de pruebas.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Pruebas agregadas por nivel.
2. Casos cubiertos y casos conscientemente no cubiertos.
3. Cómo se comprobó que las pruebas pueden fallar.
4. Salida de `dotnet test`.
