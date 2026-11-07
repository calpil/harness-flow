---
description: Reglas de seguridad para Data Products, APIs y credenciales en Python
globs: ["src/**", ".env*"]
---

# Reglas de Seguridad en Python Data Product

- PROHIBIDO hardcodear secretos, API keys, tokens o credenciales de base de datos en código fuente o archivos de configuración.
- Toda credencial debe cargarse mediante variables de entorno a través de `pydantic-settings` o almacén de secretos.
- Consultas SQL parametrizadas exclusivamente; PROHIBIDA la interpolación de f-strings en queries SQL (`f"SELECT ... WHERE id = '{id}'"`).
- Respuestas de error estandarizadas bajo RFC 7807 (`application/problem+json`) sin exponer trazas de excepciones internas ni nombres de tablas.
- En endpoints FastAPI, aplicar validación estricta de esquemas Pydantic y cabeceras de seguridad HTTP (`X-Content-Type-Options: nosniff`).
