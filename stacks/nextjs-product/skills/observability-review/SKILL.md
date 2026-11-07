---
name: observability-review
description: Agregar diagnósticos seguros y correlación en Next.js server-side sin PII/tokens y con errores accionables.
---

# Observability Review — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/shared/observability/`
- `src/instrumentation.ts`
- `src/app/api/health/`
- `src/server/auth/`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Definir evento, severidad, request/trace id, ambiente y métrica antes de loggear.
2. Usar servicios de servidor para trazas; no loggear JWT, cookies, secretos o cuerpo sensible.
3. Separar fallo negocio de dependencia y timeout; propagar correlation id BFF si contrato lo soporta.
4. Mantener health liveness/readiness independientes de SSO para AKS; probar estados esperados.
5. Revisar ruido, cardinalidad de labels y stack traces en producción.
6. Agregar tests de sanitización y errores sin depender de proveedor de telemetría real.

## Patrón de implementación

Instrumentation existente src/instrumentation.ts y src/shared/observability; probes src/app/api/health.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No console.log(user tokens).
- No retornar trace de producción al navegador.
- No usar readiness como comprobación de permisos.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:unit
npm run test:security
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

## Guía adicional existente (preservada)

# Observability Review

Use for server-side flows, route handlers, integrations and production error handling.

## Logging

Use existing structured logging conventions.

Do not:

- rely on scattered `console.log`;
- log secrets;
- log sensitive payloads unnecessarily;
- swallow failures.

## Correlation

Preserve existing request/correlation context when available.

## Errors

- use existing error/Problem Details conventions;
- keep user-facing messages safe;
- preserve useful diagnostic detail server-side;
- distinguish expected domain failures from unexpected failures.

## Metrics/tracing

Reuse existing observability mechanisms when the change creates a meaningful new operational path.

Do not invent a parallel observability stack.

## Tests

Add tests for meaningful error paths when behavior changes.

Report any production-diagnostic gap introduced by the change.
