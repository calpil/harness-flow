---
name: api-contract-testing
description: Probar integraciones/DTO frente a OpenAPI BFF externo con fixtures, auth, resiliencia y cambios incompatibles.
---

# Api Contract Testing — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/features/operations/application/ports/`
- `tests/unit/`
- `tests/integration/`
- `vitest.config.ts`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Obtener OpenAPI o especificación versionada y enumerar endpoints consumidos; no asumir campos faltantes.
2. Crear fixtures tipados para éxito, campos opcionales, extras, null, formato inválido y evolución backward-compatible.
3. Verificar serializer/deserializer, límites de fechas, enumeraciones y código de error sin hacer live calls por defecto.
4. Probar comportamiento de timeouts/cancelación y 401/403/409/429/500 sin filtrar secretos.
5. Si existe entorno contract-test real, ejecutarlo separadamente y registrar versión/hash del contrato.
6. Mantener mock y producción distinguibles; los fixtures no prueban por sí solos que el BFF esté desplegado.

## Patrón de implementación

Ejemplo: adapter detrás de OperationRepository; pruebas con MSW/fetch stub únicamente si la herramienta está instalada, sin añadir librería innecesaria.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No hardcodear estructura arbitraria como contrato aceptado.
- No snapshots únicamente como prueba de compatibilidad.
- No exponer secretos en fixtures.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:unit
npm run test:integration
npm run typecheck
```

- Código/contrato probado bajo las capacidades efectivamente disponibles; distinguir comandos ejecutados, fallidos y pendientes.
- Sin nuevas violaciones de import graph, secretos, traducciones o accesibilidad relacionadas al cambio.
- Los cambios de login, BFF, DS privado y entorno AKS precisan validación integrada fuera de tests mock.

## Contrato de entrega del agente

1. Explicar archivos cambiados y responsabilidad de cada capa.
2. Declarar habilidades activadas, alternativas descartadas, contratos y permisos requeridos.
3. Registrar pruebas con comando y resultado real; cualquier requisito no verificado queda explícito.
4. Incluir riesgos/rollback para cambios de SSO, build, deploy o compatibilidad entre features.
