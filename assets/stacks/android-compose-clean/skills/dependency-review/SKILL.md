---
name: dependency-review
description: Guía para evaluar, auditar y actualizar dependencias en Android mediante Gradle Version Catalog asegurando licencias y seguridad
---

# Revisión de Dependencias en Android con Version Catalog

## Objetivo y activación
Esta skill se activa cuando es necesario evaluar, agregar o actualizar dependencias externas en el proyecto Android utilizando el catálogo `gradle/libs.versions.toml`.

## Inspección obligatoria
Antes de modificar dependencias:
- Revisar `gradle/libs.versions.toml`.
- Revisar `app/build.gradle.kts`.
- Consultar las directrices de dependencias en `.agents/rules/dependencies.md` (o `.claude/rules/dependencies.md`).

## Procedimiento ejecutable
1. **Evaluar necesidad técnica:** Verificar si la funcionalidad requerida puede implementarse con bibliotecas oficiales de Jetpack o KotlinX antes de incorporar librerías de terceros.
2. **Auditar el paquete externo:** Comprobar en Maven Central / Google Maven que la biblioteca cuente con licencia permisiva (Apache 2.0, MIT) y mantenimiento activo.
3. **Declarar en `libs.versions.toml`:** Añadir la versión en `[versions]` y la biblioteca en `[libraries]` dentro del catálogo.
4. **Vincular en `app/build.gradle.kts`:** Consumir la dependencia tipada mediante `implementation(libs.{alias})` o `testImplementation(libs.{alias})`.
5. **Verificar compilación limpia:** Ejecutar `./gradlew assembleDebug` para confirmar que no existan conflictos de dependencias transitivas.
6. **Ejecutar pruebas completas:** Correr `./gradlew test` para asegurar que la nueva librería no altera el comportamiento del sistema.

## Patrón de implementación
```toml
# En gradle/libs.versions.toml
[versions]
datastore = "1.1.1"

[libraries]
androidx-datastore-preferences = { group = "androidx.datastore", name = "datastore-preferences", version.ref = "datastore" }
```

## Decisiones y anti-patrones
- **No codificar dependencias hardcodeadas en build.gradle.kts:** Toda dependencia debe residir en `libs.versions.toml`.
- **Alinear dependencias de Compose con BOM:** Usar Compose BOM para evitar discrepancias de versiones entre sub-librerías de UI.
- **Mantener el wrapper de Gradle versionado:** Asegurar que `gradle-wrapper.properties` esté versionado en Git.

## Verificación / Definition of Done
- Dependencia registrada en `libs.versions.toml` y consumida en `app/build.gradle.kts`.
- Compilación y tests pasando con `./gradlew test`.
- Sin conflictos de versiones transitivas.

## Contrato de entrega del agente
El agente reportará las dependencias añadidas o modificadas, su versión semver, justificación técnica y la confirmación de compilación limpia.
