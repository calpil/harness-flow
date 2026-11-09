---
description: Límites de Feature-Driven Clean Architecture y separación de capas en iOS y Swift
globs: ["Sources/**", "Tests/**"]
---

# Reglas de Arquitectura en iOS (SwiftUI + Clean Architecture)

- **Capa Domain (`Sources/CalpilDomain/**`):**
  - Swift puro e independiente de frameworks de presentación (SwiftUI) o persistencia externa.
  - Entidades con invariantes protegidas mediante métodos de fábrica (`WorkItem.create`) y mutaciones controladas (`changingStatus`).
  - Errores de negocio tipados con `DomainError`.
  - Definición de protocolos de repositorios y casos de uso individuales (`CreateWorkItemUseCase`, etc.).
- **Capa Data (`Sources/CalpilData/**`):**
  - Implementa los protocolos de repositorio definidos en Domain.
  - Provee adaptador en memoria thread-safe (`InMemoryWorkItemRepository`) y cliente HTTP remoto (`RemoteWorkItemRepository`).
  - Mapeo bidireccional estricto entre DTOs y modelos de dominio; los DTOs nunca se filtran al dominio.
  - Manejo de errores de red bajo RFC 7807 `HTTPProblemDetails`.
- **Capa UI / Presentation (`Sources/CalpilUI/**`):**
  - Vistas SwiftUI declarativas y desacopladas.
  - ViewModels aislados en el `@MainActor` con estado observable (`@Published` o `@Observable`).
  - Toda mutación de estado pasa a través de casos de uso de dominio.
- **Inversión de Dependencias:**
  - `CalpilUI` depende de `CalpilDomain` (y adaptadores de `CalpilData` en composición).
  - `CalpilData` depende de `CalpilDomain`.
  - `CalpilDomain` no depende de nadie.
