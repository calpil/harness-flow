---
name: architecture-review
description: Audita la API .NET layered en busca de violaciones reales de capas, composition root y aislamiento entre features, con evidencia archivo:línea y sin modificar código.
---

# Architecture Review — CALPIL .NET Layered

## Objetivo y activación
Activar cuando se pide revisar la arquitectura, antes de un release o tras un cambio grande. Es una revisión de solo lectura: reporta violaciones concretas con evidencia; no reescribe ni propone cambiar de patrón sin un problema identificado.

## Inspección obligatoria
Antes de escribir código, lee:
1. `.claude/rules/architecture.md`: la regla que se audita.
2. `tests/Calpil.Template.Api.Tests/Architecture/LayeringTests.cs`: qué se verifica ya de forma automática.
3. `src/Calpil.Template.Api/Program.cs`: composition root.
4. Cada carpeta de feature bajo `src/Calpil.Template.Api/` y `src/Calpil.Template.Api/Platform/`.

## Procedimiento ejecutable
1. **Ejecutar el guardián:** `dotnet test tests/Calpil.Template.Api.Tests --filter "FullyQualifiedName~LayeringTests"` y registrar el resultado.
2. **Revisar controllers:** que solo validen forma, llamen a un service y conviertan a `*Response`; buscar reglas de negocio, `try/catch` y acceso a datos.
3. **Revisar services:** que no usen tipos de `Microsoft.AspNetCore`, SQL ni nombres completamente calificados que esquiven los `using` (`grep -rn "Microsoft.AspNetCore\|Dapper\|SqlConnection" --include='*Service.cs'`).
4. **Revisar repositorios:** que no decidan reglas de negocio ni conozcan HTTP; que todo SQL sea parametrizado.
5. **Revisar el registro:** que solo `Program.cs` y los `AddXxx()` registren dependencias, y que no haya `new` de services o repositorios en el código de producción.
6. **Revisar aislamiento:** que una feature no use el repositorio de otra y que `Platform/` no referencie features.
7. **Clasificar** cada hallazgo como BLOCKER (rompe una invariante), IMPORTANT (erosiona una capa) o IMPROVEMENT, con `archivo:línea`.

## Patrón de implementación
```text
BLOCKER  src/Calpil.Template.Api/Orders/OrdersController.cs:41
         El controller inyecta IOrderRepository y consulta datos sin pasar por OrderService.
         Regla: architecture.md, "Controller".  Corrección: mover la consulta a OrderService.

IMPORTANT src/Calpil.Template.Api/Orders/OrderService.cs:17
         El service lanza BadHttpRequestException (tipo HTTP). Usar AppException(ErrorKind.Invalid, ...).
```

## Decisiones y anti-patrones
- **NO** modificar código durante la revisión, salvo pedido explícito.
- **NO** reportar preferencias de estilo como violaciones de arquitectura.
- **NO** proponer migrar a hexagonal, CQRS o MediatR: el patrón de este repositorio es layered.
- **NO** declarar "sin hallazgos" solo porque `LayeringTests` pasa: la prueba lee `using` e identificadores, no semántica.
- **NO** reportar un hallazgo sin `archivo:línea`.

## Verificación / Definition of Done
- Resultado de `LayeringTests` incluido en el reporte.
- Cada hallazgo tiene severidad, `archivo:línea`, regla incumplida y corrección sugerida.
- Se indica explícitamente qué se revisó y qué no.
- Ningún archivo del repositorio fue modificado.

## Contrato de entrega del agente
El mensaje final debe informar:
1. Resumen en una o dos líneas.
2. Hallazgos ordenados por severidad.
3. Puntos de la regla que sí se cumplen.
4. Lo que no se pudo verificar.
