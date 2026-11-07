---
description: Seguridad
globs: ['src/**', 'next.config.mjs', '.env.example', 'Dockerfile']
---

- Sin secretos. Solo NEXT_PUBLIC_* al cliente. Headers + CSP. Problem Details sin stack traces.
- Imagen non-root standalone. Entra ID = punto de extensión (`src/server/auth`).
