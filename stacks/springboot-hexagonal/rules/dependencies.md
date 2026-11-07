---
description: Evaluación de dependencias Maven Spring Boot y remediaciones verificables
globs: ["pom.xml"]
---
- Solo versiones estables publicadas y mutuamente compatibles con el parent Boot y Java 21.
- No borrar pisos de seguridad del BOM/transitivas sin `effective-pom` + `dependency:tree` y tests que lo prueben.
- Para upgrade global leer `.claude/skills/maven-upgrade/SKILL.md`; para dependencia puntual leer `dependency-review`.
- Revisar `docs/engineering/DEPENDENCIES.md`, `docs/engineering/VERSIONS.md` (o versión raíz previa al ordenamiento), `docs/security/dependency-remediation.md` y regresión de dependencias.
- No saltar pruebas, no alfas/RC/SNAPSHOT, changelog y ADR en cambios materialmente arquitectónicos.
