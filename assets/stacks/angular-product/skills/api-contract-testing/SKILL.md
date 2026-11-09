---
name: api-contract-testing
description: Crear pruebas de contrato consumidor Angular↔BFF y detectar incompatibilidades de DTO/rutas sin requerir backend real para cada unit test. Úsala cuando cambia OpenAPI.
---

# Api Contract Testing — CALPIL Angular Golden Path

## Objetivo y activación

Hacer explícita y verificable la frontera de transporte, especialmente campos opcionales, paginación y errores.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `src/app/features/work-items/data-access/http-work-item.repository.ts`.
- `src/app/features/work-items/application/work-item-repository.ts`.
- `docs/platform/deployment-contract.md`, [ficha BFF](../bff-contract/references/contract-checklist.md).
- Contrato OpenAPI entregado por backend, nunca inferido desde la UI.

## Procedimiento ejecutable

1. Obtén OpenAPI versionado (ruta commit/release) y enumera operaciones realmente usadas por la feature.
2. Verifica método, recurso, request/response status, paginación, DTO, tipos null/optional y error schema.
3. Crea fixtures validadas a partir del contrato (sanitizadas, sin datos productivos).
4. Testea HTTP mapping y deserialización con datos malformados/bordes; TS `HttpClient<T>` no valida JSON.
5. Verifica statuses 200/201/204, 400/401/403/404/409/500 y timeout donde corresponda.
6. Comprueba autenticación: el interceptor añade bearer solo al recurso allowlisted; no testear token real en unit.
7. Comprueba compatibilidad hacia atrás ante campos nuevos/desaparecidos.
8. Si contrato requiere backend para integración real, registra prueba ejecutable con ambiente y credenciales de test no persistidas.
9. Documenta discrepancias como change request backend y no inventes nuevo esquema en el consumidor.
10. Valida correlation id, headers y versionado de API si el contrato los expone.

## Patrón de implementación

```text
Spec OpenAPI → fixtures/DTOs → tests de adapter → smoke real BFF → trazabilidad de versiones.
```

## Decisiones y anti-patrones

- No copiar responses de producción con PII para fixtures.
- No asumir que compilar el tipado TS demuestra compatibilidad REST.
- No usar mock local como prueba de autorización BFF.
- No crear un API en Angular para que “cuadre” el contrato.

## Verificación / Definition of Done

- Contract tests HTTP con fixtures/version OpenAPI referenciada.
- `npm run test`, `npm run test:security`, `npm run typecheck`.
- Informar cobertura de operaciones y faltantes de prueba integrada real.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
