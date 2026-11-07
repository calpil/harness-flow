---
name: dependency-review
description: Revisar upgrades o nuevas dependencias Angular, MSAL, DS, TypeScript y tooling privado. Úsala antes de instalar, actualizar o remover paquetes.
---

# Dependency Review — CALPIL Angular Golden Path

## Objetivo y activación

Controlar compatibilidad y supply chain de forma reproducible, sin upgrades masivos ciegos.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `package.json`, `package-lock.json`, `docs/development/versions.md`, `docs/development/dependencies.md`.
- `angular.json`, `tsconfig.json`, `eslint.config.js`.
- `.npmrc` (registry sin secrets) y `docs/ui/design-system.md`.

## Procedimiento ejecutable

1. Define problema que la dependencia resuelve y verifica si el stack existente ya ofrece la capacidad.
2. Revisa compatibilidad Angular 22, compiler, TS ~6, Node 24/npm 11, MSAL browser v5 y DS privado declarado.
3. Verifica support policy, maintenance, licencia, advisories, peer deps, bundle y árbol transitivo.
4. Si es DS privado, consulta exports e instalación autorizada antes de asumir API.
5. Evalúa impacto a zonas sin Zone.js, standalone components, tooling de test Karma/Playwright.
6. Cambia dependencias con `npm ci` reproducible (al generar lock `npm install` controlado), no edites lock a mano.
7. Añade/ajusta tests críticos en compatibilidad y build.
8. Evita versiones floating; justificar excepción de rangos para paquetes propios.
9. Documenta riesgo, cambio, rollback, y plan para advisories transitorios.
10. No descargar binarios ni runtimes Node dentro del repositorio.

## Patrón de implementación

```text
Decisión: problema → alternativas nativas → compatibilidad → riesgo → diff lock → tests → rollback.
```

## Decisiones y anti-patrones

- No `--force` o `--legacy-peer-deps` por defecto.
- No mezclar actualización de Angular major con feature de negocio en el mismo PR.
- No publicar tokens de Artifacts ni introducir npmrc autenticado en repositorio.
- No introducir dependencia de UI que duplique @calpil-ds/angular.

## Verificación / Definition of Done

- `npm ci`, `npm run typecheck`, `npm run validate`, E2E de rutas críticas.
- Evidencia de versión instalada/resolved y advisories, además de build prod real cuando existe feed.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
