# Test Scenario Tracking Matrix


| Context | Scenario | Level | Fixture | Expected effect | Gate |
|---|---|---|---|---|---|
| domain | invalid state | unit | aggregate | no mutated state | JUnit |
| application | missing ID | unit | fake repository | domain error | JUnit |
| HTTP | invalid body | controller slice | JSON | ProblemDetail 400 | MVC |
| API auth | cross tenant | security + E2E | test JWTs | no data disclosed | resource server |
| DB | release schema | integration | PostgreSQL container | Liquibase passes | Testcontainers |
| architecture | domain imports | static | ArchUnit | no violation | ArchUnit |

## Test status

```text
run: NOT RUN
passed: 0
failed: 0
skipped: 0
docker_available: UNKNOWN
jacoco_line_coverage: NOT MEASURED
```

Update values exclusively from actual Surefire XML and JaCoCo reports. For Testcontainers inspect `skipped` as well as exit code.
