# Security Review — API, BFF Integration, Tenant and Runtime — Playbook técnico de ejecución


## Modelo de amenazas por request

```text
Client → Front Door/WAF → Gateway API → BFF (si existe) → Spring API
         network edge         authorization boundary     DB/partner API
```

WAF, validación de token en BFF y políticas de infraestructura corporativas **no sustituyen** la autorización de negocio dentro de la API. Documentar qué controles están existentes/implementados/evidenciados para *este* servicio, no recomendar construir un sistema que CALPIL ya posee.

## JWT / Entra ID y tenancy

1. Comprobar firma JWK válida, allowed algorithms, clock skew acotado, `iss`, `aud`, `exp`, `nbf` y tenant permitido, considerando token version real.
2. `scp` (delegated) vs `roles` (application) se interpretan según claim efectivo; no autorizarlos indistintamente.
3. Separar usuario humano (delegated) de identidad técnica app-only y API key por tenant.
4. Resolver `tenant` autorizado desde claims/lookup de identidad, no solo del `tenantId` en URL/body.
5. Resolver resource ownership desde repositorio scoped por tenant; no `findById` global seguido de chequeo tardío si filtra información.
6. Verificar revocación/rotación/expiración de API keys, no registrarlas en claro y no pasarlas como query string.
7. `permitAll` del `SecurityConfig` actual es demostrativo; para producción exigir auth real + pruebas negativas.

## Matriz endpoint→permiso

| Endpoint | Quién | Modo auth | Action | Scope/role | Tenant/resource check | Test negativo |
|---|---|---|---|---|---|---|
| GET /api/v1/assets/{id} | viewer | bearer JWT | read | assets.read | misma organización | 403/404 cross-tenant |
| POST /api/v1/assets | manager | bearer JWT | write | assets.write | tenant derivado identidad | 403 sin permiso |
| API partner | system | secret/API key | integration | tenant-bound | clave segregada | 401 clave expirada |

Tabla demostrativa, NO endpoints reales de este template. Asignar status 403 vs 404 conforme política de no enumeración y probarlo de forma explícita.

## Control de datos, API y runtime

- Validar tamaño y contenido de input, JSON depth, URLs en integraciones para evitar SSRF; no construir SQL concatenando filtros.
- Deserialización y serialización no deben filtrar secretos, stack traces, tokens ni claims personales.
- CORS se define por orígenes concretos; CSRF según uso de cookie/sesión vs stateless bearer.
- Rate limits y quotas por identidad/tenant/consumer en gateway y, si aplica, enforcement local.
- Actuator, `/v3/api-docs`, metrics y config endpoints bajo política del ambiente, no expuestos indiscriminadamente.
- Headers forwarded se confían únicamente de proxy conocido; evitar spoof de IP/origen.
- Para logs y traces usar correlation ID sin claims completos ni identificadores sensibles sin necesidad.

## Pruebas de denegación que realmente cuentan

```text
A: sin bearer token        → 401
B: JWT firma inválida      → 401
C: JWT aud/iss erróneos    → 401
D: token válido sin scope  → 403
E: tenant A pide recurso B → 403 o 404 (política)
F: API key revocada        → 401
G: replay/idempotencia     → sin segundo efecto
```

No escribir tests de seguridad mientras la chain demo permite todo y luego reportarlos PASS: habilitar configuración de pruebas que valida políticas reales. Distinguir integración funcional de verificación de autorización.

## Hallazgo formal

```text
ID: SEC-001 | Severidad: BLOCKER/HIGH/MEDIUM/LOW
Superficie: recurso/endpoint/clase
Evidencia: código/config/test/contrato observado
Exploit/fallo: secuencia reproducible y alcance
Mitigación mínima: cambio con dueño claro
Prueba de no regresión: escenario negativo con resultado esperado
Estado: abierto/corregido/verificado/no verificable
```

## Gate final

- [ ] invalid/missing token is rejected
- [ ] valid token lacking resource role/scope rejected
- [ ] cross-tenant IDs cannot read/update entities
- [ ] key rotation/revocation audited when used
- [ ] error logs redacted and actuator protected
- [ ] no demo permitAll asserted as secure
