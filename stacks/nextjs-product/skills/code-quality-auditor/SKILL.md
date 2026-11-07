---
name: code-quality-auditor
description: Auditar legibilidad y corrección de changesets React/Next.js sin sacrificar arquitectura ni scope.
---

# Code Quality Auditor — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `AGENTS.md`
- `src/features/operations/`
- `src/app/`
- `docs/ai/CODING_STANDARDS.md`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Examinar flujo de datos y side effects para fallos lógicos, stale closure y nullability.
2. Revisar tipos de dominio/DTO y prop drilling innecesario sin crear abstracciones hipotéticas.
3. Confirmar imports entre capas, server/client, ownership DS y prácticas de async/AbortSignal.
4. Evaluar error handling, i18n, a11y, tests y API design con evidencia reproducible.
5. Reducir ruido, duplicidad y cambios ajenos; proponer micro-refactor solo si facilita petición.
6. Reportar hallazgos por severidad, archivo, repro/impacto y cambios recomendados.

## Patrón de implementación

Golden path: src/features/operations y src/features/users. Preferir patrón existente frente a un nuevo framework de estado.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No usar any para callar TS.
- No export barrels que filtren servidor a client.
- No reescribir medio repo para arreglar bug local.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run lint
npm run typecheck
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

# Code Quality Auditor

Run before completing non-trivial implementation.

Review only the changed/affected scope unless evidence requires broader inspection.

## Check

### Structure

- responsibilities are separated;
- domain logic is not buried in UI;
- existing architecture is respected;
- no unnecessary abstraction/layer was introduced.

### TypeScript

- no avoidable `any`;
- types are meaningful and narrow;
- casts are justified;
- finite states are handled safely.

### React/Next.js

Flag:

- unnecessary Client Components;
- effect loops;
- unstable dependencies;
- derived state stored via effects unnecessarily;
- duplicated fetches;
- router refresh/navigation used as state management;
- RSC requests caused by local-only interactions;
- giant page/components.

### Duplication

- no repeated business logic;
- no duplicate helpers/primitives;
- no duplicated fetching/state logic.

### Reliability

- errors are not swallowed;
- async flows are handled;
- loading/error/empty states are coherent;
- edge cases introduced by the change are covered.

### Localization

- no new visible hardcoded strings;
- translated labels are not used as business values.

### Tests

- relevant behavior has meaningful tests;
- assertions were not weakened.

## Output

Report:

```text
Critical:
Important:
Minor:
No issue:
```

Fix critical/important issues that are in scope before completion.
