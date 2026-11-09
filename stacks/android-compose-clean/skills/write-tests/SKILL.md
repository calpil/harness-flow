---
name: write-tests
description: Guía para escribir pruebas unitarias deterministas, fakes en memoria y pruebas de ViewModel con coroutines en Android
---

# Estrategia y Escritura de Pruebas en Android

## Objetivo y activación
Esta skill se activa cuando se requiere añadir, ampliar o refactorizar pruebas unitarias en la aplicación Android, garantizando rapidez, determinismo y cobertura de casos límite con coroutines.

## Inspección obligatoria
Antes de escribir pruebas:
- Revisar pruebas existentes en `app/src/test/`.
- Revisar pruebas de ViewModel en `app/src/test/.../presentation/WorkItemListViewModelTest.kt`.
- Revisar las dependencias de testing en `gradle/libs.versions.toml`.
- Consultar las directrices de testing en `.claude/rules/testing.md`.

## Procedimiento ejecutable
1. **Identificar la capa a evaluar:** Determinar si la prueba evalúa reglas de dominio puro (`domain`), adaptadores de datos (`data`) o lógica de presentación (`presentation`).
2. **Escribir pruebas de Dominio:** En `domain/`, evaluar invariantes de negocio, datos límite (textos vacíos, límites de longitud) y transiciones de estado permitidas e inválidas.
3. **Escribir pruebas de Repositorio con Fakes:** En `data/`, utilizar `InMemoryWorkItemRepository` para validar operaciones asíncronas con `runTest`.
4. **Escribir pruebas de ViewModel con Dispatchers:** En `presentation/`, configurar `StandardTestDispatcher()`, `Dispatchers.setMain(testDispatcher)` en `@Before` y `Dispatchers.resetMain()` en `@After`.
5. **Avanzar el despachador de coroutines:** Usar `advanceUntilIdle()` de `kotlinx-coroutines-test` para asegurar que las coroutines pendientes se ejecuten antes de las aserciones.
6. **Ejecutar la suite completa:** Ejecutar `./gradlew test` y comprobar que todos los casos pasen en milisegundos.

## Patrón de implementación
```kotlin
@OptIn(ExperimentalCoroutinesApi::class)
class FeatureViewModelTest {
    private val testDispatcher = StandardTestDispatcher()

    @Before fun setUp() { Dispatchers.setMain(testDispatcher) }
    @After fun tearDown() { Dispatchers.resetMain() }

    @Test fun testActionUpdatesState() = runTest(testDispatcher) {
        val vm = FeatureViewModel(useCase)
        advanceUntilIdle()
        assertThat(vm.uiState.value.isLoaded).isTrue()
    }
}
```

## Decisiones y anti-patrones
- **No usar `Thread.sleep`:** Usar `runTest` y `advanceUntilIdle()` para sincronizar coroutines de forma determinista.
- **Configurar Main Dispatcher:** Siempre reasignar `Dispatchers.setMain` al probar componentes vinculados a `viewModelScope`.
- **Fakes explícitos sobre mocks pesados:** Preferir implementaciones en memoria reales frente a frameworks de mockeo complejos.

## Verificación / Definition of Done
- Pruebas compiladas y ejecutadas con éxito con JUnit y Google Truth.
- Cobertura de caminos felices y de error.
- Tiempo de ejecución inferior a 1 segundo para la suite de pruebas unitarias.

## Contrato de entrega del agente
El agente reportará los casos de prueba agregados, las aserciones implementadas y el log de salida de `./gradlew test`.
