---
name: accessibility-review
description: Auditar y corregir accesibilidad de pantallas Angular y componentes corporativos. Úsala en cambios visuales, formularios, rutas y modales.
---

# Accessibility Review — CALPIL Angular Golden Path

## Objetivo y activación

Garantizar uso con teclado/lectores de pantalla y estados dinámicos perceptibles, más allá del contraste visual.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `src/app/core/layout/portal-shell.component.ts`.
- `src/app/features/work-items/ui/*`, `src/app/core/auth/login-page.component.ts`.
- `docs/ui/design-system.md` y guía WCAG vigente de la organización.

## Procedimiento ejecutable

1. Identifica acciones, navegación, foco, anuncios y formularios; registra ruta, selector y comportamiento actual.
2. Revisa estructura semántica: landmarks, encabezados en orden, buttons reales y enlaces para navegación.
3. Recorre todo con Tab/Shift+Tab/Enter/Escape: menú, dropdown, dialog, cambio de rutas, detalle, formularios.
4. Asegura foco visible, orden lógico, return focus tras cerrar overlay y foco en encabezado/errores al navegar cuando aplica.
5. Valida label asociado, required, invalid, error description, fieldset para grupos y mensajes comprensibles.
6. Usa `role=status` para carga no intrusiva y `role=alert` para errores importantes; evita anuncios duplicados.
7. Asegura filtros/tablas/listas navegables; paginación con controles semánticos, orden estable y track ids.
8. Revisa responsive/zoom, contraste y uso sin color exclusivo; usa tokens DS existentes.
9. Prueba con lector de pantalla cuando el equipo dispone, y registra verificaciones manuales y automatizadas por separado.
10. Revisa estados vacíos/loading/error y route 404, no solo happy path.

## Patrón de implementación

```html
<label for="title">Título</label>
<input id="title" formControlName="title" aria-describedby="title-help" />
<p id="title-help">Máximo 140 caracteres</p>
```

El estado invalid debe agregar descripción de error de forma dinámica.

## Decisiones y anti-patrones

- No cambiar `<button>` por `<div (click)>`.
- No fijar tabindex positivo para “ordenar” navegación.
- No poner aria-label genérico en cada elemento sin propósito.
- No considerar accesible un componente solo por venir del DS.

## Verificación / Definition of Done

- Test de selectores por rol/nombre cuando sea estable; auditoría teclado con evidencia.
- `npm run lint && npm run test:e2e` en journeys afectados.
- Reportar hallazgos severidad, ubicación, criterio y corrección.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
