---
description: Límites de seguridad para APIs, configuración y secretos
globs: ["src/**", "Dockerfile", ".env.example"]
---
- No secretos en código, configuración ni logs. `.env.example` es documental.
- API stateless: validar JWT real, scopes/roles/tenants y autorización por recurso en integración productiva.
- `SecurityConfig` actual de ejemplo usa `permitAll`; nunca reportar Entra ID como operativo sin configurarlo y probar 401/403.
- Adaptadores traducen fallos a Problem Details seguros; imagen non-root y runtime mínimo.
- Detalle aplicable: `docs/ai/SECURITY_RULES.md` y `.claude/skills/security-review/SKILL.md`.
