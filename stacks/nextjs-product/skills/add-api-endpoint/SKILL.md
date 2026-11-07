---
name: add-api-endpoint
description: Evaluar solicitudes de APIs y Route Handlers sin convertir este frontend Next.js en BFF de negocio; establecer integraciones autorizadas.
---

# Add Api Endpoint — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/app/api/auth/`
- `src/app/api/health/`
- `src/server/`
- `docs/architecture/overview.md`
- `src/server/auth/session.ts`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Clasificar el endpoint solicitado: autenticación, probe, prueba aislada, proxy técnico genérico hacia BFF externo o API de negocio.
2. Si es API funcional de negocio, detener creación en Next.js y proponer contrato para NestJS BFF externo. Si es proxy técnico `clientDirect=false`, reutilizar el Route Handler genérico existente y la fachada `bff-client.ts`; validar destinos permitidos, SSRF, session/auth/CSRF, propagación de métodos/headers y respuestas sin transformación de dominio.
3. Si es permitido, especificar método, ruta, validación, identidad, autorización, errores y cache.
4. Usar getSession para devolver 401 JSON; nunca requireSession con redirect dentro de Route Handler.
5. Prohibir reenvío de secretos/tokens a navegador; evaluar SSRF al consumir URLs externas.
6. Agregar tests de métodos incorrectos, 401, 403, entradas inválidas y exfiltración de error.
7. Documentar ownership: Next.js frontend, BFF NestJS y API de dominio/Java separados.

## Patrón de implementación

Rutas de frontend permitidas: src/app/api/auth/_, src/app/api/health/_, seam E2E controlado y **proxy BFF técnico genérico** (identificar ruta real, no inventar una segunda). Integración browser: `bff-client.ts` → BFF público si `clientDirect=true`; `bff-client.ts` → proxy técnico Next.js → BFF privado si `false`. Integración iniciada en servidor: transporte server-side del cliente central → BFF. Nunca servidor de negocio improvisado.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No CRUD de dominio en src/app/api.
- No retornar stack traces ni refresh/access tokens.
- No reemplazar reglas de producto por un endpoint proxy opaco.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:architecture
npm run test:unit
npm run test:security
```

- Código/contrato probado bajo las capacidades efectivamente disponibles; distinguir comandos ejecutados, fallidos y pendientes.
- Sin nuevas violaciones de import graph, secretos, traducciones o accesibilidad relacionadas al cambio.
- Los cambios de login, BFF, DS privado y entorno AKS precisan validación integrada fuera de tests mock.

## Contrato de entrega del agente

1. Explicar archivos cambiados y responsabilidad de cada capa.
2. Declarar habilidades activadas, alternativas descartadas, contratos y permisos requeridos.
3. Registrar pruebas con comando y resultado real; cualquier requisito no verificado queda explícito.
4. Incluir riesgos/rollback para cambios de SSO, build, deploy o compatibilidad entre features.

## Restricción de consistencia

Toda comunicación BFF en páginas, features y adaptadores utiliza `bff-client.ts` existente. No introducir Route Handlers por recurso de negocio ni proxies dinámicos con URL de destino controlada por el usuario. El Route Handler técnico genérico implementa únicamente transporte y no constituye BFF de negocio.
