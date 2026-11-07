---
name: feature-flag-rollout
description: Implementar o modificar feature flags corporativos, fallbacks locales y rollout seguro. Úsala para activaciones, desactivaciones y experimentos de producto.
---

# Feature Flag Rollout — CALPIL Angular Golden Path

## Objetivo y activación

Flags controlan exposición visual, no autorización; la política del servidor es siempre fuente de permisos.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `docs/platform/feature-flags.md`, `config/feature-flags.fallback.json`.
- `src/app/core/feature-flags/{feature-flags.ts,evaluate-feature-flag.ts}`.
- `src/app/shared/feature-flags/catalog.ts`, `src/app/core/feature-flags/feature-flags.spec.ts`.
- `src/app/core/config/runtime-config.ts`.

## Procedimiento ejecutable

1. Define key, propietario, caducidad, default seguro, ambientes y rollback del flag.
2. Evalúa si se trata de toggle de producto, permiso de negocio o release; **solo primer caso** pertenece a feature flag frontend.
3. Agrega key tipada al catálogo/fallback aprobado; evita flags dinámicos sin inventario.
4. Si está conectado a BFF, respeta `featureFlagsBffBaseUrl` y auth delegada existente; validar respuesta/fallo.
5. Ante indisponibilidad del BFF, define fallback explícito y seguro; no abrir capacidad sensible por defecto.
6. Consumer de feature evalúa flag al momento adecuado, no en dominio o adapter; actualización si cambia sesión/entorno.
7. No almacenar decisiones sensibles como autorización ni asumir que UI oculta un endpoint.
8. Planifica eliminación del flag una vez rollout estable; no acumular deuda infinita.
9. Prueba habilitado/deshabilitado, fallo remoto, fallback, permisos backend y cleanup.
10. Documenta política, TTL y rollback al activar en prod.

## Patrón de implementación

```text
Flag OFF → UI no expone funcionalidad; backend igualmente valida autorización.
BFF flags caído → fallback seguro/documentado; no excepción silenciosa.
```

## Decisiones y anti-patrones

- No esconder autorización real detrás de flag.
- No usar flag local para evitar contrato BFF en nonprod/prod.
- No concatenar bearer manual a orígenes desconocidos.
- No inventar capacidades de targeting no definidas por la plataforma.

## Verificación / Definition of Done

- Specs de feature-flags y pruebas de consumidor; `npm run test:security` si cambió URL/token.
- Validar default y fallo remoto en cada ambiente afectado.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
