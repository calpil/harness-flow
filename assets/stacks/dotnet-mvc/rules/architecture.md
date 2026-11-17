---
description: Patrón MVC del portal .NET - controllers delgados, vistas que solo presentan y datos únicamente por la API
globs: ["src/**", "tests/**"]
trigger: always_on
---

# Reglas de arquitectura MVC (portal .NET)

El portal presenta y captura; no decide reglas de negocio ni guarda datos. `tests/Calpil.Template.Web.Tests/ArchitectureTests.cs` verifica estas reglas leyendo el código fuente.

- **Model (`Models/`, `Services/*Models.cs`):**
  - `Models/`: modelos de vista y formularios. Un formulario declara sus validaciones con DataAnnotations y mensajes en español.
  - `Services/*Models.cs`: el contrato de la API tal como lo ve el portal. No se usa como formulario.
- **View (`Views/**/*.cshtml`):**
  - Solo presenta el modelo que recibe. Prohibido `@inject`, `Html.Raw`, llamadas a servicios y lógica que no sea de presentación.
  - Prohibido `<script>` sin `src`, `<style>`, atributos `style=` y manejadores `on*=`: la CSP los bloquea. El código propio va en `wwwroot/js` y `wwwroot/css`.
  - Lo repetido va en parciales bajo `Views/Shared/`.
- **Controller (`Controllers/*.cs`):**
  - Recibe el request, llama a una interfaz `I*Api`, arma el modelo de vista y elige la vista o la redirección.
  - Prohibido `HttpClient`, `HttpRequestMessage`, el cliente concreto (`WorkItemsApiClient`), acceso a datos y reglas de negocio.
  - Después de un POST exitoso siempre redirige (Post/Redirect/Get); los mensajes viajan en `TempData`.
- **Services (`Services/`):** única salida hacia los datos. Una interfaz `I*Api` por recurso y su cliente tipado. Traduce los errores esperados a `ApiProblem` y lo inesperado a `ApiUnavailableException`.
- **Platform (`Platform/`):** transversal (correlación, cabeceras, autenticación). No conoce features.
- **Composition root:** solo `Program.cs` registra dependencias.
- **Sin acceso a datos:** ningún paquete ni `using` de `Microsoft.Data.*`, Dapper, Entity Framework u otro proveedor.
- **Reglas de negocio:** viven en la API. El portal puede anticipar una regla solo para ayudar a la interfaz (por ejemplo, qué botones mostrar) y siempre trata la respuesta de la API como la verdad.
