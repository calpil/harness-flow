---
description: Estándares de pruebas automatizadas deterministas en NestJS con Jest
globs: ["test/**", "**/*.spec.ts"]
---

# Reglas de Pruebas en NestJS

- Pruebas deterministas, ejecutables en paralelo y sin esperas arbitrarias (`setTimeout` o delays fijos).
- **Pruebas de Dominio:** Probar entidades e invariantes en TypeScript puro sin instanciar módulos de Nest ni dependencias de BD.
- **Pruebas de Aplicación:** Emplear implementaciones fake en memoria de los puertos de persistencia para validar orquestación.
- **Pruebas de Controladores / Integración:** Usar `Test.createTestingModule` y `supertest` para validar el pipeline HTTP completo, códigos de respuesta y DTOs de error.
- Toda la suite `npm test` debe pasar limpiamente al 100%.
