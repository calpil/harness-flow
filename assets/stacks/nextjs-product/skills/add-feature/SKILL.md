---
name: add-feature
description: Implementar o ampliar una feature de negocio Next.js siguiendo domain/application/infrastructure/ui, puertos, composición App Router, tests y permisos.
---

# Add Feature — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/features/operations/{domain,application,infrastructure,ui,demo}/`
- `src/features/users/`
- `src/app/(portal)/ y tests/unit/`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

- Referencia detallada: [guía concreta](./references/operations-walkthrough.md).

## Procedimiento ejecutable

1. Traducir el pedido en actor, resultado, invariantes, permisos, datos, estados de pantalla, contrato API y aceptación verificable.
2. Identificar la composición actual y decidir si es feature real o solo página; no inventar capas vacías ni endpoints inexistentes.
3. Añadir entidad o reglas puras en domain y tests de invariantes; ninguna dependencia React/Next en dominio.
4. Definir caso de uso y puerto en application; inyectar adaptador sin importar framework en esta capa.
5. Implementar infraestructura solo en entorno servidor para persistencia/integraciones; en la demo del navegador usar el patrón src/features/*/demo, no importar infraestructura en Client Components.
6. Componer route/layout Server Component y UI de feature; aislar componente client mínimo para interacción y usar DS corporativo.
7. Cubrir happy-path, 401/403, loading, vacío, error y duplicados; documentar lo que no existe aún en BFF.
8. Ejecutar checks dirigidos, arquitectura y validación; reportar contratos reales vs supuestos sin afirmar integración inexistente.

## Patrón de implementación

domain/operation.ts → application/operations-service.ts + ports/operation-repository.ts → infrastructure/in-memory-operation-repository.ts (servidor) | demo/operations-session.ts (navegador) → ui/ → src/app/(portal)/. Este golden path es frontend: no crear Route Handler de negocio.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No Client Component con infraestructura, node:* o src/server en el grafo.
- No negocio ni acceso a DB desde page.tsx, Server Actions o API de salud.
- No compartir internals de otra feature: exponer contrato aprobado o pasar por composición.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:architecture
npm run test:unit -- --run
npm run test:component -- --run
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
