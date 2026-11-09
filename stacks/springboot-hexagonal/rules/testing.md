---
description: Evidencia de pruebas deterministas proporcionales a cambios
globs: ["src/test/**"]
---
- Sin sleeps ni orden implícito; pruebas del dominio y casos de uso con tiempos/fakes controlados.
- PostgreSQL real vía Testcontainers cuando se verifican SQL/JPA/Liquibase; ddl-auto validate.
- ArchUnit cuando cambian límites, API E2E cuando hay cambio del contrato.
- No quitar tests, coverage/security gates para pasar; usar skill `write-tests` (`.agents/skills/` o `.claude/skills/`).
- Fuente de verdad: `docs/ai/TESTING_RULES.md`.
