---
name: feature-flag-rollout
description: Añadir flags de producto Next.js con fallback determinista, ownership y rollback sin saltarse permisos ni seguridad.
---

# Feature Flag Rollout — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/shared/feature-flags/`
- `src/server/feature-flags/`
- `config/feature-flags.fallback.json`
- `docs/platform/feature-flags.md`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Definir nombre, owner, valor por ambiente, expiración, impacto funcional y estrategia kill-switch.
2. Evaluar flag en lugar apropiado (server-first); pasar solo decisión pública al navegador.
3. Conservar fallback seguro ante falla de proveedor sin convertir flag en autorización.
4. Diferenciar lanzamiento controlado de funcionalidades ocultas; backend debe seguir autorizando.
5. Probar on/off, fuente indisponible, overrides mal formados y cambio por ambiente.
6. Retirar flags obsoletos junto a código muerto y documentar rollback.

## Patrón de implementación

Fallback versionado config/feature-flags.fallback.json; acceso a flags de servidor src/server/feature-flags y contrato compartido src/shared/feature-flags.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No usar flag para conceder permisos.
- No introducir variaciones aleatorias sin sticky key.
- No condicionar invariantes de dominio a UI flag.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:unit
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
