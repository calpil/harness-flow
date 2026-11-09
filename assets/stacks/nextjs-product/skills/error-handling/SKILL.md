---
name: error-handling
description: Diseñar errores de dominio/aplicación/HTTP y límites visuales Next.js con mensajes seguros, retry y observabilidad.
---

# Error Handling — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/features/operations/domain/errors.ts`
- `src/shared/errors/`
- `src/app/error.tsx`
- `src/app/global-error.tsx`
- `src/shared/observability/`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Clasificar validación usuario, conflicto de negocio, ausencia, falta de permiso, dependencia externa y error inesperado.
2. Conservar errores tipados al cruzar dominio→application→adapter; mapear HTTP sólo en frontera.
3. Agregar feedback claro, códigos estables y correlation id cuando exista en contrato BFF.
4. No filtrar stacks, claims ni payload con PII en UI/logs; usar error.tsx para fallback recuperable.
5. Evitar que status 401 se disfrace de 404 o que 403 redirija como login.
6. Probar error recuperable, timeout, schema inválido y pantalla con network offline.

## Patrón de implementación

Patrón: InvalidOperationError en domain; API/adapter traduce respuestas; src/app/error.tsx provee fallback para excepciones inesperadas.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No catch universal que retorna [] y oculta fallas.
- No stack trace en respuesta JSON pública.
- No hacer console.log de token.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:unit
npm run test:component
npm run test:security
```

- Código/contrato probado bajo las capacidades efectivamente disponibles; distinguir comandos ejecutados, fallidos y pendientes.
- Sin nuevas violaciones de import graph, secretos, traducciones o accesibilidad relacionadas al cambio.
- Los cambios de login, BFF, DS privado y entorno AKS precisan validación integrada fuera de tests mock.

## Contrato de entrega del agente

1. Explicar archivos cambiados y responsabilidad de cada capa.
2. Declarar habilidades activadas, alternativas descartadas, contratos y permisos requeridos.
3. Registrar pruebas con comando y resultado real; cualquier requisito no verificado queda explícito.
4. Incluir riesgos/rollback para cambios de SSO, build, deploy o compatibilidad entre features.
