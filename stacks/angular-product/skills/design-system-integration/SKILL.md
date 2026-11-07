---
name: design-system-integration
description: Integrar o actualizar componentes de @calpil-ds/angular y tokens corporativos, sin clonar el design system. Úsala para nuevos controles, formularios, layout y branding.
---

# Design System Integration — CALPIL Angular Golden Path

## Objetivo y activación

Maximizar consistencia y accesibilidad usando APIs verificadas del paquete privado; no asumir paridad con React.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `docs/ui/design-system.md`, `src/styles/styles.scss` (imports globales).
- `src/app/features/design-system/ui/design-system-page.component.ts`.
- `src/app/core/auth/login-page.component.ts`, `core/layout/portal-shell.component.ts`.
- `src/app/features/work-items/ui/work-item-list.component.ts`.
- [Ficha de componente DS](./references/component-acceptance.md).

## Procedimiento ejecutable

1. Identifica patrón visual y comportamiento requerido; comprueba si existe en el paquete @calpil-ds/angular instalado.
2. Inspecciona exports reales, typing, selectors, inputs, outputs, CSS tokens y demos de la versión instalada; no extrapoles @calpil-ds/react.
3. Diseña composición de producto con el componente corporativo; no vuelvas a implementar botones, inputs, modals, tooltips ni estilo base cuando exista API estable.
4. Define estados (default, hover, focus, invalid, disabled, loading, empty), responsive, densidad y comportamiento teclado.
5. Importa componentes standalone directamente en `imports: []`; evita registrar wrappers globales vacíos sin valor.
6. Usa tokens existentes y styles globales una sola vez; estilos SCSS propios solo layout/gaps de producto.
7. Si falta pieza DS: documenta gap, implementa composición mínima accesible y propón incorporación al equipo DS. No simules imports no exportados.
8. Para componentes que reciben datos no confiables, usar binding Angular normal, no `innerHTML` para eludir escaping.
9. Mantén navegación y reglas de feature; la sustitución de shell no debe afectar guards, rutas ni providers.
10. Agrega screenshot/test visual si hay entorno, tests de interacción y checklist WCAG en revisión.

## Patrón de implementación

```ts
// Referencia usada realmente en work-item-list.component.ts
imports: [CalpilButtonComponent, CalpilPageHeaderComponent];
// No extrapolar nombres de componentes adicionales.
```

## Decisiones y anti-patrones

- No copiar clases/DOM de componentes React a Angular.
- No agregar librería UI de terceros sin decisión técnica y política de dependencias.
- No inventar `CalpilTableComponent` o inputs sin inspeccionar exports.
- El template contiene `CalpilButtonComponent`, `CalpilPageHeaderComponent`, `CalpilLoginPatternComponent` como referencias pero no certifica paridad total del paquete privado.
- Branding es un contrato compartido, no CSS pixel-perfect improvisado.

## Verificación / Definition of Done

- Instalar feed autorizado y compilar con tipos reales.
- Navegación teclado/foco, error, accesibilidad y responsive verificados; contrast/focus ring.
- `npm run typecheck && npm run lint && npm run build:prod`; reportar componentes DS no verificables sin acceso al feed.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
