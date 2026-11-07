---
name: write-tests
description: Diseñar y ejecutar pruebas Vitest, React Testing Library, integración y Playwright que protejan cambios y regresiones.
---

# Write Tests — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `tests/unit/`
- `tests/component/`
- `tests/e2e/`
- `vitest.config.ts`
- `playwright.config.ts`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

- Referencia detallada: [guía concreta](./references/quality-matrix.md).

## Procedimiento ejecutable

1. Definir invariantes observables y nivel más barato que capture falla sin mockear comportamiento probado.
2. Crear unit domain/application con clock/id mock determinista y adapter fake.
3. Crear React Testing Library para UI, accesibilidad básica, submit, vacío/error/latencia.
4. Crear integración/contrato donde corresponde, y E2E para rutas, SSO seam explícitamente test-only.
5. Probar fallo antes de corrección cuando sea regresión, no eliminar tests incómodos.
6. Ejecutar pruebas dirigidas, arquitectura y build cuando altera routing o auth; informar pass/fail/no ejecutado.

## Patrón de implementación

tests/unit para dominio/application; tests/component para React; tests/e2e/login.spec.ts y auth-guards.spec.ts tienen límites de seam E2E documentados.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No snapshots vacíos ni solo tests del mock.
- No utilizar credenciales reales en Playwright.
- No declarar E2E SSO real a partir del seam local.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:unit
npm run test:component
npm run test:e2e
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

# Write Tests

Use this skill for every behavioral change or bug fix.

## Rules

1. Identify the expected observable behavior.
2. Select the smallest valid test level.
3. Reuse the repository's existing test conventions.
4. Create/update the test in the same change.
5. Execute it.
6. Fix implementation/test defects until it passes.
7. Run broader validation required by `AGENTS.md`.

## Levels

- unit: domain/application/pure functions;
- component: React behavior;
- integration: only the remaining frontend HTTP surfaces (auth/health), never a business BFF;
- architecture: boundaries;
- e2e: critical journeys.

## Regression

Every reproducible bug fix requires a regression test.

The regression test must fail without the fix and pass with it.

## Test quality

Prefer deterministic data, semantic UI queries and observable behavior.

Do not:

- weaken assertions;
- delete meaningful tests;
- mock the unit under test;
- add fixed waits;
- rely only on snapshots;
- skip relevant tests silently.

## Completion

Report:

```text
Tests created/updated:
Commands executed:
Results:
Not executed:
Remaining risk:
```

Never claim tests pass unless they were executed successfully.

## Pruebas obligatorias para clientes BFF y proxy técnico

Cuando cambie `bff-client.ts`, los adaptadores o el proxy, probar los tres recorridos: (1) navegador con `clientDirect=true` llama a BFF público, (2) navegador con `clientDirect=false` llama al proxy Next.js y éste al BFF autorizado, (3) Server Components/Actions llaman mediante server transport sin loopback. Probar GET/query, POST/PUT/PATCH/DELETE, headers funcionales, autenticación/401/403, errores HTTP 404/409/422/429/5xx, 204, JSON/FormData/binario, abort/timeout, forwarding seguro y rechazo de destinos no permitidos. Asegurar por tests de arquitectura que los consumidores BFF no usen `fetch`/`axios` directo fuera de los módulos autorizados. Reutilizar suites/scripts existentes; distinguir test unitario mockeado de integración real. No prohibir el Route Handler de proxy técnico bajo la regla «no BFF de negocio».
