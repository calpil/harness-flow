# Third-Party Dependency Architecture Review — Playbook técnico de ejecución


## Evaluación comparativa obligatoria

| Criterio | Sin dependencia | Biblioteca propuesta | Alternativa existente |
|---|---|---|---|
| Caso real resuelto | | | |
| Restricción Java 21/Boot 4 | | | |
| Soporte/mantenimiento | | | |
| CVE y transitive count | | | |
| Licencia/uso corporativo | | | |
| Huella operacional (startup/heap) | | | |
| Abstracción hexagonal | | | |
| Desinstalación/rollback | | | |

No siempre hace falta score cuantitativo: registrar ventajas, pérdidas y evidencia comprobable. Decisiones de plataforma requieren ADR; implementación puntual con alternativa inequívoca no siempre.

## Maven: decidir ubicación correcta

- En `domain` solamente API Java pura; introducir libs de serialización/DB allí crea acoplamiento.
- En `application` no usar cliente HTTP de vendor; declararlo como port out y poner SDK en outbound adapter.
- En `adapter.in.web`, librería HTTP/JSON puede ser legítima si no llega al dominio.
- En `adapter.out.persistence`, drivers, JPA y mappers quedan encerrados.
- Test libraries deben tener `<scope>test</scope>`; evitar arrastrarlas a runtime.

## Comandos para comprobar

```bash
./mvnw dependency:tree -Dverbose
./mvnw dependency:tree -Dincludes=groupId:artifactId
./mvnw dependency:analyze
./mvnw -DskipTests help:effective-pom -Doutput=target/effective-pom.xml
```

Al registrar `versions:display-dependency-updates` distinguir versión reportada, soporte real con Boot BOM y disponibilidad GA. Consultar metadata y notas de release de proveedor, no una recomendación de blog sin fecha.

## Semáforo

- **BLOCK**: CVE crítica explotable sin mitigación, licencia incompatible, ruptura probada de framework, fuga directa al dominio.
- **CONDITIONED**: upstream no mantiene, incompatibilidades transitivas/upgrade pendiente, pruebas de integración limitadas.
- **ALLOW**: ganancia demostrada, sin breaking, dependencias/procedencia trazables, gates passing.

## Nota de seguridad

Un override explícito de versión por mitigación debe quedar documentado, con fecha, CVE y criterio de retirada. No borrarlo solo para limpiar el POM o evitar warnings.

## Gate final

- [ ] necessity and no-library alternative articulated
- [ ] BOM ownership/scope and transitive graph verified
- [ ] CVE/license/upstream support evidence recorded
- [ ] domain/application remain technology agnostic
- [ ] integration smoke and rollback validated
- [ ] upgrade owner and policy documented

## Desempate entre candidatos

1. Si el parent/BOM ya ofrece el artefacto, usar esa versión salvo advisory confirmado.
2. Si hay dos proveedores equivalentes, preferir integración de menor footprint, mantenimiento verificable, licencia aceptable y API estable.
3. Si el SDK requiere credenciales o retries específicos, encapsularlo en adaptador de salida para sustituirlo sin alterar domain.
4. Si una CVE transitiva es irrelevante por ruta de ejecución no presente, documentar análisis de reachability y compensación; no omitir el finding.
5. Si el proyecto deja de mantener releases, registrar reemplazo y costo de migración.

## Ficha de decisión

```text
Dependencia y coordenadas: <groupId:artifactId:version>
Alternativas: JDK/BOM/otro proveedor/no implementar
API usada y superficie: <package adapter>
Soporte y licencia: <evidencia URL>
Resolución transitiva: <output tree>
Seguridad: <advisory + fecha verificación>
Rollback: <commit de cambio + switch de adapter>
ADR: <link si aplica, si no N/A>
```

Los números de descarga/popularidad no demuestran soporte ni seguridad. No usar versiones `LATEST`/ranges reproduciblemente indeterminados en `pom.xml`.
