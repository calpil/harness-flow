---
name: add-page-route
description: Crear o modificar rutas/layouts App Router, composición server-first, navegación, protección, metadata y boundaries por feature.
---

# Add Page Route — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/app/(portal)/layout.tsx`
- `src/app/(public)/ y src/app/api/`
- `proxy.ts`
- `src/server/auth/session.ts`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Distinguir página, layout, route group, dynamic segment o Route Handler: no confundir rutas de producto con APIs.
2. Definir acceso público/privado y RBAC; proteger con requireSession en servidor y roles donde corresponde.
3. Mantener page.tsx como composition root delgado; invocar caso de uso sin meter reglas de negocio.
4. Elegir Server Component de forma predeterminada; mover solo controles interactivos a módulo con use client.
5. Diseñar metadata, traducciones, estados not-found/loading/error y navegación directa/deep links.
6. Para Route Handler solo auth, salud o servicios de infraestructura explícitamente autorizados.
7. Agregar pruebas de navegación/autorización y revisar no fuga de server code hacia navegador.

## Patrón de implementación

src/app/(portal)/.../page.tsx: await requireSession(); return <FeaturePage />. Para browser-only: UI aislada en src/features/<feature>/ui/* con directiva use client.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No endpoints BFF ni APIs de negocio en src/app/api.
- No confiar en cookie de proxy como autorización real.
- No usar use client en layout completo para resolver un solo widget.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:architecture
npm run test:component
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
