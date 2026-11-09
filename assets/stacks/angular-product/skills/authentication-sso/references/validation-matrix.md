# Diagnóstico integral Microsoft Entra → Angular → BFF

## Flujo de confianza

`Angular bootstrap(runtime-config)` → `MSAL.initialize()` → `handleRedirectPromise()` → `loginRedirect(openid/profile)` → `account activa` → `acquireTokenSilent(scopes API)` → `interceptor allowlist` → `Front Door/BFF` → `validación JWT aud/iss/signature/exp/scopes` → `autorización recurso`.

**Identidad (OIDC) ≠ autorización para API**. El `id_token` identifica la sesión SPA; el `access_token` concedido al resource correcto va al BFF.

## Matriz de diagnóstico (sin registrar tokens completos)

| Síntoma                  | Comprobar en frontend                                        | Comprobar en API/Entra                 | Corrección segura                            |
| ------------------------ | ------------------------------------------------------------ | -------------------------------------- | -------------------------------------------- |
| Redirige a login en loop | redirect URI, origin, `handleRedirectPromise`, cuenta activa | registro SPA exacto y políticas        | corregir configuración de registro/estado    |
| `interaction_required`   | scopes del resource, ventana interactiva                     | permisos y consent                     | acción explícita `authorizeApiAccess()`      |
| 401 BFF después de login | token enviado, ruta allowlisted                              | `aud`, `iss`, `ver`, firma, expiración | alinear API registration / backend validator |
| 403 BFF                  | sesión válida + recurso                                      | roles/scopes/tenant/división           | permisos server-side, no el guard            |
| `invalid_signature`      | resource del token, key metadata                             | `kid`, JWKS del issuer adecuado, ver   | corregir autoridad/JWKS; jamás omitir firma  |
| token en host externo    | coincidencia URL exacta                                      | redirecciones/gateway                  | bloquear allowlist y test negativo           |
| Logout deja sesión       | cuentas MSAL + storage local de e2e                          | post logout redirect                   | sesión activa revocada y navegación          |

## Pruebas mínimas que deben existir

- Guard sin sesión navega a login con return relativo saneado.
- Inicializador maneja redirect antes de renderizar rutas protegidas.
- Scopes faltantes se reportan y no envía bearer.
- API permitida recibe bearer; URL de tercero, otro puerto o prefijo ambiguo no lo recibe.
- 401 y 403 tienen respuestas UX distintas.
- Login E2E fake es explícitamente local/no-prod.

## Ensayo corporativo obligatorio (fuera de test local)

1. Identificar tenant/client id/redirect registrados; no copiar valores de otro proyecto.
2. Scope expuesto por app registration de **resource API**, consent delegado.
3. Login real y adquisición de access token; inspeccionar únicamente metadata sanitizada (claims públicos autorizados, nunca token completo).
4. Probar ruta BFF con permiso/denegación y `X-Correlation-Id`.
5. Probar expiración y renovación silenciosa, login de nueva sesión y logout.
6. Documentar issuer/audience/token version según resource y política servidor.

## Falta de acceso

Si no hay cuenta Entra, BFF o feed: ejecutar unit/security checks, dejar ensayos externos como **pendientes**, no fabricar evidencia.
