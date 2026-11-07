# Automated Tests / Contract / Architecture — Playbook técnico de ejecución


## Pirámide y seam hexagonal

| Nivel | Qué prueba | Dependencia | Ejemplo existente |
|---|---|---|---|
| dominio | estados, value objects, invariantes | JUnit/AssertJ | `WorkItemTest` |
| application | puerto de entrada + fake port out | Java puro, sin web | `WorkItemServiceTest` |
| web adapter | mapping, `@Valid`, error, status | MockMvc o controller slice | `WorkItemControllerTest` |
| arquitectura | imports entre capas | ArchUnit | `HexagonalArchitectureTest` |
| DB E2E | Liquibase, JPA, HTTP real | Postgres Testcontainers | `WorkItemApiE2ETest` |
| seguridad | autenticación y autorización reales | Spring Security Test | crear si corresponde |
| regresión Maven | pisos de dependencias | resolved tree/compilación | `DependencySecurityRegressionTest` |

## Casos de prueba de cada feature

```text
ID | Given | When | Then | Efecto colateral | Nivel | Estado
T01 | aggregate válido | create | id y estado esperados | guardado 1 vez | unit+DB | NOT RUN
T02 | dato inválido | create | 400/exception | no guardado | unit+web | NOT RUN
T03 | recurso de otro tenant | get | 403/404 | no datos expuestos | security+DB | NOT RUN
T04 | actualización concurrente | update | 409/concurrencia | no lost update | DB E2E | NOT RUN
T05 | request reintentado | create | respuesta definida | no duplicación | integration | NOT RUN
```

Modifica filas según requisitos, no presupone que todos los servicios sean multi-tenant. Agregar pruebas de boundaries 0/1/max/null y locale/timezone cuando aplique.

## Java test examples (conceptual)

```java
@Test
void rejectInvalidStateTransitionWithoutPersisting() {
  // Arrange aggregate valid state and fake port out
  // Act command causing an invalid transition
  // Assert domain exception + unchanged aggregate + no port writes
}
```

Preferir state assertions (`saved.status()`) y eventos emitidos a mock-based `verify()` de cada llamada auxiliar. Tests no deben acoplarse a implementación privada o strings traducibles.

## E2E con PostgreSQL en Docker

El ejemplo `WorkItemApiE2ETest` usa `@Testcontainers(disabledWithoutDocker = true)`, `postgres:17` y `DynamicPropertyRegistry` para DB. Si Docker está apagado, JUnit puede marcar tests `skipped`. **No reportar PASS** sin examinar `target/surefire-reports/TEST-*.xml` y contar skipped. Para APIs de auth, configurar tokens de test reales o mocks estrictos que ejecuten la chain de seguridad.

## Secuencia de validación

```bash
./mvnw -Dtest=WorkItemTest test            # muestra, usar test del cambio
./mvnw -Dtest=HexagonalArchitectureTest test
./mvnw -Dtest=DependencySecurityRegressionTest test
./mvnw verify
```

Separar fallos de JDK, Docker, DB externa y dependencias del producto; no hacer `-DskipTests` como evidencia de éxito. JaCoCo 80% LINE BUNDLE es baseline actual, no rebajarlo para cerrar un PR.

## Evidencia

Reportar por clase tests run/fail/error/skipped, cobertura lograda y ausencia de ejecución. Una prueba de regresión idealmente falla antes de fix en código original (cuando sea factible) y pasa después. Si no se pudo reproducir estado rojo, explicar por qué.

## Gate final

- [ ] domain tests run without Spring container
- [ ] service tests verify state + side effects
- [ ] negative API/status tests exercise actual adapter
- [ ] Testcontainers skipped count visible and zero for release signoff
- [ ] ArchUnit and dependency regression stay intact
- [ ] coverage threshold not lowered
