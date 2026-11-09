---
name: secure-dependency-lifecycle
description: Mantener dependencias npm con riesgo controlado, auditoria reproducible, lockfile coherente y gates de seguridad para Next.js en Azure DevOps.
---

# Secure Dependency Lifecycle — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill se activa para mantenimiento de dependencias, auditorias SCA y cambios en scripts/pipeline de actualizacion continua. El objetivo es disminuir riesgo sin romper compatibilidad de Next.js App Router, Auth.js, Design System ni contratos corporativos.

Combinar con `dependency-review`, `security-review`, `pipeline-hygiene` y `write-tests` cuando aplique.

## Inspección obligatoria

Inspeccionar solo archivos necesarios antes de editar:

- `package.json`
- `package-lock.json`
- `pipelines/deploy.yml`
- `docs/development/dependencies.md`
- `docs/maintenance/*.md`
- `AGENTS.md`
- `docs/ai/SKILL_CATALOG.md`

Verificar herramientas disponibles y conectividad de registry/audit para no reportar falsos verdes.

## Procedimiento ejecutable

1. Ejecutar discovery: `git status`, version de Node/npm, `npm config get registry`, `npm ls --all`.
2. Capturar baseline: `npm outdated --json`, `npm audit --json` y `npm audit --omit=dev --json`, conservando exit codes.
3. Priorizar por riesgo: primero CVE high/critical compatibles, luego patch/minor por lotes pequenos y majors en PR separada.
4. Actualizar `package.json` y `package-lock.json` de forma consistente sin `--force` ni `--legacy-peer-deps`.
5. Re-ejecutar auditorias y validar lockfile reproducible con `npm ci`.
6. Registrar inventario, vulnerabilidades antes/despues, overrides y riesgos residuales en `docs/audits/`.
7. Mantener automatizacion con scripts `deps:*`, pipeline con gates activos y configuracion `renovate.json` sin credenciales.

## Patrón de implementación

Mantener `package.json` como fuente de verdad y lockfile versionado. Evitar upgrades masivos no relacionados; preferir cambios trazables por categoria de riesgo.

Cuando el pipeline real depende de templates compartidos, habilitar banderas de seguridad desde el YAML local y documentar cualquier paso pendiente en plataforma.

Si el audit o registry no responde, marcar estado "no verificable" y bloquear certificacion.

## Decisiones y anti-patrones

- No usar `npm audit fix --force`, `npm install --force` ni `--legacy-peer-deps`.
- No suprimir fallos con `|| true` ni reportar "0 vulnerabilidades" sin evidencia ejecutada.
- No comitear `.npmrc` autenticado, tokens, PAT o secretos en scripts/YAML.
- No mezclar upgrade npm con provisioning de AKS/Front Door/DB/Key Vault.
- No reemplazar silenciosamente `next-auth` beta por una major distinta sin migracion formal.

## Verificación / Definition of Done

Aplicar comandos segun alcance:

```bash
npm run deps:check
npm run deps:audit
npm run deps:audit:prod
npm run deps:verify
npm run test:repo-hygiene
npm run test:skills
```

La entrega debe distinguir claramente comandos pasados, fallidos y no ejecutados.

Debe existir evidencia de baseline y resultado en `docs/audits/dependencies-YYYY-MM-DD.md`.

## Contrato de entrega del agente

1. Informar framework detectado, Node/npm usados y estado del registry/audit.
2. Enumerar dependencias cambiadas con motivo, riesgo y rollback.
3. Reportar vulnerabilidades antes/despues separando arbol completo y runtime.
4. Indicar overrides agregados/removidos/mantenidos con justificacion y fecha de revision.
5. Listar validaciones ejecutadas con salida real y pendientes por entorno corporativo.
