---
name: debug-targeted
description: "Diagnose and fix a concrete Java/Spring/Maven/PostgreSQL/Liquibase/security/AKS failure by reproducing the issue, isolating root cause, applying the smallest correct fix, adding regression tests and proving no collateral breakage. Use for build, runtime, integration or CI failures."
---

# Root-Cause Debugging / Reproducible Fix — CALPIL Engineering Skill

> Skill ejecutable por GitHub Copilot/Claude Code. Ruta única: `.claude/skills/debug-targeted/`. Cada conclusión exige evidencia: no completar casillas con suposiciones.

## Cuándo activar y no activar

**Activar** cuando el usuario pide trabajo de root-cause debugging / reproducible fix o una historia/cambio que involucra esa superficie.
**No activar** para solicitudes ajenas al alcance; no modificar dependencias, seguridad ni documentación no relacionada para inflar el diff.

## Contrato de entrada (descubrir antes de tocar código)

1. Error exacto con versión/tiempo y entorno.
2. Comando/endpoint del fallo, commit reciente y primer frame propio.
3. Resultado esperado vs observado, reproducibilidad y alcance.

Si falta una definición no bloqueante, continuar con supuesto explícito conservador y anotarlo; **nunca asumir aprobaciones, identidades o riesgo de producción**. Si falta requisito esencial de seguridad/integridad, dejarlo como bloqueo y no declarar listo.

## Preflight obligatorio

1. Confirmar raíz del repositorio y revisar `git status --short` para no pisar cambios ajenos.
2. Leer los archivos de la superficie implicada (no todo el repo); identificar cómo se prueba actualmente.
3. Distinguir hechos observados, hipótesis, supuestos y decisiones pendientes.
4. Crear mini-plan: archivos, riesgos, tests y efectos colaterales antes de editar.

## Workflow obligatorio, en secuencia

1. **Fase 01** — Guardar output/error literal sanitizado y contexto de versión, profile, commit y ambiente.
2. **Fase 02** — Crear reproducer mínimo, controlando puertos, DB, claves y variables; nunca mostrar credenciales.
3. **Fase 03** — Clasificar fallo: compile, classpath/BOM, Spring beans, Hibernate/Liquibase, HTTP auth, DB, Docker, AKS, tests.
4. **Fase 04** — Formular hasta tres hipótesis ordenadas por evidencia con prueba discriminante de cada una.
5. **Fase 05** — Inspeccionar solo símbolos implicados y sus callers/versions; comparar commit diffs recientes.
6. **Fase 06** — Aislar causa raíz de síntomas secundarios, dejando trazabilidad comando→output→conclusión.
7. **Fase 07** — Aplicar corrección más pequeña sin bajar seguridad ni gates, preservando contratos y arquitectura.
8. **Fase 08** — Agregar prueba de regresión que reproduzca el síntoma, idealmente roja antes del arreglo.
9. **Fase 09** — Re-ejecutar reproducer y pruebas de borde; para cambio transversal ejecutar verify.
10. **Fase 10** — Registrar explicación causal y posibles efectos laterales, rollback y pendientes verificables.

## Guardrails y condiciones de bloqueo

- **NO**: No adivinar causas de `ClassNotFoundException` actualizando todas las versiones.
- **NO**: No modificar `mvnw`, excluir tests ni hacer `clearCheckSums` para que arranque.
- **NO**: No diagnosticar falta de Docker como fracaso del caso de uso ni como test exitoso.

## Operación paso a paso y ejemplos (leer al ejecutar)

- [PLAYBOOK: patrones, contratos, comandos, fallos y ejemplos](./references/PLAYBOOK.md)
- [ACCEPTANCE: matriz auditable de evidencia y pruebas](./references/ACCEPTANCE.md)
- [Checklist transversal de evidencias](./references/EVIDENCE_REPORT.md)

## Comandos útiles — usar solo en el contexto adecuado

```bash
./mvnw -v
./mvnw -Dtest=NombrePruebaTest test
./mvnw dependency:tree -Dincludes=group:artifact
git diff -- pom.xml src/main src/test
```

Los comandos con `Nombre...` o `group:artifact` son **plantillas**: sustituir por nombres reales antes de ejecutar. No usar build offline como prueba de versions GA; no interpretar `skipped` como aprobado.

## Definition of Done específico

- [ ] Existe reproducción original y resultado contrastado después.
- [ ] Un único mecanismo causal explica el fallo y la corrección.
- [ ] La prueba de regresión y otros componentes afectados se informan honestamente.
### Dependencias y handoff

- Si la tarea toca simultáneamente **contrato HTTP, persistencia, seguridad, observabilidad, ADR o dependencias**, invocar/leer las skills especializadas de `.claude/skills/` para **esa** superficie. No crear una segunda implementación de la misma política.
- La documentación canónica de ingeniería existente (si está en checkout) vive en `docs/ai/`; leer solo la guía del dominio afectado: `ARCHITECTURE_RULES.md`, `TESTING_RULES.md`, `SECURITY_RULES.md`, `DEPENDENCY_POLICY.md`, `DEFINITION_OF_DONE.md`.
- La ruta del ejemplo `workitems` **no** es requisito de los equipos, ni fuente de verdad corporativa si se elimina.

## Contrato de salida obligatorio

Al concluir devolver: **(a)** resultado y alcance real; **(b)** tabla archivo→cambio→motivo; **(c)** contrato/riesgo/alternativas; **(d)** comandos realmente ejecutados y salida resumida con PASS/FAIL/SKIPPED/BLOCKED/NOT RUN; **(e)** pruebas faltantes + forma de ejecutarlas; **(f)** dependencias/compatibilidad/rollback; **(g)** documentos/ADR/changelog tocados; **(h)** decisión pendiente y owner si corresponde.

Nunca afirmar ejecución, aprobación, publicación, despliegue o vulnerabilidad corregida sin salida/evidencia verificable. No auto-commit ni push salvo solicitud explícita.
