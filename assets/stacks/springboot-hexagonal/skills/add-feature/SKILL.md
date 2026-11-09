---
name: add-feature
description: "Build an entire business feature in a Java Spring Boot hexagonal repository: domain invariants, application use cases, input/output ports, HTTP adapters, JPA adapters, Liquibase migrations, security, tests, OpenAPI and evidence. Use for user stories or new capabilities, not scaffolding alone."
---

# Vertical Slice / Feature End-to-End — CALPIL Engineering Skill

> Skill compatible con todos los agentes (Claude Code, OpenAI Codex, Gemini CLI, Antigravity, Hermes, Grok, Kimi). Rutas: `.agents/skills/add-feature/` o `.claude/skills/add-feature/`. Cada conclusión exige evidencia: no completar casillas con suposiciones.

## Cuándo activar y no activar

**Activar** cuando el usuario pide trabajo de vertical slice / feature end-to-end o una historia/cambio que involucra esa superficie.
**No activar** para solicitudes ajenas al alcance; no modificar dependencias, seguridad ni documentación no relacionada para inflar el diff.

## Contrato de entrada (descubrir antes de tocar código)

1. Historia y criterios verificables; entidades/actores y autorización.
2. Contratos solicitados API, persistencia, eventos y comportamiento de errores.
3. Límites del bounded context y dependencias externas conocidas.

Si falta una definición no bloqueante, continuar con supuesto explícito conservador y anotarlo; **nunca asumir aprobaciones, identidades o riesgo de producción**. Si falta requisito esencial de seguridad/integridad, dejarlo como bloqueo y no declarar listo.

## Preflight obligatorio

1. Confirmar raíz del repositorio y revisar `git status --short` para no pisar cambios ajenos.
2. Leer los archivos de la superficie implicada (no todo el repo); identificar cómo se prueba actualmente.
3. Distinguir hechos observados, hipótesis, supuestos y decisiones pendientes.
4. Crear mini-plan: archivos, riesgos, tests y efectos colaterales antes de editar.

## Workflow obligatorio, en secuencia

1. **Fase 01** — Redactar primero tabla Given/When/Then de éxito, invalidaciones, concurrencia, autorización y tenant-crossing.
2. **Fase 02** — Identificar bounded context, aggregates, value objects, IDs e invariantes; no crear genéricos innecesarios.
3. **Fase 03** — Diseñar API y comandos de aplicación (inputs/outputs) en vez de copiar requests HTTP dentro del core.
4. **Fase 04** — Implementar domain model con estado válido y transiciones consistentes, tests puros (sin Spring).
5. **Fase 05** — Declarar port in por caso de uso y port out solo para colaboración externa real.
6. **Fase 06** — Implementar caso de uso con dependencias constructor, control de atomicidad y emisión de evento definida para commit correcto.
7. **Fase 07** — Crear adapters web con Bean Validation, mapping y ProblemDetail; integración externa detrás de ACL.
8. **Fase 08** — Crear adapters JPA, repositorio, mapping y Liquibase en cambio aditivo/expand-contract.
9. **Fase 09** — Agregar autorización por recurso y tenant en capa apropiada; tests 401/403/404, no solo happy path.
10. **Fase 10** — Probar unidad → controller → integración DB → ArchUnit; verificar feature operativa end-to-end; actualizar docs/ADR si es cambio arquitectónico.

## Guardrails y condiciones de bloqueo

- **NO**: No asumir que WorkItems es dominio fijo del servicio.
- **NO**: No declarar feature lista si falta DB migration, 4xx coherentes o pruebas negativas.
- **NO**: No disparar eventos no idempotentes antes de confirmar transacción; decidir outbox cuando hay entrega confiable.

## Operación paso a paso y ejemplos (leer al ejecutar)

- [PLAYBOOK: patrones, contratos, comandos, fallos y ejemplos](./references/PLAYBOOK.md)
- [ACCEPTANCE: matriz auditable de evidencia y pruebas](./references/ACCEPTANCE.md)
- [Checklist transversal de evidencias](./references/EVIDENCE_REPORT.md)
- [Worksheet técnico reutilizable](./examples/WORKSHEET.md)

## Comandos útiles — usar solo en el contexto adecuado

```bash
find src/main/java -path "*/application/port/*" -type f | head -30
./mvnw -Dtest=HexagonalArchitectureTest test
./mvnw -Dtest=NombreDeTuCasoDeUsoTest test
./mvnw verify
```

Los comandos con `Nombre...` o `group:artifact` son **plantillas**: sustituir por nombres reales antes de ejecutar. No usar build offline como prueba de versions GA; no interpretar `skipped` como aprobado.

## Definition of Done específico

- [ ] Existe un recorrido completo y trazable de escenario a archivos y pruebas.
- [ ] Los mappers nunca exponen entidades de persistencia como contrato API.
- [ ] Se demuestran validaciones de transición, excepciones, concurrencia y tenant.
### Dependencias y handoff

- Si la tarea toca simultáneamente **contrato HTTP, persistencia, seguridad, observabilidad, ADR o dependencias**, invocar/leer las skills especializadas (`.agents/skills/` o `.claude/skills/`) para **esa** superficie. No crear una segunda implementación de la misma política.
- La documentación canónica de ingeniería existente (si está en checkout) vive en `docs/ai/`; leer solo la guía del dominio afectado: `ARCHITECTURE_RULES.md`, `TESTING_RULES.md`, `SECURITY_RULES.md`, `DEPENDENCY_POLICY.md`, `DEFINITION_OF_DONE.md`.
- La ruta del ejemplo `workitems` **no** es requisito de los equipos, ni fuente de verdad corporativa si se elimina.

## Contrato de salida obligatorio

Al concluir devolver: **(a)** resultado y alcance real; **(b)** tabla archivo→cambio→motivo; **(c)** contrato/riesgo/alternativas; **(d)** comandos realmente ejecutados y salida resumida con PASS/FAIL/SKIPPED/BLOCKED/NOT RUN; **(e)** pruebas faltantes + forma de ejecutarlas; **(f)** dependencias/compatibilidad/rollback; **(g)** documentos/ADR/changelog tocados; **(h)** decisión pendiente y owner si corresponde.

Nunca afirmar ejecución, aprobación, publicación, despliegue o vulnerabilidad corregida sin salida/evidencia verificable. No auto-commit ni push salvo solicitud explícita.
