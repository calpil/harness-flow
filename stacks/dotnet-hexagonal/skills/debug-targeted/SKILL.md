---
name: debug-targeted
description: Diagnostica y resuelve fallos específicos, excepciones no controladas o pruebas que fallan en .NET mediante trazabilidad con correlation ID y análisis de causa raíz.
---

# Debug Targeted — CALPIL .NET Engineering Skill

## Objetivo y activación
Activar cuando se reporte un defecto, una prueba automatizada falle, un endpoint devuelva errores 500 no esperados o se produzca una excepción en el servicio ASP.NET Core. Guía el aislamiento del problema, la formulación de pruebas de regresión y la corrección quirúrgica.

## Inspección obligatoria
Antes de tocar código, inspecciona:
1. El stack trace completo y mensaje de la excepción registrada.
2. El archivo y línea señalada en el informe de fallo.
3. El `X-Correlation-ID` en los logs estructurados para seguir la traza de la petición.
4. `git status` para asegurar un working tree limpio antes de comenzar.

## Procedimiento ejecutable
1. **Reproducir el Fallo:** Escribir una prueba unitaria o de integración mínima en `tests/` que reproduzca de forma determinista el fallo reportado (TDD inverso).
2. **Identificar la Capa Responsable:** Determinar si el error ocurre en la validación HTTP (`WebApi`), orquestación de use case (`Application`), reglas de modelo (`Domain`) o consulta SQL (`Infrastructure`).
3. **Analizar la Causa Raíz:** Comprobar valores nulos, transiciones de estado inválidas, parseo de enums o parámetros SQL incorrectos.
4. **Aplicar la Corrección Mínima:** Corregir el defecto en la capa pertinente sin modificar comportamiento ni contratos de otras áreas no relacionadas.
5. **Verificar la Prueba de Regresión:** Ejecutar la prueba creada en el paso 1 y confirmar que ahora pase exitosamente.
6. **Ejecutar Suite Completa:** Correr `dotnet test` para asegurar que la solución permanezca completamente verde.

## Patrón de implementación
```csharp
// Test de regresión aislando el caso de borde
[Fact]
public void Create_WithWhitespaceTitle_ThrowsValidationException()
{
    var id = WorkItemId.New();
    var now = DateTime.UtcNow;

    Assert.Throws<ValidationException>(() => WorkItem.Create(id, "   \t   ", "Desc", now));
}
```

## Decisiones y anti-patrones
- **NO** colocar bloques `try-catch` vacíos o silenciar excepciones sin registrar el motivo.
- **NO** alterar contratos públicos de la API para enmascarar un error de implementación interna.
- **NO** aplicar refactorizaciones masivas durante una sesión de resolución de bugs.

## Verificación / Definition of Done
- Prueba de regresión creada y pasando.
- Causa raíz identificada y documentada.
- `dotnet test` ejecutado con 100% de éxito.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Causa raíz identificada del problema.
2. Capa y archivo donde se originó el fallo.
3. Corrección aplicada y prueba de regresión agregada.
4. Resultado de la suite completa de pruebas.
