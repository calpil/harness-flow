---
description: Reglas de seguridad para backend Rust, validación de inputs, SQL Injection y secrets
globs: ["crates/**", "Dockerfile", ".env*"]
---

# Reglas de Seguridad en Backend Rust

- **Inyección SQL y Consultas a Base de Datos:**
  - Prohibido concatenar o formatear cadenas SQL dinámicamente (`format!("SELECT ... WHERE id = '{}'")`).
  - Todas las consultas en `crates/infrastructure` deben utilizar parámetros tipados vinculados mediante `sqlx::query!` o `sqlx::query_as` (`$1, $2, ...`).
- **Seguridad en HTTP y Cabeceras:**
  - Todo endpoint debe responder con cabeceras de seguridad: `x-content-type-options: nosniff`, `x-frame-options: DENY`, `x-xss-protection: 1; mode=block`.
  - Propagación y retorno mandatorio de cabecera de trazabilidad `x-correlation-id` en todas las respuestas HTTP.
  - Respuestas de error sin filtración de trazas internas o datos sensibles; emisión estricta de RFC 7807 `application/problem+json`.
- **Cero Secretos en Código o Repositorio:**
  - Prohibido almacenar contraseñas, tokens JWT, API keys o cadenas de conexión en el código fuente.
  - La configuración debe cargarse mediante variables de entorno a través de `Config::from_env()`.
- **Contenedores de Producción con Mínimo Privilegio:**
  - `Dockerfile` debe ejecutarse como usuario no privilegiado (`appuser:appuser`, UID 1000).
  - Utilizar imágenes base mínimas y limpias (`debian:bookworm-slim` o distroless) sin herramientas de compilación en el artefacto final.
