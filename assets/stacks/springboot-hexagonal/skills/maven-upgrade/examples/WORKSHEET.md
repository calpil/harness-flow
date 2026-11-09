# Maven Version Decision Record — fill at runtime


## Matriz de upgrade

| Group:Artifact | Resolución anterior | Candidato estable verificado | Admin BOM / Override | Advisory / Security floor | API compatibility | Tests | Decisión |
|---|---|---|---|---|---|---|---|
| org.springframework.boot:starter-parent | 4.1.0 (original) | TBD | Parent | TBD | Java 21/Jakarta | verify | PENDING |
| org.springdoc:springdoc-openapi-starter-webmvc-ui | 2.8.6 (original) | TBD (línea compatible con Boot 4) | Manual | TBD | OpenAPI | context/API | PENDING |
| org.testcontainers:testcontainers-bom | configured | TBD | BOM | TBD | pg container | E2E | PENDING |
| org.apache.commons:commons-compress | configured | TBD | security override | keep floors | indirect | regression | PENDING |

## Baseline/after reports

```bash
./mvnw -B -DskipTests help:effective-pom -Doutput=target/effective-before.xml
./mvnw -B dependency:tree -Dverbose -DoutputFile=target/dependencies-before.txt
# update only verified releases, then
./mvnw -B clean verify
./mvnw -B -DskipTests help:effective-pom -Doutput=target/effective-after.xml
./mvnw -B dependency:tree -Dverbose -DoutputFile=target/dependencies-after.txt
```

A successful Maven return code does not prove any Testcontainers test ran. Inspect Surefire XML skipped counters.
