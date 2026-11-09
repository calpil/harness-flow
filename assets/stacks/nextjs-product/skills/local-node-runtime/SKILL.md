---
name: local-node-runtime
description: Ejecutar el template con Node requerido por engines y gestor de versiones global; eliminar runtimes portables internos al repositorio.
---

# Local Node Runtime — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `package.json#engines`
- `scripts/bootstrap-local.mjs`
- `package.json#scripts.start:local`
- `docs/getting-started/local-development.md`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Leer engines.node y packageManager, y comparar con node --version/npm --version antes de instalar.
2. Si Node no cumple, detenerse con instrucción fnm/nvm/Volta o instalador corporativo; no descargar ejecutables en el checkout.
3. No alterar versiones de Node/npm del sistema automáticamente; permitir al usuario seleccionar toolchain.
4. Configurar .npmrc LOCAL ignorado para feed; usar login/cuenta autorizada sin persistir token en Git.
5. Ejecutar npm ci solo con lockfile; no mutar lockfile salvo cambio de dependencia explícito.
6. Usar scripts oficiales y documentar prerequisitos Node24/npm y fallas reproducibles.

## Patrón de implementación

`npm run start:local` (con `npm run bootstrap:local`) es el entrypoint local. `package.json` exige >=24 <25; engines es fuente de verdad.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No carpetas ocultas de runtime portable dentro del repo.
- No curl|bash, downloads de toolchain automáticos ni npm install -g ocultos.
- No saltarse engines con --force.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
node --version
npm --version
npm run test:skills
npm run test:repo-hygiene
```

- Código/contrato probado bajo las capacidades efectivamente disponibles; distinguir comandos ejecutados, fallidos y pendientes.
- Sin nuevas violaciones de import graph, secretos, traducciones o accesibilidad relacionadas al cambio.
- Los cambios de login, BFF, DS privado y entorno AKS precisan validación integrada fuera de tests mock.

## Contrato de entrega del agente

1. Explicar archivos cambiados y responsabilidad de cada capa.
2. Declarar habilidades activadas, alternativas descartadas, contratos y permisos requeridos.
3. Registrar pruebas con comando y resultado real; cualquier requisito no verificado queda explícito.
4. Incluir riesgos/rollback para cambios de SSO, build, deploy o compatibilidad entre features.
