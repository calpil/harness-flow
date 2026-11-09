---
name: authentication-sso
description: Modificar Auth.js/Microsoft Entra ID, roles, callback y sesiones protegiendo secretos y utilizando solamente tokens delegados browser-safe cuando el BFF lo requiera y exista un flujo autorizado.
---

# Authentication Sso — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/auth.ts`
- `src/server/auth/session.ts`
- `src/server/auth/roles.ts`
- `proxy.ts`
- `src/app/(public)/login/`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

- Referencia detallada: [guía concreta](./references/auth-validation-matrix.md).

## Procedimiento ejecutable

1. Confirmar tenant, App Registration, issuer, redirect URI, roles y scopes desde entorno/config real.
2. Mantener Auth.js 5 como propietario del flujo OIDC; usar auth/signIn/signOut centralizados sin reimplementar PKCE.
3. Validar cookie solo como optimización en proxy; revalidar sesión/roles autoritativamente en layouts y endpoints permitidos.
4. En Client Components exponer solo campos y credenciales expresamente browser-safe: secretos, client secrets, refresh tokens y cookies de sesión HttpOnly permanecen server-side. Si `clientDirect=true` requiere bearer, utilizar únicamente un access token delegado con audience/scopes BFF comprobados, mediante flujo aprobado y almacenamiento/uso seguro. No exponer tokens de servidor ni asumir que Auth.js sesión implica token BFF.
5. Separar acceso autenticado y autorización: navegación a login; APIs 401/403; RBAC App Roles por contrato.
6. Cubrir callback seguro, logout, vencimiento, falla Entra, sesiones incompletas y rutas deep link.
7. Para consumo BFF externo negociar OAuth delegation/OBO si se requiere; nunca usar ID token como access token.

## Patrón de implementación

getSession/requireSession/requireRole existen en src/server/auth/session.ts; callback se sirve por src/app/api/auth/[...nextauth]/route.ts y UI login por @calpil-ds/react.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No credenciales en .env.example ni .npmrc versionado.
- No usar roles/email visibles en frontend como única autorización.
- No afirmar OBO implementado sin flujo real validado.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:unit
npm run test:e2e
npm run test:security
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

# Authentication & SSO — CALPIL Next.js

Use this skill whenever adding, changing or reviewing authentication or authorization.

## Identity provider

- Microsoft Entra ID is the corporate identity provider.
- Use OIDC/OAuth 2.0 Authorization Code flow through a maintained server-side auth library.
- Treat Next.js as a server-side web app/BFF for authentication.
- Corporate applications are tenant-specific/single tenant unless an explicit architecture decision states otherwise.
- Never default to `/common`.

## Login UI contract

The public login route is:

```text
/login
```

`/login` MUST use the official login window/component exported by:

```text
@calpil-ds/react
```

The application must discover and use the real exported component API.

Never invent its component name.

Never recreate the login window from lower-level DS primitives, custom CSS, Tailwind or another UI library when the official component exists.

Never copy the component implementation into the application.

The Design System owns:

- visual structure;
- branding;
- typography;
- spacing;
- responsive behavior;
- accessibility;
- login interaction presentation.

The application owns:

- SSO invocation;
- authentication state;
- safe error mapping;
- post-auth redirect.

If the installed DS version does not expose the expected login component, report the package/API mismatch. Do not build a local imitation.

## `/login` behavior

`/login` is public.

Unauthenticated:

```text
/login -> DS login component -> Entra SSO
```

Authenticated:

```text
/login -> redirect to protected landing route
```

Prefer a Server Component page and add the smallest possible Client Component wrapper only if required by the DS component API.

Do not render a local username/password form.

## Server owns authentication

Never store OAuth access/refresh tokens in:

- localStorage;
- sessionStorage;
- React context;
- client state.

Never expose client secrets or raw provider tokens through `NEXT_PUBLIC_*`, Client Components, logs or API responses.

## Next.js guards

Next.js does not use Angular `CanActivate`.

Use defense in depth:

1. `proxy.ts` for early navigation gating;
2. protected server layouts/pages calling `requireSession()`;
3. protected Route Handlers enforcing authentication/authorization.

Unauthenticated browser navigation should go to `/login`.

Proxy is not the final authorization boundary.

## Auth facade

Keep server authentication behind a local facade such as:

```text
src/server/auth/session.ts
```

Provide typed helpers such as:

```text
getSession
requireSession
hasRole
requireRole
requireAnyRole
```

Do not scatter provider-library details unnecessarily.

## Authorization

Use Microsoft Entra App Roles for RBAC where application roles are required.

Do not authorize by email/display name.

Expected semantics:

- unauthenticated browser route -> `/login`
- unauthenticated protected API -> 401
- authenticated but unauthorized -> 403
- authorized -> continue

## Public routes

At minimum keep these public:

```text
/login
/api/auth/*
/api/health/liveness
/api/health/readiness
```

Do not break AKS probes.

## Client/server boundary

Client Components must not import:

```text
src/server/auth/*
src/auth.ts
server-only token/provider logic
```

They may receive safe display identity and derived UI flags.

Server-side checks remain authoritative.

## App Registration

For the Next.js BFF:

- Platform: Web
- Tenant: single tenant
- Use server callback URI
- Do not enable implicit grant
- Keep credentials outside Git
- Use App Roles when RBAC is required

Typical callback:

```text
/api/auth/callback/microsoft-entra-id
```

Confirm it against the actual installed provider.

## Testing

Vitest:

- role helpers
- session facade
- 401/403
- login redirect behavior
- integration contract with DS login component

Do not test internal DS DOM implementation.

Playwright:

- `/login`
- protected-route redirect
- protected portal with test session
- unauthorized admin
- health probes

Never automate real employee Microsoft credentials in CI.

Any test-auth bypass must be explicit, test-only and impossible to enable accidentally in production.

## Review rejection criteria

Reject changes that:

- recreate the CALPIL login window locally;
- use a generic login form instead of the official DS component;
- implement a client-only auth guard;
- rely only on `proxy.ts`;
- expose tokens to React/browser storage;
- use email as authorization;
- hardcode identities;
- protect health probes;
- use `/common` for a corporate single-tenant app without explicit approval;
- return login redirects instead of 401/403 from business APIs;
- duplicate provider configuration;
- weaken security/architecture tests to make the build pass.
