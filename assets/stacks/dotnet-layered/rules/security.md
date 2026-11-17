---
description: Límites de seguridad para la API .NET - SQL parametrizado, secretos, errores, cabeceras y TLS a SQL Server
globs: ["src/**", "db/**", "Dockerfile", "compose.yaml", "**/appsettings*.json", ".env.example"]
trigger: always_on
---

# Reglas de seguridad

- **SQL siempre parametrizado.** Todo valor que venga de un request, de la base o de configuración viaja como parámetro de Dapper (`@Id`) o de procedimiento almacenado. Prohibido interpolar (`$"... {valor}"`) o concatenar valores en SQL. Las únicas interpolaciones aceptadas son constantes del propio repositorio (por ejemplo la lista de columnas).
- **Sin secretos en el repositorio.** Nada de contraseñas, cadenas de conexión ni tokens en código, `appsettings*.json`, `Dockerfile` o pruebas. La configuración llega por variables `DB_*`. Los valores de `.env.example` y `compose.yaml` son solo para la máquina local.
- **TLS a la base.** En `Production`, `DB_SSL=true` (cifrado obligatorio y certificado validado). Prohibido `TrustServerCertificate=true` fuera de local.
- **Mínimo privilegio en SQL Server.** El login de la aplicación no es `sa` ni `db_owner` fuera de local: solo lectura/escritura sobre sus tablas y `EXECUTE` sobre sus procedimientos. Las migraciones usan un login aparte.
- **Errores sin fugas.** Las respuestas de error son Problem Details. Jamás incluir mensajes de excepción no controlada, SQL, nombres de tablas o stack traces. El detalle va al log con el `correlationId`.
- **Validación en la frontera.** Todo DTO de entrada declara tipo, obligatoriedad y largo máximo. Los enums rechazan valores numéricos y desconocidos.
- **Cabeceras:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` y `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`. No se usa `X-XSS-Protection` (obsoleta; OWASP recomienda no activarla).
- **`X-Correlation-ID`** solo se acepta del cliente si cumple `^[A-Za-z0-9._-]{1,64}$`; si no, se genera uno.
- **Logs:** no registrar contraseñas, tokens, cadenas de conexión ni cuerpos completos de requests.
- **Imagen:** base chiseled, usuario no root, digest fijo. No agregar shell ni herramientas a la imagen final.
- **No habilitar descompresión de requests** (`UseRequestDecompression`) ni subir el límite de 1 MB del cuerpo sin una razón documentada.
