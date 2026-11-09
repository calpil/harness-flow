---
name: add-ui-component
description: Crear un componente Angular standalone tipado, accesible y integrado con Design System. Úsala para controles, cards, listas, páginas y formularios de una feature.
---

# Add Ui Component — CALPIL Angular Golden Path

## Objetivo y activación

Crear una pieza UI con ownership de feature y responsabilidad clara, sin negocio ni acceso HTTP directo.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `src/app/features/work-items/ui/{status-badge.component.ts,create-work-item-form.component.ts}`.
- `docs/ui/design-system.md`, `src/app/features/design-system/ui/design-system-page.component.ts`.
- Skill `design-system-integration` + `accessibility-review` cuando haya interacción.

## Procedimiento ejecutable

1. Decide ownership: dentro `features/<feature>/ui` por defecto; `shared/ui` solo si es puramente reusable y usado en más de una feature.
2. Escribe contrato de inputs/outputs tipados, estados y responsabilidad; evita introducir dependencias de infraestructura.
3. Inspecciona exports `@calpil-ds/angular` antes de agregar un componente existente.
4. Define selector `calpil-*`, `standalone: true`, imports mínimos y template con `@if`/`@for track` cuando aplica.
5. Utiliza `input()`/`output()` o patrón existente sin mezclar contratos para lo mismo; no manipules DOM con `document.querySelector`.
6. Coloca invariantes y reglas de negocio en domain, casos de uso en servicio application; el componente emite eventos de UI.
7. Renderiza loading/empty/error sin ocultar errores; botones disabled y validación de submit.
8. Asegura accesibilidad: label, aria-describedby, focus visible, roles semánticos, teclado y mensajes en `role=alert/status`.
9. Prueba renderización/inputs/outputs/interacción; actualizar ejemplo DS cuando es patrón reusable.
10. Si modifica ruta, coordina skill `routing-navigation` y conserva lazy providers.

## Patrón de implementación

```ts
// Referencia del formulario existente:
readonly created = output<string>();
// El servicio de aplicación procesa el comando; el formulario no realiza HTTP.
```

## Decisiones y anti-patrones

- No copiar implementaciones de DS ya publicadas.
- Evitar CSS de tokens duplicados, estilos inline no justificables y DOM injection.
- No convertir página completa en componente monolítico; separar según responsabilidades reales.
- No `HttpClient` directo en componente.

## Verificación / Definition of Done

- Unit/component test, `npm run typecheck`, `npm run lint`, revisión teclado y móvil.
- Comprobar default/loading/error/disabled, y uso del theme del DS real si disponible.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
