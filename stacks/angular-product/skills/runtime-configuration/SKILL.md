---
name: runtime-configuration
description: Cambiar configuración pública y despliegue multiambiente Angular sin rebuild. Úsala para nuevas URLs BFF, scopes SPA, flags y parámetros de producto.
---

# Runtime Configuration — CALPIL Angular Golden Path

## Objetivo y activación

Respetar contrato runtime validado antes de bootstrap. Un mismo bundle debe operar en sandbox/nonprod/prod mediante variables públicas y sin secretos.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `docs/platform/configuration.md`, `config/configuration.contract.yaml` y `config/runtime-config.template.json`.
- `src/app/core/config/runtime-config.ts`, `src/main.ts`, `src/app/core/config/app-config.ts`.
- `scripts/docker-entrypoint.sh`, `src/assets/runtime-config.json`, `scripts/check-security-config.mjs`.
- `src/app/core/config/runtime-config.spec.ts` y docs de deployment.

## Procedimiento ejecutable

1. Clasifica la propiedad: pública de navegador, secreta de backend, feature flag o infraestructura externa. Solo la primera puede vivir en JSON de Angular.
2. Define nombre, tipo, default seguro, validación, ambientes permitidos, dueño y consumidor real.
3. Modifica interfaz `RuntimeConfig` + `parseRuntimeConfig`, incluyendo validación semántica/host/longitud; evita `any` y coerciones silenciosas.
4. Añade clave a `config/runtime-config.template.json` y `src/assets/runtime-config.json` (local) con valores seguros.
5. Ajusta `scripts/docker-entrypoint.sh` para variables `CALPIL_*` y `docs/platform/configuration.md`; evita duplicación manual entre ambientes.
6. Asegura que `loadRuntimeConfig()` siga ejecutándose antes de `bootstrapApplication` y que APP_CONFIG sea la única vía de consumo.
7. Para APIs protegidas: registra únicamente endpoints y scopes específicos y amplía **allowlist de interceptor** con tests.
8. Verifica same-origin para sandbox/nonprod/prod; local admite host local según contrato; nunca relajar globalmente por conveniencia.
9. Crea tests de input válido, ausente, malicioso, entorno no local sin API/scope y fuga de secreto.
10. Mantén un artefacto OCI idéntico promovido entre ambientes; no editar JS bundle durante deploy.
11. Coordina cambios de variables con pipeline de deploy de plataforma, sin provisionar Key Vault/Front Door/AKS desde este repo.

## Patrón de implementación

```text
Variable de arranque → scripts/docker-entrypoint.sh →
/assets/runtime-config.json → loadRuntimeConfig() → APP_CONFIG → feature.
```

No hay acceso a variables de contenedor después de cargar el navegador.

## Decisiones y anti-patrones

- No `environment.prod.ts` para URLs/tenants de negocio; ese archivo solo contiene flag compile-time anti-bypass.
- No leer `process.env` en Angular runtime de navegador.
- JSON de `/assets/runtime-config.json` es públicamente accesible: NUNCA secrets, PAT, tokens o connection strings.
- Nada de URLs wildcard para scopes/access tokens.
- No introducir fallback silencioso a demo en nonprod/prod.

## Verificación / Definition of Done

- `npm run test:security`, `npm run typecheck`, tests de `runtime-config.spec.ts`.
- En contenedor verificar que nuevas variables produzcan JSON válido y se sirvan sin caché.
- Probar promote de misma imagen con 2 configuraciones diferentes y observar rutas efectivas sin exponer credenciales.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
