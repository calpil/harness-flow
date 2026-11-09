---
name: authentication-sso
description: Diagnosticar, configurar o modificar SSO Microsoft Entra MSAL Angular SPA, tokens para BFF y guardias. Usar para login, consent, token, 401/403, logout, redirect y scopes.
---

# Authentication Sso — CALPIL Angular Golden Path

## Objetivo y activación

Separar identidad, adquisición de credencial delegada, envío de bearer y autorización backend. Un login exitoso NO demuestra que el token sirve para la API.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `docs/security/sso-integration.md` y [matriz de diagnóstico](./references/validation-matrix.md).
- `src/app/core/auth/entra-auth.session.ts`, `entra-auth.guard.ts`, `entra-api.interceptor.ts`.
- `src/app/app.config.ts` (interceptors) y `src/app/core/config/runtime-config.ts` (config pública).
- `src/app/core/auth/*.spec.ts`, `tests/e2e/local-session.ts`.
- Confirmar App Registration, scopes expuestos y contrato backend con el dueño de Entra/BFF.

## Procedimiento ejecutable

1. Identifica el síntoma exacto: navegación, login, consent, `interaction_required`, falta de token, `invalid_signature`, audiencia errónea, 401 o 403.
2. Traza flujo completo: `runtime-config` → MSAL initialize + handleRedirect → loginRedirect → cuenta activa → acquireTokenSilent(scope API) → interceptor allowlist → BFF → JWT validation → RBAC recurso.
3. Comprueba SPA client ID, tenant-specific authority, redirect URI exacto, origen y políticas de navegador. Para client-side usa auth code + PKCE; nunca secret.
4. Distingue `openid`/`profile` (identidad) de scopes delegados `api://<resource>/...` (API). Nunca uses `User.Read` como bearer del BFF propio, ni id_token.
5. Al cambiar scopes valida que la API exponga esa delegación y consentimiento concedido; no inventar resource ni audience.
6. Maneja `acquireTokenSilent()` como primera opción; cuando requiera interacción, informa y usa `authorizeApiAccess()` bajo evento explícito de usuario.
7. Asegura que interceptor inyecte bearer solo a URL exacta/subrutas autorizadas **del mismo origen**, nunca por coincidencia de host o substring.
8. Para 401/403 recopila diagnóstico sin almacenar JWT: status, método, ruta sanitizada, correlation id, configuración de issuer/audience en backend.
9. No cambiar backend JWT validation por ensayo y error; mapear `iss`, `aud`, `ver`, `scp`/`roles` a la política de ese resource.
10. Protege returnUrl relativo, logout y rehidratación de cuenta; trata guard cliente solo como UX.
11. Prueba sin login, post-login, refresh, acceso API, scopes faltantes, consent, permisos insuficientes, logout, reload y varios tabs según uso.
12. Separa claramente mock E2E local de validación SSO real corporativa.

## Patrón de implementación

```ts
// Usar patrón existente; los scopes proceden de runtime config y del resource BFF.
const result = await msal.acquireTokenSilent({ account, scopes: [...config.entraApiScopes] });
// Enviar result.accessToken exclusivamente a URLs validadas por isProtectedApiRequest.
```

Nunca generar un bearer a partir del `idToken` de `loginRedirect()`.

## Decisiones y anti-patrones

- Prohibido `client_secret`, PAT, token en console, query string, localStorage propio o logs.
- Nunca desactivar verificación de firma, issuer o audience para resolver un 401.
- `User.Read` Graph e `id_token` no sustituyen scopes de la API propia.
- Nunca aplicar Authorization a un `HttpClient` genérico sin allowlist; la app usa interceptor `isProtectedApiRequest`.
- No declarar acceso concedido por un guard Angular; el BFF valida permisos y segregación de tenant.

## Verificación / Definition of Done

- Unit `entra-auth.session.spec.ts`, `entra-api.interceptor.spec.ts`, `entra-auth.guard.spec.ts`.
- `npm run test:security`, `npm run test:architecture`, `npm run typecheck`.
- Entra real requiere ensayo externo con app registration/tenant/BFF y evidencia sanitizada de `aud`, `iss`, `scp`, estado HTTP.
- Comunicar explícitamente si solo se probó bypass Playwright local.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
