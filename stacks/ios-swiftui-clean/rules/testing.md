---
description: Reglas de pruebas unitarias, determinismo de estado y pruebas de integración en iOS
globs: ["Tests/**", "**/*Test*.swift"]
---

# Reglas de Pruebas en iOS (XCTest & Swift Concurrency)

- **Pruebas Unitarias de Dominio:**
  - `CalpilDomainTests` debe verificar todas las reglas de negocio, validaciones de constructores y transiciones de estado de forma pura y síncrona/asíncrona sin simular red.
- **Testing con Fakes en Memoria (Testing Determinista):**
  - Probar ViewModels y flujos de negocio usando `InMemoryWorkItemRepository`.
  - Prohibido el uso de `Thread.sleep` o `Task.sleep` arbitrarios para sincronizar estados en pruebas asíncronas.
- **Aislamiento en MainActor:**
  - Las pruebas de ViewModels deben ejecutarse bajo `@MainActor` para garantizar consistencia de estado con SwiftUI.
- **Ejecución y Verificación Continua:**
  - Antes de cada commit, la suite de pruebas completa debe pasar con 0 fallos: `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test`.
