---
name: dependency-review
description: Guía para evaluar, auditar y actualizar paquetes externos en iOS con Swift Package Manager asegurando licencias y seguridad
---

# Revisión de Dependencias en iOS con Swift Package Manager

## Objetivo y activación
Esta skill se activa cuando es necesario evaluar, agregar o actualizar dependencias externas de Swift Package Manager en `Package.swift`, auditando su procedencia, licencia y compatibilidad con Swift 6.

## Inspección obligatoria
Antes de modificar dependencias:
- Revisar `Package.swift` y `Package.resolved`.
- Revisar las dependencias declaradas en cada target.
- Consultar las directrices de dependencias en `.agents/rules/dependencies.md` (o `.claude/rules/dependencies.md`).

## Procedimiento ejecutable
1. **Evaluar necesidad técnica:** Verificar si la capacidad requerida puede implementarse con Foundation, SwiftUI o Concurrency antes de añadir un paquete de terceros.
2. **Auditar el paquete externo:** Comprobar en GitHub/Swift Package Index que el repositorio cuente con soporte para Swift 6, licencia permisiva (MIT, Apache 2.0) y mantenimiento activo.
3. **Declarar en `Package.swift`:** Añadir el paquete en el array `dependencies` de `Package.swift` utilizando reglas de versión exactas o acotadas por semver (`from: "x.y.z"`).
4. **Vincular al target correspondiente:** Añadir la dependencia exclusivamente al target que la utiliza en `targets: [...]`.
5. **Resolver y compilar dependencias:** Ejecutar `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift package resolve` y `swift build` para verificar compatibilidad.
6. **Ejecutar pruebas completas:** Correr `swift test` para asegurar que el paquete no introduce regresiones ni advertencias de concurrencia.

## Patrón de implementación
```swift
// En Package.swift
dependencies: [
    .package(url: "https://github.com/apple/swift-algorithms.git", from: "1.2.0")
],
targets: [
    .target(
        name: "CalpilData",
        dependencies: [
            "CalpilDomain",
            .product(name: "Algorithms", package: "swift-algorithms")
        ]
    )
]
```

## Decisiones y anti-patrones
- **No usar gestores legados:** Prohibido CocoaPods o Carthage. Solo Swift Package Manager.
- **Evitar paquetes abandonados:** Rechazar paquetes sin commits recientes o sin compatibilidad con Swift 6 y Concurrency estricto.
- **Mantener `Package.resolved` en control de versiones:** Garantizar builds idénticos y reproducibles en CI y entornos de producción.

## Verificación / Definition of Done
- Dependencia agregada en `Package.swift` con versión semver explícita.
- Compilación y tests pasando al 100%.
- `Package.resolved` actualizado.

## Contrato de entrega del agente
El agente reportará los paquetes añadidos o modificados, su justificación técnica, versión semver y la confirmación de compilación limpia.
