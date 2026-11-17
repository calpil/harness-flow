---
name: architecture-review
description: Audita el portal .NET MVC en busca de violaciones reales del patrón: controllers con lógica o HttpClient, vistas con código, acceso a datos o reglas de negocio fuera de la API.
---

# Architecture Review — CALPIL .NET MVC

## Objetivo y activación
Activar cuando se pide revisar la arquitectura del portal, antes de un release o tras un cambio grande. Es de solo lectura: reporta violaciones concretas con evidencia y no propone cambiar de patrón sin un problema identificado.

## Inspección obligatoria
Antes de escribir código, lee:
1. `.claude/rules/architecture.md`: la regla que se audita.
2. `tests/Calpil.Template.Web.Tests/ArchitectureTests.cs`: qué se verifica ya de forma automática.
3. `src/Calpil.Template.Web/Program.cs`: composition root.
4. `src/Calpil.Template.Web/Controllers`, `Models`, `Views`, `Services` y `Platform`.

## Procedimiento ejecutable
1. **Ejecutar el guardián:** `dotnet test tests/Calpil.Template.Web.Tests --filter "FullyQualifiedName~ArchitectureTests"` y registrar el resultado.
2. **Revisar controllers:** que solo reciban, llamen a `I*Api`, armen el modelo y elijan vista; buscar reglas de negocio, `try/catch` de `ApiUnavailableException` y uso de `HttpClient`.
3. **Revisar vistas:** lógica que no sea de presentación, `@inject`, `Html.Raw`, código en línea y HTML duplicado que debería ser un parcial.
4. **Revisar modelos:** que los formularios no reutilicen el contrato de la API y que los modelos de vista no llamen servicios.
5. **Revisar Services:** que toda salida de datos pase por un cliente tipado registrado con `IHttpClientFactory` y que los errores se traduzcan según la regla.
6. **Buscar reglas de negocio duplicadas** de la API: deben ser solo ayudas de interfaz y la respuesta de la API debe prevalecer.
7. **Verificar la ausencia de acceso a datos** en paquetes y `using`.
8. **Clasificar** cada hallazgo como BLOCKER, IMPORTANT o IMPROVEMENT, con `archivo:línea`.

## Patrón de implementación
```text
BLOCKER  src/Calpil.Template.Web/Controllers/OrdersController.cs:33
         El controller crea un HttpClient y llama a la API sin pasar por IOrdersApi.
         Regla: architecture.md, "Controller".  Corrección: agregar la operación a IOrdersApi.

IMPORTANT src/Calpil.Template.Web/Views/Orders/Details.cshtml:21
         La vista calcula si el pedido puede anularse. Mover el cálculo al modelo de vista.
```

## Decisiones y anti-patrones
- **NO** modificar código durante la revisión, salvo pedido explícito.
- **NO** reportar preferencias de estilo como violaciones.
- **NO** proponer convertir el portal en SPA, Blazor o agregarle capas de dominio: es un portal MVC delgado.
- **NO** declarar "sin hallazgos" solo porque `ArchitectureTests` pasa: detecta patrones de texto, no semántica.
- **NO** reportar un hallazgo sin `archivo:línea`.

## Verificación / Definition of Done
- Resultado de `ArchitectureTests` incluido en el reporte.
- Cada hallazgo tiene severidad, `archivo:línea`, regla incumplida y corrección sugerida.
- Se indica qué se revisó y qué no.
- Ningún archivo del repositorio fue modificado.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Resumen en una o dos líneas.
2. Hallazgos ordenados por severidad.
3. Puntos de la regla que sí se cumplen.
4. Lo que no se pudo verificar.
