---
name: performance-review
description: Optimizar Next.js server-first, hidratar solo UI necesaria y eliminar cascadas fetch/re-render/hydration.
---

# Performance Review — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/app/`
- `src/features/operations/ui/`
- `src/features/operations/demo/`
- `next.config.mjs`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Identificar render path y si datos pueden resolverse en Server Component o cache de servidor.
2. Medir bundle y número de Client Components antes de cambiar memo/effects.
3. Eliminar cascada de fetch y side-effects duplicados; AbortSignal para búsqueda y filtros.
4. Evitar trasladar todo estado al cliente si no es interactivo; particionar import de DS con verificación.
5. Controlar loading.tsx, streaming y cache boundaries para no servir datos entre usuarios.
6. Revisar datos de listados paginados, imágenes y reportes; documentar medida antes/después o incertidumbre.

## Patrón de implementación

Seguir componentes Server por defecto y UI client local. No cachear datos autenticados cross-user sin keys seguras.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No useMemo por reflejo.
- No fetch redundantes en useEffect.
- No client-side bundle con server-only.

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

## Guía adicional existente (preservada)

# Performance Review

Use when changing fetching, effects, routing, Client Components or interactive data-heavy UI.

## Check

### Client/server boundary

- Server Components remain default;
- Client Components are limited to required interaction;
- server-only code does not leak into client graphs.

### Rendering

Flag:

- render loops;
- unstable effect dependencies;
- duplicated derived state;
- unnecessary context/global state;
- broad re-renders from local interactions.

### Requests

Flag:

- duplicated fetching;
- unnecessary polling;
- repeated RSC requests;
- router refresh for local state;
- waterfalls that can use existing patterns;
- requests triggered by cosmetic interactions.

### Navigation

Avoid using navigation/reload to update data that can be updated locally.

### Bundle/runtime

Avoid adding heavy dependencies for small functionality.

## Evidence

Use targeted profiling/log/network evidence when needed; do not guess.

Report/fix performance regressions in scope.
