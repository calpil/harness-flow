---
name: security-review
description: Revisar amenazas frontend/server Next.js, SSO, CSP, secretos, SSRF, permisos y supply chain.
---

# Security Review — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `proxy.ts`
- `src/server/auth/session.ts`
- `src/auth.ts`
- `.dockerignore`
- `Dockerfile`
- `SECURITY.md`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Mapear superficie cambiada: navegación, Route Handler, servidor, dependencia, variables o container.
2. Comprobar validación de identidad server-side, RBAC real y fallos 401/403 correctos.
3. Revisar tokens OAuth: access token correcto para API, nunca ID token ni sesión completa en client.
4. Revisar CSP, callbackUrl, redirects, URL externas/SSRF, contenido HTML y headers sin filtrar nonce.
5. Buscar secret/cert/PAT en repositorio, lockfiles y Docker context; impedir empaquetado .npmrc.
6. Añadir pruebas negativas y enumerar riesgos que requieren infraestructura/Entra reales.

## Patrón de implementación

proxy.ts genera CSP nonce; src/server/auth/session.ts hace enforcement; .dockerignore excluye .npmrc. Autenticación Azure Artifacts solo local/BuildKit.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No tratar proxy o client UI como frontera de seguridad final.
- No hardcodear credenciales.
- No afirmar auditoría completa con solo regex.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:security
npm run test:repo-hygiene
npm run test:architecture
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

# Security Review

Focus on the requested boundary and preserve least privilege.
Never expose server secrets to client bundles or logs.

## Route/BFF security

- validate untrusted request input at the boundary;
- prefer existing `zod` schemas/dependency rather than ad-hoc duplicated validation;
- return safe client errors without stack traces/internal exception data;
- do not log credentials, tokens or sensitive payloads.

## CSP for Next.js 16

For strict script CSP in App Router, prefer a fresh per-request nonce generated in `proxy.ts` and propagated through the request/response CSP header.

Production scripts:

```text
script-src 'self' 'nonce-<request nonce>' 'strict-dynamic'
```

Do not use `'unsafe-inline'` or `'unsafe-eval'` for production scripts.
Development may use `'unsafe-eval'` only where Next.js/React tooling requires it.

Nonce-based CSP implies request-time rendering for affected HTML routes; report that tradeoff.

Do not assume style nonces solve React inline `style={{...}}` attributes. If the application/Design System currently uses inline style attributes, keep a compatible `style-src` policy until a dedicated style migration is performed.

Avoid duplicate/conflicting CSP headers between `proxy.ts` and `next.config.mjs`.

## Server/client

Use the `server-client-boundary` skill whenever security code/config is imported by UI or when `'use client'` is involved.

Load `docs/ai/SECURITY_RULES.md` when deeper repository policy is needed.
