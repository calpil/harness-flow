---
name: springboot
description: "Implement, configure or refactor a Java 21 Spring Boot hexagonal service using CALPIL golden-path conventions: module boundaries, dependency injection, profiles, configuration, startup, security, persistence and release readiness. Use on broad Spring Boot work or when a change spans layers."
---

# Spring Boot / Java 21 Golden Path — CALPIL Engineering Skill

> Skill compatible con todos los agentes (Claude Code, OpenAI Codex, Gemini CLI, Antigravity, Hermes, Grok, Kimi). Rutas: `.agents/skills/springboot/` o `.claude/skills/springboot/`. Cada conclusión exige evidencia: no completar casillas con suposiciones.

## Cuándo activar y no activar

**Activar** cuando el usuario pide trabajo de spring boot / java 21 golden path o una historia/cambio que involucra esa superficie.
**No activar** para solicitudes ajenas al alcance; no modificar dependencias, seguridad ni documentación no relacionada para inflar el diff.

## Contrato de entrada (descubrir antes de tocar código)

1. Caso de negocio y ambientes afectados (sandbox/nonprod/prod).
2. Comandos reproducibles, JDK, Maven wrapper, profile, dependencias reales.
3. API/DB/seguridad/infra que se modifican; expectativas de compatibilidad.

Si falta una definición no bloqueante, continuar con supuesto explícito conservador y anotarlo; **nunca asumir aprobaciones, identidades o riesgo de producción**. Si falta requisito esencial de seguridad/integridad, dejarlo como bloqueo y no declarar listo.

## Preflight obligatorio

1. Confirmar raíz del repositorio y revisar `git status --short` para no pisar cambios ajenos.
2. Leer los archivos de la superficie implicada (no todo el repo); identificar cómo se prueba actualmente.
3. Distinguir hechos observados, hipótesis, supuestos y decisiones pendientes.
4. Crear mini-plan: archivos, riesgos, tests y efectos colaterales antes de editar.

## Workflow obligatorio, en secuencia

1. **Fase 01** — Situar el cambio con `git status --short`, `pom.xml`, `application.yml` y paquetes implicados; no explorar indiscriminadamente.
2. **Fase 02** — Crear un mapa antes/después de módulos y ruta de llamada entrada → port in → caso de uso → domain → port out → adapter out.
3. **Fase 03** — Aislar dominio Java puro; aplicación con interfaces/puertos y sin imports de Spring/JPA/HTTP; inyección por composition root.
4. **Fase 04** — Definir contratos explícitos y comprobables (HTTP/DB/events/config), actores y errores; verificar versiones actuales antes de asumir dependencias.
5. **Fase 05** — Resolver persistencia con changelog Liquibase ordenado y mappers JPA exclusivos de infraestructura; `ddl-auto=validate` donde corresponda.
6. **Fase 06** — Diseñar seguridad desde identidad confiable: JWT issuer/audience/scopes, autorización por acción/recurso/tenant y pruebas negativas.
7. **Fase 07** — Definir configuración por ambiente con variables/Key Vault; verificar health, readiness, startup y shutdown, sin loggear secretos.
8. **Fase 08** — Programar pruebas por capa (dominio, caso de uso, adapter, contrato, arquitectura, integración real) antes de dar por terminado.
9. **Fase 09** — Revisar consecuencias para runtime (timeouts, pools, retries, idempotencia, transacciones, métricas, features, despliegue).
10. **Fase 10** — Ejecutar gate focal y `./mvnw verify` para corte transversal; registrar fallas reales y riesgos residuales.

## Guardrails y condiciones de bloqueo

- **NO**: No introducir `@Service`, `@Entity`, `ResponseEntity` ni `org.springframework.*` en domain.
- **NO**: Nunca fingir que `anyRequest().permitAll()` equivale a authz corporativa.
- **NO**: El paquete `workitems` es demostrativo; debe poder eliminarse sin romper las convenciones del template.

## Operación paso a paso y ejemplos (leer al ejecutar)

- [PLAYBOOK: patrones, contratos, comandos, fallos y ejemplos](./references/PLAYBOOK.md)
- [ACCEPTANCE: matriz auditable de evidencia y pruebas](./references/ACCEPTANCE.md)
- [Checklist transversal de evidencias](./references/EVIDENCE_REPORT.md)

## Comandos útiles — usar solo en el contexto adecuado

```bash
./mvnw -v
./mvnw -DskipTests help:effective-pom -Doutput=target/effective-pom.xml
./mvnw -Dtest=HexagonalArchitectureTest test
./mvnw verify
```

Los comandos con `Nombre...` o `group:artifact` son **plantillas**: sustituir por nombres reales antes de ejecutar. No usar build offline como prueba de versions GA; no interpretar `skipped` como aprobado.

## Definition of Done específico

- [ ] Los límites son respetados por ArchUnit; config e infraestructura fuera de domain/application.
- [ ] Los endpoints y migraciones coinciden con contrato y pruebas; rollback abordado.
- [ ] Compilación y pruebas reportadas con resultados de la ejecución actual.
### Dependencias y handoff

- Si la tarea toca simultáneamente **contrato HTTP, persistencia, seguridad, observabilidad, ADR o dependencias**, invocar/leer las skills especializadas (`.agents/skills/` o `.claude/skills/`) para **esa** superficie. No crear una segunda implementación de la misma política.
- La documentación canónica de ingeniería existente (si está en checkout) vive en `docs/ai/`; leer solo la guía del dominio afectado: `ARCHITECTURE_RULES.md`, `TESTING_RULES.md`, `SECURITY_RULES.md`, `DEPENDENCY_POLICY.md`, `DEFINITION_OF_DONE.md`.
- La ruta del ejemplo `workitems` **no** es requisito de los equipos, ni fuente de verdad corporativa si se elimina.

## Contrato de salida obligatorio

Al concluir devolver: **(a)** resultado y alcance real; **(b)** tabla archivo→cambio→motivo; **(c)** contrato/riesgo/alternativas; **(d)** comandos realmente ejecutados y salida resumida con PASS/FAIL/SKIPPED/BLOCKED/NOT RUN; **(e)** pruebas faltantes + forma de ejecutarlas; **(f)** dependencias/compatibilidad/rollback; **(g)** documentos/ADR/changelog tocados; **(h)** decisión pendiente y owner si corresponde.

Nunca afirmar ejecución, aprobación, publicación, despliegue o vulnerabilidad corregida sin salida/evidencia verificable. No auto-commit ni push salvo solicitud explícita.
