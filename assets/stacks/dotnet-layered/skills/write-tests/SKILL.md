---
name: write-tests
description: Escribe pruebas xUnit deterministas para la API .NET layered: servicios con fake en memoria, pipeline HTTP con WebApplicationFactory, capas e integración con SQL Server real.
---

# Write Tests — CALPIL .NET Layered

## Objetivo y activación
Activar cuando se pide agregar o mejorar pruebas, o como parte de cualquier cambio de comportamiento. Decide en qué nivel va cada prueba y asegura que cada una pueda fallar.

## Inspección obligatoria
Antes de escribir código, lee:
1. `.claude/rules/testing.md`: reglas del stack.
2. `tests/Calpil.Template.Api.Tests/WorkItems/WorkItemServiceTests.cs`: pruebas de reglas con `FakeTimeProvider`.
3. `tests/Calpil.Template.Api.Tests/WorkItems/WorkItemsApiTests.cs` y `tests/Calpil.Template.Api.Tests/ApiFactory.cs`: pruebas HTTP.
4. `tests/Calpil.Template.Api.IntegrationTests/SqlServerFixture.cs` y `tests/Calpil.Template.Api.IntegrationTests/DatabaseTests.cs`: pruebas con SQL Server.
5. El código bajo prueba, completo.

## Procedimiento ejecutable
1. **Elegir el nivel:** regla de negocio → service; contrato HTTP, validación o middleware → `ApiFactory`; SQL, migración o procedimiento → integración.
2. **Enumerar los casos:** camino feliz, cada error, bordes (límite exacto y límite + 1) y, en máquinas de estado, la matriz completa.
3. **Escribir la prueba con nombre de frase** (`Create_rejects_title_shorter_than_three_characters_after_trim`) y estructura preparar / actuar / afirmar.
4. **Controlar el tiempo** con `FakeTimeProvider` y `Advance`; nunca esperar.
5. **Afirmar lo observable:** status, `Content-Type`, cuerpo, `Location`, `AppException.Kind` y `Code`. No afirmar detalles internos.
6. **Comprobar que la prueba falla:** romper a propósito el comportamiento, ver el rojo y restaurar.
7. **Ejecutar** el filtro de la prueba y luego el proyecto completo.

## Patrón de implementación
```csharp
[Fact]
public async Task ChangeStatus_with_a_forbidden_transition_returns_409_problem()
{
    var id = await CreateAsync("Saltar a DONE");

    var response = await PatchStatusAsync(id, "DONE");

    var problem = await AssertProblemAsync(response, HttpStatusCode.Conflict);
    Assert.Equal("urn:calpil:problem:invalid-status-transition", problem.GetProperty("type").GetString());
}
```

## Decisiones y anti-patrones
- **NO** usar `Thread.Sleep`, `Task.Delay` ni `DateTime.UtcNow` en pruebas.
- **NO** usar librerías de mocks para el repositorio: existe el fake en memoria, que respeta el contrato.
- **NO** probar SQL contra el fake y darlo por cubierto.
- **NO** depender del orden de ejecución ni de datos creados por otra prueba.
- **NO** afirmar solo el status cuando el cuerpo es parte del contrato.
- **NO** marcar pruebas con `Skip` ni borrar aserciones para llegar a verde.

## Verificación / Definition of Done
- Cada rama nueva del código tiene al menos una prueba que la ejercita.
- Se comprobó que cada prueba nueva falla al romper el comportamiento.
- `dotnet test tests/Calpil.Template.Api.Tests` en verde; `make test-integration` si se tocó SQL.
- Sin warnings de compilación en los proyectos de prueba.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Pruebas agregadas por nivel (service, HTTP, capas, integración).
2. Casos cubiertos y casos conscientemente no cubiertos.
3. Cómo se comprobó que las pruebas pueden fallar.
4. Salida de `dotnet test`.
