---
name: bff-contract
description: Integrar endpoints REST del BFF corporativo con adapters Angular, DTOs, paginación, errores y pruebas de contrato. Usar cuando se agrega/cambia el consumo HTTP.
---

# Bff Contract — CALPIL Angular Golden Path

## Objetivo y activación

Implementar contrato verificable antes de escribir llamadas HTTP. El repositorio es consumidor; no debe crear BFF, NestJS, Azure resources ni endpoints imaginarios.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `src/app/features/work-items/{application/work-item-repository.ts,data-access/http-work-item.repository.ts,data-access/work-item-repository.provider.ts}`.
- `src/app/core/auth/entra-api.interceptor.ts`, `src/app/core/http/correlation-id.interceptor.ts`.
- `docs/platform/configuration.md`, `docs/platform/deployment-contract.md`.
- [Ficha de integración](./references/contract-checklist.md); OpenAPI/Swagger proporcionado por el equipo BFF.

## Procedimiento ejecutable

1. Reúne base URL y **recurso completo** `/bff/v1/{api}/resource`, método, request DTO, response DTO, errores, scopes y paginación.
2. Si no hay contrato OpenAPI, solicita/deja pendiente; no adivines nombres de campos, endpoints ni HTTP status.
3. Define modelos internos en `domain` y puerto de aplicación; mapea DTO de transporte en `data-access` con funciones explícitas en límites.
4. Inyecta `HttpClient` mediante provider factory en el composition root de la feature. No uses `new HttpClient` ni `inject()` en factory ejecutada fuera de DI.
5. `APP_CONFIG` lleva ruta de colección; URL para detalle usa `encodeURIComponent(id)` sin interpolar strings no confiables en origen.
6. Reutiliza interceptores globales para correlation id + bearer allowlisted; no pegues headers `Authorization` en cada adapter.
7. Aplica timeout y mensajes de error sin filtrar detalles internos; diferencia 400 validación, 401 sesión/token, 403 permiso, 404 ausencia, 409 conflicto, 5xx falla.
8. Diseña retries solo para operaciones seguras/idempotentes y fallas transitorias, nunca PATCH/POST indiscriminadamente.
9. Añade tests de request/response/error con HttpTestingController o mock adapter; comprueba ruta, query, status y mapping.
10. Separa demonstración in-memory local de ambientes corporativos que exigen `workItemsApiBaseUrl` y scopes.
11. Documenta contrato de caché, consistencia, paginación, concurrencia y ownership de datos cuando aplique.
12. Si BFF necesita cambios, registra dependencia para repositorio backend, no implementes endpoint en frontend.

## Patrón de implementación

```ts
// Referencia existente: no copiar este endpoint a otra API sin contrato.
list(offset: number, limit: number) {
  return this.http.get<{ items: WorkItemSnapshot[]; total: number }>(
    this.baseUrl, { params: { offset, limit } }
  );
}
```

En una integración real validar DTOs y mapear transporte a modelo de dominio.

## Decisiones y anti-patrones

- Nunca usar `as WorkItemSnapshot` como validación de JSON externo. Tipado TS no valida runtime; elegir parser/guard razonable si el contrato lo requiere.
- Evitar dependencias entre features por importar un adapter ajeno; contrato compartido aprobado primero.
- Política same-origin de runtime config evita leaks de bearer/CORS por diseño.
- Nada de token en URLs, localStorage ni logs.
- Los endpoints Work Items del template son ilustrativos, no garantizados en servicios productivos.

## Verificación / Definition of Done

- Validación de contrato contra OpenAPI, unit tests de request y mapping, `npm run test:security`.
- 401/403/404/409/500/timeout/reintento y paginación comprobados al menos con pruebas.
- `npm run typecheck && npm run test:architecture` y E2E con BFF real solo si existe ambiente accesible.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
