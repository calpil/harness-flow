---
name: changelog
description: "Maintain an accurate, human-readable CHANGELOG.md based on verified git diff and actual versioned features/fixes/security/deprecations. Use after meaningful changes, dependency upgrades, migration changes or release preparation; preserve historical decisions and avoid fabricated issues."
---

# Keep a Changelog / Traceable Release History — CALPIL Engineering Skill

> Skill ejecutable por GitHub Copilot/Claude Code. Ruta única: `.claude/skills/changelog/`. Cada conclusión exige evidencia: no completar casillas con suposiciones.

## Cuándo activar y no activar

**Activar** cuando el usuario pide trabajo de keep a changelog / traceable release history o una historia/cambio que involucra esa superficie.
**No activar** para solicitudes ajenas al alcance; no modificar dependencias, seguridad ni documentación no relacionada para inflar el diff.

## Contrato de entrada (descubrir antes de tocar código)

1. Diff o rango de commits correcto (base/HEAD).
2. SemVer objetivo solo si hay release explícita.
3. Ticket, PR y ADR solamente cuando están verificados.

Si falta una definición no bloqueante, continuar con supuesto explícito conservador y anotarlo; **nunca asumir aprobaciones, identidades o riesgo de producción**. Si falta requisito esencial de seguridad/integridad, dejarlo como bloqueo y no declarar listo.

## Preflight obligatorio

1. Confirmar raíz del repositorio y revisar `git status --short` para no pisar cambios ajenos.
2. Leer los archivos de la superficie implicada (no todo el repo); identificar cómo se prueba actualmente.
3. Distinguir hechos observados, hipótesis, supuestos y decisiones pendientes.
4. Crear mini-plan: archivos, riesgos, tests y efectos colaterales antes de editar.

## Workflow obligatorio, en secuencia

1. **Fase 01** — Leer encabezado y categorías existentes del changelog; no borrar historial ni cambiar estilo de releases publicados.
2. **Fase 02** — Identificar cambios verificables con git diff y commits en alcance, no memoria ni texto generado.
3. **Fase 03** — Agrupar por Added, Changed, Deprecated, Removed, Fixed y Security.
4. **Fase 04** — Escribir una línea accionable por cambio visible para consumidores, no por archivo ni por refactor interno irrelevante.
5. **Fase 05** — En ruptura de contrato incluir instrucciones de migración y compatibilidad.
6. **Fase 06** — En migraciones DB describir efecto para datos/operaciones y requisito de rollback sin prometer reversibilidad.
7. **Fase 07** — En seguridad adjuntar evidencia del cambio y no decir CVE remediada sin comprobación transitiva.
8. **Fase 08** — En versiones incluir versión+fecha solo de release real, no fecha futura ni hash inventado.
9. **Fase 09** — Eliminar duplicados entre tickets y cambios; mantener Unreleased al tope.
10. **Fase 10** — Mostrar diff de changelog y relacionar DEPENDENCIES/VERSIONS/ADR cuando se afecten.

## Guardrails y condiciones de bloqueo

- **NO**: No inventar issue IDs/PRs/fechas/autores.
- **NO**: No incluir secretos, nombres de clientes u otros datos privados en notas públicas.
- **NO**: No reescribir releases históricas para acomodar notas recientes.

## Operación paso a paso y ejemplos (leer al ejecutar)

- [PLAYBOOK: patrones, contratos, comandos, fallos y ejemplos](./references/PLAYBOOK.md)
- [ACCEPTANCE: matriz auditable de evidencia y pruebas](./references/ACCEPTANCE.md)
- [Checklist transversal de evidencias](./references/EVIDENCE_REPORT.md)

## Comandos útiles — usar solo en el contexto adecuado

```bash
git diff --name-status
git log -n 10 --oneline
git diff -- CHANGELOG.md
```

Los comandos con `Nombre...` o `group:artifact` son **plantillas**: sustituir por nombres reales antes de ejecutar. No usar build offline como prueba de versions GA; no interpretar `skipped` como aprobado.

## Definition of Done específico

- [ ] Cada línea se puede respaldar en diff/commit existente.
- [ ] Queda bien clasificado Unreleased y secciones publicadas intactas.
- [ ] Incluye impacto y acciones de migración cuando corresponde.
### Dependencias y handoff

- Si la tarea toca simultáneamente **contrato HTTP, persistencia, seguridad, observabilidad, ADR o dependencias**, invocar/leer las skills especializadas de `.claude/skills/` para **esa** superficie. No crear una segunda implementación de la misma política.
- La documentación canónica de ingeniería existente (si está en checkout) vive en `docs/ai/`; leer solo la guía del dominio afectado: `ARCHITECTURE_RULES.md`, `TESTING_RULES.md`, `SECURITY_RULES.md`, `DEPENDENCY_POLICY.md`, `DEFINITION_OF_DONE.md`.
- La ruta del ejemplo `workitems` **no** es requisito de los equipos, ni fuente de verdad corporativa si se elimina.

## Contrato de salida obligatorio

Al concluir devolver: **(a)** resultado y alcance real; **(b)** tabla archivo→cambio→motivo; **(c)** contrato/riesgo/alternativas; **(d)** comandos realmente ejecutados y salida resumida con PASS/FAIL/SKIPPED/BLOCKED/NOT RUN; **(e)** pruebas faltantes + forma de ejecutarlas; **(f)** dependencias/compatibilidad/rollback; **(g)** documentos/ADR/changelog tocados; **(h)** decisión pendiente y owner si corresponde.

Nunca afirmar ejecución, aprobación, publicación, despliegue o vulnerabilidad corregida sin salida/evidencia verificable. No auto-commit ni push salvo solicitud explícita.
