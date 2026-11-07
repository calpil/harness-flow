---
description: Límites feature-oriented layered
globs: ['src/features/**', 'src/app/**', 'src/components/**/*.tsx']
---

- `domain/**`: TypeScript puro; sin Next/React/application/infrastructure/ui.
- `application/**`: puede depender de domain/ports propios; sin Next/React/infrastructure/ui.
- `infrastructure/**`: implementa ports; no debe depender de UI.
- `app/**`: routing y composición frontend; sin APIs de BFF/backend ni reglas de dominio.
- Server Components por defecto.
- Un Client Component no puede arrastrar módulos `server-only`, `src/server/**` ni APIs `node:*`.
- Tomar `src/features/operations` como referencia estructural principal.
- `npm run test:architecture` cubre hoy domain/application; revisar manualmente el resto de límites.
