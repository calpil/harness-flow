---
name: security-review
description: "Review and harden Spring Boot API security end-to-end: Entra ID OAuth2 JWT validation, scopes/roles, per-resource and per-tenant authorization, API keys, secrets, injection, outbound clients, logging, rate limits, CSRF/CORS and negative security tests. Use for security-sensitive changes or audits."
---

# Security Review — API, BFF Integration, Tenant and Runtime — CALPIL Engineering Skill

> Skill ejecutable por GitHub Copilot/Claude Code. Ruta única: `.claude/skills/security-review/`. Cada conclusión exige evidencia: no completar casillas con suposiciones.

## Cuándo activar y no activar

**Activar** cuando el usuario pide trabajo de security review — api, bff integration, tenant and runtime o una historia/cambio que involucra esa superficie.
**No activar** para solicitudes ajenas al alcance; no modificar dependencias, seguridad ni documentación no relacionada para inflar el diff.

## Contrato de entrada (descubrir antes de tocar código)

1. Actores, proveedores IdP, trusts y exposición API/BFF.
2. Mapa endpoint→permiso→recurso→tenant, datos sensibles y secretos.
3. Configuración por ambiente y evidencia real de controles ya implementados.

Si falta una definición no bloqueante, continuar con supuesto explícito conservador y anotarlo; **nunca asumir aprobaciones, identidades o riesgo de producción**. Si falta requisito esencial de seguridad/integridad, dejarlo como bloqueo y no declarar listo.

## Preflight obligatorio

1. Confirmar raíz del repositorio y revisar `git status --short` para no pisar cambios ajenos.
2. Leer los archivos de la superficie implicada (no todo el repo); identificar cómo se prueba actualmente.
3. Distinguir hechos observados, hipótesis, supuestos y decisiones pendientes.
4. Crear mini-plan: archivos, riesgos, tests y efectos colaterales antes de editar.

## Workflow obligatorio, en secuencia

1. **Fase 01** — Mapear ataque desde request hasta DB y downstream, assets protegidos y boundary BFF/backend.
2. **Fase 02** — Verificar que identidad se obtiene de token validado (issuer, audience, exp, nbf, signature, scopes/roles).
3. **Fase 03** — Separar authentication de authorization; proteger cada acción y cada recurso dentro del use case/servicio apropiado.
4. **Fase 04** — Tratar tenant del usuario como contexto confiable, rechazar acceso cruzado por ID aunque token sea válido.
5. **Fase 05** — Revisar API keys técnicas, scope, expiración, rotación, revocación y redacción.
6. **Fase 06** — Evaluar input validation, binding, SQL, serialización, tamaño, carga/archivos, SSRF en outbound, CORS/CSRF según auth.
7. **Fase 07** — Verificar WAF/API gateway/rate limits como controles complementarios; no asumir que sustituyen autorización.
8. **Fase 08** — Auditar logs, exception handler, OpenAPI, actuator, health, TLS y secretos Key Vault.
9. **Fase 09** — Crear matriz 401/403/404/429, JWT malformado/vencido, tenant crossing y recurso ajeno; probar con Spring Security real.
10. **Fase 10** — Diferenciar controles corporativos existentes de controles demostrados por el proyecto; producir findings priorizados.

## Guardrails y condiciones de bloqueo

- **NO**: El baseline incluye `anyRequest().permitAll()`: CRÍTICO si no hay compensación probada; no vender como seguridad de producción.
- **NO**: Nunca registrar JWT/PAT/client secret ni datos personales en evidencias.
- **NO**: No deshabilitar autenticación para hacer pasar pruebas sin diseño explícito de entorno.

## Operación paso a paso y ejemplos (leer al ejecutar)

- [PLAYBOOK: patrones, contratos, comandos, fallos y ejemplos](./references/PLAYBOOK.md)
- [ACCEPTANCE: matriz auditable de evidencia y pruebas](./references/ACCEPTANCE.md)
- [Checklist transversal de evidencias](./references/EVIDENCE_REPORT.md)
- [Worksheet técnico reutilizable](./examples/WORKSHEET.md)

## Comandos útiles — usar solo en el contexto adecuado

```bash
sed -n "1,200p" src/main/java/com/calpil/template/platform/security/SecurityConfig.java
./mvnw -Dtest=NombreSecurityTest test
./mvnw -Dtest=DependencySecurityRegressionTest test
./mvnw verify
```

Los comandos con `Nombre...` o `group:artifact` son **plantillas**: sustituir por nombres reales antes de ejecutar. No usar build offline como prueba de versions GA; no interpretar `skipped` como aprobado.

## Definition of Done específico

- [ ] Matriz endpoint→principal→scope/rol→tenant/recurso→prueba negativa trazable.
- [ ] Vulnerabilidades reales priorizadas con evidencia; no confundir control definido vs implementado.
- [ ] Pruebas cubren evasión, acceso cruzado, errores 401/403 y falsos positivos.
### Dependencias y handoff

- Si la tarea toca simultáneamente **contrato HTTP, persistencia, seguridad, observabilidad, ADR o dependencias**, invocar/leer las skills especializadas de `.claude/skills/` para **esa** superficie. No crear una segunda implementación de la misma política.
- La documentación canónica de ingeniería existente (si está en checkout) vive en `docs/ai/`; leer solo la guía del dominio afectado: `ARCHITECTURE_RULES.md`, `TESTING_RULES.md`, `SECURITY_RULES.md`, `DEPENDENCY_POLICY.md`, `DEFINITION_OF_DONE.md`.
- La ruta del ejemplo `workitems` **no** es requisito de los equipos, ni fuente de verdad corporativa si se elimina.

## Contrato de salida obligatorio

Al concluir devolver: **(a)** resultado y alcance real; **(b)** tabla archivo→cambio→motivo; **(c)** contrato/riesgo/alternativas; **(d)** comandos realmente ejecutados y salida resumida con PASS/FAIL/SKIPPED/BLOCKED/NOT RUN; **(e)** pruebas faltantes + forma de ejecutarlas; **(f)** dependencias/compatibilidad/rollback; **(g)** documentos/ADR/changelog tocados; **(h)** decisión pendiente y owner si corresponde.

Nunca afirmar ejecución, aprobación, publicación, despliegue o vulnerabilidad corregida sin salida/evidencia verificable. No auto-commit ni push salvo solicitud explícita.
