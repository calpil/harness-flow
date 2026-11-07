# Operations walkthrough — referencia real, no implementación ficticia

## Mapa de carpetas

- `src/features/operations/domain/operation.ts`: `Operation`, `OperationStatus`, `CreateOperationInput`, `createOperation()` y validación de nombre.
- `src/features/operations/domain/errors.ts`: errores de dominio.
- `src/features/operations/application/ports/operation-repository.ts`: `OperationRepository` (list, findById, save).
- `src/features/operations/application/operations-service.ts`: `OperationsService`, filtros, paginación, creación, Clock e IdGenerator.
- `src/features/operations/infrastructure/in-memory-operation-repository.ts`: adaptador server-side del puerto.
- `src/features/operations/demo/operations-session.ts`: persistencia DEMO por sesión del navegador, nunca backend productivo.
- `src/features/operations/ui/operations-local-client.ts`: puerta client de demo, importa `demo/`, no `infrastructure/`.
- `src/features/operations/ui/new-operation-form.tsx`: interfaz de creación.
- `src/app/(portal)/`: compose rendering y acceso; no dominio en rutas.

## Receta E2E

1. Encontrar operación requerida, invariantes y permiso (no extrapolar roles).
2. Extender el modelo de dominio y pruebas con entradas inválidas.
3. Modificar puerto/caso de uso si el dominio cambia.
4. Para demo, extender session mock; para integración real, definir contrato BFF externo y adapter server-only después de tener OpenAPI.
5. UI muestra loading/error/empty/success sin importar infrastructure desde use client.
6. Agregar pruebas de UI y navegación; validar límites con `npm run test:architecture`.

## Antipatrón señalado

Un `use client` que importe `InMemoryOperationRepository` viola la separación aunque el repositorio parezca inocuo: la capa infrastructure se reserva para composición server. No crear `/api/operations` en este frontend para evitar el BFF externo.
