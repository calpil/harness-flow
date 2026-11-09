---
name: add-data-source
description: Guía para implementar fuentes de datos en iOS mediante adaptadores en memoria y clientes HTTP con RFC 7807
---

# Implementación de Fuentes de Datos en iOS

## Objetivo y activación
Esta skill se activa cuando es necesario añadir una nueva fuente de datos en `Sources/CalpilData`, implementando protocolos de repositorio definidos en `CalpilDomain` ya sea mediante almacenamiento local en memoria o mediante integración con APIs REST.

## Inspección obligatoria
Antes de codificar la fuente de datos:
- Inspeccionar el protocolo de repositorio en `Sources/CalpilDomain/Repositories/`.
- Revisar el cliente de red en `Sources/CalpilData/Network/APIClient.swift`.
- Revisar la estructura de errores RFC 7807 en `Sources/CalpilData/Network/HTTPProblemDetails.swift`.
- Revisar los DTOs de transferencia en `Sources/CalpilData/DTOs/`.
- Consultar `.agents/rules/security.md` (o `.agents/rules/security.md (o .claude/rules/security.md)`).

## Procedimiento ejecutable
1. **Definir DTOs de transporte:** Crear las estructuras `Codable & Sendable` en `Sources/CalpilData/DTOs/` con sus respectivos métodos de mapeo hacia la entidad de dominio (`toDomain()`).
2. **Implementar el repositorio en memoria:** Crear o extender un `actor` en `Sources/CalpilData/Repositories/` implementando el protocolo del repositorio para soportar entornos offline, tests y previews.
3. **Implementar el repositorio remoto:** Crear una clase o actor que utilice `APIClientProtocol` para invocar los endpoints HTTP correspondientes.
4. **Mapear respuestas de error:** Asegurar que los fallos HTTP deserialicen `HTTPProblemDetails` (RFC 7807) y los propaguen como errores de dominio comprensibles.
5. **Inyectar cabeceras de trazabilidad:** Garantizar que cada llamada HTTP propague la cabecera `x-correlation-id`.
6. **Escribir pruebas unitarias de persistencia:** Validar operaciones de lectura, escritura y filtrado en `Tests/CalpilDataTests/`.

## Patrón de implementación
```swift
public actor RemoteUserRepository: UserRepositoryProtocol {
    private let apiClient: APIClientProtocol

    public init(apiClient: APIClientProtocol) {
        self.apiClient = apiClient
    }

    public func getProfile() async throws -> UserProfile {
        let dto: UserProfileDTO = try await apiClient.request(
            endpoint: "/api/v1/profile",
            method: "GET",
            body: nil,
            correlationId: nil
        )
        return dto.toDomain()
    }
}
```

## Decisiones y anti-patrones
- **No filtrar DTOs al dominio:** Las entidades de dominio nunca deben adoptar dependencias de deserialización de la API externa.
- **Concurrencia segura con actores:** Usar `actor` para repositorios mutables y evitar condiciones de carrera en Swift 6.
- **Manejo de errores tipado:** No atrapar excepciones genéricas silenciosamente; transformar errores de red a `DomainError` o `HTTPProblemDetails`.

## Verificación / Definition of Done
- Adaptador en memoria y remoto implementando el protocolo completamente.
- Mapeo bidireccional DTO <-> Entidad probado con tests unitarios.
- `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test` pasando al 100%.

## Contrato de entrega del agente
El agente entregará los DTOs, la implementación del repositorio, el mapeo de errores y la evidencia de ejecución de pruebas.
