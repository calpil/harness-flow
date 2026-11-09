---
name: dependency-review
description: Evaluar cambios npm (Next.js/React/DS) según compatibilidad, seguridad, lockfile y semántica de versiones.
---

# Dependency Review — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `package.json`
- `package-lock.json`
- `docs/development/dependencies.md`
- `next.config.mjs`
- `vitest.config.ts`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Comprobar necesidad concreta y existencia de dependencia equivalente instalada.
2. Evaluar release/compatibilidad de Next16, React19, Node24, Auth.js5 beta y @calpil-ds/react real.
3. Verificar pares, engines, breaking changes, SCA y licencias antes de actualizar.
4. Modificar package.json y lockfile de forma coherente; usar npm ci para reproducibilidad.
5. Actualizar imports/tests y medir efecto en bundle/server-client boundary.
6. Registrar versión antigua/nueva, motivo, impacto, comandos ejecutados y rollback.

## Patrón de implementación

Source of truth: package.json y package-lock.json. La dependencia @calpil-ds/react requiere feed privado.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No npm install --force/legacy-peer-deps sin aprobación.
- No subir versiones por intuición sin changelog.
- No afirmar build sin acceso al feed.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run typecheck
npm run test:architecture
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
