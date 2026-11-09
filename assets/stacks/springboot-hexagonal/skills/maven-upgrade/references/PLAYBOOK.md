# Maven Upgrade / Compatibility and Security — Playbook técnico de ejecución


## Estado inicial a verificar, no a asumir

Template observado: Java 21, parent Spring Boot `4.1.0`, Springdoc `2.8.6`, Testcontainers y Spring/Jackson/Tomcat/Postgres overrides; hay `DependencySecurityRegressionTest`. **No** declarar que estas versiones son las más actuales sin consultar repositorio central durante la ejecución. La línea Springdoc 2.8.x es incompatible con Boot 4: analizar releases Springdoc 3.x con upstream y tests.

## Fase 0: Baseline reproducible

```bash
./mvnw -v
./mvnw -DskipTests help:effective-pom -Doutput=target/pom-before.xml
./mvnw dependency:tree -Dverbose -DoutputFile=target/tree-before.txt
./mvnw versions:display-dependency-updates
./mvnw versions:display-plugin-updates
./mvnw -Dtest=DependencySecurityRegressionTest test
```

Para Maven Wrapper y `versions-maven-plugin`, los goals pueden requerir red/descarga; registrar restricción offline. Guardar resultados reales, no fabricarlos. No subir reportes con credenciales.

## Matriz de compatibility y rollout

| Componente | Control de compatibilidad | Prueba y decisión |
|---|---|---|
| Parent Boot | línea GA y soporte Java 21 | build + app context |
| Spring Framework | alineación BOM Boot; override solo por CVE documentada | effective-pom |
| Servlet/Tomcat | Servlet API y Tomcat de línea soportada | inicio HTTP |
| Jackson 3 | cambios de package `tools.jackson`, usos ObjectMapper | compile + JSON contract |
| Springdoc | soporte Boot 4 / Jakarta, serie compatible | endpoint OpenAPI |
| Testcontainers | BOM y artefactos coordinados | integración PostgreSQL real |
| Postgres JDBC | soporte PG server y TLS | E2E con container |
| Commons Compress | piso de seguridad observado | regression test + resolved tree |
| ArchUnit | JUnit/JVM compatibility | architecture test |
| Maven plugins | plugin API/JDK 21, cobertura y formato | verify |

**Orden sugerido**: 1) parent/BOM + springdoc compatible; 2) remediaciones transitive; 3) librerías fuera de BOM; 4) plugins. Tras cada lote registrar diff y test. No mezclar cambio funcional no relacionado.

## Diagnóstico si falla el upgrade

- `NoClassDefFoundError`: comparar resolved tree y `jdeps`/clases faltantes, buscar dependencia transitiva esperada; evitar exclusions masivas.
- `NoSuchMethodError`: mezcla de versiones binariamente incompatibles; revisar árbol efectivo/BOM.
- `ClassNotFoundException` de Jackson: Boot 4/Jackson 3 cambia packages; revisar imports/mappers/tests.
- OpenAPI falla al iniciar: confirmar springdoc compatible con Framework/Boot; validar release real.
- Testcontainers skips: Docker ausente, marcar BLOCKED y solicitar gate CI con Docker; jamás PASS.
- `spotless:check`: aplicar format de fuente solo en scope cambiado y no rebajar gate.
- JaCoCo: corregir tests relevantes; no bajar mínimo 0.80.

## Gate de aceptación

```bash
./mvnw -Dtest=DependencySecurityRegressionTest,HexagonalArchitectureTest test
./mvnw verify
./mvnw dependency:tree -Dverbose -DoutputFile=target/tree-after.txt
```

Conservar outputs comparables: parent, versions, transitive diff, CVEs antes/después, tests (ejecutados/fallidos/skipped), cambio de JAR y documentación. Si hay bloqueo por red/Docker, no merge automático, informar en matriz.

## Tabla de evidencia a llenar

| Artefacto | Antes | Después | Fuente GA + fecha | Seguridad/licencia | Prueba ejecutada | Estado |
|---|---|---|---|---|---|---|
| Boot parent | 4.1.0* | [resuelto] | [URL] | [advisory] | [output] | PASS/BLOCKED |
| springdoc | 2.8.6* | [resuelto] | [URL] | [advisory] | [output] | PASS/BLOCKED |

*Versiones son las del template inspeccionado, no afirmación sobre mercado actual.*

## Gate final

- [ ] resolved parent/BOM alignment and effective POM available
- [ ] stable versions with release dates/sources verified
- [ ] security floors still satisfied in resolved graph
- [ ] springdoc endpoint and Jackson compilation verified
- [ ] ArchUnit JaCoCo Spotless and Unit PASS
- [ ] Postgres Testcontainers really ran, not skipped
