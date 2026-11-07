---
name: architecture-review
description: "Audit a Java Spring Boot hexagonal architecture and a PR for boundary leaks, application flow, APIs, contracts, data consistency, security, operational failure modes, dependencies, testability and nonfunctional quality; produce severity-ranked grounded findings and ADR triggers."
---

# Architecture Fitness / Review and ADR — CALPIL Engineering Skill

> Skill ejecutable por GitHub Copilot/Claude Code. Ruta única: `.claude/skills/architecture-review/`. Cada conclusión exige evidencia: no completar casillas con suposiciones.

## Cuándo activar y no activar

**Activar** cuando el usuario pide trabajo de architecture fitness / review and adr o una historia/cambio que involucra esa superficie.
**No activar** para solicitudes ajenas al alcance; no modificar dependencias, seguridad ni documentación no relacionada para inflar el diff.

## Contrato de entrada (descubrir antes de tocar código)

1. Scope (PR diff or paths) and architecture baseline.
2. Business criticality, consumers and known failure modes.
3. Requested output: review only, remediation plan or approved implementation.

Si falta una definición no bloqueante, continuar con supuesto explícito conservador y anotarlo; **nunca asumir aprobaciones, identidades o riesgo de producción**. Si falta requisito esencial de seguridad/integridad, dejarlo como bloqueo y no declarar listo.

## Preflight obligatorio

1. Confirmar raíz del repositorio y revisar `git status --short` para no pisar cambios ajenos.
2. Leer los archivos de la superficie implicada (no todo el repo); identificar cómo se prueba actualmente.
3. Distinguir hechos observados, hipótesis, supuestos y decisiones pendientes.
4. Crear mini-plan: archivos, riesgos, tests y efectos colaterales antes de editar.

## Workflow obligatorio, en secuencia

1. **Fase 01** — Revisar diff y código realmente tocado; expandir por callers, contratos, ports y adapters estrictamente necesarios.
2. **Fase 02** — Modelar flujo externo→entrada→caso uso→dominio→salida→dependencias, anotando dependencias invertidas.
3. **Fase 03** — Buscar framework leakage en domain/application, DTO/entity leakage, puertos vacíos, servicios base falsos.
4. **Fase 04** — Evaluar atomicidad y efectos colaterales: transacciones, eventos, outbox, idempotencia, retries, race, locks.
5. **Fase 05** — Revisar evolución API y esquema: compatibilidad, versionamiento, migración, volumen y rollback.
6. **Fase 06** — Comprobar autorización/tenant y trust boundaries, secretos, datos sensibles y fallbacks.
7. **Fase 07** — Inspeccionar configuración y operación: readiness/liveness, failure domains, timeouts, pool pressure y tracing.
8. **Fase 08** — Relacionar invariantes ArchUnit, pruebas y documentación ADR existente sin reescribir decisiones anteriores.
9. **Fase 09** — Reportar hallazgos por severidad con archivo, evidencia, riesgo, cambio mínimo y prueba requerida.
10. **Fase 10** — Proponer ADR solo cuando exista trade-off o decisión transversal; no crear ADR por cada refactor menor.

## Guardrails y condiciones de bloqueo

- **NO**: No transformar revisión en refactor masivo sin autorización.
- **NO**: Nunca confundir preferencia de estilo con bug crítico.
- **NO**: No afirmar vulnerabilidad concreta sin ruta de explotación/evidencia apropiada.

## Operación paso a paso y ejemplos (leer al ejecutar)

- [PLAYBOOK: patrones, contratos, comandos, fallos y ejemplos](./references/PLAYBOOK.md)
- [ACCEPTANCE: matriz auditable de evidencia y pruebas](./references/ACCEPTANCE.md)
- [Checklist transversal de evidencias](./references/EVIDENCE_REPORT.md)

## Comandos útiles — usar solo en el contexto adecuado

```bash
git diff --stat
git diff -- src/main/java src/test/java pom.xml
./mvnw -Dtest=HexagonalArchitectureTest test
```

Los comandos con `Nombre...` o `group:artifact` son **plantillas**: sustituir por nombres reales antes de ejecutar. No usar build offline como prueba de versions GA; no interpretar `skipped` como aprobado.

## Definition of Done específico

- [ ] Cada finding indica ruta/línea, evidencia observable, impacto y mitigación.
- [ ] Hay clasificación BLOCKER/HIGH/MEDIUM/LOW y separación de hechos/hipótesis.
- [ ] Se explicitan trade-offs, dependencias, riesgos y verificaciones faltantes.
### Dependencias y handoff

- Si la tarea toca simultáneamente **contrato HTTP, persistencia, seguridad, observabilidad, ADR o dependencias**, invocar/leer las skills especializadas de `.claude/skills/` para **esa** superficie. No crear una segunda implementación de la misma política.
- La documentación canónica de ingeniería existente (si está en checkout) vive en `docs/ai/`; leer solo la guía del dominio afectado: `ARCHITECTURE_RULES.md`, `TESTING_RULES.md`, `SECURITY_RULES.md`, `DEPENDENCY_POLICY.md`, `DEFINITION_OF_DONE.md`.
- La ruta del ejemplo `workitems` **no** es requisito de los equipos, ni fuente de verdad corporativa si se elimina.

## Contrato de salida obligatorio

Al concluir devolver: **(a)** resultado y alcance real; **(b)** tabla archivo→cambio→motivo; **(c)** contrato/riesgo/alternativas; **(d)** comandos realmente ejecutados y salida resumida con PASS/FAIL/SKIPPED/BLOCKED/NOT RUN; **(e)** pruebas faltantes + forma de ejecutarlas; **(f)** dependencias/compatibilidad/rollback; **(g)** documentos/ADR/changelog tocados; **(h)** decisión pendiente y owner si corresponde.

Nunca afirmar ejecución, aprobación, publicación, despliegue o vulnerabilidad corregida sin salida/evidencia verificable. No auto-commit ni push salvo solicitud explícita.
