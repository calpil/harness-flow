---
name: prepare-release
description: Preparar release Angular con checklist de calidad, seguridad, integración SSO/BFF, imagen y rollback. Úsala antes de tag/promoción a nonprod o prod.
---

# Prepare Release — CALPIL Angular Golden Path

## Objetivo y activación

Entregar release reproducible y declarar qué fue validado de verdad y qué queda a cargo de plataforma.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `docs/maintenance/releases.md`, `CHANGELOG.md`, `TEMPLATE_VERSION`, `package.json`.
- `docs/platform/deployment.md`, `docs/platform/deployment-contract.md`, `SECURITY.md`.
- `pipelines/deploy.yml`, `Dockerfile`, `config/runtime-config.template.json`.

## Procedimiento ejecutable

1. Congela scope/cambios y evalúa breaking changes de runtime-config, scopes, contrato API o DS.
2. Revisa versión, changelog, migraciones de features, ADR y documentación que cambió.
3. Ejecuta `npm run validate`, `npm run test:e2e` y comprobaciones manuales de journeys si ambiente disponible.
4. Confirma dependencias privadas, CVEs, secretos, provenance/artifact digest y calidad de container.
5. Solicita evidencia de QA de SSO real: login/logout, refresh, issuer/aud/scope y BFF 401/403; no confundir con Playwright bypass.
6. Prueba variables runtime específicas del ambiente y endpoints allowlisted con mismo build digest.
7. Verifica ownership de deploy/rollback en plataforma y probes health/ready/SPA fallback.
8. Establece señales de éxito y rollback ante errores 5xx/autenticación, no solo despliegue verde.
9. Publica nota de release con evidencias, aprobaciones, riesgos y limitaciones.
10. Bloquea promoción si faltan gates críticos o datos productivos/credenciales aparecen en frontend.

## Patrón de implementación

```text
READY = calidad + contrato + seguridad + observabilidad + operacionalización + rollback.
```

## Decisiones y anti-patrones

- No llamar productivo al mock local.
- No saltar verificaciones `test:security`, `test:architecture` o revisión de tokens.
- No añadir provisioning dentro del pipeline de app para agilizar un release.
- No declarar SSO real probado si no se ejecutó contra tenant.

## Verificación / Definition of Done

- Evidencia CI, tests, build, imagen + scans corporativos.
- Sign-off del dueño BFF/Entra y plataforma cuando el cambio toca sus contratos.
- Plan de rollback/redeploy del digest anterior documentado.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
