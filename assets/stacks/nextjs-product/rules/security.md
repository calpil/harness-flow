---
description: Seguridad
globs: ['src/**', 'next.config.mjs', '.env.example', 'Dockerfile']
trigger: always_on
---

- **Secretos y frontera servidor/cliente (OWASP A02):** cero secretos en código o bundle. Solo variables `NEXT_PUBLIC_*` llegan al cliente; credenciales y acceso a datos viven aislados con `import 'server-only'`.
- **Control de acceso en Server Actions y Route Handlers (OWASP A01/A07):** validar sesión, permisos y pertenencia a tenant/recurso dentro de cada Server Action y Route Handler (nunca confiar solo en middleware o UI). Entra ID = punto de extensión (`src/server/auth`). Cookies de sesión con `HttpOnly`, `Secure` y `SameSite=Lax`.
- **XSS e inyección (OWASP A03):** usar escape automático de React; prohibido `dangerouslySetInnerHTML`, `innerHTML` o `eval` con entrada externa o de API. Validar todos los inputs de Server Actions/Route Handlers con esquemas tipados.
- **Anti-SSRF (OWASP A10):** toda petición `fetch` saliente hacia URLs influenciadas por el cliente valida contra whitelist de dominios y bloquea IPs privadas y metadata cloud (`169.254.169.254`).
- **Cabeceras, errores y runtime (OWASP A05/A09):** configurar CSP estricta, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy` y HSTS en `next.config.mjs` (sin `X-XSS-Protection` obsoleta). Respuestas de error RFC 7807 sin stack traces; logs sin tokens ni PII; imagen standalone non-root.
