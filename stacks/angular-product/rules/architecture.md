---
description: Límites feature-oriented layered (Angular)
globs: ['src/app/features/**', 'src/app/core/**']
---

- `domain/**`: sin `@angular`. `application/**`: sin `data-access`/`ui`. `ui/**`: sin `data-access` directo.
- Estado de feature con Signals; sin estado global innecesario. Verificado por `npm run test:architecture`.
