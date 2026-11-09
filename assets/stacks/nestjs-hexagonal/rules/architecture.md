---
description: Límites de Clean Architecture y Arquitectura Hexagonal en NestJS / TypeScript
globs: ["src/**", "test/**"]
---

# Reglas de Arquitectura Hexagonal en NestJS

- **Capa Dominio (`src/**/domain/**/*.ts`):**
  - TypeScript puro libre de frameworks.
  - PROHIBIDO importar `@nestjs/*`, `@prisma/client`, `typeorm`, `express`, `fastify` o adaptadores de infraestructura.
  - Entidades y Value Objects protegen sus invariantes de negocio mediante métodos explícitos.
- **Capa Aplicación (`src/**/application/**/*.ts`):**
  - Solo depende de `domain` y define sus propios puertos de entrada (Use Cases) y salida (`ports/out`).
  - PROHIBIDO importar adaptadores concretos de infraestructura ni controladores.
- **Capa Adaptadores / Infraestructura (`src/**/adapter/**/*.ts` o `infrastructure/`):**
  - Implementa puertos secundarios (`ports/out`) con Prisma/PostgreSQL, repositorios en memoria y clientes externos.
  - Expone puertos primarios mediante NestJS Controllers decorados y DTOs mapeados.
- **Composition Root (`src/app.module.ts` / `src/main.ts`):**
  - Nest Modules cablean la inyección de dependencias (`providers`, `useClass`) entre use cases y adaptadores concretos.
