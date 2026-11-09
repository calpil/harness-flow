---
description: Límites de seguridad para APIs, configuración y gestión de secretos en Golang
globs: ["internal/**", "cmd/**", "Dockerfile", ".env*"]
---

# Reglas de Seguridad en Golang

- Prohibido incluir secretos, credenciales, tokens o connection strings hardcodeados en código o archivos de configuración.
- Toda configuración sensible se inyecta por variables de entorno leídas a través de `internal/platform/config`.
- Las respuestas de error hacia el cliente deben seguir RFC 7807 (`application/problem+json`) y jamás exponer stack traces, nombres de tablas, queries SQL ni detalles internos del runtime.
- Headers de seguridad mandatorios en toda respuesta HTTP (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`).
- Correlación obligatoria mediante `X-Correlation-ID` en logs y trazas de error para auditoría sin filtrar datos PII.
- Validar rigurosamente los payloads entrantes (`Validate()` en DTOs) antes de llegar a la capa de aplicación.
