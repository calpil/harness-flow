---
name: bff-contract
description: Integrar todas las llamadas de negocio al BFF externo mediante el cliente HTTP centralizado de Next.js, respetando clientDirect, contratos, seguridad y arquitectura por features.
---

# BFF Contract — CALPIL Next.js Golden Path

## Objetivo y activación

Usar esta skill cuando una tarea modifique consumo de APIs de negocio, transporte hacia BFF, proxy técnico o adaptadores que transformen DTOs.

Regla innegociable: toda llamada de negocio al BFF debe pasar por el contrato público de `src/shared/bff/bff-client.ts`.

## Inspección obligatoria

Antes de editar, inspeccionar:

1. Implementación real de `src/shared/bff/bff-client.ts` y sus exports.
2. Configuración y resolución de `clientDirect` en runtime/build.
3. Proxy técnico permitido en `src/app/api/v1/[...bffPath]/route.ts`.
4. Consumidores actuales en `src/features/**`, `src/app/**`, hooks y acciones.
5. Reglas de arquitectura/seguridad en `AGENTS.md` y `.github/copilot-instructions.md`.
6. Contratos de API/BFF documentados para rutas, headers y códigos.

## Procedimiento ejecutable

1. Inventariar llamadas al BFF y distinguir integraciones no-BFF (Auth.js, terceros, recursos estáticos).
2. Corregir primero el contrato central (`bff-client.ts`) antes de tocar consumidores.
3. Mantener selección de transporte según `clientDirect` sin crear flags paralelos.
4. Para `clientDirect=true`, enrutar browser al BFF público autorizado, sin secretos ni hosts internos.
5. Para `clientDirect=false`, enrutar browser al proxy técnico genérico y de allí al BFF autorizado.
6. En ejecución server-side, usar transporte server-only del contrato sin self-fetch innecesario a Next.js.
7. Preservar semántica HTTP: método, path, query, body, status, content type y headers permitidos.
8. Propagar estados de error relevantes (401/403/404/409/422/429/5xx), incluyendo 204 y payloads binarios.
9. Reforzar seguridad: allowlist de destinos, anti-SSRF y no forward indiscriminado de credenciales.
10. Ejecutar pruebas dirigidas y validaciones existentes antes de cerrar la tarea.

## Patrón de implementación

Patrón recomendado por capas:

- UI y composición invocan casos de uso de `application`.
- `application` define puertos y no conoce transporte HTTP.
- `infrastructure` mapea DTOs y delega transporte a `bff-client.ts`.
- El proxy técnico es transparente y no implementa reglas de dominio.

Matriz mínima de verificación funcional:

- Browser + `clientDirect=true` -> BFF público.
- Browser + `clientDirect=false` -> proxy técnico -> BFF.
- Server Component/Action -> transporte server-side del contrato.

## Decisiones y anti-patrones

- No crear un segundo cliente BFF por feature.
- No usar `fetch`, `axios` o `ky` directo al BFF fuera del contrato autorizado.
- No convertir Route Handlers en backend CRUD de dominio.
- No reenviar `id_token` como bearer para negocio.
- No hardcodear URLs BFF ni exponer hosts internos en frontend.
- No usar fallback silencioso a mocks ante errores reales del BFF.

## Verificación / Definition of Done

Se considera completado cuando:

- El consumo de negocio del BFF está centralizado en `bff-client.ts`.
- `clientDirect=true/false` funciona según contrato sin romper límites server/client.
- El proxy técnico conserva semántica HTTP y controles anti-SSRF.
- No quedan consumidores BFF fuera del contrato permitido.
- Las pruebas ejecutadas respaldan los recorridos modificados.

Comandos típicos (si aplican al alcance):

```bash
npm run test:unit
npm run test:component
npm run test:architecture
npm run lint
npm run build
```

## Contrato de entrega del agente

1. Informar qué consumidores BFF se tocaron y por qué.
2. Indicar cómo quedó la selección de transporte para `clientDirect`.
3. Reportar pruebas/validaciones ejecutadas con resultado real.
4. Declarar riesgos y dependencias externas pendientes (CORS, scopes, permisos).
5. Confirmar explícitamente que no se creó un BFF de negocio en `src/app/api`.

## Referencia

- Checklist de integración: [./references/bff-integration-checklist.md](./references/bff-integration-checklist.md)
