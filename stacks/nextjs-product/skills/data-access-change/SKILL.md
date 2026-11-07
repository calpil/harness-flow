---
name: data-access-change
description: Evolucionar adaptadores, repositorios y contratos de acceso a datos manteniendo ports de application y límites server/client.
---

# Data Access Change — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/features/operations/application/ports/operation-repository.ts`
- `src/features/operations/infrastructure/`
- `src/features/operations/demo/`
- `src/features/operations/ui/operations-local-client.ts`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Localizar el puerto afectado y consumidores; decidir si se trata de demo navegador o adapter de servidor.
2. Especificar DTO HTTP, validación/parseo y mapeo explícito hacia dominio; no filtrar DTO a UI por defecto.
3. Implementar timeout, cancelación/AbortSignal, paginación, error mapeado y observabilidad sin datos sensibles.
4. Propagar auth delegada solo desde capa de servidor definida con contrato; no inventar bearer de proveedor.
5. Evitar import directo de infraestructura en src/features/*/ui; respetar demo/ como seam de navegador.
6. Probar con repo fake o stub HTTP, y validar 404/409/429/5xx/timeouts y respuestas inesperadas.

## Patrón de implementación

Puerto: OperationRepository (application/ports). Adaptador: InMemoryOperationRepository en infrastructure, exclusivamente server; demo local: operations-session.ts consumido por operations-local-client.ts.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No fallbacks silenciosos a mocks en producción.
- No tokens o API keys en NEXT_PUBLIC ni consola.
- No convertir ui en capa de acceso a BD.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:unit
npm run test:architecture
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
