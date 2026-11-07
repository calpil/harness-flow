---
name: agent-change-review
description: Revisar cambios generados por Copilot/Claude para detectar alucinaciones de APIs, features acopladas, exceso de cambios o gaps de tests.
---

# Agent Change Review — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `AGENTS.md`
- `docs/ai/SKILL_CATALOG.md`
- `docs/ai/DEFINITION_OF_DONE.md`
- `.azuredevops/scripts/check-architecture.mjs`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

- Referencia detallada: [guía concreta](./references/review-rubric.md).

## Procedimiento ejecutable

1. Comparar diff con pedido original: scope autorizado, files tocados y cambios incidentales.
2. Enumerar contratos externos citados; exigir evidencia de API/export real para Auth, DS, Entra y BFF.
3. Revisar import graph client/server, direction de features, secretos y nuevas dependencias.
4. Examinar estados vacíos, accesibilidad, regionalización, errores, degradación y pruebas regresión.
5. Ejecutar cambios mínimos de corrección; generar evidencia sin declarar pruebas que no corrieron.
6. Emitir hallazgos por severidad con archivo/riesgo/solución y gaps de integración corporativa.

## Patrón de implementación

Use src/features/operations como patrón. Verificar que package.json, lockfile, scripts, docs y pipeline estén sincronizados si cambia tooling.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No aceptar pruebas inventadas por el agente.
- No introducir dependencia o endpoint sin verificar.
- No confiar en usuario autenticado como autorización.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:skills
npm run test:architecture
npm run test:repo-hygiene
npm run validate
```

- Código/contrato probado bajo las capacidades efectivamente disponibles; distinguir comandos ejecutados, fallidos y pendientes.
- Sin nuevas violaciones de import graph, secretos, traducciones o accesibilidad relacionadas al cambio.
- Los cambios de login, BFF, DS privado y entorno AKS precisan validación integrada fuera de tests mock.

## Contrato de entrega del agente

1. Explicar archivos cambiados y responsabilidad de cada capa.
2. Declarar habilidades activadas, alternativas descartadas, contratos y permisos requeridos.
3. Registrar pruebas con comando y resultado real; cualquier requisito no verificado queda explícito.
4. Incluir riesgos/rollback para cambios de SSO, build, deploy o compatibilidad entre features.
