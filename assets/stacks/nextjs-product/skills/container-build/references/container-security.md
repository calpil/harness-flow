# Build reproducible y seguro

- `npm ci` necesita `@calpil-ds/react` en Azure Artifacts privado.
- Dockerfile usa `RUN --mount=type=secret,id=npmrc,target=/root/.npmrc,required=true npm ci`.
- `docker build --secret id=npmrc,src=.npmrc ...` acepta credencial LOCAL sin COPY, ARG ni ENV en layers.
- `.dockerignore`: excluir `.npmrc`, `.env`, `.git`, `node_modules`, cache.
- Runtime `node:24-slim`, no-root, `standalone`, puerto 3000 y `/api/health/readiness`.
- La imagen no provisiona ACR, Front Door, AKS, networking o Key Vault.
- No subir exportaciones, logs ni zip que contengan `.npmrc`; revocar tokens expuestos.
