---
name: architecture-review
description: Auditar estructura feature-oriented, imports entre capas, boundaries, composición y deuda arquitectónica. Úsala antes de refactors, PRs grandes y creación de features.
---

# Architecture Review — CALPIL Angular Golden Path

## Objetivo y activación

Detectar violaciones reales y proponer el cambio mínimo que restituye límites sin introducir ceremonias hexagonales innecesarias.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `docs/architecture/overview.md`, `docs/adr/0001-architecture-profile.md`.
- `.azuredevops/scripts/check-architecture.mjs` (validación automática: examina imports; no cubre comportamiento/runtime).
- `tsconfig.json` (aliases); todos los archivos modificados y consumidores.
- `src/app/features/work-items/{domain,application,data-access,ui}`.

## Procedimiento ejecutable

1. Identifica feature afectada, capa que contiene decisión de negocio y consumidores reales.
2. Dibuja dependencias **de código concretas**: `ui → application → domain`, `data-access → application port/domain`; `core` para cross-cutting singleton; `shared` para reutilizables sin negocio.
3. Revisa imports relativos, aliases y exports `index.ts` buscando acoplamientos profundos o ciclos.
4. Encuentra lógica de dominio en componentes: validación de transiciones, reglas de monto, estado final, cambios de lifecycle. Muévela a `domain` y crea tests.
5. Encuentra HTTP, `localStorage`, MSAL o config directamente en vistas; extrae hacia servicio de aplicación/adaptador o `core` según ownership.
6. Verifica que providers sean scope de feature cuando mantienen estado de feature. Solo `core` registra providers singleton globales.
7. Verifica que route lazy no arrastre imports eager ni registradores globales innecesarios.
8. Distingue contaminación del código versus falsos positivos del validador; **no silenciar reglas** para pasar CI.
9. Cuando un cambio afecta contrato compartido/estructura: proponer ADR, migración y plan de compatibilidad.
10. Produce matriz hallazgo (ruta, regla, severidad, evidencia, refactor y test).

## Patrón de implementación

| Origen         | Puede usar                            | Rechazar                         |
| -------------- | ------------------------------------- | -------------------------------- |
| `domain`       | mismo dominio TS puro                 | Angular, RxJS, BFF, DS, `core`   |
| `application`  | dominio + ports                       | adapters concretos, vista        |
| `data-access`  | ports + dominio + HTTP                | UI                               |
| `ui`           | application + domain (view decisions) | data-access directamente         |
| routes feature | providers, lazy routes                | registrarse global sin necesidad |

## Decisiones y anti-patrones

- No convertir todos los folders de UI estática en hexágonos ficticios.
- `shared` no debe ser sumidero de servicios de negocio ni data-access.
- No relajar test:architecture ni crear excepciones de una sola feature sin ADR.
- Alinear cambios con los límites reales del repositorio; no imponer NgModule ni NgRx por reflejo.

## Verificación / Definition of Done

- Ejecutar `npm run test:architecture` y `npm run typecheck`; pruebas enfocadas para refactors.
- Revisión manual de ciclos/lazy boundaries porque el validador basado en imports es parcial.
- Hallazgos ordenados por impacto (seguridad/datos > arquitectura > estilo), sin declarar falsos éxitos.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
