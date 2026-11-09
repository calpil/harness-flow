# API Contract / HTTP Adapter — Playbook técnico de ejecución


## Ficha de contrato obligatoria

```text
Consumer: BFF/operación/integrador | Exposure: public/private | API version: v1
METHOD /api/v1/<plural-resource>   Auth: audience + scopes/role + resource ownership
Request: body/path/query schema, limits, nullability, filter/order/page
Success: 200/201/204 + headers, location, example JSON
Failure: 400/401/403/404/409/422/429/5xx (solo los aplicables)
Idempotency: by HTTP method / explicit key | Deprecation plan: if breaking
```

El frontend/BFF consume contrato propio estable; APIs externas no se filtran en DTO de producto. Si Helm u otro tercero usa un shape diferente, escribir ACL outbound que traduzca sus errores, payloads y autenticación.

## Separación capa web

```java
// Ejemplo conceptual: package adapter.in.web, NO copiar tal cual.
@PostMapping
@ResponseStatus(HttpStatus.CREATED)
public AssetResponse create(@Valid @RequestBody CreateAssetRequest request) {
  Asset asset = createAssetUseCase.create(new CreateAssetCommand(request.name()));
  return AssetResponse.from(asset);
}
```

Para `201 Created` incluir `Location` cuando el recurso sea direccionable; si la API actual ya retorna `ResponseEntity.created(...)`, seguir patrón contractual coherente. El `CreateAssetCommand` vive en application y no referencia request web.

## Respuestas de error

| Condición | Status sugerido | Consideración |
|---|---|---|
| JSON inválido / Bean Validation | 400 | campo, error code seguro, no payload sensible |
| Falta token / invalid signature | 401 | no filtrar detalles de token |
| Token correcto sin permiso | 403 | ocultar existencia solo si política lo requiere |
| Recurso no existe | 404 | evitar enumeración cross-tenant |
| Conflicto state/unique/etag | 409 | concurrent updates |
| Regla semántica de entrada | 422 si contrato lo adopta | distinguir 400 vs 422 |
| Rate limit | 429 | Retry-After cuando esté definido |
| Error inesperado | 500 | correlation ID, sin stack trace |

El `GlobalExceptionHandler` actual es la fuente de traducción; revisar su mapping antes de agregar otro. Para paginación, poner máximo acotado y estable; no permitir `limit` arbitrario ni sort por columna SQL libre.

## Casos negativos requeridos

1. Path ID inválido, no encontrado y ajeno al tenant.
2. Request con tipo incorrecto, campo requerido faltante, min/max y XSS/SQL injection como dato inertizado.
3. 401 sin bearer y token firmado para `aud`/`iss` incorrectos.
4. 403 con scope/rol insuficiente y acceso cruzado por ID.
5. Paginación 0, max, > max; sorting determinista.
6. Borrado o transición repetida (idempotencia o conflicto definido).
7. JSON serializer: fechas UTC y enum unknown/forward compatibility.

## Gate de OpenAPI y versión

Spring Boot 4 de este template no debe combinarse ciegamente con springdoc 2.8.6. Consultar release compatible en upstream y ejecutar app/context test que inicializa documentación. Validar `/v3/api-docs` solo en ambientes autorizados y con controles reales; no publicar Swagger público por defecto.

## Gate final

- [ ] HTTP route/verb/media type/version stable
- [ ] DTO validation maps to bounded error body
- [ ] 201/Location and 204 semantics where applicable
- [ ] 401/403/404/409 status proven with security enabled
- [ ] pagination order and max enforced
- [ ] schema OpenAPI reflects actual response and Springdoc works
