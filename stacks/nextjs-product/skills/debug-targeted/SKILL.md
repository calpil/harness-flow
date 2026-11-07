---
name: debug-targeted
description: Diagnosticar una falla concreta de Next.js TypeScript, React hydration, Auth.js, Vitest/Playwright o deploy sin refactor incidental.
---

# Debug Targeted — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `README.md`
- `tests/`
- `src/app/`
- `src/server/auth/`
- `proxy.ts`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Recoger comando exacto, log relevante, entorno/Node y repro mínima; ocultar tokens y PII.
2. Reducir scope a primera causa raíz; seguir imports/referencias de stack con búsquedas dirigidas.
3. Separar error de compilación, boundary client/server, routing, auth, Azure feed y tests flaky.
4. Escribir spec regresión que falle antes si el defecto es automatizable.
5. Corregir mínimo necesario, ejecutar prueba enfocada y revisar impacto lateral en permisos/DS.
6. Registrar causa raíz, evidencia, cambio y checks no disponibles.

## Patrón de implementación

Para client→server use npm run test:architecture; para fallos de sesión revisar src/auth.ts, src/server/auth/session.ts y proxy.ts sin loggear JWT.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No reinstalar toolchain/destruir lockfile automáticamente.
- No agregar any/skip test para silenciar síntoma.
- No editar módulos no afectados.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:unit
npm run test:architecture
npm run validate
```

- Código/contrato probado bajo las capacidades efectivamente disponibles; distinguir comandos ejecutados, fallidos y pendientes.
- Sin nuevas violaciones de import graph, secretos, traducciones o accesibilidad relacionadas al cambio.
- Los cambios de login, BFF, DS privado y entorno AKS precisan validación integrada fuera de tests mock.

## Contrato de entrega del agente

1. Explicar archivos cambiados y responsabilidad de cada capa.
2. Declarar habilidades activadas, alternativas descartadas, contratos y permisos requeridos.
3. Registrar pruebas con comando y resultado real; cualquier requisito no verificado queda explícito.
4. Incluir riesgos/rollback para cambios de SSO, build, deploy o compatibilidad entre features.
