---
name: container-build
description: Mantener build Docker multi-stage Angular y Nginx SPA seguros, con npm privado vía secret y config runtime. Úsala para imagen, healthcheck, CSP y bugs de despliegue.
---

# Container Build — CALPIL Angular Golden Path

## Objetivo y activación

Garantizar que imagen sea reproducible, no-root y portable entre ambientes; imagen de app no provisiona infraestructura.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `Dockerfile`, `.dockerignore`, `nginx.conf`, `scripts/docker-entrypoint.sh`.
- `config/runtime-config.template.json`, `docs/platform/deployment.md`, `pipelines/deploy.yml`.
- `package.json` / lockfile; .npmrc SIN credenciales persistidas.

## Procedimiento ejecutable

1. Diagnostica fase: npm ci feed, build Angular, copy dist, nginx startup, envsubst, health, SPA fallback.
2. Usa multi-stage: Node 24 build, Nginx runtime mínimo; respeta dist real de `angular.json`.
3. Usa BuildKit secret para autenticación npm del build y `.dockerignore` que excluye `.npmrc`; verifica que no quede token en imagen/capas.
4. Mantén lockfile estricto `npm ci`, no `npm install` implícito de build.
5. Runtime non-root (puerto 8080) con FS read-only compatible y rutas temporales de Nginx.
6. Genera `/assets/runtime-config.json` con variables `CALPIL_*` al arranque; rechaza faltantes corporate; evita rebuild por ambiente.
7. Verifica cache headers de HTML/runtime config, fallback Angular routes, healthz/readyz y CSP compatible con MSAL.
8. Usa tags/digests trazables, evita secretos en ARG/ENV y logs; SBOM/SAST/SCA son controles de la plataforma.
9. Separa imagen de implementación Helm, Front Door, DNS, Key Vault y AKS (repos externos).
10. Si pruebas sin feed corporativo no son posibles, no declare build exitoso: entrega comando y bloqueo.

## Patrón de implementación

```text
build container: npm privado autenticado → dist/app/browser
runtime container: nginx:8080 + entrypoint → config pública en /assets/
platform repo: publica imagen, inyecta CALPIL_*, routing /bff/v1/
```

## Decisiones y anti-patrones

- No incluir `.npmrc` con token en `COPY . .`; revisar context y Docker history.
- No escribir `ENV API_SECRET=...` en imagen frontend.
- No ejecutar en root en runtime por conveniencia.
- No cambiar CSP a `*` para esconder falta de orígenes/redirects documentados.
- `Dockerfile` no crea landing zone ni namespaces Kubernetes.

## Verificación / Definition of Done

- `npm run build:prod`, `npm run test:security`.
- En entorno con credenciales: `docker build --secret id=npmrc,src=<npmrc-autenticado> -t angular:test .`.
- `docker run` con variables dummy no sensibles: verificar `/readyz`, `/assets/runtime-config.json`, fallback de `/work-items/123`, respuesta de errores de arranque.
- Escanear imagen con controles corporativos antes de promover.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
