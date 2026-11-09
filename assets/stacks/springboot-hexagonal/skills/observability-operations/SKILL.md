---
name: observability-operations
description: "Implement observability for Spring Boot APIs on AKS: request correlation, structured logs, Micrometer metrics and OpenTelemetry tracing, health probes, dashboards/alerts, redaction, SLOs, dependency instrumentation and production incident playbooks. Use for operational readiness and monitoring."
---

# Observability / SLO / AKS Operations — CALPIL Engineering Skill

> Skill compatible con todos los agentes (Claude Code, OpenAI Codex, Gemini CLI, Antigravity, Hermes, Grok, Kimi). Rutas: `.agents/skills/observability-operations/` o `.claude/skills/observability-operations/`. Cada conclusión exige evidencia: no completar casillas con suposiciones.

## Cuándo activar y no activar

**Activar** cuando el usuario pide trabajo de observability / slo / aks operations o una historia/cambio que involucra esa superficie.
**No activar** para solicitudes ajenas al alcance; no modificar dependencias, seguridad ni documentación no relacionada para inflar el diff.

## Contrato de entrada (descubrir antes de tocar código)

1. SLO o síntoma operativo (latencia, errores, saturación, disponibilidad).
2. Flujo y dependencias relevantes; cluster/namespace/release cuando aplica.
3. Canal de telemetría realmente habilitado y política de privacidad.

Si falta una definición no bloqueante, continuar con supuesto explícito conservador y anotarlo; **nunca asumir aprobaciones, identidades o riesgo de producción**. Si falta requisito esencial de seguridad/integridad, dejarlo como bloqueo y no declarar listo.

## Preflight obligatorio

1. Confirmar raíz del repositorio y revisar `git status --short` para no pisar cambios ajenos.
2. Leer los archivos de la superficie implicada (no todo el repo); identificar cómo se prueba actualmente.
3. Distinguir hechos observados, hipótesis, supuestos y decisiones pendientes.
4. Crear mini-plan: archivos, riesgos, tests y efectos colaterales antes de editar.

## Workflow obligatorio, en secuencia

1. **Fase 01** — Definir señales de usuario (rate/errors/duration/saturation) y SLI/SLO antes de crear dashboards.
2. **Fase 02** — Verificar filtros y correlation IDs presentes, propagación entrante/saliente con rechazo de IDs malformados.
3. **Fase 03** — Crear logs estructurados por operación con traceId/requestId/tenant pseudonimizado y sin secretos.
4. **Fase 04** — Configurar métricas Micrometer, histogramas solo cuando útiles, cardinalidad controlada y tags acotados.
5. **Fase 05** — Instrumentar trazas OTel para web, DB y clientes salientes; verificar sample/propagación/collector y spans costosos.
6. **Fase 06** — Definir health liveness/readiness/startup consistentes con Kubernetes; no poner dependencia externa frágil en liveness.
7. **Fase 07** — Diseñar alertas por síntomas/SLO y runbook de triage, no solo CPU o alarmas estáticas.
8. **Fase 08** — Definir timeouts/pools/retries y efecto cascada, agotamiento de conexiones, cierre ordenado.
9. **Fase 09** — Crear tests/logging sanitization y smoke tests que consulten endpoints técnicos protegidos.
10. **Fase 10** — Evidenciar dashboard, alert rules, cardinalidad y límites de costos/retención.

## Guardrails y condiciones de bloqueo

- **NO**: No insertar PII, tokens, API keys o payloads sensibles en spans/logs.
- **NO**: No confundir readiness y liveness; liveness que depende de DB provoca restart storms.
- **NO**: No etiquetar userId/tenant libre o resourceId como metric tags de alta cardinalidad.

## Operación paso a paso y ejemplos (leer al ejecutar)

- [PLAYBOOK: patrones, contratos, comandos, fallos y ejemplos](./references/PLAYBOOK.md)
- [ACCEPTANCE: matriz auditable de evidencia y pruebas](./references/ACCEPTANCE.md)
- [Checklist transversal de evidencias](./references/EVIDENCE_REPORT.md)
- [Worksheet técnico reutilizable](./examples/WORKSHEET.md)

## Comandos útiles — usar solo en el contexto adecuado

```bash
grep -R "CorrelationId\|micrometer\|management.endpoint" -n src/main/java src/main/resources pom.xml
./mvnw -Dtest=NombreObservabilityTest test
./mvnw verify
```

Los comandos con `Nombre...` o `group:artifact` son **plantillas**: sustituir por nombres reales antes de ejecutar. No usar build offline como prueba de versions GA; no interpretar `skipped` como aprobado.

## Definition of Done específico

- [ ] Al menos un request de prueba correlacionable a través de API y dependencia.
- [ ] Liveness/readiness, PII redaction y alertas SLO probadas.
- [ ] Existe runbook de incidente con comandos/evidencia y owners.
### Dependencias y handoff

- Si la tarea toca simultáneamente **contrato HTTP, persistencia, seguridad, observabilidad, ADR o dependencias**, invocar/leer las skills especializadas (`.agents/skills/` o `.claude/skills/`) para **esa** superficie. No crear una segunda implementación de la misma política.
- La documentación canónica de ingeniería existente (si está en checkout) vive en `docs/ai/`; leer solo la guía del dominio afectado: `ARCHITECTURE_RULES.md`, `TESTING_RULES.md`, `SECURITY_RULES.md`, `DEPENDENCY_POLICY.md`, `DEFINITION_OF_DONE.md`.
- La ruta del ejemplo `workitems` **no** es requisito de los equipos, ni fuente de verdad corporativa si se elimina.

## Contrato de salida obligatorio

Al concluir devolver: **(a)** resultado y alcance real; **(b)** tabla archivo→cambio→motivo; **(c)** contrato/riesgo/alternativas; **(d)** comandos realmente ejecutados y salida resumida con PASS/FAIL/SKIPPED/BLOCKED/NOT RUN; **(e)** pruebas faltantes + forma de ejecutarlas; **(f)** dependencias/compatibilidad/rollback; **(g)** documentos/ADR/changelog tocados; **(h)** decisión pendiente y owner si corresponde.

Nunca afirmar ejecución, aprobación, publicación, despliegue o vulnerabilidad corregida sin salida/evidencia verificable. No auto-commit ni push salvo solicitud explícita.
