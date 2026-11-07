---
name: add-feature
description: Implementar una feature Angular completa (dominio, caso de uso, repositorio, rutas, UI y pruebas). Úsala al crear módulos de negocio o ampliar verticales existentes.
---

# Add Feature — CALPIL Angular Golden Path

## Objetivo y activación

Entregar comportamiento comprobable de extremo a extremo sin violar `ui → application → domain` ni acoplar la UI a `data-access`. Empezar por el caso de uso, no por componentes visuales.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `docs/architecture/overview.md` y `src/app/features/work-items/` como golden path funcional.
- `src/app/app.routes.ts`, `work-items/work-items.routes.ts`, `app.config.ts` como composition roots.
- `docs/ai/ARCHITECTURE_RULES.md` y pruebas existentes, más OpenAPI si existe backend.
- [Walkthrough de Work Items](./references/work-items-walkthrough.md) para nombres y mapeos reales.

## Procedimiento ejecutable

1. Reformula la solicitud como actor, evento, resultado, invariantes, permisos, contrato, estados UI y aceptación observable. Marca expresamente API/DS no verificados.
2. Distingue **feature de negocio** de página informativa (`dashboard`, `help`, `reports` no requieren dominio vacío). Crea capas solo si aportan responsabilidad.
3. Diseña entidades/value objects/reglas de transición en `domain/` TS puro; prueba invariantes y errores antes de conectar UI.
4. Declara el **puerto** en `application/` (ejemplo `WorkItemRepository`) y caso de uso en servicio de feature; usa Signals para `loading`, `error`, `items`, `selected` y estado derivado.
5. Implementa adaptadores en `data-access/`: HTTP según contrato BFF; in-memory solamente para demo `local`. DTOs nunca salen como modelo implícito de dominio.
6. Crea provider de feature mediante `InjectionToken` y factory con dependencias explícitas; no uses `inject()` fuera de contexto DI.
7. Implementa `ui/` con componentes standalone, control flow `@if`/`@for`, formularios tipados, `@calpil-ds/angular` verificado y estados loading/empty/error.
8. Declara `<feature>.routes.ts` con `providers` a nivel de ruta; conecta por `loadChildren` o `loadComponent`, sin eager import de componentes a `app.routes.ts`.
9. Protege navegación con el guard compartido; autorización del recurso va al BFF, nunca al guard. No apliques permisos a partir de claims sin contrato.
10. Escribe tests de dominio, servicio/mock port, adapter HTTP, componentes y E2E del journey. Documenta flags, endpoint y decisiones no triviales en ADR.
11. Ejecuta las puertas de calidad y entrega rutas/código/test/evidencia/resultados/no verificado.

## Patrón de implementación

```text
features/<capacidad>/
  domain/          # invariantes y tipos puros
  application/     # puertos, casos de uso y signals
  data-access/     # HttpAdapter/DTO/provider
  ui/              # páginas/formularios/estado visual
  <capacidad>.routes.ts  # providers por ruta + lazy routing
```

La referencia es Work Items; no copiar su vocabulario de negocio a otra feature.

## Decisiones y anti-patrones

- No crear estado compartido singleton para un estado que solo vive en una feature; scope de `providers` por ruta.
- No acoplar una feature con internals de otra; coordinar mediante rutas o un contrato transversal explícito aprobado.
- Si la API no existe, declara adapter/mock como demo, no inventes endpoints de producción.
- `domain` no importa Angular, RxJS, HTTP, DS ni `core`; `application` no importa `ui`/`data-access`; `ui` no importa `data-access`.
- Si es únicamente UI read-only, implementar `ui/` sin inventar `domain`/`application`.

## Verificación / Definition of Done

- `npm run test:architecture`; specs nuevos; `npm run typecheck`; `npm run lint`.
- Si cambia recorrido: `npm run test:e2e`; al cerrar PR: `npm run validate`.
- Comprobar manualmente usuario autenticado, error del BFF, vacío, latencia, permiso insuficiente y navegación directa por URL.
- Reportar en entrega archivos afectados, alcance, pruebas ejecutadas vs pendientes y supuestos del BFF.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
