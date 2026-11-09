---
name: architecture-review
description: Guía de auditoría y revisión de límites de Feature-Driven Clean Architecture en Android y Jetpack Compose
---

# Auditoría de Arquitectura en Android (Jetpack Compose)

## Objetivo y activación
Esta skill se activa para auditar que el código del proyecto Android respete estrictamente los límites de Clean Architecture, la separación de responsabilidades y la inversión de dependencias entre paquetes.

## Inspección obligatoria
Antes de emitir un veredicto:
- Inspeccionar `app/build.gradle.kts` y el catálogo `libs.versions.toml`.
- Verificar que el paquete `domain` no contenga dependencias hacia `data`, `presentation` ni `android.*`.
- Verificar que `data` no dependa de `presentation`.
- Verificar que los ViewModels expongan `StateFlow` inmutables.
- Consultar las directrices en `.agents/rules/architecture.md` (o `.agents/rules/architecture.md (o .claude/rules/architecture.md)`).

## Procedimiento ejecutable
1. **Auditar pureza del Dominio:** Comprobar que en `domain/` no existan imports de paquetes de Android (`android.os.*`, `androidx.compose.*`) ni de red/persistencia.
2. **Revisar contratos de repositorio:** Confirmar que `domain/repository/` solo contenga interfaces y no implementaciones concretas.
3. **Validar aislamiento de datos:** Confirmar que `data/` implemente los contratos de dominio sin exponer modelos DTO a capas superiores.
4. **Verificar separación de presentación:** Comprobar que las pantallas en Jetpack Compose no ejecuten llamadas de red directas ni consultas de base de datos sin pasar por ViewModels o Casos de Uso.
5. **Auditar gestión de estado reactivo:** Verificar que los ViewModels utilicen `_uiState.asStateFlow()` para proteger el estado mutable interno.
6. **Ejecutar suite de tests:** Correr `./gradlew test` para certificar la estabilidad de la solución.

## Patrón de implementación
```text
Grafo de Dependencias Permitido:
presentation -> domain
data -> domain
app/composition root -> presentation, data, domain
```

## Decisiones y anti-patrones
- **No acoplar dominio al framework:** Las entidades de dominio no deben depender del ciclo de vida de Android.
- **Inversión de dependencias:** Los ViewModels consumen casos de uso; los casos de uso reciben interfaces de repositorio.
- **Evitar estados globales mutables:** Evitar variables estáticas mutables en `Companion Objects` o clases `Application`.

## Verificación / Definition of Done
- Comprobación de pureza de la capa `domain`.
- Verificación del flujo unidireccional de datos en ViewModels.
- Ejecución limpia de `./gradlew test`.

## Contrato de entrega del agente
El agente entregará una tabla de evaluación por capa (Domain, Data, Presentation, Core) detallando el cumplimiento de límites arquitectónicos.
