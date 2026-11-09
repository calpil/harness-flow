---
name: prepare-release
description: Guía de preparación y validación de releases para Android, versionamiento semver, ProGuard/R8 y changelog
---

# Preparación de Releases en Android

## Objetivo y activación
Esta skill se activa cuando se prepara una nueva versión de la aplicación Android para distribución interna en Firebase App Distribution o despliegue productivo en Google Play Store.

## Inspección obligatoria
Antes de generar la release:
- Revisar `CHANGELOG.md` y los commits recientes.
- Revisar `versionCode` y `versionName` en `app/build.gradle.kts`.
- Revisar las reglas de ProGuard/R8 en `app/proguard-rules.pro`.
- Comprobar que todos los tests unitarios pasen sin errores.

## Procedimiento ejecutable
1. **Verificar el changelog:** Actualizar `CHANGELOG.md` detallando las novedades bajo secciones Added, Changed, Fixed y Security siguiendo el formato Keep a Changelog.
2. **Incrementar versión semver y build:** Incrementar `versionCode` (entero secuencial) y `versionName` (semver) en `app/build.gradle.kts`.
3. **Ejecutar la suite completa de pruebas:** Correr `./gradlew test` y certificar 100% de éxito en todas las pruebas unitarias.
4. **Validar las skills de agentes:** Ejecutar `node scripts/validate-agent-skills.mjs` para verificar la conformidad de la documentación de agentes.
5. **Verificar compilación release:** Ejecutar `./gradlew assembleRelease` o `bundleRelease` para comprobar que la optimización con R8/ProGuard compile sin conflictos de ofuscación.
6. **Revisar claves de firmado:** Comprobar que el Keystore de firmado de producción y los alias estén configurados a través de variables de entorno seguras en el pipeline de CI/CD.

## Patrón de implementación
```bash
# Compilación release y validación de skills
./gradlew test
./gradlew assembleRelease
node scripts/validate-agent-skills.mjs
```

## Decisiones y anti-patrones
- **No liberar con tests fallando:** Toda release debe contar con una suite de pruebas completamente en verde.
- **Mantener versionamiento secuencial:** `versionCode` debe incrementarse estrictamente de forma monótona ascendente para Google Play.
- **Ofuscación y optimización:** Configurar reglas de ProGuard explícitas para modelos serializables con `@Serializable` para evitar pérdidas de campos en release.

## Verificación / Definition of Done
- `CHANGELOG.md` actualizado con fecha y notas de versión.
- `./gradlew test` y compilación release exitosos.
- Validador `scripts/validate-agent-skills.mjs` pasando con 0 errores.

## Contrato de entrega del agente
El agente reportará la versión preparada, el resumen de notas de release en `CHANGELOG.md` y la evidencia de ejecución de pruebas y validación de skills.
