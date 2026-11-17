---
description: Límites de seguridad del portal web .NET MVC - XSS, CSRF, sesión, redirecciones, CSP, secretos y errores
globs: ["src/**", "Dockerfile", "compose.yaml", "**/appsettings*.json", ".env.example"]
trigger: always_on
---

# Reglas de seguridad

- **Salida codificada (XSS).** Todo texto dinámico se emite con `@valor`, que Razor codifica. Prohibido `Html.Raw`, `HtmlString` y armar HTML concatenando cadenas. Los datos de la API se tratan como no confiables.
- **CSP sin código en línea.** La política es `default-src 'self'`. Prohibido agregar `'unsafe-inline'`, `'unsafe-eval'` u orígenes externos para "hacer funcionar" algo: el script o estilo va a un archivo de `wwwroot`.
- **CSRF.** Todo cambio de estado es un POST de formulario con token antiforgery (el filtro global lo exige). Prohibido `[IgnoreAntiforgeryToken]` salvo en la página de error, y prohibido cambiar estado con GET.
- **Sesión por defecto.** El filtro global `AuthorizeFilter` exige sesión en toda acción. `[AllowAnonymous]` solo en páginas realmente públicas. No reemplazarlo por convenciones de ruta: no cubren las rutas por atributo.
- **Autorización por recurso.** Cuando el proyecto agregue pertenencia o roles, cada acción verifica que la persona puede ver ese recurso; ocultar el enlace no es control de acceso.
- **Cookie de sesión:** `HttpOnly`, `Secure`, `SameSite=Lax`, prefijo `__Host-`. No guardar tokens ni datos personales en la cookie ni en `TempData`.
- **`AUTH_MODE=dev`** autentica a un usuario fijo: solo `Development`. No agregar otros atajos de autenticación.
- **Redirecciones.** Un `returnUrl` solo se usa si `Url.IsLocalUrl` lo acepta; si no, se va a `/`.
- **Sin secretos en el repositorio.** `OIDC_CLIENT_SECRET` y cualquier credencial llegan por variable de entorno desde el almacén de secretos. Nunca en código, `appsettings*.json`, `Dockerfile` ni pruebas.
- **Errores sin fugas.** La página de error muestra solo el código de seguimiento. Nunca mensajes de excepción, URLs internas de la API ni stack traces. Los mensajes técnicos de la API no se muestran tal cual salvo los de validación de campos.
- **Cabeceras:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, CSP y HSTS fuera de `Development`. No se usa `X-XSS-Protection` (obsoleta).
- **Logs:** no registrar tokens, cookies, secretos ni datos personales.
- **Varias réplicas:** `DATA_PROTECTION_KEYS_PATH` en almacenamiento compartido y con acceso restringido; esas claves cifran las sesiones.
- **Imagen:** base chiseled, usuario no root, digest fijo.
