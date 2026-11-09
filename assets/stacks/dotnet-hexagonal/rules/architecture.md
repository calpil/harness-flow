---
description: Límites de Clean Architecture y Arquitectura Hexagonal en .NET / C#
globs: ["src/**", "tests/**"]
---

# Reglas de Arquitectura Hexagonal en .NET / C#

- **Proyecto Dominio (`src/Calpil.Template.Domain/**`):**
  - Solo C# estándar (.NET BCL).
  - Prohibido referenciar `Calpil.Template.Application`, `Calpil.Template.Infrastructure`, `Calpil.Template.WebApi` o librerías externas de transporte o persistencia.
  - Las entidades protegen sus invariantes de negocio mediante constructores controlados y métodos explícitos.
- **Proyecto Aplicación (`src/Calpil.Template.Application/**`):**
  - Solo referencia `Calpil.Template.Domain`.
  - Define contratos de entrada (`Ports/I...UseCase.cs`) y contratos de salida (`Ports/I...Repository.cs`).
  - Prohibido referenciar Dapper, Npgsql, ASP.NET Core o implementaciones concretas de infraestructura.
- **Proyecto Infraestructura (`src/Calpil.Template.Infrastructure/**`):**
  - Referencia `Calpil.Template.Application`.
  - Implementa puertos de salida mediante Dapper / ADO.NET (`DapperWorkItemRepository`), adaptadores en memoria y servicios de plataforma.
  - Prohibido acoplar tipos de transporte HTTP (como `HttpContext` o `ControllerBase`).
- **Proyecto Presentación / API (`src/Calpil.Template.WebApi/**`):**
  - Controladores MVC / REST delegando el 100% de la lógica a los casos de uso (`IWorkItemUseCase`).
  - Prohibido consultar directamente la base de datos o repositorios desde los controladores.
  - `Program.cs` es el Composition Root único autorizado para configurar el contenedor de inyección de dependencias (`IServiceCollection`).
