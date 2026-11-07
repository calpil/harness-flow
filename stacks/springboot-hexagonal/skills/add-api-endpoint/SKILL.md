---
name: add-api-endpoint
description: "Design and implement versioned REST endpoints in Spring Boot MVC on top of hexagonal ports, with OpenAPI contracts, DTO validation, ProblemDetail, authorization, pagination, idempotency, controller tests and downstream compatibility. Use for any public/private API creation or changes."
---

# API Contract / HTTP Adapter — CALPIL Engineering Skill

> Skill ejecutable por GitHub Copilot/Claude Code. Ruta única: `.claude/skills/add-api-endpoint/`. Cada conclusión exige evidencia: no completar casillas con suposiciones.

## Cuándo activar y no activar

**Activar** cuando el usuario pide trabajo de api contract / http adapter o una historia/cambio que involucra esa superficie.
**No activar** para solicitudes ajenas al alcance; no modificar dependencias, seguridad ni documentación no relacionada para inflar el diff.

## Contrato de entrada (descubrir antes de tocar código)

1. Actor y consumidor (BFF, cliente interno, API externa); exposición pública/privada.
2. Rutas, verbos, request/response, filtros, paginación, semántica 4xx/5xx.
3. Autorización por scope/rol/tenant/recurso y normas de versionamiento.

Si falta una definición no bloqueante, continuar con supuesto explícito conservador y anotarlo; **nunca asumir aprobaciones, identidades o riesgo de producción**. Si falta requisito esencial de seguridad/integridad, dejarlo como bloqueo y no declarar listo.

## Preflight obligatorio

1. Confirmar raíz del repositorio y revisar `git status --short` para no pisar cambios ajenos.
2. Leer los archivos de la superficie implicada (no todo el repo); identificar cómo se prueba actualmente.
3. Distinguir hechos observados, hipótesis, supuestos y decisiones pendientes.
4. Crear mini-plan: archivos, riesgos, tests y efectos colaterales antes de editar.

## Workflow obligatorio, en secuencia

1. **Fase 01** — Verificar el contrato existente y callers; definir si es extensión compatible o cambio de versión.
2. **Fase 02** — Escribir tabla METHOD/PATH/OWNER/REQ/RESP/STATUS/SECURITY, ejemplos válidos y errores.
3. **Fase 03** — Validar entrada con Bean Validation, límites de tamaño y formatos, no confiar en IDs ni tenants del body.
4. **Fase 04** — Definir DTOs del adapter web sin JPA, secretos ni objetos de dominio mutables expuestos.
5. **Fase 05** — Crear mapping a port in o comando de aplicación, sin lógica de negocio en controller.
6. **Fase 06** — Alinear errores con GlobalExceptionHandler y `ProblemDetail` estable; no incluir stack trace ni datos internos.
7. **Fase 07** — En recursos creados considerar 201/Location; delete 204 cuando aplique; 409 conflictos y 422 cuando contrato lo exija.
8. **Fase 08** — Implementar paginación con límites y ordenamiento estable; explicar filtros y total.
9. **Fase 09** — Verificar Springdoc compatible con la versión actual de Boot; la línea 2.x del baseline no debe darse por válida en Boot 4.
10. **Fase 10** — Probar request válido, Bean Validation, status, headers, authn/authz, error shape y E2E con DB cuando corresponda.

## Guardrails y condiciones de bloqueo

- **NO**: No convertir objetos externos de Helm/terceros en contrato propio por exposición accidental.
- **NO**: No usar 200 para todos los errores; no omitir casos 401/403/404.
- **NO**: No considerar seguros endpoints solo por estar detrás de BFF o gateway.

## Operación paso a paso y ejemplos (leer al ejecutar)

- [PLAYBOOK: patrones, contratos, comandos, fallos y ejemplos](./references/PLAYBOOK.md)
- [ACCEPTANCE: matriz auditable de evidencia y pruebas](./references/ACCEPTANCE.md)
- [Checklist transversal de evidencias](./references/EVIDENCE_REPORT.md)
- [Worksheet técnico reutilizable](./examples/WORKSHEET.md)

## Comandos útiles — usar solo en el contexto adecuado

```bash
./mvnw -Dtest=WorkItemControllerTest test # patrón ilustrativo, reemplazar por test real
./mvnw -Dtest=NombreControllerTest test
./mvnw verify
```

Los comandos con `Nombre...` o `group:artifact` son **plantillas**: sustituir por nombres reales antes de ejecutar. No usar build offline como prueba de versions GA; no interpretar `skipped` como aprobado.

## Definition of Done específico

- [ ] OpenAPI y DTO implementado responden al mismo contrato probado.
- [ ] Errores de validación, auth, tenant y recursos ajenos están cubiertos.
- [ ] La semántica HTTP y backwards compatibility tienen evidencia.
### Dependencias y handoff

- Si la tarea toca simultáneamente **contrato HTTP, persistencia, seguridad, observabilidad, ADR o dependencias**, invocar/leer las skills especializadas de `.claude/skills/` para **esa** superficie. No crear una segunda implementación de la misma política.
- La documentación canónica de ingeniería existente (si está en checkout) vive en `docs/ai/`; leer solo la guía del dominio afectado: `ARCHITECTURE_RULES.md`, `TESTING_RULES.md`, `SECURITY_RULES.md`, `DEPENDENCY_POLICY.md`, `DEFINITION_OF_DONE.md`.
- La ruta del ejemplo `workitems` **no** es requisito de los equipos, ni fuente de verdad corporativa si se elimina.

## Contrato de salida obligatorio

Al concluir devolver: **(a)** resultado y alcance real; **(b)** tabla archivo→cambio→motivo; **(c)** contrato/riesgo/alternativas; **(d)** comandos realmente ejecutados y salida resumida con PASS/FAIL/SKIPPED/BLOCKED/NOT RUN; **(e)** pruebas faltantes + forma de ejecutarlas; **(f)** dependencias/compatibilidad/rollback; **(g)** documentos/ADR/changelog tocados; **(h)** decisión pendiente y owner si corresponde.

Nunca afirmar ejecución, aprobación, publicación, despliegue o vulnerabilidad corregida sin salida/evidencia verificable. No auto-commit ni push salvo solicitud explícita.
