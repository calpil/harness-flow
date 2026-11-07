---
name: container-build
description: Construir imagen OCI Next.js standalone con private registry por secreto temporal, runtime non-root y probes AKS.
---

# Container Build — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `Dockerfile`
- `.dockerignore`
- `next.config.mjs`
- `scripts/test-dockerfile.mjs`
- `docs/platform/deployment.md`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

- Referencia detallada: [guía concreta](./references/container-security.md).

## Procedimiento ejecutable

1. Confirmar output standalone, existencia public/config runtime y archivos copiados.
2. Separar deps/build/runtime y validar base images Node24 compatibles; no copiar node_modules host.
3. Usar BuildKit --secret id=npmrc; .npmrc y .env quedan excluidos del contexto Docker.
4. Correr como node non-root, revisar healthcheck readiness, graceful shutdown y exposición de puertos.
5. Probar sin secret (debe fallar temprano) y con secret autorizado (npm ci); nunca embedder token en layer.
6. Documentar image tag inmutable, scanner SCA y dependencia de Azure Artifacts sin afirmar rollout.

## Patrón de implementación

Dockerfile actual instala con mount secret /root/.npmrc required=true y copia .next/standalone en runtime.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No ARG TOKEN, ENV PAT ni COPY .npmrc.
- No correr root en runtime.
- No mezclar provisioning ACR/AKS con Dockerfile.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
node scripts/test-dockerfile.mjs
npm run test:repo-hygiene
npm run build
```

- Código/contrato probado bajo las capacidades efectivamente disponibles; distinguir comandos ejecutados, fallidos y pendientes.
- Sin nuevas violaciones de import graph, secretos, traducciones o accesibilidad relacionadas al cambio.
- Los cambios de login, BFF, DS privado y entorno AKS precisan validación integrada fuera de tests mock.

## Contrato de entrega del agente

1. Explicar archivos cambiados y responsabilidad de cada capa.
2. Declarar habilidades activadas, alternativas descartadas, contratos y permisos requeridos.
3. Registrar pruebas con comando y resultado real; cualquier requisito no verificado queda explícito.
4. Incluir riesgos/rollback para cambios de SSO, build, deploy o compatibilidad entre features.

## Guía adicional existente (preservada)

# Container Build

Use this skill for Dockerfile, local container build, private npm dependencies, OCI hardening or runtime-image changes.

## Private npm dependencies

`@calpil-ds/*` is served from a private registry. Build authentication is a build-time secret.

Required pattern:

```text
build client/pipeline -> BuildKit secret (npmrc) -> npm ci RUN only
```

Never pass npm/PAT credentials through:

- Docker `ARG`;
- Docker `ENV`;
- committed `.npmrc`;
- `COPY .npmrc`;
- generated files copied into later stages.

Use `RUN --mount=type=secret,...` for the dependency-install instruction.

## Build stages

- Node major must match `package.json`.
- Install full dependencies needed to compile in deps/build stage.
- Build Next.js with `output: 'standalone'`.
- Runtime stage contains only standalone output/static/public assets actually required.
- Runtime executes as non-root.
- Never copy source, tests, dev tooling or npm credentials to runtime.

## Optional assets

Do not make the image fail merely because optional `public/` is absent. Establish a deterministic repository/build-stage convention.

## Health

Container readiness must use the actual Next.js endpoint:

```text
/api/health/readiness
```

Do not copy Java/Spring `/actuator/health` conventions into this workload.

## Pipeline ownership

Do not duplicate platform deployment logic in the application repo. Align the Dockerfile's expected BuildKit secret ID with the shared pipeline contract.

## Validation

When Docker is available, verify:

- private dependencies resolve with secret supplied;
- build fails clearly without required authentication;
- final image has no `.npmrc`/token;
- `docker history` contains no credential;
- runtime user is non-root;
- readiness healthcheck is correct.
