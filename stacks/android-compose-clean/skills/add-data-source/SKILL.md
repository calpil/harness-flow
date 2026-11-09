---
name: add-data-source
description: Guía para implementar fuentes de datos en Android mediante adaptadores en memoria y clientes HTTP con RFC 7807
---

# Implementación de Fuentes de Datos en Android

## Objetivo y activación
Esta skill se activa cuando es necesario añadir una nueva fuente de datos en `features/*/data/`, implementando interfaces de repositorio definidas en `domain` mediante almacenamiento local o clientes de red HTTP.

## Inspección obligatoria
Antes de codificar la fuente de datos:
- Inspeccionar la interfaz de repositorio en `features/*/domain/repository/`.
- Revisar el modelo de errores RFC 7807 en `core/network/ProblemDetails.kt`.
- Revisar los DTOs de serialización en `features/*/data/dto/`.
- Consultar las reglas de seguridad en `.agents/rules/security.md` (o `.agents/rules/security.md (o .claude/rules/security.md)`).

## Procedimiento ejecutable
1. **Definir DTOs serializables:** Crear data classes con `@Serializable` en `data/dto/` con métodos de transformación `toDomain()`.
2. **Implementar el repositorio en memoria:** Crear una clase en `data/repository/` con `Mutex` y `LinkedHashMap` para garantizar concurrencia segura en tests y entornos locales.
3. **Implementar el repositorio remoto:** Crear una clase que realice peticiones de red utilizando coroutines y serialice/deserialice mediante `kotlinx.serialization`.
4. **Mapear respuestas de error RFC 7807:** Deserializar `ProblemDetails` en respuestas HTTP de error (4xx/5xx) y transformarlas a excepciones de dominio.
5. **Inyectar cabecera de trazabilidad:** Asegurar que cada petición HTTP incluya la cabecera `x-correlation-id`.
6. **Escribir pruebas de repositorio:** Validar las operaciones CRUD y filtrado de datos en `app/src/test/`.

## Patrón de implementación
```kotlin
class RemoteOrderRepository(private val client: ApiClient) : OrderRepository {
    override suspend fun getOrder(id: UUID): Result<Order> = runCatching {
        val dto: OrderDto = client.get("/api/v1/orders/$id")
        dto.toDomain()
    }
}
```

## Decisiones y anti-patrones
- **No filtrar DTOs al dominio:** Las entidades de dominio nunca deben tener anotaciones `@Serializable` de librerías externas ni campos de transporte.
- **Concurrencia segura con Mutex:** Proteger el estado en memoria contra accesos concurrentes de múltiples coroutines.
- **Manejo tipado con Result:** Devolver `Result<T>` en las operaciones de repositorio para evitar excepciones no controladas.

## Verificación / Definition of Done
- Repositorio en memoria y remoto implementando la interfaz completa.
- Mapeo bidireccional DTO <-> Dominio cubierto por tests.
- `./gradlew test` pasando con 0 errores.

## Contrato de entrega del agente
El agente entregará los DTOs, las implementaciones del repositorio, el mapeo de errores y la evidencia de ejecución de pruebas.
