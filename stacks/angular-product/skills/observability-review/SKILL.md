---
name: observability-review
description: Instrumentar errores, correlation IDs y telemetría frontend Angular sin exponer tokens ni PII. Úsala para incidentes, BFF tracing y operaciones.
---

# Observability Review — CALPIL Angular Golden Path

## Objetivo y activación

La correlación debe seguir el trayecto browser→Front Door→BFF; las señales deben ayudar a reproducir el incidente sin datos sensibles.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `src/app/core/http/correlation-id.interceptor.ts`, `src/app/core/observability/telemetry.ts`.
- `src/app/core/error-handling/global-error-handler.ts`, `docs/platform/observability.md`.
- `src/app/features/work-items/application/work-item.service.ts`.

## Procedimiento ejecutable

1. Define evento, severidad, consumidor y contexto mínimo de diagnóstico.
2. Reutiliza `X-Correlation-Id` del interceptor; para un journey con varios requests evalúa propagación/correlación acorde contrato BFF.
3. Instrumenta en `core/observability` concern global; no usar `console.log` con payload completo en features.
4. Registra acción, componente/feature, outcome, duración aproximada si relevante, correlation id y status técnico.
5. Filtra acceso tokens, cookies, headers Authorization, nombres privados, datos contractuales y respuesta BFF completa.
6. Distingue error de validación dominio (esperable) de error HTTP y fallas inesperadas.
7. El GlobalErrorHandler no debe consumir ni silenciar errores; UI entrega feedback relevante al usuario.
8. Verifica que telemetría no bloquee caso de uso ni cause loops sobre fallos de red.
9. Define tags por ambiente/versión de imagen que no contengan información sensible.
10. Testea qué se emite ante 401/403/500, timeout y error no manejado; revisa log redaction.

## Patrón de implementación

```text
Evento sano: {feature:'work-items', action:'change-status', outcome:'http-409', correlationId:'...'}
Evento inseguro: {accessToken:'eyJ...', userEmail:'...', responseBody:{...}}
```

## Decisiones y anti-patrones

- No registrar JWT ni respuestas completas del BFF.
- No convertir observabilidad en dependencia de dominio puro.
- No usar polling o llamadas extra para métricas sin necesidad.
- En clientes SPA, la plataforma recolecta/suma señales de Front Door/BFF; no inventar agente no configurado.

## Verificación / Definition of Done

- Test de sanitización, error handler, correlation header.
- Correlación de un request falla/éxito observada sin JWT.
- `npm run test:security` si cambian filtros HTTP o logging.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
