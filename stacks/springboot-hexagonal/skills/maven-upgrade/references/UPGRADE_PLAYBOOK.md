# Maven Upgrade — playbook de compatibilidad y gates

## Fuentes que se deben consultar EN EL MOMENTO de ejecutar
Maven Central (metadata y releases), Spring Boot release notes y migration guide, Spring Framework, springdoc compatibility FAQ, Testcontainers upgrade guide, Liquibase, Apache Tomcat, PostgreSQL JDBC, GitHub Security Advisories/CVE y reporte corporativo de SCA. Cada candidato debe quedar con URL y fecha consultada.

## Inventario inicial
- Spring Boot parent, Java/Maven wrapper, perfiles, releases reportados en `VERSIONS.md` y dependencias explícitas.
- `spring-framework.version`, `tomcat.version`, `jackson-2-bom.version`, `jackson-bom.version`, `postgresql.version`, `log4j2.version`, `commons-compress.version`, `springdoc.version`, `testcontainers.version`, `archunit.version`, `spotless.version`.
- `dependencyManagement`, transitivas, BOMs importados, versiones plugins y tests de regresión.
- Springdoc 2.x NO es compatible con Spring Boot 4 (revisar línea springdoc 3.x). Otros artefactos pueden haber cambiado de nombre entre Boot 3 y Boot 4. **No extrapolar**.

## Secuencia
1. Registrar `git status`, `java -version`, `./mvnw -v`, árbol y effective POM original; si falla por red/proxy, registrar impedimento.
2. Obtener lista de upgrades sugeridos con `./mvnw versions:display-dependency-updates versions:display-plugin-updates versions:display-property-updates -DallowSnapshots=false` si el plugin está disponible; no aceptar propuestas sin confirmar con fuentes oficiales.
3. Matriz: familia, versión actual efectiva, candidata estable, piso seguridad, compatibilidad Java/Boot/Jakarta, artifactId/rename, pruebas afectadas, decisión.
4. Seleccionar Boot parent soportado y mantener su BOM como autoritativo; revisar transitive security overrides contra pisos registrados. Si la candidata segura del BOM todavía es insegura, mantener override coherente y con evidencia.
5. Migrar en fases pequeñas; después de cada fase, `./mvnw -B -DskipTests compile` **solo como paso intermedio**, nunca resultado final. Verificar bytecode Java 21 y package APIs.
6. `./mvnw -B spotless:check`, `./mvnw -B clean verify`; cobertura/ArchUnit/JUnit/Testcontainers y security regression. No eliminar tests ni cambiar scope para simplificar.
7. Generar árboles y effective POM después; cotejar direct/transitive, conflictos, APIs y si el artifact `springdoc-openapi-starter-webmvc-ui` realmente sirve Swagger/JSON.
8. Actualizar documentación correcta (antes o después de organizar docs), fecha de consulta, change log de dependencias; ADR de migración mayor solo si hubo decisión arquitectónica importante.
9. Informar gates PASS/FAIL/BLOCKED/NOT RUN y instrucciones exactas de reproducibilidad. Un bloqueo de red/Docker NO equivale a un verde.

## Particularidades de este template
- `SecurityConfig` usa `anyRequest().permitAll()` DEMO: no usar el éxito del test como evidencia de seguridad real.
- `DependencySecurityRegressionTest` comprueba versiones/conjunto de JARs; cambios justificados deben actualizar expectativas respaldadas con árbol real, no eliminar assertions.
- Liquibase y Hibernate `ddl-auto=validate` deben verificar PostgreSQL real con Testcontainers.
- El proyecto contiene rutas SQL `db/changelog/sql` y `db/changelog/changes/sql`: usar únicamente las referenciadas por master, no asumir duplicado ejecutado.
- `mvnw` no garantiza reproducibilidad de plugins/transitivas por sí solo: comparar effective POM y provenance.

## Rollback
Mantener commits por fase (si el usuario autoriza commit). Revertir el cambio de POM/código de la fase fallida sin retroceder fixes de seguridad. No modificar o borrar migraciones previamente ejecutadas para hacer rollback.
