---
description: Dirección de dependencias entre capas (Controller → Service → Repository) en la API .NET layered
globs: ["src/**", "tests/**"]
trigger: always_on
---

# Reglas de arquitectura en capas (.NET)

Un solo proyecto, una carpeta por feature y una clase por capa. El compilador no impide saltarse capas: lo impiden estas reglas y `tests/Calpil.Template.Api.Tests/Architecture/LayeringTests.cs`.

- **Controller (`*Controller.cs`):**
  - Valida la forma del request (DataAnnotations, tipos), llama a un service y convierte el resultado a un DTO de respuesta.
  - Prohibido: reglas de negocio, `I*Repository`, `SqlConnection`, Dapper o cualquier tipo de `Platform/Database`.
  - Nunca devuelve el modelo interno (`WorkItem`); siempre un `*Response`.
- **Service (`*Service.cs`):**
  - Contiene las reglas de negocio y la máquina de estados. Depende solo de `I*Repository`, `TimeProvider` y `AppException`.
  - Prohibido: `Microsoft.AspNetCore.*`, `HttpContext`, `IActionResult`, `StatusCodes`, SQL, Dapper.
  - Reporta errores esperados con `AppException(ErrorKind, code, detail)`; el `code` es un slug estable.
- **Repository (`*Repository.cs` + `I*Repository.cs`):**
  - Único lugar con SQL. Recibe y devuelve modelos; no decide reglas de negocio.
  - Prohibido: tipos HTTP y referencias a services.
- **Platform (`Platform/**`):** transversal y sin conocimiento de features. Una feature puede usar Platform; Platform no referencia features.
- **Composition root:** solo `Program.cs` registra dependencias, mediante el `AddXxx()` que cada feature define en su carpeta.
- **Features aisladas:** una feature no usa el repositorio de otra; si necesita sus datos, llama a su service.
