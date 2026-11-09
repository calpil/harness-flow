---
name: data-access-change
description: Crear, modificar o migrar puertos y adapters HTTP/in-memory sin filtrar infraestructura al dominio. Úsala para cambio de proveedor, DTO o cache de feature.
---

# Data Access Change — CALPIL Angular Golden Path

## Objetivo y activación

Preservar semántica de negocio al sustituir mecanismos de persistencia o transporte.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `src/app/features/work-items/application/work-item-repository.ts` (interface e InjectionToken).
- `src/app/features/work-items/data-access/{http-work-item.repository.ts,in-memory-work-item.repository.ts,work-item-repository.provider.ts}`.
- `docs/adr/0002-persistence-adapter.md`, `docs/platform/configuration.md`.

## Procedimiento ejecutable

1. Identifica capacidad del puerto en términos del dominio, no en términos HTTP.
2. Revisa consumidores y testes antes de variar firma (`Observable`, paginación, idempotencia).
3. Mantén la interface en application; implementaciones en data-access con tipos de DTO y mappers explícitos.
4. Define side effects, concurrencia, timeouts, ordering y semántica de errores.
5. Crea factory de provider con `deps` explícitas; ejemplar `provideWorkItemRepository()`; no `inject()` dentro de constructor manual sin DI.
6. Los fakes de test deben implementar el puerto, no simular detalles privados del adaptador.
7. Datos in-memory son únicamente demos local/test; no se permite fallback silencioso en ambientes corporativos.
8. Cambios de contrato API requieren registrar versión, compatibilidad y evidencia de pruebas.
9. Añade tests por implementación + test de feature que verifica sustitución sin cambiar UI.
10. Documenta migraciones/adaptadores removidos; evita acoplar repositorios de distintos bounded contexts.

## Patrón de implementación

```ts
{ provide: WORK_ITEM_REPOSITORY,
  deps: [APP_CONFIG, HttpClient],
  useFactory: (config: AppConfig, http: HttpClient) =>
    config.workItemsApiBaseUrl ? new HttpWorkItemRepository(http, config.workItemsApiBaseUrl)
                               : new InMemoryWorkItemRepository() }
```

Esta factory solo es válida porque config de ambientes corporativos impide URL vacía.

## Decisiones y anti-patrones

- Evita inyección global de un repositorio stateful de feature.
- No acceder a HttpClient en `ui` o `domain`.
- No usar `as SomeType` como parser de JSON externo; tipado de TS no hace validación runtime.
- No confundir datasource de demo con persistencia productiva.

## Verificación / Definition of Done

- Unit tests de puerto/implementación, `npm run typecheck`, `npm run test:architecture`.
- Confirmar fallo de BFF se propaga a UI como error y no crea datos falsos.
- Revisar 404, paginación, retries y manejo de conflictos según contrato.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
