---
name: async-state-management
description: Gestionar loading/empty/error/refetch/cancelación en UI React sin efectos redundantes ni fugas de requests.
---

# Async State Management — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/features/operations/ui/`
- `src/features/operations/demo/operations-session.ts`
- `src/features/operations/application/operations-service.ts`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Elegir Server Component fetching cuando no hay razón para traer estado al navegador.
2. Si hay UI client, modelar estados explícitos idle/loading/success/error y datos obsoletos sin variables inconsistentes.
3. Definir key/criterio de consulta y AbortSignal; cancelar requests obsoletas al cambiar filtros o desmontar.
4. Evitar efectos que copian props sin necesidad; derivar valores con funciones puras.
5. Ofrecer retry contextual y feedback accesible, sin duplicar efectos en Strict Mode.
6. Probar concurrencia y respuestas fuera de orden, latencia, vacío y error recuperable.

## Patrón de implementación

El ejemplo fetchOperations(input, {pageSize,signal}) permite cancelación; su implementación demo no equivale a API remota de producción.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No mezclar caché global, contexto y feature state sin necesidad.
- No useEffect para derivar datos computables.
- No ocultar errores con listado vacío.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:component
npm run test:unit
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
