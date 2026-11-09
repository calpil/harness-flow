---
name: debug-targeted
description: Diagnostica y resuelve fallos específicos, panics en tiempo de ejecución o pruebas que fallan mediante trazabilidad con correlation ID y análisis de causa raíz.
---

# Debug Targeted — CALPIL Golang Engineering Skill

## Objetivo y activación
Activar cuando se reporte un bug específico, una prueba unitaria falle, un endpoint devuelva errores 500 no esperados o se produzca un panic en el servicio Go. Guía la reproducción aislada del problema, análisis de causa raíz y remediación mínima verificable.

## Inspección obligatoria
Antes de tocar código, inspecciona:
1. El stack trace completo o mensaje de fallo del test/log.
2. El archivo y línea exacta señalada en el reporte de error.
3. El `X-Correlation-ID` en los logs estructurados para correlacionar los eventos de la petición afectada.
4. `git status` para aislar cambios no confirmados antes de iniciar el debug.

## Procedimiento ejecutable
1. **Reproducir el Fallo:** Escribir una prueba unitaria o de integración mínima que reproduzca de manera determinista el fallo observado (estrategia TDD de reproducción previa).
2. **Localizar la Capa Afectada:** Determinar si el fallo se origina en la deserialización HTTP (`adapter/in`), orquestación de caso de uso (`application`), invariantes de modelo (`domain`) o consulta SQL (`adapter/out`).
3. **Analizar Causa Raíz:** Examinar valores de entrada, punteros nulos, conversiones de tipo o condiciones de carrera concurrentes (`go test -race`).
4. **Aplicar la Corrección Mínima:** Corregir el defecto en la capa correspondiente sin realizar refactorizaciones mayores ni alterar código ajeno al bug.
5. **Verificar la Prueba de Regresión:** Ejecutar la prueba creada en el paso 1 y confirmar que ahora pase exitosamente.
6. **Ejecutar Suite Completa:** Correr `go test -v -race ./...` para asegurar que la corrección no introdujo regresiones en otras áreas.

## Patrón de implementación
```go
// Ejemplo de test de regresión reproduciendo el defecto antes de corregir
func TestRegression_WorkItem_EmptyTitleWhitespace(t *testing.T) {
    now := time.Now()
    _, err := NewWorkItem("id-123", "   \t\n   ", "desc", now)
    if err != ErrTitleRequired {
        t.Fatalf("expected ErrTitleRequired, got %v", err)
    }
}
```

## Decisiones y anti-patrones
- **NO** aplicar soluciones superficiales tipo "silenciar el error con `_ = ...`" o capturar panics sin registrar la causa.
- **NO** alterar contratos públicos de la API para enmascarar un bug interno.
- **NO** modificar múltiples capas a la vez durante el diagnóstico.

## Verificación / Definition of Done
- Prueba de regresión agregada y pasando.
- Causa raíz explicada claramente.
- `go test -race ./...` pasando limpiamente.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Causa raíz identificada del problema.
2. Capa y archivo donde se originó el defecto.
3. Remediación aplicada y prueba de regresión incorporada.
4. Evidencia de paso de las pruebas.
