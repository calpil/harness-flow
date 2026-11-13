---
name: architecture-review
description: Guía de auditoría y revisión de límites de Clean Architecture y aislamiento de módulos en iOS con Swift Package Manager
---

# Auditoría de Arquitectura en iOS (SwiftUI)

## Objetivo y activación
Esta skill se activa para auditar que el código del proyecto iOS respete estrictamente los límites de Clean Architecture, la separación de responsabilidades y la inversión de dependencias entre los targets de SPM.

## Inspección obligatoria
Antes de emitir un veredicto:
- Inspeccionar `Package.swift` y validar el grafo de dependencias de cada target.
- Verificar que `CalpilDomain` no importe `SwiftUI`, `CalpilData` o `CalpilUI`.
- Verificar que `CalpilData` no importe `CalpilUI` ni `SwiftUI`.
- Verificar que los ViewModels en `CalpilUI` estén aislados en `@MainActor`.
- Consultar las directrices en `.agents/rules/architecture.md` (o `.claude/rules/architecture.md`).

## Procedimiento ejecutable
1. **Auditar dependencias de `CalpilDomain`:** Verificar en `Package.swift` que `CalpilDomain` tenga `dependencies: []` y no importe librerías de terceros o frameworks de interfaz.
2. **Revisar imports en ficheros de dominio:** Escanear archivos en `Sources/CalpilDomain/` confirmando que solo dependan de `Foundation`.
3. **Validar aislamiento de datos:** Confirmar que `CalpilData` implemente los protocolos de `CalpilDomain` sin exponer detalles de implementación o red a capas superiores.
4. **Verificar separación de UI:** Comprobar que las vistas de `CalpilUI` no realicen llamadas HTTP directas ni ejecuten mutaciones de almacenamiento sin pasar por casos de uso o ViewModels.
5. **Auditar concurrencia en Swift 6:** Validar que los tipos compartidos cumplan con `Sendable` y que los actores protejan su estado mutable.
6. **Ejecutar compilación y tests:** Correr `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test` para certificar la compilación modular.

## Patrón de implementación
```text
Grafo de Dependencias Permitido:
CalpilUI -> CalpilDomain
CalpilData -> CalpilDomain
CalpilApp -> CalpilUI, CalpilData, CalpilDomain
```

## Decisiones y anti-patrones
- **No acoplar dominio a SwiftUI:** Las entidades de dominio no deben conformar protocolos de presentación ni contener lógica de renderizado.
- **Inversión de dependencias estricta:** La capa de UI interactúa con casos de uso, los cuales reciben protocolos de repositorio inyectados.
- **Cero singletons globales mutables:** Evitar estados globales mutables no controlados; usar inyección de dependencias a través de constructores.

## Verificación / Definition of Done
- Comprobación de pureza de `CalpilDomain`.
- Conformidad de `Sendable` en tipos concurrentes.
- Ejecución limpia de `swift test`.

## Contrato de entrega del agente
El agente entregará una tabla de evaluación por módulo (Domain, Data, UI, App) detallando el cumplimiento de límites arquitectónicos y cualquier advertencia detectada.
