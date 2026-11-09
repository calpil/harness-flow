---
name: security-review
description: Auditar amenazas Angular SPA: autenticación, bearer, XSS, PII, configuración, CSP y dependencias. Úsala antes de releases y cambios en auth/HTTP/rendering.
---

# Security Review — CALPIL Angular Golden Path

## Objetivo y activación

Buscar amenazas concretas y validar mitigaciones sin mover responsabilidad de autorización backend al navegador.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `SECURITY.md`, `docs/security/sso-integration.md`, `src/app/core/auth/*`.
- `nginx.conf`, `Dockerfile`, `.dockerignore`, `scripts/check-security-config.mjs`.
- `src/app/core/config/runtime-config.ts`, `.npmrc` y `pipelines/deploy.yml`.

## Procedimiento ejecutable

1. Determina datos sensibles y trust boundaries: browser, Front Door, BFF, Entra, feed privado, plataforma.
2. Revisa flows de acceso: returnUrl relativo, PKCE, scopes API, cache MSAL, guard UX y autorización servidor.
3. Busca filtración de `Authorization`: URL exacta allowlist, mismo origen, fetch manual, redirects, console/telemetry.
4. Valida que config frontend no contenga secretos ni acepte hosts arbitrarios; inspecciona archivos rastreados y dist.
5. Revisa interpolaciones, `innerHTML`, sanitización Angular, uploads/downloads y HTML externo.
6. Analiza CSP, security headers, cache de runtime-config, frames, scripts y policy frente a login remoto.
7. Prueba 401/403 y privilegios: UI oculta acciones cuando corresponde pero backend verifica siempre.
8. Comprueba separación `.npmrc` y credenciales de Artifacts; Docker BuildKit secret nunca en capas/logs.
9. Revisa deps/directas/transitivas por advisory y licencia, sin ejecutar upgrades ciegos.
10. Produce informe P0/P1/P2 con exploit path, evidencia, mitigación, test y responsable.
11. No marcar “seguro” un token/API con pruebas solo de navegador si no existe validación backend.

## Patrón de implementación

| Amenaza                         | Control cliente       | Control obligatorio servidor |
| ------------------------------- | --------------------- | ---------------------------- |
| Usuario sin sesión              | Guard, login          | JWT válido                   |
| Scope ajeno                     | MSAL scopes correctos | `aud`, `iss`, `scp`/roles    |
| Acceso a datos de otra división | UX filtrada           | autorización recurso/tenant  |
| Token exfiltrado                | allowlist exacta      | TLS/WAF + validación JWT     |

## Decisiones y anti-patrones

- Nunca incluir access token/JWT completo en reporte o captures.
- Nunca deshabilitar issuer/signature/audience para solventar login.
- Nunca usar secrets de app registration SPA.
- Nunca permitir `*` para bearer forwarding por facilidad.
- No exponer datos productivos en fixtures/demo.

## Verificación / Definition of Done

- `npm run test:security`, `npm run test:architecture`, pruebas SSO + HTTP.
- Inspección de assets build, Dockerfile y variables antes de release.
- Para bugs severos: regression test y verificación negativa (token NO llega a destino no confiable).

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
