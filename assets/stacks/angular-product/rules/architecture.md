---
description: Límites feature-oriented layered (Angular)
globs: ['src/app/features/**', 'src/app/core/**', 'projects/*/src/app/features/**', 'projects/*/src/app/core/**']
---

- `domain/**`: sin `@angular`. `application/**`: sin `data-access`/`ui`. `ui/**`: sin `data-access` directo.
- Estado de feature con Signals; sin estado global innecesario. Verificado por `npm run test:architecture`.
- Workspace con varios proyectos (`angular.json` -> `projects`): `check-architecture.py` verifica cada proyecto de tipo `application` en su propia raíz (`projects/<app>/src/app/**`); las librerías no se verifican y el resultado las nombra.
