---
name: write-tests
description: "Create maintainable JUnit 5, AssertJ, MockMvc and Testcontainers tests for a Spring Boot hexagonal service: domain, use case, web/security, JPA/PostgreSQL migrations, end-to-end HTTP, ArchUnit, regressions, coverage and CI reproducibility. Use for test coverage, bug regression or change validation."
---

# Automated Tests / Contract / Architecture — CALPIL Engineering Skill

> Skill ejecutable por GitHub Copilot/Claude Code. Ruta única: `.claude/skills/write-tests/`. Cada conclusión exige evidencia: no completar casillas con suposiciones.

## Cuándo activar y no activar

**Activar** cuando el usuario pide trabajo de automated tests / contract / architecture o una historia/cambio que involucra esa superficie.
**No activar** para solicitudes ajenas al alcance; no modificar dependencias, seguridad ni documentación no relacionada para inflar el diff.

## Contrato de entrada (descubrir antes de tocar código)

1. Behavior, acceptance criteria and impacted code paths.
2. Test level required and Docker/test environment constraints.
3. Contracts to preserve and failure modes not yet covered.

Si falta una definición no bloqueante, continuar con supuesto explícito conservador y anotarlo; **nunca asumir aprobaciones, identidades o riesgo de producción**. Si falta requisito esencial de seguridad/integridad, dejarlo como bloqueo y no declarar listo.

## Preflight obligatorio

1. Confirmar raíz del repositorio y revisar `git status --short` para no pisar cambios ajenos.
2. Leer los archivos de la superficie implicada (no todo el repo); identificar cómo se prueba actualmente.
3. Distinguir hechos observados, hipótesis, supuestos y decisiones pendientes.
4. Crear mini-plan: archivos, riesgos, tests y efectos colaterales antes de editar.

## Workflow obligatorio, en secuencia

1. **Fase 01** — Derivar escenarios observables de la historia o bug; no empezar por mocks aleatorios.
2. **Fase 02** — Elegir nivel mínimo que pruebe riesgo: domain sin Spring, use case con fake ports, web slice, DB real E2E.
3. **Fase 03** — Implementar Given/When/Then con nombres que describan comportamiento, no método interno.
4. **Fase 04** — Verificar excepción/estado y efectos colaterales, no solo cantidad de invocaciones mock.
5. **Fase 05** — Probar validación, errores, borde, paginación, concurrencia, idempotencia y tenant cuando aplique.
6. **Fase 06** — Para DB y Liquibase usar Testcontainers PostgreSQL y verificar upgrade/snapshot; evitar H2 como sustituto del motor productivo.
7. **Fase 07** — Para seguridad comprobar 401/403 y permisos por recurso, no marcar `permitAll` como passing security.
8. **Fase 08** — Para cambios de dependencias o arquitectura incluir DependencySecurityRegressionTest y HexagonalArchitectureTest.
9. **Fase 09** — Ejecutar foco por clase o package, luego integración y `verify`; distinguir test skipped por ausencia Docker.
10. **Fase 10** — Comprobar flakiness, reproducibilidad y cobertura real; no modificar umbrales JaCoCo para ocultar fallas.

## Guardrails y condiciones de bloqueo

- **NO**: No usar `@SpringBootTest` para invariantes puras del dominio.
- **NO**: No vaciar assertions ni retocar test para esconder defecto real.
- **NO**: `@Testcontainers(disabledWithoutDocker=true)` puede saltar tests: skipped ≠ passed.

## Operación paso a paso y ejemplos (leer al ejecutar)

- [PLAYBOOK: patrones, contratos, comandos, fallos y ejemplos](./references/PLAYBOOK.md)
- [ACCEPTANCE: matriz auditable de evidencia y pruebas](./references/ACCEPTANCE.md)
- [Checklist transversal de evidencias](./references/EVIDENCE_REPORT.md)
- [Worksheet técnico reutilizable](./examples/WORKSHEET.md)

## Comandos útiles — usar solo en el contexto adecuado

```bash
./mvnw -Dtest=WorkItemTest test # ejemplo, no requisito permanente
./mvnw -Dtest=HexagonalArchitectureTest test
./mvnw -Dtest=NombreIntegracionTest test
./mvnw verify
```

Los comandos con `Nombre...` o `group:artifact` son **plantillas**: sustituir por nombres reales antes de ejecutar. No usar build offline como prueba de versions GA; no interpretar `skipped` como aprobado.

## Definition of Done específico

- [ ] Test falla antes del fix y pasa después para regresión comprobable.
- [ ] Aserciones verifican efectos y respuestas, no detalles privados.
- [ ] Se informa skipped, ejecutados, fallidos y cobertura sin maquillajes.
### Dependencias y handoff

- Si la tarea toca simultáneamente **contrato HTTP, persistencia, seguridad, observabilidad, ADR o dependencias**, invocar/leer las skills especializadas de `.claude/skills/` para **esa** superficie. No crear una segunda implementación de la misma política.
- La documentación canónica de ingeniería existente (si está en checkout) vive en `docs/ai/`; leer solo la guía del dominio afectado: `ARCHITECTURE_RULES.md`, `TESTING_RULES.md`, `SECURITY_RULES.md`, `DEPENDENCY_POLICY.md`, `DEFINITION_OF_DONE.md`.
- La ruta del ejemplo `workitems` **no** es requisito de los equipos, ni fuente de verdad corporativa si se elimina.

## Contrato de salida obligatorio

Al concluir devolver: **(a)** resultado y alcance real; **(b)** tabla archivo→cambio→motivo; **(c)** contrato/riesgo/alternativas; **(d)** comandos realmente ejecutados y salida resumida con PASS/FAIL/SKIPPED/BLOCKED/NOT RUN; **(e)** pruebas faltantes + forma de ejecutarlas; **(f)** dependencias/compatibilidad/rollback; **(g)** documentos/ADR/changelog tocados; **(h)** decisión pendiente y owner si corresponde.

Nunca afirmar ejecución, aprobación, publicación, despliegue o vulnerabilidad corregida sin salida/evidencia verificable. No auto-commit ni push salvo solicitud explícita.
