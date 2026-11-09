---
name: domain-modeling
description: Modelar invariantes, entidades, value objects y transiciones de negocio independientes de React/Next y de la forma de los DTO.
---

# Domain Modeling — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/features/operations/domain/operation.ts`
- `src/features/operations/domain/errors.ts`
- `src/features/operations/application/operations-service.ts`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Derivar vocabulario ubicuo, estados permitidos e invariantes de historias y casos reales.
2. Separar tipo de dominio, entrada del caso de uso y representación HTTP, incluyendo nulabilidad y fechas.
3. Implementar factorías/funciones puras; rechazar entradas inválidas con errores tipados.
4. Inyectar clock/id generator en application para pruebas deterministas; no usar Date.now oculto en reglas.
5. Probar límites, normalización, idempotencia de operaciones y mutación accidental.
6. Evitar sobre-modelar simples vistas read-only; registrar decisiones que afectan otras features.

## Patrón de implementación

Referencia: createOperation(input) en domain/operation.ts valida nombre; OperationsService recibe Clock e IdGenerator; los DTO se mapean fuera del dominio.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No fetch, Next, React, localStorage, node:* ni Zod importado desde framework en domain.
- No permitir estados arbitrarios vía string sin union o regla.
- No representar entidades con un único objeto DTO sin mapeo.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:unit
npm run test:architecture
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
