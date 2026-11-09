---
name: documentation-maintenance
description: "Update and organize Spring Boot template Markdown documentation, architecture standards, Runbooks, README, links and prompt references; keep the repository root minimal and the canonical docs current. Use after structural, API, deployment or process changes."
---

# Documentation as Code / Link Integrity — CALPIL Engineering Skill

> Skill compatible con todos los agentes (Claude Code, OpenAI Codex, Gemini CLI, Antigravity, Hermes, Grok, Kimi). Rutas: `.agents/skills/documentation-maintenance/` o `.claude/skills/documentation-maintenance/`. Cada conclusión exige evidencia: no completar casillas con suposiciones.

## Cuándo activar y no activar

**Activar** cuando el usuario pide trabajo de documentation as code / link integrity o una historia/cambio que involucra esa superficie.
**No activar** para solicitudes ajenas al alcance; no modificar dependencias, seguridad ni documentación no relacionada para inflar el diff.

## Contrato de entrada (descubrir antes de tocar código)

1. Cambio técnico verificado que debe documentarse.
2. Audiencia (dev, operación, arquitectura) y documento canónico.
3. Estado Git y árbol de docs para evitar sobrescribir modificaciones.

Si falta una definición no bloqueante, continuar con supuesto explícito conservador y anotarlo; **nunca asumir aprobaciones, identidades o riesgo de producción**. Si falta requisito esencial de seguridad/integridad, dejarlo como bloqueo y no declarar listo.

## Preflight obligatorio

1. Confirmar raíz del repositorio y revisar `git status --short` para no pisar cambios ajenos.
2. Leer los archivos de la superficie implicada (no todo el repo); identificar cómo se prueba actualmente.
3. Distinguir hechos observados, hipótesis, supuestos y decisiones pendientes.
4. Crear mini-plan: archivos, riesgos, tests y efectos colaterales antes de editar.

## Workflow obligatorio, en secuencia

1. **Fase 01** — Inventariar documentación afectada por feature, seguridad, operabilidad o contrato.
2. **Fase 02** — Decidir documento canónico para cada tema; no duplicar listas de versiones o decisiones.
3. **Fase 03** — Ejecutar organizador `--dry-run` y revisar rutas destino/colisiones antes de aplicar.
4. **Fase 04** — Preservar README, CHANGELOG, LICENCE, AGENTS y guía de entrada en raíz; docs técnicos en subcarpetas.
5. **Fase 05** — Actualizar instrucciones por secuencia reproducible: prerequisitos, comandos reales, outputs y rollback.
6. **Fase 06** — Actualizar enlaces Markdown relativos, anchors y rutas de imágenes/scripts tras moves.
7. **Fase 07** — Revisar que rutas (.agents/skills o .claude/skills) se resuelvan desde el repo real.
8. **Fase 08** — No confundir documentación del template con evidencia de cumplimiento productivo.
9. **Fase 09** — Ejecutar validador de customizaciones y git diff --check; revisar enlaces rotos.
10. **Fase 10** — Resumir archivos movidos, reemplazados y contenido expresamente preservado.

## Guardrails y condiciones de bloqueo

- **NO**: No ejecutar `mv` masivo sin dry-run cuando haya archivos homónimos o local changes.
- **NO**: No sustituir contenido existente para dejar una carpeta bonita.
- **NO**: No crear una segunda copia de skills en `.github/skills`.

## Operación paso a paso y ejemplos (leer al ejecutar)

- [PLAYBOOK: patrones, contratos, comandos, fallos y ejemplos](./references/PLAYBOOK.md)
- [ACCEPTANCE: matriz auditable de evidencia y pruebas](./references/ACCEPTANCE.md)
- [Checklist transversal de evidencias](./references/EVIDENCE_REPORT.md)

## Comandos útiles — usar solo en el contexto adecuado

```bash
bash scripts/organize-docs.sh --dry-run
bash scripts/organize-docs.sh --apply
python3 scripts/validate-copilot-customizations.py
git diff --check
```

Los comandos con `Nombre...` o `group:artifact` son **plantillas**: sustituir por nombres reales antes de ejecutar. No usar build offline como prueba de versions GA; no interpretar `skipped` como aprobado.

## Definition of Done específico

- [ ] Enlaces locales de docs/prompts/skills verifican en repo de prueba.
- [ ] Root mínimo y documentación canónica inequívoca.
- [ ] Script idempotente sin sobrescribir material existente.
### Dependencias y handoff

- Si la tarea toca simultáneamente **contrato HTTP, persistencia, seguridad, observabilidad, ADR o dependencias**, invocar/leer las skills especializadas (`.agents/skills/` o `.claude/skills/`) para **esa** superficie. No crear una segunda implementación de la misma política.
- La documentación canónica de ingeniería existente (si está en checkout) vive en `docs/ai/`; leer solo la guía del dominio afectado: `ARCHITECTURE_RULES.md`, `TESTING_RULES.md`, `SECURITY_RULES.md`, `DEPENDENCY_POLICY.md`, `DEFINITION_OF_DONE.md`.
- La ruta del ejemplo `workitems` **no** es requisito de los equipos, ni fuente de verdad corporativa si se elimina.

## Contrato de salida obligatorio

Al concluir devolver: **(a)** resultado y alcance real; **(b)** tabla archivo→cambio→motivo; **(c)** contrato/riesgo/alternativas; **(d)** comandos realmente ejecutados y salida resumida con PASS/FAIL/SKIPPED/BLOCKED/NOT RUN; **(e)** pruebas faltantes + forma de ejecutarlas; **(f)** dependencias/compatibilidad/rollback; **(g)** documentos/ADR/changelog tocados; **(h)** decisión pendiente y owner si corresponde.

Nunca afirmar ejecución, aprobación, publicación, despliegue o vulnerabilidad corregida sin salida/evidencia verificable. No auto-commit ni push salvo solicitud explícita.
