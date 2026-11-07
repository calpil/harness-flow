---
name: domain-modeling
description: Modelar reglas puras y máquinas de estado de una feature sin Angular ni transporte. Úsala cuando aparecen entidades, agregados, invariantes y transiciones.
---

# Domain Modeling — CALPIL Angular Golden Path

## Objetivo y activación

Extraer semántica funcional durable y protegerla con tests independientes del framework.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `src/app/features/work-items/domain/{work-item.ts,work-item-status.ts,errors.ts,work-item.spec.ts}`.
- `docs/architecture/overview.md`, `docs/adr/0001-architecture-profile.md`.
- Skill `add-feature` para completar adaptación y UI.

## Procedimiento ejecutable

1. Extrae lenguaje de negocio y ubica aggregate root/identidad, snapshots y reglas de transición reales.
2. Decide qué necesita entidad con comportamiento vs type/value object simple; no inventar clases donde un type basta.
3. Implementa dominio TS puro, sin DI/Angular/RxJS/HttpClient/sessions.
4. Normaliza inputs en frontera de creación (`trim`, longitud, ISO) y define errores intencionales.
5. Considera estado inicial, estado terminal, cambio idempotente y transiciones inválidas explícitas.
6. Para persistencia API, separa snapshot/DTO y define rehydrate solo si invariante validada por frontera.
7. Versionado y timestamps tienen semántica de ownership: backend decide versión, cliente no debe falsificar concurrencia.
8. Evita setters indiscriminados; comandos exponen acciones del negocio.
9. Prueba tabla de transición completa, bordes y estado resultante.
10. No utilizar reglas del DOM, flags de vista ni claims de usuario como verdad funcional.

## Patrón de implementación

```ts
const TRANSITIONS = {
  TODO: ['IN_PROGRESS', 'CANCELLED'],
  IN_PROGRESS: ['DONE', 'CANCELLED', 'TODO'],
  DONE: [],
  CANCELLED: [],
} as const;
```

En este template Work Items es un ejemplo, no política general de estados CALPIL.

## Decisiones y anti-patrones

- No añadir repositorios en domain.
- No meter tokens Entra, rutas REST, traducción ni estilos en entidad.
- No usar enum abierto para estado sin contrato BFF.
- No copiar `WorkItem` como modelo genérico sin renombrar conceptos.

## Verificación / Definition of Done

- `npm run test` con specs domain; `npm run test:architecture` y typecheck.
- Confirmar que las reglas se mantienen iguales bajo adaptador HTTP/in-memory.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
