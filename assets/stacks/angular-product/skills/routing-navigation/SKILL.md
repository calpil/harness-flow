---
name: routing-navigation
description: Crear o modificar rutas Angular lazy, navegación del portal, guard y scope de providers. Úsala al crear pantallas, rutas de detalle y módulos de features.
---

# Routing Navigation — CALPIL Angular Golden Path

## Objetivo y activación

Mantener lazy routing, guard SSO correcto y aislamiento de estado por feature, evitando eager bundle y rutas rotas.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `src/app/app.routes.ts`, `src/app/features/work-items/work-items.routes.ts`.
- `src/app/core/layout/portal-shell.component.ts`, `src/app/core/auth/entra-auth.guard.ts`.
- `tests/e2e/smoke.spec.ts`, `tests/e2e/work-item-detail.spec.ts`.

## Procedimiento ejecutable

1. Identifica ruta pública vs protegida y jerarquía en shell; `/login` es pública y el resto se anida bajo guard.
2. Define path canónico, parámetros, query, 404 y retorno desde detalle; no expongas secrets en URL.
3. Para feature completa usa `loadChildren` del archivo `.routes.ts`; para página aislada `loadComponent` lazy.
4. Registra providers stateful por ruta feature; no en `app.config.ts` a menos que sea singleton transversal.
5. Conserva `canActivate`/`canActivateChild` en shell y saneamiento `returnUrl` en auth session.
6. Usa `routerLink` y navegación Angular en vez de `window.location.href` para pantallas internas.
7. Soporta navegación directa, reload, SPA fallback de nginx y ruta inexistente.
8. Revisa permisos de backend: guard protege UX, no datos; la API debe validar resource.
9. Escribe tests para URL directa/protegida, nav activa, parámetros no válidos y route 404.
10. Evalúa tamaño de bundle y ownership UI antes de agregar nuevas secciones al shell.

## Patrón de implementación

```ts
{ path: 'work-items',
  loadChildren: () => import('@work-items/work-items.routes')
    .then(m => m.WORK_ITEMS_ROUTES) }
```

El archivo `.routes.ts` es el composition root de Work Items.

## Decisiones y anti-patrones

- No mover features enteras a `core` solo por visibilidad de navegación.
- No cargar componentes eager con imports en `app.routes.ts`.
- No duplicar providers de feature globalmente.
- No usar query param libre como redirect absoluto tras login.

## Verificación / Definition of Done

- `npm run test:architecture`, `npm run typecheck`, rutas E2E y prueba reload en Nginx.
- Capturar evidencia de rutas protegidas con/sin sesión.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
