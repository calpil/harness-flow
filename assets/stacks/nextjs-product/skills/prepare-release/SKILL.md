---
name: prepare-release
description: Preparar release de Next.js con quality gates, semver, changelog, artefacto sin secretos y smoke tests.
---

# Prepare Release — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `docs/maintenance/releases.md`
- `CHANGELOG.md`
- `package.json`
- `TEMPLATE_VERSION`
- `azure-pipelines.yml`
- `Dockerfile`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Confirmar alcance release, versión, notas, compatibilidad y breaking changes.
2. Verificar coherencia package.json y TEMPLATE_VERSION según esquema actual del repositorio.
3. Ejecutar lint, typecheck, tests, architecture, skills/hygiene, build y E2E críticos cuando entorno disponible.
4. Validar imagen standalone, probes, permisos de ejecución, secrets y configuración de entornos.
5. Revisar no generación de .npmrc/.env en paquetes, archivos .git y logs sensibles.
6. Entregar release notes y matriz ejecutado/no ejecutado con blockers de feed/Entra/BFF.

## Patrón de implementación

Artefactos OCI por pipeline corporativo; templates ZIP para repositorio deben excluir .git, .npmrc, .env y carpetas de build.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No etiquetar si checks fallaron sin excepción aprobada.
- No cambiar dependencias como limpieza incidental.
- No afirmar deploy producción sin release real.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:skills
npm run test:repo-hygiene
npm run validate
npm run build
```

- Código/contrato probado bajo las capacidades efectivamente disponibles; distinguir comandos ejecutados, fallidos y pendientes.
- Sin nuevas violaciones de import graph, secretos, traducciones o accesibilidad relacionadas al cambio.
- Los cambios de login, BFF, DS privado y entorno AKS precisan validación integrada fuera de tests mock.

## Contrato de entrega del agente

1. Explicar archivos cambiados y responsabilidad de cada capa.
2. Declarar habilidades activadas, alternativas descartadas, contratos y permisos requeridos.
3. Registrar pruebas con comando y resultado real; cualquier requisito no verificado queda explícito.
4. Incluir riesgos/rollback para cambios de SSO, build, deploy o compatibilidad entre features.
