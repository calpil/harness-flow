---
description: Seguridad
globs: ['src/**', 'nginx.conf', 'Dockerfile', 'src/environments/**']
trigger: always_on
---

- Sin secretos en código, `src/environments/**` ni bundle cliente. Imagen nginx non-root.
- **XSS (OWASP A03):** usar interpolación y saneamiento nativo de Angular. Prohibido `bypassSecurityTrustHtml`, `bypassSecurityTrustUrl`, `bypassSecurityTrustScript` o manipulación directa con `innerHTML`/`outerHTML` sobre datos externos o de API.
- **Cabeceras y CSP (OWASP A05):** configurar `Content-Security-Policy` estricta (sin `'unsafe-inline'`/`'unsafe-eval'`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy` y HSTS en `nginx.conf`. No usar `X-XSS-Protection` (obsoleta).
- **Autenticación y redirecciones (OWASP A01/A07):** Entra ID = MSAL public client + PKCE (`@azure/msal-browser`) y LoginPattern en `/login`; sin client secret. Validar rutas de retorno (`returnUrl`) como locales para evitar Open Redirects. Ocultar botones en UI nunca reemplaza autorización en backend.
- **Errores y logs (OWASP A09):** manejo centralizado de errores sin filtrar stack traces ni payloads internos; prohibido registrar tokens, cookies o PII en `console.*` o telemetría.
