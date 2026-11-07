---
name: pipeline-hygiene
description: Mantener separación entre CI de aplicación, despliegue corporativo y aprovisionamiento plataforma; proteger credenciales y evidencias.
---

# Pipeline Hygiene — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `azure-pipelines.yml`
- `pipelines/deploy.yml`
- `examples/application-deploy.yml`
- `Dockerfile`
- `.calpil/workload.yaml`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

- Referencia detallada: [guía concreta](./references/ci-deploy-boundary.md).

## Procedimiento ejecutable

1. Clasificar cambio en CI/test, package OCI, deploy aplicación o provisioning compartido.
2. Reutilizar Azure DevOps templates existentes; no crear Front Door/AKS/ACR/Key Vault en pipeline de frontend.
3. Instalar npm con autenticación temporal y secreto en tareas/BuildKit, nunca PAT en YAML o artefacto.
4. Mantener stage boundaries y promotion sb→np→prod conforme plataforma, no inferir permisos de suscripciones.
5. Correr test:repo-hygiene, skills, arquitectura, unit, lint y build en gates correspondientes.
6. Verificar task injection, logs sin secretos, pasos con set -e y evidencia reproducible.

## Patrón de implementación

CI actual azure-pipelines.yml valida npm ci/validate/build; pipelines/deploy.yml separa despliegue; workload.yaml es managed by platform.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No mezclar Terraform provisioning con Helm deploy aquí.
- No editar .calpil/workload.yaml generado por plataforma sin instrucción explícita.
- No persistir credenciales en artifact.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:repo-hygiene
npm run test:skills
npm run test:architecture
npm run validate
```

- Código/contrato probado bajo las capacidades efectivamente disponibles; distinguir comandos ejecutados, fallidos y pendientes.
- Sin nuevas violaciones de import graph, secretos, traducciones o accesibilidad relacionadas al cambio.
- Los cambios de login, BFF, DS privado y entorno AKS precisan validación integrada fuera de tests mock.

## Contrato de entrega del agente

1. Explicar archivos cambiados y responsabilidad de cada capa.
2. Declarar habilidades activadas, alternativas descartadas, contratos y permisos requeridos.
3. Registrar pruebas con comando y resultado real; cualquier requisito no verificado queda explícito.
4. Incluir riesgos/rollback para cambios de SSO, build, deploy o compatibilidad entre features.
