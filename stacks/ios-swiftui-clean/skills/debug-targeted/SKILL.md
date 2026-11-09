---
name: debug-targeted
description: Procedimiento sistemático para aislar, reproducir y corregir bugs en iOS mediante pruebas focalizadas y depuración en Swift Concurrency
---

# Depuración Focalizada en iOS (Swift & SwiftUI)

## Objetivo y activación
Esta skill se activa cuando se detecta un fallo en tiempo de ejecución, una prueba rota o un comportamiento visual o de estado anómalo en la aplicación iOS, guiando al agente en la resolución quirúrgica del problema.

## Inspección obligatoria
Antes de modificar código:
- Inspeccionar el mensaje de error de XCTest o la traza del crash.
- Identificar el módulo (Domain, Data o UI) donde ocurre la anomalía.
- Revisar advertencias de Swift Concurrency o posibles carreras en actores.
- Consultar las reglas de testing en `.agents/rules/testing.md` (o `.agents/rules/testing.md (o .claude/rules/testing.md)`).

## Procedimiento ejecutable
1. **Capturar la falla exacta:** Ejecutar `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test --filter {FailingTest}` para aislar el fallo y observar el resultado.
2. **Crear prueba de reproducción mínima:** Escribir un test unitario en la suite correspondiente que reproduzca el error de forma consistente y determinista.
3. **Analizar la causa raíz:** Identificar si el problema es de validación de invariante (`CalpilDomain`), condición de carrera / actor (`CalpilData`) o sincronización de UI en el hilo principal (`CalpilUI`).
4. **Aplicar la corrección mínima necesaria:** Modificar el código fuente afectado sin alterar contratos públicos innecesariamente.
5. **Ejecutar la prueba focalizada:** Correr la prueba creada en el paso 2 para validar que el fallo ha sido resuelto.
6. **Ejecutar regresión completa:** Correr toda la suite de pruebas del proyecto (`swift test`) para asegurar que no se introdujeron regresiones colaterales.

## Patrón de implementación
```bash
# Ejecutar un caso de prueba individual en Swift
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test --filter WorkItemTests/testStatusTransitions
```

## Decisiones y anti-patrones
- **No forzar desempaquetados con `!`:** Evitar force unwraps que puedan provocar crashes en producción; usar `guard let`, `if let` o coalescencia `??`.
- **No alterar el hilo principal fuera de MainActor:** Asegurar que las mutaciones de propiedades `@Published` se ejecuten siempre bajo `@MainActor`.
- **Mantener determinismo:** Evitar retardos artificiales con `sleep` para solucionar condiciones de carrera.
- **Aislamiento de pruebas:** Cada prueba debe crear su propio repositorio en memoria para no compartir estado con otros tests.

## Verificación / Definition of Done
- La prueba focalizada que antes fallaba ahora pasa al 100%.
- La suite completa de pruebas pasa con 0 fallos.
- Sin advertencias del compilador de Swift.
- Aislamiento verificado en el entorno de pruebas.

## Contrato de entrega del agente
El agente reportará la causa raíz identificada, el diff de la solución, la prueba de regresión agregada y la evidencia de ejecución limpia de `swift test`.
