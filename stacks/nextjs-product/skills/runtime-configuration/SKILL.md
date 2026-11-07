---
name: runtime-configuration
description: Modificar configuración de Next.js por ambiente y contratos públicos/privados conservando secrets en servidor y deploy reproducible.
---

# Runtime Configuration — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `config/configuration.contract.yaml`
- `src/server/config/server-config.ts`
- `src/shared/config/`
- `scripts/bootstrap-local.mjs`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Identificar configuración build-time NEXT_PUBLIC versus servidor runtime; Next no equivale a runtime JSON SPA Angular.
2. Actualizar fuente de verdad config/configuration.contract.yaml y `.env.example` si aparece una nueva clave.
3. Validar tipos y required al inicio con errores seguros; no depender de valores implícitos en producción.
4. Preferir server-only para secretos AUTH_* y acceso a servicios; no propagar al navegador accidentalmente.
5. Verificar ambientes sandbox/nonprod/prod de acuerdo al contrato corporativo sin inventar hostnames.
6. Probar ausencia de variable, tipo inválido y ausencia de secretos en build cliente/artefacto.

## Patrón de implementación

Contrato único: config/configuration.contract.yaml. Next.js Server Config es runtime por servidor; NEXT_PUBLIC se fija en build, no reutilizarlo como secreto.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No AUTH_SECRET o OAuth secret en NEXT_PUBLIC.
- No hardcodear ambientes corporativos en código.
- No convertir Next.js SSR en SPA runtime JSON sin ADR.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run bootstrap:local
npm run test:security
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
