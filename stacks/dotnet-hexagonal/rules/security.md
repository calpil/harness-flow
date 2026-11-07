---
description: Límites de seguridad para APIs, configuración y consultas SQL en .NET
globs: ["src/**", "Dockerfile", "appsettings*.json"]
---

# Reglas de Seguridad en .NET / C#

- Prohibido hardcodear contraseñas, connection strings, API keys o secretos en archivos de código o en `appsettings.json`.
- Toda credencial sensible debe provenir de variables de entorno (`DATABASE_URL`, etc.) o Azure Key Vault en producción.
- En Dapper / ADO.NET, todas las consultas SQL deben usar parámetros tipados (`@Id`, `@Title`). Prohibida la interpolación directa de cadenas SQL (`$"SELECT ... WHERE id = '{id}'"`).
- Respuestas de error estandarizadas bajo RFC 7807 (`application/problem+json`) mediante `GlobalExceptionMiddleware`. Jamás exponer stack traces, detalles de tablas o excepciones internas al cliente.
- Headers de seguridad obligatorios en toda respuesta HTTP (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`).
- Trazabilidad y correlación obligatoria mediante `X-Correlation-ID` en logs estructurados.
