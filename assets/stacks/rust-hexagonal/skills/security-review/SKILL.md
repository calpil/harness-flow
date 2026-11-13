---
name: security-review
description: Guía de auditoría y revisión de seguridad estricta para APIs backend en Rust, prevención de SQLi, headers HTTP y secrets
---

# Auditoría de Seguridad en Backend Rust

## Objetivo y activación
Esta skill se activa para auditar la seguridad estricta del backend Rust, previniendo inyecciones SQL, exposición de secretos, fuga de información en respuestas de error y configuraciones inseguras de red.

## Inspección obligatoria
Antes de emitir el reporte de seguridad:
- Revisar las consultas SQL en `crates/infrastructure/src/persistence/postgres.rs`.
- Revisar las cabeceras HTTP inyectadas en `crates/api/src/middlewares/correlation_id.rs`.
- Revisar el formato de errores en `crates/api/src/problem_details.rs`.
- Inspeccionar `Dockerfile` y validar usuario no root.
- Revisar `.agents/rules/security.md` (o `.claude/rules/security.md`).

## Procedimiento ejecutable
1. **Auditar consultas a bases de datos:** Verificar que el 100% de las consultas en `crates/infrastructure` utilicen sentencias preparadas con parámetros vinculados (`bind(...)`) y que ninguna concatene variables de usuario.
2. **Auditar cabeceras de seguridad:** Comprobar que el middleware HTTP agregue `x-content-type-options: nosniff`, `x-frame-options: DENY` y `x-xss-protection: 1; mode=block`.
3. **Validar trazabilidad de Correlation ID:** Confirmar que `x-correlation-id` sea recibido o generado con UUID v4 y propagado en la respuesta.
4. **Verificar respuestas de error RFC 7807:** Comprobar que en ningún escenario de error se envíen stack traces internos, credenciales de conexión o información de infraestructura a los clientes.
5. **Escanear secretos en el repositorio:** Verificar que `.env`, archivos con contraseñas o tokens privados estén ignorados en `.gitignore`.
6. **Auditar privilegios en Dockerfile:** Confirmar que el contenedor de producción cree y ejecute la aplicación bajo el usuario no root `appuser` (UID 1000).

## Patrón de implementación
```rust
// Middleware de cabeceras de seguridad y trazabilidad
response.headers_mut().insert(
    HeaderName::from_static("x-content-type-options"),
    HeaderValue::from_static("nosniff"),
);
response.headers_mut().insert(
    HeaderName::from_static("x-frame-options"),
    HeaderValue::from_static("DENY"),
);
```

## Decisiones y anti-patrones
- **Cero SQL dinámico:** Nunca construir sentencias SQL usando formateo de cadenas `format!()`.
- **No exponer excepciones de base de datos directamente:** Mapear errores de base de datos a mensajes genéricos y seguros en la capa HTTP.
- **No correr contenedores como root:** Siempre crear un grupo y usuario no privilegiado en la imagen final.

## Verificación / Definition of Done
- Comprobación de consultas SQL parametrizadas.
- Cabeceras de seguridad presentes en respuestas HTTP validadas por tests.
- Dockerfile con usuario `appuser`.
- Cero secretos expuestos.

## Contrato de entrega del agente
El agente entregará una lista de verificación de seguridad cubriendo SQL Injection, cabeceras de respuesta, manejo de errores RFC 7807 y hardening de contenedores.
