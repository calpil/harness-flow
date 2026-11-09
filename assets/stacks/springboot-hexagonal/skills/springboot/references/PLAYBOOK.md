# Spring Boot / Java 21 Golden Path — Playbook técnico de ejecución


## Plano técnico mínimo (observado en este template)

```text
com.calpil.template/
  <bounded-context>/domain/{model,exception,event}/          # Java puro
  <bounded-context>/application/{command,port/in,port/out,usecase}/
  <bounded-context>/adapter/in/web/                       # Spring MVC + DTO
  <bounded-context>/adapter/out/{persistence,event}/      # JPA, colas, clients
  <bounded-context>/configuration/                        # composition root
  platform/{security,configuration,errorhandling,observability}/
```

La aplicación *no* debe depender de implementaciones de infraestructura. En este repositorio `WorkItemService` implementa puertos de entrada, recibe puertos de salida por constructor y se cablea desde configuración. Es un ejemplo, no componente obligatorio. La persistencia está en PostgreSQL y Liquibase: jamás generar schema con Hibernate.

## Recorrido de un cambio transversal

1. Identificar entrada real: `Controller` / scheduled job / event consumer / integration client.
2. Determinar identidad confiable, origen de `tenant` y permisos por acción/recurso.
3. Definir command/query inmutable, resultado y errores de aplicación/domain.
4. Especificar transacción (`@Transactional` en boundary apropiado, sin introducir Spring en domain).
5. Identificar puerto de persistencia/integración y mapeo a entidades/contratos externos.
6. Considerar eventos en relación a confirmación de DB: usar outbox si se necesita entrega fiable.
7. Incorporar errores y observabilidad al request path; redacción PII.
8. Construir cadena de tests: unit puro → slice web → DB → ArchUnit → E2E con cliente real.

## Matriz de decisiones de infraestructura

| Tema | Elección por defecto | Cambiar si | Riesgo a probar |
|---|---|---|---|
| Persistencia | Postgres + JPA | caso de acceso justificado | locking, N+1, transacciones |
| Schema | Liquibase | ADR explícito corporativo | checksum, backfill, rollback |
| HTTP | Spring MVC DTO → port in | streaming/asíncrono justificado | status, retries, consumer drift |
| Auth | resource server + authz por recurso | auth alternative aprobada | 401,403, tenant-crossing |
| Idempotencia | por operación crítica de escritura | no aplica por semántica | duplicados en retry |
| Observabilidad | actuator + Micrometer/OTel | collector no habilitado | PII, overhead y cardinalidad |

## Checklist de code review cross-cutting

- Configuración vía `@ConfigurationProperties` tipada y validada, defaults seguros.
- No credenciales embebidas ni configuración de nonprod copiada a prod.
- Timeouts en clientes y pools; retry solo en operaciones idempotentes; circuit breaker justificado.
- Errores coherentes y traducidos una sola vez, preferir `ProblemDetail` estable.
- Contratos públicos internos/externos desacoplados mediante ACL cuando corresponde.
- Readiness falla ante incapacidad de recibir tráfico; liveness NO depende de DB externa.

## Prueba concreta de arquitectura

```bash
./mvnw -Dtest=HexagonalArchitectureTest test
./mvnw -Dtest=DependencySecurityRegressionTest test
./mvnw verify
```

Registrar si Testcontainers se ejecutó o fue saltado. Guardar `target/surefire-reports`, reportes JaCoCo y comandos de CI como evidencia, sin crear resultados ficticios.

## Gate final

- [ ] domain/application imports match dependency inversion
- [ ] bean wiring by configuration/constructor, no component scan magic in core
- [ ] profile config default safe, secrets indirect
- [ ] transaction, event and error boundaries deliberate
- [ ] HTTP + DB + auth integration tested when exposed
- [ ] readiness, liveness and shutdown operationally sound
