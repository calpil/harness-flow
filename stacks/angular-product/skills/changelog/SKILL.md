---
name: changelog
description: Actualizar CHANGELOG por commit con fecha, formato estable y evidencia verificable del cambio. Úsala al cerrar tareas, PRs o fixes pequeños.
---

# Changelog — CALPIL Angular Golden Path

## Objetivo y activación

Mantener `CHANGELOG.md` como registro confiable y auditable: cada commit funcional debe dejar una entrada clara, fechada y trazable.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `prepare-release` y `write-tests`. **No inventes** cambios, hashes, resultados de pruebas ni validaciones no ejecutadas.

## Inspección obligatoria (lectura selectiva)

- `CHANGELOG.md`, `TEMPLATE_VERSION`, `package.json`.
- `git --no-pager log --oneline -n <N>` del rango a documentar.
- Diff real (`git --no-pager diff` o archivos tocados) para no resumir en falso.
- `README.md` y docs modificadas por el commit (si aplica).

## Procedimiento ejecutable

1. Determina el alcance exacto del commit: feature, fix, refactor, docs, test, chore o seguridad.
2. Usa fecha real en formato `YYYY-MM-DD` (zona local del autor de commit).
3. Mantén el formato de encabezado existente: `## [<version|Unreleased>] - <fecha>`.
4. Si no hay versión de release cerrada, agrega o reutiliza `## [Unreleased] - <fecha-actual>` en la parte superior.
5. Añade una línea por commit con estructura recomendada:
   `- <tipo(scope)>: <resultado visible y concreto> (commit <sha-corto>)`.
6. Describe resultados observables, no acciones internas vagas (evita “se cambió código”).
7. Incluye impacto técnico relevante cuando corresponda: seguridad, arquitectura, contrato BFF, runtime config o DX.
8. Si el commit modifica varios frentes, divide en 2-4 bullets cortos en lugar de un párrafo ambiguo.
9. No mezcles trabajo no mergeado ni suposiciones de otros branches.
10. Si no puedes resolver el `sha` localmente, deja el bullet sin hash y marca bloqueo explícito en la entrega.
11. Antes de cerrar, valida consistencia con Conventional Commits y que la entrada apunte al cambio real.

## Patrón de implementación

```markdown
## [Unreleased] - 2026-10-18

- chore(dev): unifica bootstrap local PowerShell/Unix y genera `.env.local` automáticamente (commit 54b8721)
- feat(runtime): agrega `start:local` con bootstrap automático cuando falta `.env.local` (commit 54b8721)
```

El patrón es orientativo; adapta tipo/scope al commit real.

## Decisiones y anti-patrones

- No escribir changelog “por lote” semanas después si la solicitud pide trazabilidad por commit.
- No registrar “tests pasaron” si no se ejecutaron en ese entorno.
- No repetir título del commit sin contexto funcional.
- No borrar historial previo para “ordenar”; solo anexar/corregir de forma explícita.
- No usar fechas ambiguas (`18/10/26`); usar siempre `YYYY-MM-DD`.

## Verificación / Definition of Done

- `CHANGELOG.md` contiene entrada nueva con fecha válida y formato consistente.
- Cada bullet nuevo refleja cambios realmente presentes en el diff/commit.
- Si cambió skill/docs de skills, ejecutar `npm run test:skills`.
- Si hubo cambios funcionales de app, referenciar en entrega los comandos corridos (arquitectura, seguridad, tests, etc.).

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
