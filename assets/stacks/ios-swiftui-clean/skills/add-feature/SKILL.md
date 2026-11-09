---
name: add-feature
description: Guía de implementación end-to-end de una nueva funcionalidad en iOS siguiendo Feature-Driven Clean Architecture
---

# Implementación de Funcionalidades en iOS con SwiftUI

## Objetivo y activación
Esta skill se activa cuando el agente necesita implementar una nueva característica o requerimiento funcional en la aplicación iOS, guiando el desarrollo ordenado a través de las capas de Dominio, Datos y Presentación (SwiftUI).

## Inspección obligatoria
Antes de escribir código:
- Inspeccionar entidades y errores existentes en `Sources/CalpilDomain/Models/` y `Errors/`.
- Revisar protocolos de repositorio en `Sources/CalpilDomain/Repositories/`.
- Revisar adaptadores de datos en `Sources/CalpilData/Repositories/`.
- Revisar componentes de UI y temas en `Sources/CalpilUI/Core/`.
- Consultar las directrices de arquitectura en `.agents/rules/architecture.md` (o `.agents/rules/architecture.md (o .claude/rules/architecture.md)`).

## Procedimiento ejecutable
1. **Modelar la entidad de Dominio:** Crear la estructura inmutable en `Sources/CalpilDomain/Models/` con constructores que validen invariantes de negocio y lancen `DomainError`.
2. **Definir el contrato de repositorio:** Declarar el protocolo `Sendable` en `Sources/CalpilDomain/Repositories/` con métodos asíncronos (`async throws`).
3. **Crear los Casos de Uso:** Implementar estructuras individuales en `Sources/CalpilDomain/UseCases/` que orquesten la lógica de negocio requerida.
4. **Implementar el repositorio en Data:** Crear la implementación en memoria (`InMemoryRepository`) en `Sources/CalpilData/Repositories/` para pruebas deterministas y la versión remota con `APIClient`.
5. **Implementar el ViewModel en UI:** Crear una clase `@MainActor ObservableObject` en `Sources/CalpilUI/Features/{Feature}/ViewModels/` que exponga estados `@Published` de carga, datos y error.
6. **Diseñar la vista SwiftUI:** Crear la vista declarativa en `Sources/CalpilUI/Features/{Feature}/Views/` conectada al ViewModel.
7. **Escribir pruebas automatizadas:** Añadir pruebas unitarias de dominio y de ViewModel en `Tests/`.

## Patrón de implementación
```swift
// Capa Domain: Invariante protegida
public struct Account: Identifiable, Sendable {
    public let id: UUID
    public let name: String

    public static func create(name: String) throws -> Account {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { throw DomainError.titleRequired }
        return Account(id: UUID(), name: trimmed)
    }
}
```

## Decisiones y anti-patrones
- **No importar SwiftUI en Domain:** La capa de dominio debe ser Swift puro sin acoplamiento a frameworks de interfaz gráfica.
- **ViewModels en MainActor:** Todo ViewModel que altere estado para vistas SwiftUI debe estar anotado con `@MainActor`.
- **Doble adaptador de persistencia:** Siempre proveer la implementación en memoria para permitir tests rápidos y previsualizaciones sin depender de red.

## Verificación / Definition of Done
- Pruebas unitarias de dominio y ViewModel ejecutadas exitosamente con `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test`.
- Cero dependencias circulares entre targets de SPM.
- Vista SwiftUI interactiva y con manejo explícito de estados vacío, carga y error.

## Contrato de entrega del agente
El agente reportará los archivos creados en Domain, Data y UI, detallará los casos de uso implementados y confirmará la ejecución exitosa de la suite de pruebas.
