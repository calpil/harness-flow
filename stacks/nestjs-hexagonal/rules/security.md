---
description: Reglas de seguridad para APIs, configuración y saneamiento de inputs en NestJS
globs: ["src/**", ".env*"]
---

# Reglas de Seguridad en NestJS

- Validación estricta de inputs mediante `ValidationPipe` global con `{ whitelist: true, forbidNonWhitelisted: true, transform: true }`.
- PROHIBIDO hardcodear contraseñas, secretos JWT o connection strings en el código; cargar vía `@nestjs/config` desde variables de entorno.
- Respuestas de error estandarizadas con `HttpExceptionFilter` bajo RFC 7807 (`application/problem+json`), sin filtrar stack traces ni detalles de Prisma/BD.
- Cabeceras de seguridad HTTP activas mediante `helmet` (`x-content-type-options: nosniff`, `x-frame-options: DENY`).
- Trazabilidad y correlación obligatoria mediante `x-correlation-id` en logs estructurados.
