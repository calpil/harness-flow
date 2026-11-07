---
name: ui-quality-review
description: Revisar UX de portal Angular con Design System: estados, navegación, formularios, listados y responsive. Úsala en pantallas nuevas y antes de merges de UI.
---

# Ui Quality Review — CALPIL Angular Golden Path

## Objetivo y activación

Dar calidad de producto real, no solo una captura bonita de happy path.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `src/app/core/layout/portal-shell.component.ts` y `src/styles/styles.scss`.
- `src/app/features/{dashboard,work-items,reports,admin}/ui`.
- `docs/ui/design-system.md`, `docs/quality/testing.md`.

## Procedimiento ejecutable

1. Identifica tarea principal del usuario y define jerarquía de información y acciones primarias/secundarias.
2. Revisa consistencia con shell CALPIL, breadcrumbs/rutas y componentes del DS realmente instalados.
3. Audita todas las variantes: loading, sin registros, filtro sin coincidencia, error, retry, no autorizado, offline/timeout.
4. Verifica que acciones deshabilitadas expliquen motivo; no mostrar éxito antes de confirmación del backend.
5. Comprueba layouts desde viewport móvil a escritorio, zoom 200%, textos largos, internacionalización prevista y tablas overflow.
6. Revisa formularios tipados: etiquetas, helper text, validaciones, errores inline y submit protegido de dobles clics.
7. Revisa affordances: link navegación vs button acción; focus/hover/active y estados optimistas coherentes.
8. No diseñar métricas ficticias o admin RBAC inexistente: marcar visualizaciones como ejemplos no productivos.
9. Completa revisión de accesibilidad y screenshot antes/después para cambios de alto impacto.
10. Entrega hallazgos priorizados con referencia de pantalla y criteria de aceptación.

## Patrón de implementación

```text
Checklist página: propósito claro · acción primaria · loading · empty · error · permisos · móvil · teclado · volver.
```

## Decisiones y anti-patrones

- No reemplazar DS por CSS de conveniencia.
- No esconder errores tras banner de éxito.
- No usar modales como solución para cualquier interacción.
- No simular datos productivos en dashboard sin rotulado claro.

## Verificación / Definition of Done

- Pruebas por estados UI, responsive y teclado; `npm run test:e2e` si cambian journeys.
- Validar pantallas con textos reales largos y rutas directas.
- Enumerar inconsistencias DS solo cuando verificadas con paquete instalado.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
