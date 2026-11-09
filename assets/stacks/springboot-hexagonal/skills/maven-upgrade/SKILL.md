---
name: maven-upgrade
description: "Upgrade Maven pom.xml and dependency/plugin versions to the latest verified stable compatible releases with Spring Boot 4/Java 21 constraints, managed BOM resolution, SBOM/security floors, incremental builds, Testcontainers/ArchUnit/JaCoCo gates, evidence and rollback. Use for dependency maintenance or a full pom refresh."
---

# Maven Upgrade / Compatibility and Security — CALPIL Engineering Skill

> Skill compatible con todos los agentes (Claude Code, OpenAI Codex, Gemini CLI, Antigravity, Hermes, Grok, Kimi). Rutas: `.agents/skills/maven-upgrade/` o `.claude/skills/maven-upgrade/`. Cada conclusión exige evidencia: no completar casillas con suposiciones.

## Cuándo activar y no activar

**Activar** cuando el usuario pide trabajo de maven upgrade / compatibility and security o una historia/cambio que involucra esa superficie.
**No activar** para solicitudes ajenas al alcance; no modificar dependencias, seguridad ni documentación no relacionada para inflar el diff.

## Contrato de entrada (descubrir antes de tocar código)

1. `pom.xml` actual, Maven wrapper y versión JDK.
2. Repositorio de artefactos accesible, restricciones de licencia y política interna.
3. Advisories/umbrales de seguridad conocidos, test infra Docker disponible o no.

Si falta una definición no bloqueante, continuar con supuesto explícito conservador y anotarlo; **nunca asumir aprobaciones, identidades o riesgo de producción**. Si falta requisito esencial de seguridad/integridad, dejarlo como bloqueo y no declarar listo.

## Preflight obligatorio

1. Confirmar raíz del repositorio y revisar `git status --short` para no pisar cambios ajenos.
2. Leer los archivos de la superficie implicada (no todo el repo); identificar cómo se prueba actualmente.
3. Distinguir hechos observados, hipótesis, supuestos y decisiones pendientes.
4. Crear mini-plan: archivos, riesgos, tests y efectos colaterales antes de editar.

## Workflow obligatorio, en secuencia

1. **Fase 01** — Capturar `git status`, JDK, Maven, parent, properties, plugins y overrides explícitos; emitir snapshot del baseline.
2. **Fase 02** — Ejecutar help:effective-pom, dependency:tree y dependency:analyze antes de tocar versiones.
3. **Fase 03** — Separar versiones administradas por Boot BOM de versiones realmente propias; explicar cada override.
4. **Fase 04** — Comprobar versiones estables disponibles en repos oficiales al momento de la ejecución, nunca adivinar la última.
5. **Fase 05** — Construir matriz Java/Jakarta/Boot/Spring Framework/Servlet/Tomcat/Jackson/springdoc/Testcontainers/Plugins.
6. **Fase 06** — Revisar advisories y pistas de regresión `DependencySecurityRegressionTest` antes y después.
7. **Fase 07** — Actualizar en lotes pequeños compatibles: parent y BOM, dependencias independientes, plugins de build; mantener registro de diff.
8. **Fase 08** — Resolver fallos por causa raíz (package changes, transitive conflicts, APIs, tests) sin excluir pruebas ni reducir calidad.
9. **Fase 09** — Comparar effective POM/tree antes/después, correr tests unitarios, ArchUnit, integración PostgreSQL y Maven verify.
10. **Fase 10** — Actualizar evidencia de versiones, changelog, restricciones, rollback y declarar explícitamente gates no ejecutados.

## Guardrails y condiciones de bloqueo

- **NO**: No incorporar RC/M/SNAPSHOT ni inventar versión de Maven Central.
- **NO**: No quitar pisos de seguridad de `commons-compress`, Spring/Jackson o transitive sin evidencia.
- **NO**: No declarar éxito con `-DskipTests` ni esconder falta de Docker como test aprobado.

## Operación paso a paso y ejemplos (leer al ejecutar)

- [PLAYBOOK: patrones, contratos, comandos, fallos y ejemplos](./references/PLAYBOOK.md)
- [ACCEPTANCE: matriz auditable de evidencia y pruebas](./references/ACCEPTANCE.md)
- [Checklist transversal de evidencias](./references/EVIDENCE_REPORT.md)
- [Worksheet técnico reutilizable](./examples/WORKSHEET.md)
- [Playbook Maven previo — referencia preservada](./references/UPGRADE_PLAYBOOK.md)
- [Matriz de evidencia Maven](./references/EVIDENCE_MATRIX.md)

## Comandos útiles — usar solo en el contexto adecuado

```bash
./mvnw -v
./mvnw -DskipTests help:effective-pom -Doutput=target/effective-pom.xml
./mvnw dependency:tree -Dverbose
./mvnw versions:display-dependency-updates
./mvnw -Dtest=DependencySecurityRegressionTest test
./mvnw verify
```

Los comandos con `Nombre...` o `group:artifact` son **plantillas**: sustituir por nombres reales antes de ejecutar. No usar build offline como prueba de versions GA; no interpretar `skipped` como aprobado.

## Definition of Done específico

- [ ] Matriz versión→origen→compatibilidad→evidencia completa, sin versiones inventadas.
- [ ] No regresan los mínimos de seguridad y el dependency tree realmente resuelto es coherente.
- [ ] La actualización de Springdoc vs Boot 4 se valida compilando, no cambiando números a ojo.
### Dependencias y handoff

- Si la tarea toca simultáneamente **contrato HTTP, persistencia, seguridad, observabilidad, ADR o dependencias**, invocar/leer las skills especializadas (`.agents/skills/` o `.claude/skills/`) para **esa** superficie. No crear una segunda implementación de la misma política.
- La documentación canónica de ingeniería existente (si está en checkout) vive en `docs/ai/`; leer solo la guía del dominio afectado: `ARCHITECTURE_RULES.md`, `TESTING_RULES.md`, `SECURITY_RULES.md`, `DEPENDENCY_POLICY.md`, `DEFINITION_OF_DONE.md`.
- La ruta del ejemplo `workitems` **no** es requisito de los equipos, ni fuente de verdad corporativa si se elimina.

## Contrato de salida obligatorio

Al concluir devolver: **(a)** resultado y alcance real; **(b)** tabla archivo→cambio→motivo; **(c)** contrato/riesgo/alternativas; **(d)** comandos realmente ejecutados y salida resumida con PASS/FAIL/SKIPPED/BLOCKED/NOT RUN; **(e)** pruebas faltantes + forma de ejecutarlas; **(f)** dependencias/compatibilidad/rollback; **(g)** documentos/ADR/changelog tocados; **(h)** decisión pendiente y owner si corresponde.

Nunca afirmar ejecución, aprobación, publicación, despliegue o vulnerabilidad corregida sin salida/evidencia verificable. No auto-commit ni push salvo solicitud explícita.
