---
name: form-validation
description: Implementar formularios Angular reactivos tipados, reglas de dominio y errores del BFF. Úsala al crear/editar entidades y flujos multi-step.
---

# Form Validation — CALPIL Angular Golden Path

## Objetivo y activación

Un formulario valida UX, pero el dominio y el servidor siguen siendo responsables de reglas e integridad.

Usa esta skill si la solicitud encaja con la descripción. Antes de editar, confirma alcance real; si el trabajo cruza dominios, combina esta skill con `architecture-review` y `write-tests`. **No inventes** dependencias, endpoints, componentes privados, resultados de tests ni infraestructura.

## Inspección obligatoria (lectura selectiva)

- `src/app/features/work-items/ui/create-work-item-form.component.ts`.
- `src/app/features/work-items/domain/work-item.ts` y `work-item.spec.ts`.
- `src/app/features/work-items/application/work-item.service.ts`.
- Skill `design-system-integration` y `accessibility-review`.

## Procedimiento ejecutable

1. Define campos, tipo, obligatoriedad, límites, dependencias y reglas de dominio antes de escribir template.
2. Usa `FormGroup`/`FormControl` nonNullable, validators adecuados y defaults explícitos; evita `any`.
3. Aplica validaciones UX (required/maxLength) coherentes con constantes de dominio; no dupliques reglas complejas en componente.
4. Diseña errores inline con mensajes útiles/aria-describedby, tocado y submit; foco al primer error relevante.
5. Comando de formulario se envía a application service; no llames HttpClient desde UI.
6. En caso de error 409/422 del BFF, conserva inputs, muestra error y no resetees formulario hasta confirmación.
7. Maneja submitting/loading y doble clic; identifica retries seguros e idempotencia.
8. Cuando hay edición, considera control de concurrencia/version y volver con cambios sin guardar.
9. Usa componentes DS reales para field/button si están disponibles; fallback accesible sin inventar APIs privadas.
10. Prueba required, whitespace, max length, submit, server error, cancel y teclado.

## Patrón de implementación

```ts
readonly form = new FormGroup({
  title: new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.maxLength(TITLE_MAX_LENGTH)]
  })
});
```

Fíjate que `WorkItem.create()` repite **invariante de dominio**, no la UI.

## Decisiones y anti-patrones

- Nunca afirmar que frontend sustituye validación backend.
- No resetear formulario al emitir evento si la operación asíncrona puede fallar, salvo flujo claramente de demo.
- No almacenar adjuntos sensibles en localStorage ni logs.
- Evitar component con mapeos API y reglas de negocio incrustadas.

## Verificación / Definition of Done

- Pruebas de dominio independientes + componente con TestBed + E2E happy/error.
- Inspección de error en pantalla y focus; typecheck/lint.

## Contrato de entrega del agente

- Describe **qué se cambió y por qué**, con archivos y frontera arquitectónica afectada.
- Resume el flujo completo y el contrato/permiso involucrado (si aplica).
- Informa comandos **efectivamente ejecutados** con resultado real; diferencia éxito, fallo y no ejecutado.
- Indica supuestos y dependencias externas no disponibles (feed CALPIL, Entra, OpenAPI, ambiente AKS).
- No declares `listo para producción` si no se han validado dependencias privadas, SSO real o BFF real.
