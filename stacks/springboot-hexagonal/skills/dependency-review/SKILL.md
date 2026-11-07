---
name: dependency-review
description: "Evaluate adding, removing, or replacing one Maven dependency based on technical necessity, transitive conflicts, security, license, Java/Boot compatibility, maintenance, operational impact and alternatives. Use for dependency requests or dependency risk assessment."
---

# Third-Party Dependency Architecture Review — CALPIL Engineering Skill

> Skill ejecutable por GitHub Copilot/Claude Code. Ruta única: `.claude/skills/dependency-review/`. Cada conclusión exige evidencia: no completar casillas con suposiciones.

## Cuándo activar y no activar

**Activar** cuando el usuario pide trabajo de third-party dependency architecture review o una historia/cambio que involucra esa superficie.
**No activar** para solicitudes ajenas al alcance; no modificar dependencias, seguridad ni documentación no relacionada para inflar el diff.

## Contrato de entrada (descubrir antes de tocar código)

1. Capacidad buscada y librerías candidatas.
2. Superficie de ejecución (runtime/test/build), licencias y repositorios.
3. Versión de Java, Boot y restricciones de seguridad actuales.

Si falta una definición no bloqueante, continuar con supuesto explícito conservador y anotarlo; **nunca asumir aprobaciones, identidades o riesgo de producción**. Si falta requisito esencial de seguridad/integridad, dejarlo como bloqueo y no declarar listo.

## Preflight obligatorio

1. Confirmar raíz del repositorio y revisar `git status --short` para no pisar cambios ajenos.
2. Leer los archivos de la superficie implicada (no todo el repo); identificar cómo se prueba actualmente.
3. Distinguir hechos observados, hipótesis, supuestos y decisiones pendientes.
4. Crear mini-plan: archivos, riesgos, tests y efectos colaterales antes de editar.

## Workflow obligatorio, en secuencia

1. **Fase 01** — Justificar la necesidad concreta; comprobar alternativa existente en Spring Boot BOM y JDK.
2. **Fase 02** — Determinar si la capacidad pertenece a domain, application o adapter; prohibir framework leak en core.
3. **Fase 03** — Consultar artefacto/release estable y fecha de publicación, política de soporte, licencia, transitive graph.
4. **Fase 04** — Inspeccionar CVEs con evidencia, deuda de mantenimiento, tamaño, reflection, startup y huella operacional.
5. **Fase 05** — Comparar mínimo tres opciones cuando hay decisión significativa: no agregar, usar dependencia actual, adoptar nueva.
6. **Fase 06** — Identificar owner de upgrades, plan de sustitución, SBOM y evidencia de cobertura.
7. **Fase 07** — Agregar scope exacto y evitar override del BOM cuando éste ya maneja la versión.
8. **Fase 08** — Crear test pequeño de integración de la capacidad, revisar grafo de dependencias y arranque.
9. **Fase 09** — Actualizar avisos VERSIONS/DEPENDENCIES y ADR cuando sea decisión de plataforma.

## Guardrails y condiciones de bloqueo

- **NO**: No agregar dependencia solo por costumbre o scaffolding.
- **NO**: Nunca considerar una dependencia segura por ausencia de resultados en un escáner desconectado.
- **NO**: No introducir SDKs externos en objetos del dominio.

## Operación paso a paso y ejemplos (leer al ejecutar)

- [PLAYBOOK: patrones, contratos, comandos, fallos y ejemplos](./references/PLAYBOOK.md)
- [ACCEPTANCE: matriz auditable de evidencia y pruebas](./references/ACCEPTANCE.md)
- [Checklist transversal de evidencias](./references/EVIDENCE_REPORT.md)

## Comandos útiles — usar solo en el contexto adecuado

```bash
./mvnw dependency:tree -Dincludes=group:artifact
./mvnw dependency:analyze
./mvnw -Dtest=NombrePruebaTest test
```

Los comandos con `Nombre...` o `group:artifact` son **plantillas**: sustituir por nombres reales antes de ejecutar. No usar build offline como prueba de versions GA; no interpretar `skipped` como aprobado.

## Definition of Done específico

- [ ] Hay valor funcional y alternativa descartada explícitamente.
- [ ] Versiones, CVEs y licencia comprobadas con fuentes trazables.
- [ ] Cambio reversible y test específico funcionando.
### Dependencias y handoff

- Si la tarea toca simultáneamente **contrato HTTP, persistencia, seguridad, observabilidad, ADR o dependencias**, invocar/leer las skills especializadas de `.claude/skills/` para **esa** superficie. No crear una segunda implementación de la misma política.
- La documentación canónica de ingeniería existente (si está en checkout) vive en `docs/ai/`; leer solo la guía del dominio afectado: `ARCHITECTURE_RULES.md`, `TESTING_RULES.md`, `SECURITY_RULES.md`, `DEPENDENCY_POLICY.md`, `DEFINITION_OF_DONE.md`.
- La ruta del ejemplo `workitems` **no** es requisito de los equipos, ni fuente de verdad corporativa si se elimina.

## Contrato de salida obligatorio

Al concluir devolver: **(a)** resultado y alcance real; **(b)** tabla archivo→cambio→motivo; **(c)** contrato/riesgo/alternativas; **(d)** comandos realmente ejecutados y salida resumida con PASS/FAIL/SKIPPED/BLOCKED/NOT RUN; **(e)** pruebas faltantes + forma de ejecutarlas; **(f)** dependencias/compatibilidad/rollback; **(g)** documentos/ADR/changelog tocados; **(h)** decisión pendiente y owner si corresponde.

Nunca afirmar ejecución, aprobación, publicación, despliegue o vulnerabilidad corregida sin salida/evidencia verificable. No auto-commit ni push salvo solicitud explícita.
