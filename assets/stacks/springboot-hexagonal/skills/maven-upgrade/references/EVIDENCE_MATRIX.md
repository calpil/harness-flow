# Matriz de evidencia de actualización

| Familia / artefacto | Antes (resuelto) | Candidata estable (fuente+fecha) | Después (resuelto) | CVE/piso seguro | Compatibilidad | Pruebas | Estado |
|---|---|---|---|---|---|---|---|
| Spring Boot BOM |  |  |  |  | Java 21 / Jakarta | startup + verify | NOT RUN |
| Springdoc |  | 3.x (verificar release estable) |  |  | Spring Boot 4 | `/v3/api-docs` | NOT RUN |
| PostgreSQL / Liquibase |  |  |  |  | Migration + Hibernate validate | Testcontainers | NOT RUN |
| JUnit / Testcontainers |  |  |  |  | módulos/API changed? | tests E2E | NOT RUN |
| Plugins Maven |  |  |  |  | Wrapper/JDK | spotless + jacoco | NOT RUN |

Usar PASS/FAIL/BLOCKED/NOT RUN. Solo `PASS` si existe salida auténtica de comando ejecutado. No copiar versiones sugeridas sin comprobar metadata oficial.
