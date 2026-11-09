---
name: add-ui-component
description: Crear componentes React reutilizables o de feature con DS, accesibilidad, i18n y separación server/client.
---

# Add Ui Component — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/components/portal/`
- `src/features/operations/ui/`
- `src/shared/i18n/`
- `docs/ui/design-system.md`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Determinar ownership: UI empresarial de negocio en feature, shell visual reutilizable en components/portal.
2. Preferir Server Component puro; agregar use client solo si hay interacción o navegador.
3. Definir API con props tipadas; distinguir modelos de dominio de view models, normalizando en borde.
4. Reutilizar @calpil-ds/react con exports verificados; si falta, dejar gap en lugar de un sustituto inventado.
5. Agregar estados vacío, carga, error, disabled, confirmación y recuperación cuando corresponda.
6. Probar navegación teclado, foco, anuncios de error, tamaños viewport y traducciones.

## Patrón de implementación

UI: src/features/operations/ui/new-operation-form.tsx y src/components/portal/*.tsx; props tipadas y DS primero.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No componentes globales dependientes de operaciones.
- No side effects durante render.
- No mover toda la página a use client por una interacción.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:component
npm run lint
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
