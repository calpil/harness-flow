---
description: Reglas de dependencias y gobierno de paquetes npm en NestJS
globs: ["package.json", "package-lock.json"]
---

# Reglas de Dependencias en NestJS

- Solo dependencias evaluadas y estrictamente necesarias; evitar duplicidad de librerías.
- Mantener versiones consistentes de `@nestjs/*` alineadas a la versión mayor del runtime.
- Cero dependencias externas en la capa `domain/`.
- Dependencias de desarrollo (`devDependencies`) para herramientas de compilación, linters y tests (`jest`, `@types/*`, `prisma`).
- Verificar vulnerabilidades conocidas antes de introducir paquetes de terceros mediante `npm audit --audit-level=high`.
