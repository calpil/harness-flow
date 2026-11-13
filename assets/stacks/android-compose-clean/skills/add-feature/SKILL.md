---
name: add-feature
description: Guía de implementación end-to-end de una nueva funcionalidad en Android siguiendo Feature-Driven Clean Architecture
---

# Implementación de Funcionalidades en Android con Jetpack Compose

## Objetivo y activación
Esta skill se activa cuando el agente necesita implementar una nueva característica o requerimiento funcional en la aplicación Android, guiando el desarrollo ordenado a través de las capas de Dominio, Datos y Presentación (Jetpack Compose).

## Inspección obligatoria
Antes de escribir código:
- Inspeccionar entidades y errores existentes en `app/src/main/java/.../domain/model/` y `domain/errors/`.
- Revisar interfaces de repositorio en `domain/repository/`.
- Revisar adaptadores de datos en `data/repository/`.
- Revisar componentes de UI y tema en `core/ui/theme/` y `core/ui/components/`.
- Consultar las directrices de arquitectura en `.agents/rules/architecture.md` (o `.claude/rules/architecture.md`).

## Procedimiento ejecutable
1. **Modelar la entidad de Dominio:** Crear la data class inmutable en `domain/model/` con métodos de fábrica (`create`) que validen invariantes y devuelvan `Result<T>`.
2. **Definir el contrato de repositorio:** Declarar la interfaz en `domain/repository/` con métodos `suspend` que utilicen `Result<T>`.
3. **Crear los Casos de Uso:** Implementar clases en `domain/usecases/` con operador invocable (`suspend operator fun invoke`) para cada caso de uso.
4. **Implementar el repositorio en Data:** Crear la implementación en memoria (`InMemoryRepository`) en `data/repository/` para pruebas y la versión remota con cliente HTTP.
5. **Implementar el ViewModel en Presentation:** Crear la clase `ViewModel` en `presentation/` exponiendo una data class `UiState` a través de `StateFlow`.
6. **Diseñar la pantalla en Jetpack Compose:** Crear la función `@Composable` en `presentation/` conectada al `UiState` del ViewModel.
7. **Escribir pruebas automatizadas:** Añadir pruebas unitarias de dominio y de ViewModel con `kotlinx-coroutines-test` en `app/src/test/`.

## Patrón de implementación
```kotlin
// Capa Domain: Invariante protegida
data class Project(val id: UUID, val name: String) {
    companion object {
        fun create(name: String): Result<Project> {
            val trimmed = name.trim()
            if (trimmed.isEmpty()) return Result.failure(DomainError.TitleRequired)
            return Result.success(Project(UUID.randomUUID(), trimmed))
        }
    }
}
```

## Decisiones y anti-patrones
- **No importar Android Framework en Domain:** La capa de dominio debe ser Kotlin puro sin acoplamiento a Compose ni Context.
- **Flujo de estado unidireccional (UDF):** El ViewModel expone un único `StateFlow<UiState>` y recibe eventos mediante métodos públicos.
- **Doble adaptador de persistencia:** Proveer siempre la implementación en memoria para permitir tests rápidos y previews sin red.

## Verificación / Definition of Done
- Pruebas unitarias de dominio y ViewModel ejecutadas exitosamente con `./gradlew test`.
- Cero advertencias de dependencias circulares.
- Pantalla Compose con manejo de estados de carga, vacío, error y contenido.

## Contrato de entrega del agente
El agente reportará los archivos creados en domain, data y presentation, detallará los casos de uso implementados y confirmará la ejecución de `./gradlew test`.
