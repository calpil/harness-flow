---
name: localization
description: Introducir o extender localización de UI Angular en español, inglés y portugués sin contaminar el dominio. Úsala para textos, fecha, moneda, validaciones y accesibilidad multiidioma.
---

# Localization — CALPIL Angular Golden Path

## Objetivo y activación

Establecer decisiones i18n antes de cambiar textos sin inventar una plataforma de traducción que el repositorio no tiene implementada.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `src/app/core/layout/portal-shell.component.ts`, `features/work-items/ui/*` (textos actuales).
- `src/app/core/config/runtime-config.ts` y documentación de experiencia multilingüe (si disponible).
- Skill `add-ui-component`, `write-tests`, `accessibility-review`.

## Procedimiento ejecutable

1. Definir alcance y estrategia: build-time Angular i18n, runtime catálogo o librería aprobada; este template todavía no trae motor i18n activo.
2. Levanta inventario de strings visibles y copy de error/carga/empty; prioriza rutas de negocio reales.
3. Acuerda locales soportados (`es-CL`, `en`, `pt-BR` según producto), fallback y persistencia de elección.
4. No traducir claves de dominio, statuses transportados, nombres de campos API ni log identifiers.
5. Mapear enums a etiquetas presentacionales en UI; contemplar plural/género y variables con formato localizado.
6. Fechas y cifras por Intl/locale; no formatear valores de persistencia ni cambiar ISO de API.
7. Mantén mensajes validación accesibles y tamaños de layout robustos ante traducciones extensas.
8. Traducciones revisadas por negocio, no inventadas para operaciones legales/críticas.
9. Añade tests de fallback, claves ausentes y orden de navegación por idioma.
10. Documenta ADR si introduce una dependencia i18n o contrato transversal nuevo.

## Patrón de implementación

```text
API: status = IN_PROGRESS (inmutable por locale)
UI es-CL: En progreso
UI en: In progress
UI pt-BR: Em andamento
```

## Decisiones y anti-patrones

- No hardcodear claves de traducción en dominio.
- No asumir idioma por countryCode de dato; preferencia UI es distinta del país operativo.
- No importar una nueva dependencia sin decisión/documentación.
- No prometer multilingüismo completo: actualmente es una capacidad por desarrollar.

## Verificación / Definition of Done

- Ejecutar typecheck y specs i18n; prueba manual de rutas principales en cada idioma definido.
- Comprobar números/fechas y longitudes de copy en responsive.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
