---
name: architecture-review
description: Auditar dependencias entre features, capas y App Router, además de contaminación server/client y ownership API.
---

# Architecture Review — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `docs/architecture/overview.md`
- `.azuredevops/scripts/check-architecture.mjs`
- `docs/ai/ARCHITECTURE_RULES.md`
- `src/features/operations/`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Dibujar grafo de imports del cambio: feature A→B, domain→application, application→infrastructure, ui→server.
2. Comprobar domain puro y application con puertos; infrastructure adapta, ui compone sin importar adapter server.
3. Inspeccionar Server vs Client Components de manera transitiva; node:* y src/server no pueden llegar a bundle client.
4. Confirmar que App Router alberga presentación y endpoints técnicos, nunca BFF de negocio.
5. Revisar rutas y roles en servidor, boundary de demo, tests y cambios fuera de alcance.
6. Ejecutar checker con todas las features descubiertas y reportar falsos negativos/limitaciones del análisis regex.

## Patrón de implementación

Checker existente .azuredevops/scripts/check-architecture.mjs descubre src/features/* y trazas transitivas desde archivos use client.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No mover reglas de negocio a page.tsx.
- No compartir private modules de una feature.
- No tratar checker regex como equivalente a un compilador o threat model completo.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:architecture
npm run test:skills
npm run test:unit
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

# Architecture Review

Review the current repository, not an imagined generic layout.
Read `docs/architecture/overview.md` and architecture rules (`.agents/rules/architecture.md` or `.claude/rules/architecture.md` / `AGENTS.md`) before recommending structural changes.

## Feature model

Discover features from `src/features/*`; never hardcode a historical example feature name.

Expected layers:

```text
feature/
  domain/
  application/
  infrastructure/
  ui/
```

## Dependency rules

### domain

- framework-independent;
- no React/Next.js;
- no `server-only` or `node:*`;
- no application/infrastructure/ui dependencies.

### application

- depends on domain/ports;
- framework-independent;
- no React/Next.js;
- no infrastructure/ui dependencies;
- prefer injected clock/ID/network/storage abstractions over Node globals.

### infrastructure

- implements ports/adapters;
- may depend on application/domain;
- must not depend on UI;
- server composition roots that wire server capabilities must be `server-only`.

### ui

- React/Next presentation and interaction;
- may consume domain/application types/contracts as allowed by the feature;
- must not bypass the server boundary by importing server infrastructure/composition roots.

## Client/server rule

For every `'use client'` module, inspect the transitive import graph for server-only code, not only direct imports.
Treat Client -> `node:*`, `server-only`, `src/server`, or server infrastructure as a BLOCKER.

## Review output

Report evidence-based findings only, classified:

- BLOCKER: invalid dependency/security/runtime boundary;
- IMPORTANT: architecture drift likely to create coupling;
- IMPROVEMENT: non-blocking structure/maintainability.

Do not rewrite code unless requested.

## Automated guard

`npm run test:architecture` must automatically discover `src/features/*`; adding a new feature must not require editing a hardcoded feature list.
The guard should cover layer direction plus Client/server reachability.
