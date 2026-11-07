---
name: prepare-release
description: "Prepare and verify a Spring Boot service release to Azure/AKS using SemVer, CI gates, artifact provenance, database migration compatibility, smoke tests, security, observability, rollback and change records. Use before promoting sandbox/nonprod/prod or cutting a version."
---

# Release Engineering / Operational Go-No-Go — CALPIL Engineering Skill

> Skill ejecutable por GitHub Copilot/Claude Code. Ruta única: `.claude/skills/prepare-release/`. Cada conclusión exige evidencia: no completar casillas con suposiciones.

## Cuándo activar y no activar

**Activar** cuando el usuario pide trabajo de release engineering / operational go-no-go o una historia/cambio que involucra esa superficie.
**No activar** para solicitudes ajenas al alcance; no modificar dependencias, seguridad ni documentación no relacionada para inflar el diff.

## Contrato de entrada (descubrir antes de tocar código)

1. Tag/version target, environment and release window.
2. Pipeline/service connection/AKS namespace/Helm settings exactos del proyecto.
3. Criterios de cambio, stakeholders y planes de mitigación.

Si falta una definición no bloqueante, continuar con supuesto explícito conservador y anotarlo; **nunca asumir aprobaciones, identidades o riesgo de producción**. Si falta requisito esencial de seguridad/integridad, dejarlo como bloqueo y no declarar listo.

## Preflight obligatorio

1. Confirmar raíz del repositorio y revisar `git status --short` para no pisar cambios ajenos.
2. Leer los archivos de la superficie implicada (no todo el repo); identificar cómo se prueba actualmente.
3. Distinguir hechos observados, hipótesis, supuestos y decisiones pendientes.
4. Crear mini-plan: archivos, riesgos, tests y efectos colaterales antes de editar.

## Workflow obligatorio, en secuencia

1. **Fase 01** — Definir alcance commit SHA/tag y registro de cambios; no crear release si código no es reproducible.
2. **Fase 02** — Comprobar lint/format, JUnit/ArchUnit/JaCoCo, SAST/SCA/IaC y dependencias según CI corporativo.
3. **Fase 03** — Confirmar JDK, Docker build reproducible, SBOM/provenance, tags inmutables y acceso a registry.
4. **Fase 04** — Revisar schema DB vs app y orden expand-contract; ensayar backup/restore o mitigación según impacto.
5. **Fase 05** — Verificar variables/Key Vault/service connections y permisos de ambiente, sin mostrar secretos.
6. **Fase 06** — Inspeccionar Helm chart, recursos, Gateway API, Front Door header trust, probes, HPA y límites.
7. **Fase 07** — Definir plan de despliegue canary/rolling, smoke API autenticada, telemetría y umbrales go/no-go.
8. **Fase 08** — Plan de rollback independiente para aplicación y estado de datos, con condiciones de abort.
9. **Fase 09** — Coordinar notas de release y changelog con riesgos conocidos/usuarios afectados.
10. **Fase 10** — Emitir checklist con PASS/FAIL/NOT RUN/BLOCKED, evidencia, owners y ventana de monitoreo.

## Guardrails y condiciones de bloqueo

- **NO**: No promover con seguridad demo `permitAll` sin evidencia compensatoria aprobada.
- **NO**: No declarar integración validada si Testcontainers se omitió por falta de Docker.
- **NO**: No confundir rollback de manifiesto Helm con rollback reversible de datos.

## Operación paso a paso y ejemplos (leer al ejecutar)

- [PLAYBOOK: patrones, contratos, comandos, fallos y ejemplos](./references/PLAYBOOK.md)
- [ACCEPTANCE: matriz auditable de evidencia y pruebas](./references/ACCEPTANCE.md)
- [Checklist transversal de evidencias](./references/EVIDENCE_REPORT.md)
- [Worksheet técnico reutilizable](./examples/WORKSHEET.md)

## Comandos útiles — usar solo en el contexto adecuado

```bash
./mvnw verify
git rev-parse HEAD
git status --short
bash scripts/organize-docs.sh --dry-run
```

Los comandos con `Nombre...` o `group:artifact` son **plantillas**: sustituir por nombres reales antes de ejecutar. No usar build offline como prueba de versions GA; no interpretar `skipped` como aprobado.

## Definition of Done específico

- [ ] Evidencia de gates y versionado concreto; ninguna aprobación inventada.
- [ ] Compatibilidad de versiones de DB/Helm/app y smoke checks conocidos.
- [ ] Plan de rollback/forward-fix que distingue datos y runtime.
### Dependencias y handoff

- Si la tarea toca simultáneamente **contrato HTTP, persistencia, seguridad, observabilidad, ADR o dependencias**, invocar/leer las skills especializadas de `.claude/skills/` para **esa** superficie. No crear una segunda implementación de la misma política.
- La documentación canónica de ingeniería existente (si está en checkout) vive en `docs/ai/`; leer solo la guía del dominio afectado: `ARCHITECTURE_RULES.md`, `TESTING_RULES.md`, `SECURITY_RULES.md`, `DEPENDENCY_POLICY.md`, `DEFINITION_OF_DONE.md`.
- La ruta del ejemplo `workitems` **no** es requisito de los equipos, ni fuente de verdad corporativa si se elimina.

## Contrato de salida obligatorio

Al concluir devolver: **(a)** resultado y alcance real; **(b)** tabla archivo→cambio→motivo; **(c)** contrato/riesgo/alternativas; **(d)** comandos realmente ejecutados y salida resumida con PASS/FAIL/SKIPPED/BLOCKED/NOT RUN; **(e)** pruebas faltantes + forma de ejecutarlas; **(f)** dependencias/compatibilidad/rollback; **(g)** documentos/ADR/changelog tocados; **(h)** decisión pendiente y owner si corresponde.

Nunca afirmar ejecución, aprobación, publicación, despliegue o vulnerabilidad corregida sin salida/evidencia verificable. No auto-commit ni push salvo solicitud explícita.
