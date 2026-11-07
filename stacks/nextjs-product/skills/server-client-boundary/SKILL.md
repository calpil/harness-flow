---
name: server-client-boundary
description: Proteger los límites Server/Client de Next.js App Router, datos privados y composición de dependencias transitivas.
---

# Server Client Boundary — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/app/`
- `src/server/`
- `src/features/operations/ui/`
- `proxy.ts`
- `next.config.mjs`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Comprobar directiva use client solo en nodos que usan hooks/events/DOM.
2. Rastrear imports transitivos de todo client component incluyendo barrel exports y aliases.
3. Separar DTO/view model serializable sin handlers, secrets, node:* ni acceso al servidor.
4. Mover integración privada a server boundary y pasar props seguras explícitamente.
5. Verificar hydration con locales/fechas/estado, y evitar clocks aleatorios renderizados distinto servidor/client.
6. Cubrir boundary con npm run test:architecture y una prueba de build real cuando Node/registry estén disponibles.

## Patrón de implementación

Un componente client puede importar domain puro, application puro, demo de navegador y un **adaptador de infraestructura expresamente browser-safe** que delegue en `bff-client.ts`. Nunca puede importar `server-only`, `src/server/**`, secretos, ni adaptadores que tengan dependencias transitivas de servidor. Para llamadas BFF, el browser transport central decide entre BFF público (`clientDirect=true`) y proxy Next.js (`clientDirect=false`); las llamadas iniciadas en servidor usan server transport central. No crear un cliente HTTP BFF por feature.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No marcar una ruta completa use client para evitar error.
- No importar env server o Auth.js directamente en client.
- No esconder server dependencies detrás de barrel export.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:architecture
npm run typecheck
npm run build
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

# Server / Client Boundary

Use this skill whenever a change touches `'use client'`, Route Handlers, Server Components, composition roots, `server-only`, Node built-ins, auth/config/secrets, or browser/server data access.

## Core rule

A Client Component must never directly or transitively reach server-only code.

Forbidden from a `'use client'` import graph:

- `server-only`
- `node:*`
- `src/server/**`
- feature server composition roots
- `src/features/*/infrastructure/**` when that infrastructure is server-side
- secret-bearing/server configuration

Do not “fix” a boundary by swapping a Node API for a browser API while leaving Client -> server infrastructure coupling intact.

## Preferred Next.js boundary

This repository is a frontend. Do not introduce a BFF or backend Route Handler for product data.

For browser reads and mutations of the demo:

```text
Client UI -> src/features/<feature>/demo session
```

Server Components may render UI and read session/locale. They must not call a localhost business API.

Do not import `src/features/*/infrastructure`, `server-only`, or `node:*` from a Client Component.

## Composition roots

Server composition roots should explicitly import `server-only` when they wire server adapters, Node APIs, credentials, filesystem/network clients or server state.

Keep construction/wiring out of Client Components.

## Client surface

Minimize `'use client'` boundaries. Split a Server Component wrapper from a small Client Component when only locale preference, interaction, hooks or browser APIs require client execution.

Do not add `'use client'` broadly to silence framework errors.

## Configuration

Only expose intentionally public `NEXT_PUBLIC_*` values to the browser. Never import server configuration into a client graph.

## Validation

Run `npm run test:architecture`, then typecheck/tests/build relevant to the change.
A successful build is not proof of a correct boundary; architecture validation must also pass.

## Verificación de clientDirect

Verificar con tests que `clientDirect` solo se resuelva en la infraestructura/configuración central de BFF. Módulos importados desde `use client` no pueden depender transitivamente de `server-only`, Auth.js confidencial ni `node:*`. No transformar una carga de Server Component en client fetch sin necesidad y no duplicar peticiones entre SSR e hidratación.
