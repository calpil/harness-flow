---
name: ui-quality-review
description: Revisar experiencia React/Next.js consistente con Design System, responsive, estados, visual hierarchy y uso real.
---

# Ui Quality Review — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `docs/ui/design-system.md`
- `src/components/portal/`
- `src/features/operations/ui/`
- `src/shared/i18n/`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Definir tareas del usuario y contexto móvil/escritorio; priorizar DS antes de estilos a mano.
2. Cubrir loading, empty, partial/error, disabled, retry, éxito y confirmación de acciones críticas.
3. Verificar densidad, contraste, spacing, fecha/locales, truncamiento y tablas adaptativas.
4. No duplicar controles, feedback ni iconografía si DS ya lo resuelve.
5. Probar 320px/768px/desktop, navegación teclado y datos extremos; registrar hallazgos.
6. Cuidar Server/Client boundaries para no pagar hidratar componentes estáticos.

## Patrón de implementación

Portal compartido en src/components/portal; features alojan su UI. Entra login usa ventana oficial de @calpil-ds/react.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No colores/estilos hardcodeados sin token.
- No esconder error de API como listado vacío.
- No client boundary demasiado grande.

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

## Guía adicional existente (preservada)

# UI Quality Review

Use for new/modified pages, forms, lists, tables, filters, dialogs and responsive layouts.

## Layout

Check:

- desktop width is intentional;
- mobile remains usable;
- whitespace/density is appropriate;
- content does not stretch unnecessarily;
- alignment is consistent;
- controls use appropriate widths.

## Forms

Check:

- every control has a clear label;
- technical IDs are not the only visible label;
- validation is near the field;
- destructive actions are explicit;
- short forms may use dialogs;
- larger forms may use pages/breadcrumb flows;
- values are preserved during non-destructive interactions.

## Data interaction

Prefer:

- partial/local updates;
- loading skeletons or clear loading state;
- filters without full-page reload;
- stable state;
- clear empty/error states.

Avoid:

- page refresh for local changes;
- oversized controls;
- cards nested without purpose;
- dense mobile layouts copied directly from desktop.

## Design System

Reuse existing components/tokens before creating custom UI primitives.

## Output

Report concrete UI issues and fix those in scope.
