# Root-Cause Debugging / Reproducible Fix — Playbook técnico de ejecución


## Árbol de diagnóstico guiado

```text
mvn compile fails?
  ├─ package/NoSuchMethod → check effective POM + dependency tree; Boot/Jackson compatibility
  ├─ syntax/checkstyle → inspect exact javac/Spotless error and changed file
  └─ Java version → ./mvnw -v / toolchain
Spring context fails?
  ├─ unsatisfied dependency → composition root, profile, bean qualifiers
  ├─ datasource/Liquibase → credentials sanitized, changelog master, schema, DB connectivity
  └─ security → filter chain, resource server, issuer/aud/token version
Runtime API fails?
  ├─ 400/415 → DTO/JSON validation/media type
  ├─ 401/403 → JWT + scopes/roles + tenant ownership
  ├─ 404/409 → use case exceptions/conflict/ID boundaries
  └─ 500 → correlation ID, service/repository path, SQL/external dependency
AKS only?
  └─ probes, Helm rendered values, Key Vault CSI, config, image digest, network
```

## Discriminating experiments

- Si `NoSuchMethodError`: imprimir resolved dependency graph; comparar API signature de jar realmente seleccionado. No sirve actualizar `pom.xml` completo y rezar.
- Si migración checksum falla: inspeccionar `DATABASECHANGELOG` contra changeset versionado; nunca mutar historiales para forzar ARRANQUE.
- Si Spring falla por bean faltante: verificar que `@Configuration` realmente se escanee, profiles activos y mocks de test.
- Si test falla solo CI: comparar JDK, Maven wrapper, Docker, timezone, locales, `application-test.yml`, secretos y limits.
- Si request 403: distinguir validación de token vs autorización por scope/recurso, ver el mismo request con tokens de test válidos.
- Si 500 tras deployment: comparar chart values y Key Vault references reales, recursos saturados y readiness, sin tocar aplicación a ciegas.

## Plantilla de hipótesis

```text
Síntoma: evidencia redactada del error
H1: <causa> | sustento: <archivo/stack> | prueba: <comando> | predicción: <output>
H2: <causa> | sustento: ...            | prueba: ...       | predicción: ...
Resultado H1/H2: se acepta/rechaza por evidencia, no por intuición
Corrección: archivos mínimos
Regresión: test falla antes (si reproducible), pasa después
Cierre: impactos en config, DB, seguridad, despliegue y APIs
```

## Condiciones de parada

Cuando la hipótesis quedó demostrada y el reproducer pasa, se amplía a pruebas afectadas; no refactorizar zonas vecinas sin necesidad. Si falla por falta Docker/red/credenciales, documentar reproducibilidad pendiente y el comando exacto para CI, no inventar salida.

## Comandos

```bash
./mvnw -v
./mvnw -Dtest=NombreTest test
./mvnw dependency:tree -Dverbose
git diff -- pom.xml src/main src/test
```

Sustituir `NombreTest` antes de ejecutar. En k8s usar solo comandos/identidades autorizadas, nunca copiar tokens ni configuración secreta a reporte.

## Gate final

- [ ] reproducer command and original output captured
- [ ] hypotheses discriminated by evidence
- [ ] root cause stated with causal chain
- [ ] regression fails-before/passes-after if testable
- [ ] adjacent contracts and gates not degraded
- [ ] redacted logs and environmental limits explicit
