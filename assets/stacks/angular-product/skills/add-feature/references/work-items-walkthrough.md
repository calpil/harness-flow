# Work Items: walkthrough de la vertical de referencia

Este documento corresponde al repositorio Angular 0.3.x y complementa `add-feature`; no contiene API productiva certificada.

## Ruta del usuario

1. `src/app/app.routes.ts` registra `/work-items` con `loadChildren`.
2. `src/app/features/work-items/work-items.routes.ts` define ruta raíz y `:id`, y providers `provideWorkItemRepository()` y `WorkItemService`.
3. `WorkItemListComponent` solicita estado por `WorkItemService`; no importa `HttpClient`.
4. `CreateWorkItemFormComponent` usa `FormControl` non-nullable y emite `created`.
5. `WorkItemService.create()` crea aggregate `WorkItem.create()` que valida título; invoca `WORK_ITEM_REPOSITORY.save()`.
6. `WORK_ITEM_REPOSITORY` vive en `application/work-item-repository.ts`; adapter se resuelve en data-access.
7. Si `workItemsApiBaseUrl` está configurada, el provider usa `HttpWorkItemRepository`; si está vacía **solo local**, `InMemoryWorkItemRepository`.
8. El interceptor en core añade bearer MSAL únicamente para endpoint allowlisted.
9. `WorkItemDetailComponent` lee `:id`, invoca `loadById` y enseña acciones permitidas por `canTransition`.
10. La UI muestra loading, error, vacío y filtros; cada capa conserva ownership.

## Contrato de implementación de otra feature

| Decisión               | Ubicación                      | Prueba                         |
| ---------------------- | ------------------------------ | ------------------------------ |
| Invariante de dominio  | `domain/`                      | spec de dominio                |
| Orquestación y Signals | `application/`                 | spec de servicio con port fake |
| Contrato consumidor    | application port + doc OpenAPI | contract test                  |
| Transporte/mapping     | `data-access/`                 | HTTP request/error test        |
| Elección de adapter    | feature route provider         | provider factory test          |
| Estados UI             | `ui/`                          | component test                 |
| Navegación protegida   | `app.routes` + feature routes  | E2E sin/con sesión             |

## Mini receta de implementación

- Crear entity/value object y funciones puras, testear reglas.
- Definir interface port en application y token DI si necesita adapter.
- Service orquesta llamadas y publica Signals readonly.
- Adapter DTO mapea API; no sobrecargar la entidad con decoradores JSON.
- Provider factory explícita resuelve adapter. En entorno corporativo, falla cerrado si falta config.
- Ruta lazy con provider de feature y componentes standalone.
- Formulario typed y acciones cuyo resultado remoto determina feedback.
- Unit/integration/e2e, luego arquitectura, lint, typecheck y build.

## Diferencias deliberadas respecto de un CRUD típico

- El frontend no implementa backend REST ni provisioning de la plataforma.
- La versión Work Items es demostrativa: endpoints solo ejemplo; se exige OpenAPI real para nuevas APIs.
- `WorkItemService` hoy usa `subscribe` para operaciones cortas; si se añade live-search o solicitudes concurrentes, aplicar skill `async-state-management` y controlar stale responses/destrucción.
- `create-work-item-form` reinicia al emitir, porque el ejemplo es mínimo; para formularios productivos esperar confirmación de server antes de resetear.
- El estado Angular no garantiza autorización: protección y segregación ocurren en backend.

## Tests candidatos para una feature nueva

- [ ] Dominio rechaza input inválido y transición no autorizada.
- [ ] Service muestra loading y error al fallar puerto.
- [ ] Adapter manda método/ruta/body/headers/timeout esperados.
- [ ] Provider falla/cambia correctamente según ambiente sin mocks productivos.
- [ ] UI mantiene input en conflicto y ofrece retry seguro.
- [ ] Ruta directa, reload, auth UX y E2E journey.
- [ ] Arquitectura rechaza importación UI→data-access y cross-feature.
