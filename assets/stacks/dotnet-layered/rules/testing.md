---
description: Estándares de pruebas deterministas con xUnit para servicios, HTTP, capas e integración con SQL Server
globs: ["tests/**", "**/*Tests.cs"]
trigger: always_on
---

# Reglas de pruebas

- **Deterministas.** Prohibido `Thread.Sleep`, `Task.Delay` como espera y dependencias del reloj real. El tiempo se controla con `FakeTimeProvider`.
- **Dos proyectos, dos velocidades:**
  - `Calpil.Template.Api.Tests`: sin Docker ni red. Servicios con `InMemoryWorkItemRepository`, pipeline HTTP con `ApiFactory` (`WebApplicationFactory<Program>`), configuración y capas.
  - `Calpil.Template.Api.IntegrationTests`: SQL Server real con Testcontainers. Todo SQL nuevo (consulta, migración, procedimiento) se prueba aquí; un fake no demuestra que el SQL funciona.
- **Servicios:** cubrir camino feliz y cada `AppException` (kind y code). Para una máquina de estados, la matriz completa de transiciones.
- **HTTP:** verificar status, `Content-Type` (`application/problem+json` en errores), cuerpo y `Location` en los 201. Los errores se afirman con `AssertProblemAsync`.
- **El fake respeta el contrato del repositorio real** (versión que cambia en cada escritura, `null` ante versión vieja). Si cambia el contrato, cambian ambos.
- **Independencia:** una prueba no depende del orden ni de datos de otra. En integración la base es compartida: usar ids propios y aserciones que toleren filas ajenas.
- **Una prueba nueva debe poder fallar.** Antes de darla por buena, comprobar que falla al romper el comportamiento que protege.
- **Nunca** borrar, saltar (`Skip`) o relajar una prueba para que pase un cambio.
- `make validate` termina con 0 fallas y 0 warnings.
