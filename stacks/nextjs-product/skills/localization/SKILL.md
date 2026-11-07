---
name: localization
description: Mantener traducciones es/en/pt, formatos regionales, estados y textos administrados sin strings UI hardcodeados.
---

# Localization — CALPIL Next.js Golden Path

## Objetivo y activación

Esta skill es obligatoria para tareas descritas en el frontmatter. Su resultado debe ser una implementación mínima, comprobable, segura y compatible con Next.js App Router. Componer con `architecture-review`, `write-tests`, `security-review`, `ui-quality-review` u otras skills cuando aplique; no utilizarla como sustituto de los contratos reales.

## Inspección obligatoria

Inspeccionar archivos pertinentes antes de modificar (y parar al tener evidencia suficiente):

- `src/shared/i18n/`
- `src/shared/locale/`
- `src/features/operations/ui/`
- `docs/ai/`

- `AGENTS.md` y `docs/ai/ARCHITECTURE_RULES.md` para invariantes; verificar exports y contratos externos en vez de suponerlos.

## Procedimiento ejecutable

1. Identificar locales soportados y esquema de diccionario; preservar claves y namespace existentes.
2. Extraer nuevos textos visibles, labels, errores, títulos y aria labels a catálogo de traducción.
3. Usar Intl para números/fechas según locale explícita y zona requerida por contrato.
4. Distinguir datos administrados por backend de mensajes UI: no traducir nombres de clientes por defecto.
5. Comprobar pluralización, fallback, textos largos, RTL si está contemplado y SSR/hydration estable.
6. Actualizar tests por locale evitando snapshots de strings rígidos.

## Patrón de implementación

Rutas de referencia src/shared/i18n y src/shared/locale; idiomas: en, es y pt si sus catálogos están presentes, sin inventar recursos.

**Decisión explícita:** diferenciar demostración local, contrato real y código productivo; si un servicio o API externa no se puede verificar, declarar el supuesto y su impacto sin inventar implementación.

## Decisiones y anti-patrones

- No duplicar cadenas españolas en JSX.
- No usar Date.toLocaleString sin locale/timezone definida.
- No traducir identificadores de dominio.

- No mezclar provisioning de plataforma corporativa (AKS, AFD, networking, base de datos) con el deploy de frontend.
- No declarar éxito end-to-end sin ejecutar el flujo de login, integración o build real contra el entorno correspondiente.

## Verificación / Definition of Done

Aplicar pruebas enfocadas primero. Comandos sugeridos según el cambio (ejecutar solo los aplicables):

```bash
npm run test:unit
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

# Localization

Use for any user-facing text or locale-sensitive behavior.

## Reuse existing infrastructure

Before changing localization:

- inspect the existing locale provider/resolver/catalogs;
- reuse existing hooks/helpers/types;
- do not add a second i18n framework;
- do not create parallel translation resources.

## Static UI text

Localize:

- titles;
- labels;
- buttons;
- placeholders;
- helper text;
- validations;
- errors/success;
- empty/loading states;
- tooltips;
- accessibility text.

Do not leave hardcoded visible strings when they belong in locale resources.

## Multilingual administered content

If business/administered content itself is multilingual:

- keep one logical business entity;
- use the existing localized-content domain pattern;
- do not duplicate the entity per language.

Separate display labels from stable technical values.

Business logic must use stable IDs/codes/enums/values, never translated labels.

## State

Changing locale must not unexpectedly reset unrelated state.

## Validation

Add/update relevant tests for:

- locale key consistency;
- rendering in supported locales;
- fallback;
- stable technical values;
- state preservation.

Use `write-tests`.

Report localization status accurately.
