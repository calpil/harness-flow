---
name: routing-navigation
description: Diseñar navegación Next.js App Router, deep links, rutas protegidas y estado de navegación sin acoplar features.
---

# Routing Navigation — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/app/(portal)/`
- `src/components/portal/`
- `proxy.ts`
- `src/server/auth/session.ts`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Inventariar rutas públicas/protegidas y rol requerido; documentar flujo de URL directa/refresh.
2. Crear ruta en src/app como composición delgada con Server Component.
3. Mantener breadcrumbs/shell en portal compartido y features aisladas.
4. Implementar loading.tsx, error.tsx y not-found.tsx donde el recorrido lo necesite.
5. Controlar callbackUrl de login para evitar open redirect: rutas internas permitidas.
6. Agregar prueba de navegación/roles, restauración de URL y estados de error.

## Patrón de implementación

El proxy filtra navegación temprana; la autorización real va en layout/page con requireSession/requireRole; health y auth mantienen accesibilidad pública.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No autorizaciones únicamente en menús o proxy.
- No importar feature A desde feature B.
- No rutas de backend inventadas para evitar BFF.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:component
npm run test:e2e
npm run test:architecture
```

- Código/contrato probado bajo las capacidades efectivamente disponibles; distinguir comandos ejecutados, fallidos y pendientes.
- Sin nuevas violaciones de import graph, secretos, traducciones o accesibilidad relacionadas al cambio.
- Los cambios de login, BFF, DS privado y entorno AKS precisan validación integrada fuera de tests mock.

## Contrato de entrega del agente

1. Explicar archivos cambiados y responsabilidad de cada capa.
2. Declarar habilidades activadas, alternativas descartadas, contratos y permisos requeridos.
3. Registrar pruebas con comando y resultado real; cualquier requisito no verificado queda explícito.
4. Incluir riesgos/rollback para cambios de SSO, build, deploy o compatibilidad entre features.
