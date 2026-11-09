---
description: Reglas de seguridad móvil en iOS, almacenamiento seguro, HTTPS, App Transport Security y secrets
globs: ["Sources/**", "Tests/**", ".env*"]
---

# Reglas de Seguridad en Aplicaciones Móviles iOS

- **Almacenamiento Seguro:**
  - Prohibido almacenar tokens JWT, contraseñas, claves privadas o información personal identificable (PII) en `UserDefaults`.
  - Usar Keychain Services (`kSecClassGenericPassword`) o mecanismos de almacenamiento cifrado del sistema operativo para secretos y credenciales de sesión.
- **Comunicaciones Seguras y App Transport Security (ATS):**
  - Todas las conexiones de red deben usar HTTPS con TLS 1.3 / 1.2 estricto. Prohibido habilitar excepciones arbitrarias de ATS (`NSAllowsArbitraryLoads`).
  - Cabecera obligatoria de trazabilidad `x-correlation-id` en cada petición HTTP al backend.
- **Cero Secretos en Código Fuente:**
  - Prohibido dejar API keys, tokens de autenticación o secretos empresariales embebidos en el código Swift o en archivos plist.
  - La configuración debe inyectarse mediante variables de entorno en tiempo de compilación o esquemas de configuración seguros (`xcconfig`).
- **Manejo de Errores sin Fugas de Información:**
  - Errores mostrados al usuario en la UI deben ser amigables y localizados (`LocalizedError`); nunca exponer trazas de red, URLs internas ni tokens de error técnicos al usuario final.
