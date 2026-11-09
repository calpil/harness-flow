---
name: add-auth-authorization
description: Add or modify authentication or authorization for a CALPIL NestJS API/BFF using corporate identity boundaries.
---

# Add Authentication / Authorization

Follow `AGENTS.md`. First identify the trust boundary; do not start by adding guards/decorators blindly.

## Choose the model

- Bearer-token API: backend validates an access token intended for this API.
- Server-side BFF/session: browser talks to the trusted server boundary and backend secrets/tokens remain server-side.

Do not accidentally mix SPA/browser token handling with a BFF session model.

## Authentication

Hexagonal boundary: token/session parsing and framework guards live at `adapter/in` or `platform`. Translate verified identity into a small application-facing principal/value. Domain/application rules must not depend on Nest guards, HTTP request objects or raw Entra token claims.

1. Reuse the established Microsoft Entra ID/platform integration when corporate identity is required.
2. Validate issuer/audience/signature/expiry according to the chosen platform mechanism.
3. Convert verified identity into the minimum principal needed by the application.
4. Keep raw tokens/claims mechanics at inbound/platform boundaries.
5. Never invent tenant IDs, app registrations, client IDs, roles, scopes, groups, secrets or Key Vault names.

## Authorization

Authentication is not permission. Make authorization explicit using the rule required by the use case: scope, app role, group-derived role, resource ownership or domain policy. Keep business/resource authorization close to the protected operation rather than scattering it across controllers.

## Security rules

- No client secret/privileged token in browser/mobile code.
- Do not log tokens, authorization headers or unnecessary claims.
- Fail closed for missing/invalid identity and insufficient authorization.
- Avoid trusting identity or role values supplied by request bodies/headers outside the verified identity mechanism.
- Preserve least privilege; do not broaden permissions just to make integration easier.

## Tests

Prove the authorized success path and applicable missing token, invalid token/identity, missing scope/role and forbidden-resource cases. Unit-test business authorization rules separately from token parsing when those are distinct concerns.

When the change touches inbound adapters, platform auth plumbing, ports, application coordination or module wiring, run `npm run architecture` and treat any violation as blocking.

