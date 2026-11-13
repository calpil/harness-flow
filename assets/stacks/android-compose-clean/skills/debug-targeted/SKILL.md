---
name: debug-targeted
description: Procedimiento sistemático para aislar, reproducir y corregir bugs en Android mediante pruebas focalizadas y depuración de coroutines
---

# Depuración Focalizada en Android (Jetpack Compose & Coroutines)

## Objetivo y activación
Esta skill se activa cuando se detecta un fallo en tiempo de ejecución, una prueba rota o un comportamiento anómalo en la aplicación Android, guiando al agente en la resolución quirúrgica del problema.

## Inspección obligatoria
Antes de modificar código:
- Inspeccionar el mensaje de error o stack trace de JUnit / Logcat.
- Identificar el paquete (`domain`, `data` o `presentation`) donde ocurre la anomalía.
- Revisar posibles condiciones de carrera en coroutines o estados de StateFlow.
- Consultar las reglas de testing en `.agents/rules/testing.md` (o `.claude/rules/testing.md`).

## Procedimiento ejecutable
1. **Capturar la falla exacta:** Ejecutar `./gradlew testDebugUnitTest --tests "{NombreClaseTest}.{metodoTest}"` para aislar el fallo y observar el resultado.
2. **Crear prueba de reproducción mínima:** Escribir un test unitario que reproduzca el error de forma consistente y determinista usando `runTest`.
3. **Analizar la causa raíz:** Identificar si la falla es de validación de invariante (`domain`), error de persistencia/red (`data`) o estado/recomposición (`presentation`).
4. **Aplicar la corrección mínima necesaria:** Modificar el código fuente afectado sin alterar contratos públicos innecesariamente.
5. **Ejecutar la prueba focalizada:** Correr la prueba creada en el paso 2 para validar que el fallo ha sido resuelto.
6. **Ejecutar regresión completa:** Correr toda la suite de pruebas del proyecto (`./gradlew test`) para asegurar que no se introdujeron regresiones colaterales.

## Patrón de implementación
```bash
# Ejecutar un caso de prueba individual en Android
./gradlew testDebugUnitTest --tests "com.calpil.template.features.workitems.domain.WorkItemTest.createValidWorkItem_succeeds"
```

## Decisiones y anti-patrones
- **No silenciar excepciones con bloques catch vacíos:** Manejar los errores explícitamente mediante `Result` o propagación adecuada.
- **No usar retardos arbitrarios:** Reemplazar `delay()` en pruebas con `advanceUntilIdle()` o `advanceTimeBy()` de coroutines test.
- **Aislamiento de pruebas:** Cada prueba debe crear su propia instancia de repositorio en memoria para no compartir estado con otros tests.
- **Evitar mutableStateOf en dominio:** No utilizar tipos de estado de Compose dentro de capas de dominio o datos.

## Verificación / Definition of Done
- La prueba focalizada que antes fallaba ahora pasa al 100%.
- La suite completa de pruebas pasa con 0 fallos.
- Sin advertencias críticas del compilador de Kotlin.
- Aislamiento de estados confirmado en la suite de pruebas.

## Contrato de entrega del agente
El agente reportará la causa raíz identificada, el diff de la solución, la prueba de regresión agregada y la evidencia de ejecución limpia de `./gradlew test`.
