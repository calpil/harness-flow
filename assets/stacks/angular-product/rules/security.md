---
description: Seguridad
globs: ['src/**', 'nginx.conf', 'Dockerfile', 'src/environments/**']
---

- Sin secretos en código ni bundle. Headers + CSP (nginx.conf). Imagen nginx non-root.
- Entra ID = MSAL public client + PKCE (`@azure/msal-browser`) y LoginPattern en `/login`. Sin client secret. Errores centralizados sin datos sensibles.
