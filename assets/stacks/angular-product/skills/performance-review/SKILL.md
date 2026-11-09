---
name: performance-review
description: Revisar rendimiento Angular zoneless, lazy routes, Signals, DOM, bundles y requests. Úsala ante cambios de listados, dashboard, formularios o bundle.
---

# Performance Review — CALPIL Angular Golden Path

## Objetivo y activación

Optimizar cuellos de botella demostrados manteniendo una UX predecible. Evitar complejidad extra para microoptimizar.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `angular.json` (budgets), `src/app/app.routes.ts` (lazy imports).
- `src/app/features/work-items/application/work-item.service.ts` (Signals).
- `src/app/features/work-items/ui/work-item-list.component.ts` (`@for track`).
- `PERFORMANCE.md` si se añade luego; actualmente verificar `docs/platform/observability.md`.

## Procedimiento ejecutable

1. Establece métrica y escenario: carga inicial, navegación a detalle, listado grande, red lenta, interaction latency.
2. Captura baseline reproducible, dispositivo/navegador y perfil antes de modificar.
3. Comprueba separación lazy por rutas, tamaño de vendors/DS y budget `angular.json` en build prod.
4. Revisa duplicación de HTTP/fetch por navegación o renders; cancela trabajo obsoleto (RxJS `switchMap`, `takeUntilDestroyed` si aplica).
5. Usa Signals para estado de feature y `computed` para proyecciones, evitando lecturas/recomputaciones de alto costo en template.
6. `@for` siempre con track estable (`id`), no índice cuando se reordena; paginación virtual si escala.
7. Diferencia datos recientes vs cache por contrato; evita cachear permisos o datos privados sin política.
8. Optimiza imágenes, fuentes y CSS DS sin romper branding ni accesibilidad.
9. Revisa memory leaks de subscripciones y efectos; prueba rutas ida/vuelta y cambios de filtro rápidos.
10. Repite medición y registra antes/después; revierte complejidad si no hay mejora significativa.

## Patrón de implementación

```text
Señal -> computed -> template @for(...; track item.id)
No: getter costoso repetido + HTTP en componente.
```

## Decisiones y anti-patrones

- No añadir store global, worker, virtual scroll o librería por anticipación.
- No eliminar loading/error para mejorar métrica.
- No optimizar cambiando semántica de seguridad/caché.
- El caso Work Items demo no representa volumen o latencia de producción.

## Verificación / Definition of Done

- `npm run build:prod` (bundles/budgets), typecheck y E2E journey.
- Evidencia de baseline/resultado con métricas consistentes y tradeoffs.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
