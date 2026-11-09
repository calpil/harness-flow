---
name: write-tests
description: Diseñar, implementar y ejecutar pruebas unitarias de dominio, servicios, HTTP, UI, SSO y E2E. Úsala para features, bugs, refactors y criterios de aceptación.
---

# Write Tests — CALPIL Angular Golden Path

## Objetivo y activación

Una prueba comprueba resultado y contratos observables, no detalles de implementación ni snapshots superficiales.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `docs/quality/testing.md`, `karma.conf.js`, `playwright.config.ts`.
- `src/app/features/work-items/{domain/work-item.spec.ts,application/work-item.service.spec.ts,ui/work-item-list.component.spec.ts}`.
- `src/app/core/auth/*.spec.ts`, `tests/e2e/*.spec.ts`.
- [Matriz de pruebas](./references/test-matrix.md).

## Procedimiento ejecutable

1. Extrae invariantes y criterios observables del requerimiento; construye matriz caso normal/borde/error/seguridad.
2. Escribe domain tests sin TestBed; prueba reglas puras, transiciones prohibidas e inmutabilidad observable.
3. Para application tests provee `WORK_ITEM_REPOSITORY` con fake controlable; prueba Signals, loading/error y actualizaciones.
4. Para adapter HTTP usa mocks de HttpClient/TestController, URL, query params, timeouts y mapping de errores.
5. Para componente usa TestBed, providers reales/fake intencionales; prueba DOM, aria, focus, loading/empty/error.
6. Para SSO inyecta MSAL fake; comprueba allowlist token, 401/403 y redirección local segura sin invocar Entra remoto.
7. Para runtime config prueba archivos válidos/rechazados y ausencia de secretos; no desactives validación para facilitar test.
8. Para E2E Playwright cubre journey usuario: login mock **solo local no productivo**, listado→detalle→transición, URL directa, error.
9. Usa `data-testid` únicamente donde selectors semánticos sean inestables; favorece `getByRole` y `getByLabel`.
10. Evita esperas fijas y tests dependientes de un backend que no existe; fixtures reproducibles.
11. Ejecuta spec dirigida primero y luego matriz global; deja trazabilidad de suite y resultado real.
12. Test que falla por bug real se arregla en producción, no debilitando assertion/mocks.

## Patrón de implementación

```ts
// Ejemplo de intención, no copiar sin adaptar:
expect(canTransition('TODO', 'IN_PROGRESS')).toBeTrue();
expect(canTransition('DONE', 'TODO')).toBeFalse();
```

Cada regresión requiere test que falle antes del fix siempre que sea reproducible.

## Decisiones y anti-patrones

- Los E2E con bypass no validan Entra real, scopes ni autorización backend.
- Un fake in-memory que funciona no verifica el contrato BFF.
- No confundir coverage con calidad; medir caminos críticos y fallas.
- No afirmar “pasó” si no se pudo instalar npm privado o lanzar navegador.

## Verificación / Definition of Done

- Unit y API-focused → `npm run test`; `npm run test:architecture` y `npm run test:security`.
- `npm run test:e2e` para journeys; `npm run validate` para cierre.
- Documentar tests ejecutados, resultados, cobertura si disponible y bloqueos específicos.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
