---
name: error-handling
description: Diseñar manejo de errores por capas Angular, traducción HTTP→dominio y experiencia de recuperación. Úsala para 401/403/404/409, timeout y fallos globales.
---

# Error Handling — CALPIL Angular Golden Path

## Objetivo y activación

Dar mensajes accionables sin filtrar detalles backend y conservar trazabilidad técnica separada de UI.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `src/app/core/error-handling/global-error-handler.ts`.
- `src/app/features/work-items/application/work-item.service.ts` y `domain/errors.ts`.
- `src/app/core/observability/telemetry.ts`.
- `src/app/core/auth/entra-api.interceptor.ts`.

## Procedimiento ejecutable

1. Clasifica error: validación/invariante, API (4xx/5xx), sesión (401), autorización (403), recurso (404), versión (409), red/timeout o bug.
2. Ubica ownership: dominio emite error de regla; adapter traduce transporte; application decide recuperación; UI presenta mensaje; core captura inesperado.
3. No convertir todo a mensaje genérico; distingue acción posible: corregir campo, reintentar, solicitar acceso, refrescar o volver.
4. Conserva correlation id y status técnico en telemetría sanitizada; UI no muestra stacktraces ni JWT.
5. No reintentar POST/PATCH automáticamente sin idempotencia contractual.
6. Maneja 401 con sesión/token sin redirecciones en loop; 403 no se corrige automáticamente obteniendo más scopes.
7. Distingue 404 legítimo de error de infraestructura y presenta ruta de retorno.
8. Para 409 ofrece recargar/merge según negocio; no sobrescribir cambio ajeno.
9. Prueba estados UI con error, foco/aria, loading desactivado y conservación de datos del formulario.
10. Propaga fallos inesperados al error handler/observabilidad sin tragarlos silenciosamente.

## Patrón de implementación

| Caso        | Resultado UX esperado              |
| ----------- | ---------------------------------- |
| 422         | error de campo/validación          |
| 401         | sesión o token a resolver          |
| 403         | acceso denegado; sin filtrar datos |
| 404         | inexistente con navegación segura  |
| 409         | conflicto con refresh              |
| 5xx/timeout | feedback + retry seguro            |

## Decisiones y anti-patrones

- No inyectar HttpClient al dominio.
- No ocultar 403 como lista vacía.
- No interpolar cuerpos completos de error remoto en template o logs.
- No marcar éxito en UI en un error de red.

## Verificación / Definition of Done

- Test por status crítico con adapter fake/HttpTestingController y componente.
- Verificar correlation, ausencia de tokens en logs y experiencia recuperable.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
