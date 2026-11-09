---
description: Reglas de gestión y auditoría de paquetes externos en Swift Package Manager
globs: ["Package.swift", "Package.resolved"]
---

# Reglas de Dependencias en iOS (Swift Package Manager)

- **Swift Package Manager Estándar:**
  - Todas las dependencias externas se declaran en `Package.swift` con versiones semver fijas o acotadas (`from: "x.y.z"`).
  - Prohibido el uso de CocoaPods o Carthage. Toda dependencia debe integrarse como paquete SPM oficial.
- **Auditoría y Mínimo Acoplamiento:**
  - No añadir paquetes externos para capacidades que la biblioteca estándar de Apple (Foundation, SwiftUI, Combine, Concurrency) ya resuelve de forma nativa.
  - Verificar licencias permisivas (MIT, Apache 2.0, BSD) y mantenimiento activo del repositorio de la dependencia.
- **Control de Módulos y Tiempos de Build:**
  - Cada dependencia debe vincularse únicamente al target que la necesita (e.g. no enlazar bibliotecas de red en `CalpilDomain`).
  - Mantener `Package.resolved` versionado en Git para garantizar compilaciones reproducibles en CI/CD y entre desarrolladores.
