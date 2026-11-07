---
name: async-state-management
description: Diseñar estado asíncrono local por feature con Signals/RxJS, cancelación y sincronización. Úsala para búsquedas, listas, detalles, filtros y mutations.
---

# Async State Management — CALPIL Angular Golden Path

## Objetivo y activación

Conservar UI coherente y evitar respuestas fuera de orden sin introducir store global salvo necesidad probada.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `src/app/features/work-items/application/work-item.service.ts`.
- `src/app/features/work-items/ui/work-item-list.component.ts`.
- `src/app/features/work-items/application/work-item-repository.ts`.
- `docs/architecture/overview.md` y `docs/quality/testing.md`.

## Procedimiento ejecutable

1. Separa estado persistido remoto de estado local de presentación (filtro, panel abierto, formulario sucio).
2. Define estado mínimo: `items`, `total`, `selected`, `loading`, `error`; usa `computed` para proyecciones derivadas.
3. Mantén Signals escritos en service y expón `asReadonly()` para vistas; no exponer señales mutables a UI indiscriminadamente.
4. Decide cuándo usar Observable vs Promise: repositorio existente devuelve Observable, UI consume signals del servicio.
5. Al introducir búsqueda rápida/paginación, previene stale responses con `switchMap`/request-id/cancel según lifecycle.
6. En mutation, confirma respuesta del BFF antes de anunciar éxito; para optimistic UI definir rollback y conflicto.
7. No pisar error de una operación por otra; maneja abort/cancel/cleanup al destruir feature.
8. Diseña paginación y filtros con estados vacíos distintos: no hay datos vs no hay coincidencias.
9. Evita suscripciones perdidas en componentes y duplicación de requests al navegar; `takeUntilDestroyed` cuando aplique.
10. Prueba latencias desordenadas, errores, doble submit y cambios de ruta.

## Patrón de implementación

```ts
private readonly _items = signal<WorkItemSnapshot[]>([]);
readonly items = this._items.asReadonly();
readonly isEmpty = computed(() => !this._loading() && this._items().length === 0);
```

Antes de evolucionar este patrón, cubrir concurrencia y cancelación.

## Decisiones y anti-patrones

- No introducir NgRx/Akita o singleton store por preferencia sin casos de uso.
- No mezclar server/cache y UI state en una entidad de dominio.
- No dejar `subscribe()` sin estrategia de lifecycle cuando la operación puede permanecer activa.
- No actualizar estado como si HTTP PATCH hubiera tenido éxito sin confirmación.

## Verificación / Definition of Done

- Test del servicio con Observables controlados (delays y errores).
- E2E para búsqueda/filtro, optimistic rollback cuando exista.
- Inspección de memoria/race conditions en navegación repetida.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
