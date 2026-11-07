---
name: secure-dependency-lifecycle
description: Ejecutar ciclo seguro de mantenimiento npm (inventario, SCA por umbral, lockfile reproducible, Renovate y gates CI) sin exponer secretos ni romper compatibilidad.
---

# Secure Dependency Lifecycle — CALPIL Angular Golden Path

## Objetivo y activación

Establecer mantenimiento de dependencias npm repetible y seguro para este template Angular.

Usa esta skill cuando la tarea incluya auditorías de dependencias, upgrades controlados, scripts `deps:*`,
hardening de `.npmrc`, integración de gate CI o preparación de Renovate en Azure DevOps.

## Inspección obligatoria

- `package.json`, `package-lock.json`, `.npmrc`, `.npmrc.example`.
- `pipelines/deploy.yml` y `.azuredevops/scripts/*`.
- `docs/development/{dependencies,versions}.md`, `docs/maintenance/*.md`, `docs/audits/*.md`.
- `AGENTS.md`, `.github/copilot-instructions.md`, `docs/ai/SKILL_CATALOG.md`.
- `renovate.json` (si existe) o ausencia explícita de configuración.

## Procedimiento ejecutable

1. Auditar baseline real: framework, engines Node/npm, dependencias directas y flujo actual de CI.
2. Verificar que no haya credenciales en `.npmrc` ni en docs/scripts de mantenimiento.
3. Crear/ajustar scripts `deps:check`, `deps:audit`, `deps:audit:prod`, `deps:verify` con umbrales explícitos.
4. Asegurar que `deps:check` sea diagnóstico (no bloqueante por simple desactualización).
5. Hacer que `deps:audit` falle en `high/critical` y `deps:audit:prod` falle en `moderate+`.
6. Encadenar `deps:verify` en CI para bloquear cuando el estado SCA no es verificable.
7. Mantener lockfile reproducible con `npm ci`; no usar `--force` ni `--legacy-peer-deps`.
8. Configurar Renovate con `automerge: false`, lotes coherentes y exclusión de prereleases.
9. Documentar límites operativos (feed privado, Entra, conectividad, agente CI) sin inventar resultados.
10. Registrar hallazgos en `docs/audits/dependencies-YYYY-MM-DD.md`.

## Patrón de implementación

```text
baseline real -> scripts deps:* -> gate pipeline -> renovate sin secretos -> auditoría documentada
```

## Decisiones y anti-patrones

- No guardar token/PAT/correo real en `.npmrc` ni `renovate.json`.
- No editar `package-lock.json` manualmente.
- No usar `npm audit fix --force` en CI ni esconder errores con `|| true`.
- No mezclar upgrade major de framework con cambios funcionales de negocio.
- No declarar “0 vulnerabilidades” si audit/registry falló o no estuvo disponible.

## Verificación / Definition of Done

- Scripts `deps:*` disponibles y referenciados en documentación.
- Pipeline ejecuta gate de dependencias antes de pasos de release/build.
- Renovate preparado (si aplica al hosting) sin auto-merge ni secretos en repo.
- Audit documentado con resultados reales o bloqueo explícito.
- `npm run test:architecture` y `npm run test:skills` pasan cuando el entorno tiene Node/npm disponibles.

## Contrato de entrega del agente

- Reportar archivos tocados y motivo de cada cambio.
- Diferenciar comandos ejecutados vs. no ejecutados/bloqueados.
- Indicar riesgos residuales (advisories, lockfile, feed privado, CI corporativo).
- No afirmar certificación productiva si faltan credenciales o pruebas reales de infraestructura.
