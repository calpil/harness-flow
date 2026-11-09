---
description: Reglas de pruebas unitarias, testing de coroutines y determinismo en Android
globs: ["app/src/test/**", "**/*Test*.kt"]
---

# Reglas de Pruebas en Android (JUnit & Coroutines Test)

- **Pruebas Unitarias de Dominio:**
  - `features/*/domain/**` debe probarse exhaustivamente con JUnit 4/5 y Google Truth, validando la creación de entidades, invariantes de negocio y transiciones de estado.
- **Testing Determinista con Coroutines Test:**
  - Probar ViewModels y repositorios asíncronos mediante `runTest` y `StandardTestDispatcher` de `kotlinx-coroutines-test`.
  - Configurar `Dispatchers.setMain(testDispatcher)` en `@Before` y `Dispatchers.resetMain()` en `@After` para controlar la ejecución en el hilo principal sin retardos artificiales.
- **Fakes en Memoria sobre Mocks Opacos:**
  - Usar implementaciones concretas en memoria (`InMemoryWorkItemRepository`) para verificar flujos completos de forma rápida y confiable.
- **Ejecución y Verificación Continua:**
  - Toda la suite de pruebas unitarias debe ejecutarse con éxito antes de cualquier commit: `./gradlew test`.
