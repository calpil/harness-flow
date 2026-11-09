---
name: debug-targeted
description: Diagnosticar errores Angular concretos de build, runtime, DI, MSAL, BFF y tests. Úsala cuando aparece un stacktrace, síntoma o regresión.
---

# Debug Targeted — CALPIL Angular Golden Path

## Objetivo y activación

Resolver la causa raíz con cambio acotado, sin un refactor oportunista ni debilitar gates.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- Stacktrace/log íntegro sin secretos, comando, ambiente y archivo exacto.
- `package.json`, `tsconfig.json`, `angular.json`, fuente y spec relacionada.
- Para auth revisar `docs/security/sso-integration.md`; para runtime `docs/platform/configuration.md`; para arquitectura validador.

## Procedimiento ejecutable

1. Reproduce en la menor operación posible: `npm run typecheck`, spec dirigida, `ng build`, ruta y request.
2. Clasifica: dependencia/feed, import/typecheck, template Angular, DI provider, runtime config, auth token, BFF, navegador, pipeline.
3. Formula dos o tres hipótesis refutables y recopila evidencia concreta: línea, provider scope, request, response, token metadata sanitizada.
4. Traza desde evento usuario hasta owner de falla; no edites 10 archivos antes de aislar.
5. Para DI, revisar factories `deps`/injection context; el template ya corrigió instancia HTTP manual con dependencias explícitas.
6. Para MSAL, separar login, scope, audience y autorización backend; no “arreglar” cambiando valores arbitrarios.
7. Aplica parche mínimo, agrega prueba de regresión que fallaba, vuelve a correr comando original.
8. Ejecuta gate adicional correspondiente a frontera tocada (security/architecture/e2e).
9. Reporta causa raíz, fix, pruebas y riesgos remanentes; si falta feed/tenant aclara bloqueo.
10. Evita silencios de error y falsos fallbacks que escondan el incidente.

## Patrón de implementación

```text
Síntoma → evidencia → hipótesis → prueba de reproducción → cambio mínimo → regression → gates → informe.
```

## Decisiones y anti-patrones

- Nunca comentar tests, `skip`, bajar TypeScript strictness ni bloquear errores de compilación con `any` indiscriminado.
- No modificar login si el 401 está generado por audience BFF sin evidencia.
- No suponer que npx descarga versión aprobada cuando falta paquete privado.

## Verificación / Definition of Done

- Reproducción inicial, regression test, ejecución de script original y `npm run test:architecture`.
- Si hay incertidumbre informar hipótesis en vez de afirmar causalidad.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
