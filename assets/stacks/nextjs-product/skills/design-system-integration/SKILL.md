---
name: design-system-integration
description: Integrar correctamente @calpil-ds/react sin recrear controles corporativos ni asumir exports, props o CSS inexistentes.
---

# Design System Integration — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `docs/ui/design-system.md`
- `src/components/portal/`
- `src/features/operations/ui/`
- `src/app/(public)/login/`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

- Referencia detallada: [guía concreta](./references/ds-acceptance.md).

## Procedimiento ejecutable

1. Inspeccionar versión instalada de @calpil-ds/react y types/exported props; si no se instala, registrar API no verificada.
2. Identificar componente DS para caso de uso, su composición y estados, priorizando primitives corporativas.
3. Integrar estilos/tokens/provider según documentación real existente y límite server/client.
4. Comprobar teclado, labels, focus visible, aria-live, errores, densidad y responsive.
5. Evitar overrides frágiles y duplicados CSS; documentar desviación aprobada si el DS no cubre el caso.
6. Probar componentes y páginas con datos largos, locales en/es/pt y estado disabled/loading.

## Patrón de implementación

La UI de portal vive en src/components/portal; UI de feature en src/features/*/ui; login usa componente oficial DS, no mock de marca.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No inventar nombre de componente DS sin confirmar export.
- No introducir otra UI library incidental.
- No copiar el código del DS dentro del template.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:component
npm run lint
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
