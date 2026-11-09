---
name: prepare-release
description: Guía de preparación y validación de releases para iOS, versionamiento semver, changelog y verificación de calidad
---

# Preparación de Releases en iOS

## Objetivo y activación
Esta skill se activa cuando se prepara una nueva versión de la aplicación iOS para distribución interna en TestFlight o despliegue productivo en el App Store.

## Inspección obligatoria
Antes de generar la release:
- Revisar `CHANGELOG.md` y los commits recientes.
- Revisar las versiones de los paquetes en `Package.swift`.
- Revisar las reglas de releases y documentación corporativa.
- Comprobar que no existan tests pendientes ni warnings críticos.

## Procedimiento ejecutable
1. **Verificar el changelog:** Actualizar `CHANGELOG.md` detallando las novedades bajo secciones Added, Changed, Fixed y Security siguiendo el formato Keep a Changelog.
2. **Incrementar versión semver:** Establecer el nuevo número de versión semver y el número de compilación (build number) correspondiente.
3. **Ejecutar la suite completa de pruebas:** Correr `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test` y certificar 100% de éxito en todos los módulos.
4. **Validar las skills de agentes:** Ejecutar `node scripts/validate-agent-skills.mjs` para asegurar que la documentación de agentes cumpla con el estándar de 7 secciones.
5. **Verificar compilación release:** Ejecutar `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift build -c release` para garantizar que la compilación optimizada esté libre de errores.
6. **Revisar certificados y perfiles:** Comprobar que la configuración de firmas de código (code signing) y certificados de distribución estén listos para el pipeline de exportación de IPA.

## Patrón de implementación
```bash
# Comprobación de compilación optimizada en modo release
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift build -c release
node scripts/validate-agent-skills.mjs
```

## Decisiones y anti-patrones
- **No liberar con tests fallando:** Toda release debe contar con una suite de pruebas completamente en verde.
- **Mantener trazabilidad semver:** Respetar los criterios semver (MAJOR para breaking changes, MINOR para funcionalidades retrocompatibles, PATCH para corrección de errores).
- **Inmutabilidad de artefactos:** Los binarios firmados no deben modificarse tras su generación en el pipeline.

## Verificación / Definition of Done
- `CHANGELOG.md` actualizado con fecha y notas de versión.
- `swift test` y `swift build -c release` exitosos.
- Validador `scripts/validate-agent-skills.mjs` pasando con 0 errores.

## Contrato de entrega del agente
El agente reportará la versión preparada, el resumen de notas de release en `CHANGELOG.md` y la evidencia de ejecución de pruebas y validación de skills.
