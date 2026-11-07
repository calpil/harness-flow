---
description: Dependencias
globs: ['package.json', 'package-lock.json']
---

- Solo dependencias necesarias y estables; justificar mantenimiento/licencia/vulnerabilidades/alternativas.
- `package.json` + `package-lock.json` son la fuente de verdad de versiones.
- Actualizar `docs/development/dependencies.md` solo por política/decisiones, no como inventario manual.
- ADR si el cambio altera arquitectura o contrato de plataforma.
