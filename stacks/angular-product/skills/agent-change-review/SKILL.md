---
name: agent-change-review
description: Revisar PRs generados por agentes de IA en Angular con controles de arquitectura, seguridad, contrato y calidad. Úsala antes de aceptar cambios de Copilot/Claude.
---

# Agent Change Review — CALPIL Angular Golden Path

## Objetivo y activación

El agente debe justificar alcance y evidencia; un diff generado no equivale a una implementación correcta.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `AGENTS.md`, `docs/ai/REVIEW_CHECKLIST.md`, `docs/ai/DEFINITION_OF_DONE.md`.
- `package.json`, reglas `.github/instructions/`, `.azuredevops/scripts/check-architecture.mjs`.
- Archivos modificados, tests y documentos contractuales relacionados.

## Procedimiento ejecutable

1. Lee intención funcional original y compara con diff efectivo; identifica cambios no solicitados y archivos de configuración sensibles.
2. Revisa imports/feature boundaries, ownership y si se creó abstracción sin uso o se mezcló infraestructura de plataforma.
3. Busca shortcuts: `any`, `as` sin parsing, `skip`, `continueOnError`, stores globales, silencios de error o URLs inventadas.
4. Revisa flujo completo UI→service→port→adapter→BFF; autenticación y permisos server-side.
5. Comprueba DS exports reales y contratos de runtime-config, documentación de nuevas variables y zero secrets.
6. Evalúa errores/loading/empty/disabled, teclado, responsive y tiempo de respuesta para pantallas.
7. Revisa cobertura en pruebas específicas y tests de regresión; verifica que los scripts se ejecutaron realmente.
8. Distingue observaciones P0 bloqueante, P1 corregir, P2 mejora; incluye ruta y línea cuando exista.
9. Solicita plan de rollback para cambios contractuales o dependencias/infra.
10. Entrega aprobación razonada o no-aprobación con fixes concretos, incertidumbres y pruebas faltantes.

## Patrón de implementación

```text
Revisión reportada: prioridad · evidencia (archivo/línea) · impacto · corrección mínima · test de aceptación.
```

## Decisiones y anti-patrones

- No aprobar solo por lint verde.
- No asumir seguridad porque se usa MSAL o DS.
- No reescribir todo el repo como respuesta a un hallazgo puntual.
- No aceptar alucinaciones de package exports/URLs, ni afirmar E2E real no ejecutado.

## Verificación / Definition of Done

- `npm run test:architecture`, `npm run test:security`, specs dirigidos; `npm run validate` para PR transversal.
- Validación manual de contratos y de scoping de providers.
- Checklist de riesgo residual, dependencias externas y evidencia disponible.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
