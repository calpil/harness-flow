---
name: accessibility-review
description: Evaluar accesibilidad real de UI Next.js con semántica, teclado, foco, formularios, navegación y feedback.
---

# Accessibility Review — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/features/operations/ui/`
- `src/components/portal/`
- `src/app/`
- `tests/component/`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Revisar estructura headings/landmarks, labels, aria-describedby, roles, estados de foco.
2. Recorrer teclado en menús, tablas, modal/dialog y rutas; inspeccionar foco al navegar.
3. Verificar mensajes aria-live para errores, loading, éxito y status sin depender solo de color.
4. Probar textos largos/traducciones, zoom/reflow y preferencias reduced-motion.
5. Usar DS oficial y no duplicar semántica aria nativa.
6. Añadir tests de interacciones accesibles con RTL y registrar problemas manuales.

## Patrón de implementación

Primero componentes @calpil-ds/react verificados; fallback personalizado requiere justificar semántica e interacción.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No onClick en div sin teclado.
- No placeholders como sustituto labels.
- No invisibilizar foco con CSS.

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

# Accessibility Review

Use for every user-facing UI change.

## Check

- semantic elements are used;
- inputs have associated labels;
- buttons are actual buttons;
- keyboard navigation works;
- visible focus exists;
- radio/checkbox groups have meaningful names;
- validation/errors are associated with controls;
- status is not communicated by color alone;
- accessible names are localized;
- drag-and-drop has an accessible alternative when reasonable.

## Testing

Prefer role/label queries in component/E2E tests.

Do not add ARIA when native semantics already solve the problem.

Fix accessibility regressions introduced by the current change.
