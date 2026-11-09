# Ficha obligatoria de integración BFF (consumidor Angular)

Completar desde OpenAPI o especificación backend aprobada, no inventar valores.

## Identidad del contrato

- API owner / contacto / versión / link OpenAPI / lifecycle.
- Host Front Door same-origin, resource base URL completo `/bff/v1/{api}/resource`.
- Identidad del resource Entra: audience esperado, delegación scope API, tenant y políticas BFF.
- Operaciones: método, path, query/pagination, request schema, response schema, content type.
- Semántica de campos: `null`, vacío, requerido, enum, decimal, ISO dates, country code, versión/concurrencia.
- Error contract: 400/401/403/404/409/422/429/500 y códigos internos sin PII.
- Retry/backoff, timeout, cache y idempotencia por operación.
- Correlation / tracing header y rate limit (si corresponde).

## Evaluación de propiedad por capa

1. `application/` define el puerto que el caso de uso necesita.
2. `data-access/` contiene DTO y parsing/mapping.
3. `core/auth/entra-api.interceptor` decide si bearer aplica a ese endpoint.
4. `core/http/correlation-id.interceptor` inserta header; BFF lo propaga.
5. `runtime-config` provee URL pública por ambiente antes de bootstrap.
6. `ui` nunca ve HttpResponse ni headers.

## Ejemplos de preguntas al owner BFF

- ¿Cuál es el path base exacto y el sentido de cada endpoint?
- ¿El GET paginado devuelve `{items,total}` u otro envelope?
- ¿El POST retorna 201 con recurso completo o solo id?
- ¿Cómo se expresan errores de negocio y conflicto de versión?
- ¿La validación de tenant viene por claim, header confiable u ownership del recurso?
- ¿Qué scopes delegados y qué app registration audience valida el resource?
- ¿Se exponen rutas same-origin a través de Front Door o existe excepción revisada?

## Contrato mínimo de pruebas consumidor

- [ ] URL, query, método, headers, body.
- [ ] Mapping de DTO nominal + null/unknown fields.
- [ ] No bearer a origen/ruta externa; sí para ruta configurada.
- [ ] Respuestas de éxito y error 401/403/404/409/5xx.
- [ ] Timeout, paginación, retries seguros.
- [ ] Smoke real backend con datos ficticios y permisos negativos.
