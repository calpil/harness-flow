---
name: pipeline-hygiene
description: Revisar o extender CI Angular Azure DevOps separando build/test de provisioning y despliegue. Úsala para templates ADO, artefactos, caché y verificaciones.
---

# Pipeline Hygiene — CALPIL Angular Golden Path

## Objetivo y activación

Promover cambios con gates reproducibles sin convertir pipeline de app en plataforma Azure.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `pipelines/deploy.yml`, `.azuredevops/scripts/*`, `package.json`.
- `docs/platform/deployment-contract.md`, `docs/development/branching.md`, `docs/maintenance/releases.md`.
- `.npmrc`, `Dockerfile`, `.githooks/*`, `.calpil/*`.

## Procedimiento ejecutable

1. Define responsabilidad del pipeline: validar código, probar, construir bundle/imagen y publicar artefactos.
2. Mantén provisionamiento (Front Door/WAF, AKS, VNet, App Reg, PostgreSQL, Key Vault) en repos/pipelines de plataforma.
3. Instala Node 24 del agente y autentica Artifacts con `npmAuthenticate@0`; nunca PAT en YAML, variables públicas o capas Docker.
4. Cachea contenido npm por lockfile; `npm ci` debe permanecer determinístico; no cachear node_modules ciegamente.
5. Ejecución mínima de quality gates: format:check, lint, typecheck, architecture/skills, security, tests, build prod.
6. E2E Playwright con Chromium/Firefox se ejecuta sobre build development/bypass controlado; no confundir con prueba SSO real.
7. Publica reportes JUnit/evidencia en errores, y web-bundle cuando pasa; no ocultar fallos con `continueOnError` arbitrario.
8. Construye OCI usando BuildKit secret autenticado; no exponer logs de credenciales.
9. Delimita SAST/SCA/SBOM y promotion/deploy como gates de plataforma integrados, no duplicación informal.
10. Revisa condiciones de PR/branch, timeouts, trazabilidad del commit, tags de imagen y rollback documentado.
11. Declara ruta de soporte para errores de feed, npm o agente sin hacer bypass de controles.

## Patrón de implementación

```text
CI aplicación: checkout → Node → npmAuthenticate → npm ci → validate → e2e → bundle/OCI
CD plataforma: policy/scans → promote digest → variables runtime → deploy AKS → smoke
```

## Decisiones y anti-patrones

- Evitar pipeline que levante redes y bases para cada PR.
- Nunca usar `npm install` como sustituto de `npm ci` en CI.
- No deshabilitar test:architecture/test:security por falsos positivos sin investigación.
- No mezclar autenticación a Artifacts con ACR/AKS o Entra SPA.

## Verificación / Definition of Done

- Ejecutar validadores Node; inspeccionar YAML/condiciones y artefactos.
- Un PR de pipeline necesita prueba del pipeline CI corporativo, además de sintaxis local.
- Reportar qué pasos dependen de Azure DevOps y no pudieron ejecutarse localmente.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
