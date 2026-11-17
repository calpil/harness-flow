---
name: add-page
description: Agrega una página o formulario al portal ASP.NET Core MVC: acción delgada, modelo de vista, vista Razor sin código en línea, antiforgery, sesión y pruebas sobre el HTML.
---

# Add Page — CALPIL .NET MVC

## Objetivo y activación
Activar cuando se pide una pantalla, formulario o acción nueva sobre una feature que ya existe en el portal. Si la página necesita un dato que la API aún no entrega al portal, usar antes `add-api-client`; si la feature no existe, `add-feature`.

## Inspección obligatoria
Antes de escribir código, lee:
1. `src/Calpil.Template.Web/Controllers/WorkItemsController.cs`: rutas, Post/Redirect/Get y manejo de respuestas de la API.
2. `src/Calpil.Template.Web/Models/WorkItemViewModels.cs`: modelos de vista y formulario con DataAnnotations.
3. `src/Calpil.Template.Web/Views/WorkItems/` y `src/Calpil.Template.Web/Views/Shared/`: vistas, layout y parciales reutilizables.
4. `src/Calpil.Template.Web/Services/IWorkItemsApi.cs`: operaciones disponibles de la API.
5. `tests/Calpil.Template.Web.Tests/WorkItemsPagesTests.cs` y `tests/Calpil.Template.Web.Tests/AccessAndPlatformTests.cs`: estilo de las pruebas.

## Procedimiento ejecutable
1. **Definir la página:** ruta, método (GET para ver, POST para cambiar), quién puede verla y qué pasa en cada respuesta de la API (éxito, 400, 404, 409, caída).
2. **Escribir primero las pruebas** de la página: contenido esperado, caso de error y, si es un POST, el rechazo sin token antiforgery. Agregar la ruta a `Pages_with_data_require_a_session`.
3. **Crear el modelo de vista o formulario** en `Models/`: solo lo que la página muestra o recibe, con `[Display]` y mensajes de validación en español.
4. **Agregar la acción al controller:** llamar a `I*Api`, armar el modelo y devolver `View(...)`; en POST exitoso, `RedirectToAction` con el mensaje en `TempData`.
5. **Escribir la vista Razor** con tag helpers (`asp-action`, `asp-for`, `asp-validation-for`), parciales de `Shared/` y clases de Bootstrap. Sin scripts, estilos ni manejadores en línea.
6. **Mapear los rechazos de la API:** errores de campo a `ModelState`, conflictos a un mensaje claro en `TempData`, 404 a `NotFound()`. No capturar `ApiUnavailableException`.
7. **Agregar la página a la prueba de "sin código en línea"** y, si muestra texto de la API, a la de codificación HTML.
8. **Validar:** `dotnet test tests/Calpil.Template.Web.Tests` y revisar la página en el navegador con `make run`.

## Patrón de implementación
```csharp
[HttpPost("create")]
public async Task<IActionResult> Create(CreateWorkItemForm form, CancellationToken cancellationToken)
{
    if (!ModelState.IsValid)
    {
        return View(form);
    }

    var result = await api.CreateAsync(form.Title!, form.Description, cancellationToken);
    if (result.Succeeded)
    {
        TempData["SuccessMessage"] = "Work item creado.";
        return RedirectToAction(nameof(Details), new { id = result.Value!.Id });
    }

    AddApiErrors(result.Problem!);
    return View(form);
}
```

## Decisiones y anti-patrones
- **NO** cambiar estado con un enlace o un GET: siempre un formulario POST.
- **NO** usar `Html.Raw`, `@inject`, `<script>` en línea, `style=` ni `onclick=` en una vista.
- **NO** devolver una vista después de un POST exitoso (reenvío al recargar): redirigir.
- **NO** poner reglas de negocio en el controller ni en la vista; la API decide.
- **NO** usar el contrato de la API (`WorkItemDto`) como formulario de entrada.
- **NO** marcar la acción con `[AllowAnonymous]` para simplificar una prueba.

## Verificación / Definition of Done
- Pruebas de la página en verde, incluidos error de validación y, en POST, rechazo sin token.
- La ruta figura en `Pages_with_data_require_a_session` (o está justificado que sea pública).
- `ArchitectureTests` en verde sin modificarse.
- La página se ve y funciona en el navegador sin errores de CSP en la consola.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Ruta y método agregados, y si exige sesión.
2. Modelos de vista y vistas creados.
3. Cómo se presenta cada respuesta de la API.
4. Pruebas agregadas y salida de `dotnet test`.
