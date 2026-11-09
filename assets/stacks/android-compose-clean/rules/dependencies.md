---
description: Reglas de gestión y auditoría de dependencias en Android mediante Gradle Version Catalogs
globs: ["gradle/libs.versions.toml", "**/*.gradle.kts"]
---

# Reglas de Dependencias en Android (Gradle Version Catalog)

- **Catálogo Centralizado (`libs.versions.toml`):**
  - Toda dependencia de biblioteca o plugin debe declararse en `gradle/libs.versions.toml` bajo `[versions]`, `[libraries]` y `[plugins]`.
  - Prohibido codificar versiones hardcodeadas o cadenas arbitrarias en archivos `build.gradle.kts`.
- **Compose BOM (Bill of Materials):**
  - Las dependencias de Jetpack Compose deben consumir la plataforma Compose BOM (`androidx-compose-bom`) para garantizar compatibilidad estricta de versiones.
- **Auditoría y Mantenimiento:**
  - No añadir librerías no oficiales o descontinuadas.
  - Priorizar las bibliotecas oficiales de Jetpack (Navigation Compose, Lifecycle, Material 3) y KotlinX (Coroutines, Serialization).
- **Reproducibilidad:**
  - El wrapper de Gradle (`gradlew`, `gradle/wrapper/gradle-wrapper.properties`) debe versionarse en Git para asegurar builds reproducibles e idénticos en máquinas locales y CI/CD.
