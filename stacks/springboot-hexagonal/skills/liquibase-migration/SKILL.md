---
name: liquibase-migration
description: "Create, validate and deploy versioned PostgreSQL Liquibase changesets safely in a Spring Boot hexagonal service: canonical master references, data backfill, constraints, indexes, tenant safety, locking, forward-only rollouts and rollback plans. Use for any schema or seed change."
---

# PostgreSQL / Liquibase Expand-Contract — CALPIL Engineering Skill

> Skill ejecutable por GitHub Copilot/Claude Code. Ruta única: `.claude/skills/liquibase-migration/`. Cada conclusión exige evidencia: no completar casillas con suposiciones.

## Cuándo activar y no activar

**Activar** cuando el usuario pide trabajo de postgresql / liquibase expand-contract o una historia/cambio que involucra esa superficie.
**No activar** para solicitudes ajenas al alcance; no modificar dependencias, seguridad ni documentación no relacionada para inflar el diff.

## Contrato de entrada (descubrir antes de tocar código)

1. Esquema actual y esperado, tamaños y cardinalidad estimados.
2. Datos existentes, consumidores viejos/nuevos y ventana de despliegue.
3. Estrategia de rollback y reglas de denominación de columnas.

Si falta una definición no bloqueante, continuar con supuesto explícito conservador y anotarlo; **nunca asumir aprobaciones, identidades o riesgo de producción**. Si falta requisito esencial de seguridad/integridad, dejarlo como bloqueo y no declarar listo.

## Preflight obligatorio

1. Confirmar raíz del repositorio y revisar `git status --short` para no pisar cambios ajenos.
2. Leer los archivos de la superficie implicada (no todo el repo); identificar cómo se prueba actualmente.
3. Distinguir hechos observados, hipótesis, supuestos y decisiones pendientes.
4. Crear mini-plan: archivos, riesgos, tests y efectos colaterales antes de editar.

## Workflow obligatorio, en secuencia

1. **Fase 01** — Leer changelog master real y árbol referenciado; no modificar changesets ya desplegados.
2. **Fase 02** — Confirmar tipología cambio: aditivo, cambio de semántica, renombre, constraint, índice o backfill.
3. **Fase 03** — Planificar expand → dual write/read compatible → backfill resumible → contract en release separado para breaking changes.
4. **Fase 04** — Asignar ID/autor único, preconditions, contexts/labels solo si realmente se usan; respetar orden del master.
5. **Fase 05** — Crear cambios SQL PostgreSQL con tipos precisos, claves/índices y constraints; evitar locks prolongados.
6. **Fase 06** — Determinar comportamiento de datos existentes, nullability y default seguro; verificar cardinalidad y coste estimado.
7. **Fase 07** — Diseñar rollback viable cuando exista, reconocer explícitamente migraciones destructivas irreversibles.
8. **Fase 08** — Validar checksum/status contra DB de prueba limpia y DB con estado anterior (upgrade path).
9. **Fase 09** — Alinear JPA entity/mappers sin `ddl-auto=create/update`; verificar valores de seed idempotentes.
10. **Fase 10** — Probar despliegue primero DB luego app para cambios compatibles, observabilidad y plan de parada/mitigación.

## Guardrails y condiciones de bloqueo

- **NO**: No editar SQL de un changeset aplicado y luego `clearCheckSums` como solución rutinaria.
- **NO**: El repo contiene rutas `changes/` y `sql/`; usar solo grafo realmente incluido por master.
- **NO**: Nunca DROP o NOT NULL masivo sin análisis de data, locks, rollback/expand-contract.

## Operación paso a paso y ejemplos (leer al ejecutar)

- [PLAYBOOK: patrones, contratos, comandos, fallos y ejemplos](./references/PLAYBOOK.md)
- [ACCEPTANCE: matriz auditable de evidencia y pruebas](./references/ACCEPTANCE.md)
- [Checklist transversal de evidencias](./references/EVIDENCE_REPORT.md)
- [Worksheet técnico reutilizable](./examples/WORKSHEET.md)

## Comandos útiles — usar solo en el contexto adecuado

```bash
find src/main/resources/db/changelog -type f | sort
sed -n "1,120p" src/main/resources/db/changelog/db.changelog-master.yaml
./mvnw -Dtest=NombreIntegrationTest test
./mvnw verify
```

Los comandos con `Nombre...` o `group:artifact` son **plantillas**: sustituir por nombres reales antes de ejecutar. No usar build offline como prueba de versions GA; no interpretar `skipped` como aprobado.

## Definition of Done específico

- [ ] Un cambio desde DB previa y una instalación limpia convergen al mismo schema.
- [ ] Los tests detectan drift Hibernate/DDL y coherencia de mappers.
- [ ] El plan de rollback/mitigación cubre los datos antes/después.
### Dependencias y handoff

- Si la tarea toca simultáneamente **contrato HTTP, persistencia, seguridad, observabilidad, ADR o dependencias**, invocar/leer las skills especializadas de `.claude/skills/` para **esa** superficie. No crear una segunda implementación de la misma política.
- La documentación canónica de ingeniería existente (si está en checkout) vive en `docs/ai/`; leer solo la guía del dominio afectado: `ARCHITECTURE_RULES.md`, `TESTING_RULES.md`, `SECURITY_RULES.md`, `DEPENDENCY_POLICY.md`, `DEFINITION_OF_DONE.md`.
- La ruta del ejemplo `workitems` **no** es requisito de los equipos, ni fuente de verdad corporativa si se elimina.

## Contrato de salida obligatorio

Al concluir devolver: **(a)** resultado y alcance real; **(b)** tabla archivo→cambio→motivo; **(c)** contrato/riesgo/alternativas; **(d)** comandos realmente ejecutados y salida resumida con PASS/FAIL/SKIPPED/BLOCKED/NOT RUN; **(e)** pruebas faltantes + forma de ejecutarlas; **(f)** dependencias/compatibilidad/rollback; **(g)** documentos/ADR/changelog tocados; **(h)** decisión pendiente y owner si corresponde.

Nunca afirmar ejecución, aprobación, publicación, despliegue o vulnerabilidad corregida sin salida/evidencia verificable. No auto-commit ni push salvo solicitud explícita.
