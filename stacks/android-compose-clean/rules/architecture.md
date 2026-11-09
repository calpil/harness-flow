---
description: Límites de Feature-Driven Clean Architecture y separación de capas en Android con Jetpack Compose y Kotlin
globs: ["app/src/**"]
---

# Reglas de Arquitectura en Android (Jetpack Compose + Clean Architecture)

- **Capa Domain (`features/*/domain/**`):**
  - Kotlin puro sin dependencias de Android framework (`android.*`), Jetpack Compose ni librerías de persistencia.
  - Entidades de datos inmutables (`WorkItem`) con validación de invariantes en métodos de fábrica (`create`) y mutaciones explícitas (`changeStatus`).
  - Errores de negocio modelados con clases selladas (`DomainError`).
  - Interfaces de repositorios y casos de uso con operadores invocables (`suspend operator fun invoke`).
- **Capa Data (`features/*/data/**`):**
  - Implementa las interfaces de repositorio de Domain.
  - DTOs serializables con `kotlinx.serialization` mapeados explícitamente a entidades de dominio; los DTOs nunca se exponen al dominio.
  - Adaptador en memoria concurrente seguro (`InMemoryWorkItemRepository`) y cliente HTTP con parsing de RFC 7807 `ProblemDetails`.
- **Capa Presentation (`features/*/presentation/**`):**
  - Pantallas declarativas en Jetpack Compose organizadas por características.
  - ViewModels de Android Architecture Components exponiendo `StateFlow<UiState>` inmutables.
  - Manejo explícito de los cuatro estados canónicos: Carga, Vacío, Error y Contenido.
- **Inversión de Dependencias:**
  - `presentation` -> `domain`
  - `data` -> `domain`
  - `core` agrupa primitivas transversales de UI (tema, componentes) y red.
