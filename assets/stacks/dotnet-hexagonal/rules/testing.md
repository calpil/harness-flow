---
description: Estándares de pruebas automatizadas deterministas en .NET con xUnit
globs: ["tests/**", "**/*Tests.cs"]
---

# Reglas de Pruebas en .NET / C#

- Todas las pruebas deben ser deterministas, ejecutarse en paralelo y sin llamadas a `Thread.Sleep` o retrasos arbitrarios.
- **Pruebas de Dominio (`Calpil.Template.Domain.Tests`):** Probar invariantes, excepciones y métodos de negocio directamente sobre entidades, sin mocks de interfaces externas.
- **Pruebas de Aplicación (`Calpil.Template.Application.Tests`):** Utilizar implementaciones fake en memoria (`FakeWorkItemRepository`, `FakeDateTimeProvider`) para validar la orquestación y eventos de dominio.
- **Pruebas de API / Integración (`Calpil.Template.WebApi.Tests`):** Utilizar `WebApplicationFactory<Program>` para probar el pipeline HTTP completo, verificando status codes, cabeceras `Location` y respuestas RFC 7807.
- La ejecución completa `dotnet test` debe pasar siempre al 100% con 0 errores y 0 warnings.
