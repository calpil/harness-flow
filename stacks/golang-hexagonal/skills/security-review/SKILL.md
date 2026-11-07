---
name: security-review
description: Revisa vulnerabilidades de seguridad, inyección SQL, manejo seguro de secretos, configuración de cabeceras HTTP y respuestas de error RFC 7807 en Go.
---

# Security Review — CALPIL Golang Engineering Skill

## Objetivo y activación
Activar antes de cualquier entrega a producción o cuando se modifiquen endpoints, autenticación, queries de base de datos o manejo de variables de entorno para auditar que el servicio Go cumpla con los estándares de seguridad de CALPIL.

## Inspección obligatoria
Antes de emitir el reporte, inspecciona:
1. `internal/platform/config/config.go`: Carga de configuración y ausencia de credenciales por defecto inseguras.
2. `internal/platform/middleware/`: Presencia de Correlation ID, recovery middleware y security headers.
3. `internal/*/adapter/out/persistence/`: Consultas SQL para descartar inyección de código.
4. `internal/platform/httputil/problem_detail.go`: Ausencia de filtración de información técnica en respuestas de error.

## Procedimiento ejecutable
1. **Auditoría de Inyección SQL:** Revisar cada llamada `Exec`, `Query` y `QueryRow` en adaptadores PostgreSQL. Confirmar que ninguna sentencia use `fmt.Sprintf` o concatenación con valores externos; todas deben usar `$1, $2`.
2. **Auditoría de Manejo de Secretos:** Buscar en todo el repositorio cadenas hardcodeadas (`password`, `secret`, `key`, `token`). Asegurar que `.env` esté en `.gitignore` y que solo exista `.env.example` con valores de plantilla.
3. **Revisión de Cabeceras HTTP:** Verificar que el router aplique cabeceras de endurecimiento (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`).
4. **Verificación de Trazabilidad:** Confirmar que `X-Correlation-ID` sea capturado o generado en cada request y propagado a los logs sin imprimir datos personales o sensibles.
5. **Revisión de Timeouts del Servidor:** Validar que `http.Server` tenga configurados `ReadTimeout`, `WriteTimeout` e `IdleTimeout` para mitigar ataques de denegación de servicio (Slowloris).
6. **Validación de Payloads y Errores:** Comprobar que los errores 500 no envíen el stack trace al cliente y que las respuestas sigan el formato estándar RFC 7807.

## Patrón de implementación
```go
// Servidor HTTP con timeouts seguros contra Slowloris
server := &http.Server{
    Addr:         fmt.Sprintf(":%s", cfg.Port),
    Handler:      r,
    ReadTimeout:  15 * time.Second,
    WriteTimeout: 15 * time.Second,
    IdleTimeout:  30 * time.Second,
}
```

## Decisiones y anti-patrones
- **NO** registrar contraseñas, tokens de autenticación o datos de tarjetas en los logs de aplicación.
- **NO** ejecutar el contenedor Docker con usuario `root`. El `Dockerfile` debe usar un usuario no privilegiado (`appuser`).
- **NO** devolver mensajes de error internos de la base de datos (ej. `duplicate key value violates unique constraint`) directamente al frontend.

## Verificación / Definition of Done
- Sin secretos ni credenciales en el historial o archivos del repositorio.
- Todas las consultas SQL parametrizadas con placeholders `$1, $2`.
- Timeouts configurados en `http.Server`.
- Dockerfile ejecuta bajo usuario `appuser`.

## Contrato de entrega del agente
El agente debe reportar en su mensaje final:
1. Resumen de áreas de seguridad auditadas (SQL, secretos, headers, timeouts, contenedor).
2. Hallazgos o vulnerabilidades identificadas y su severidad (Crítica, Alta, Media, Baja).
3. Correcciones aplicadas.
4. Estado de cumplimiento final.
