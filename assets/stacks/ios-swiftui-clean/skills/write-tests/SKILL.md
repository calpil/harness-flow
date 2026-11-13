---
name: write-tests
description: Guía para escribir pruebas unitarias deterministas, fakes en memoria y pruebas de ViewModel en iOS
---

# Estrategia y Escritura de Pruebas en iOS

## Objetivo y activación
Esta skill se activa cuando se requiere añadir, ampliar o refactorizar pruebas unitarias o de integración en el proyecto iOS, garantizando rapidez, determinismo y cobertura de casos límite.

## Inspección obligatoria
Antes de escribir pruebas:
- Revisar pruebas existentes en `Tests/CalpilDomainTests/`.
- Revisar pruebas de repositorio en `Tests/CalpilDataTests/`.
- Revisar pruebas de ViewModel en `Tests/CalpilPresentationTests/`.
- Consultar las directrices de testing en `.agents/rules/testing.md` (o `.claude/rules/testing.md`).

## Procedimiento ejecutable
1. **Identificar la capa a evaluar:** Determinar si la prueba corresponde a reglas puras de dominio (`CalpilDomain`), adaptadores de datos (`CalpilData`) o lógica de presentación (`CalpilUI`).
2. **Escribir pruebas de Dominio:** En `Tests/CalpilDomainTests/`, evaluar validaciones de entrada, invariantes de estado y transiciones permitidas y prohibidas.
3. **Escribir pruebas de Datos con Fakes:** En `Tests/CalpilDataTests/`, utilizar `InMemoryWorkItemRepository` para verificar operaciones CRUD y filtrados concurrentes sin tocar la red.
4. **Escribir pruebas de ViewModel:** En `Tests/CalpilPresentationTests/`, anotar la clase de prueba con `@MainActor` y verificar las mutaciones de las propiedades observables ante acciones del usuario.
5. **Verificar manejo de errores:** Comprobar que los errores de dominio y de red se traduzcan en mensajes descriptivos en la propiedad `errorMessage` del ViewModel.
6. **Ejecutar la suite completa:** Ejecutar `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test` y comprobar que todos los casos pasen en menos de 2 segundos.

## Patrón de implementación
```swift
@MainActor
final class ExampleViewModelTests: XCTestCase {
    func testLoadingStateFlow() async throws {
        let repo = InMemoryWorkItemRepository()
        let useCase = ListWorkItemsUseCase(repository: repo)
        let vm = WorkItemListViewModel(listUseCase: useCase, changeStatusUseCase: ChangeWorkItemStatusUseCase(repository: repo))

        XCTAssertTrue(vm.items.isEmpty)
        await vm.loadItems()
        XCTAssertFalse(vm.isLoading)
    }
}
```

## Decisiones y anti-patrones
- **No usar `Thread.sleep` o `Task.sleep` arbitrarios:** Utilizar llamadas asíncronas deterministas con `await`.
- **Aislamiento en MainActor:** Todo test que interactúe con un ViewModel debe correr en el `@MainActor` para evitar advertencias de concurrencia en Swift 6.
- **Fakes explícitos sobre mocks automáticos:** Preferir repositorios en memoria reales y predecibles frente a frameworks de mockeo complejos.

## Verificación / Definition of Done
- Pruebas compiladas y ejecutadas con éxito en XCTest.
- Cobertura de caminos felices y de error.
- Tiempo de ejecución inferior a 2 segundos en local.

## Contrato de entrega del agente
El agente reportará los casos de prueba agregados, las aserciones implementadas y el log de salida de `swift test`.
