# Keep a Changelog / Traceable Release History — Playbook técnico de ejecución


## Formato Keep a Changelog

```markdown
## [Unreleased]

### Added
- Exposición de nueva consulta de activos con filtrado por tenant autorizado.

### Changed
- Configuración del cliente de integración para tiempos límite acotados.

### Fixed
- Tratamiento de registros antiguos que no tenían código de país.

### Security
- Validación de autorización por recurso al consultar activos.
```

Entradas **ilustrativas**: solo colocar aquellas que existen en diff/test verificado. `Security` no debe contener una afirmación de mitigación CVE sin árbol transitivo/advisory.

## Política de publicación

- Sección `Unreleased` acumula trabajo que todavía no es versión.
- En release usar `## [x.y.z] - AAAA-MM-DD` solo con versión y fecha reales; no inferir de hora del sistema una aprobación.
- SemVer MAJOR: ruptura contrato/API o cambio incompatible documentado.
- SemVer MINOR: capacidad compatible.
- SemVer PATCH: fix compatible (si la política de versiones de producto lo adopta).
- Descartar movimiento puramente interno de Markdown si no aporta al consumidor, salvo cambios de guía de integración.

## Trazabilidad

| Entrada | Evidencia | Tests | Enlaces |
|---|---|---|---|
| feature visible | PR/commit/diff | escenarios aceptados | ADR si aplica |
| breaking contract | cambio OpenAPI | contract test | migration notes |
| dependency upgrade | resolved tree | security + verify | release notes |
| DB migration | changelog SQL | DB E2E | runbook rollback |

El archivo `CHANGELOG.md` debe seguir en raíz. `docs` puede contener explicación profunda, pero no otro historial paralelo que compita con root.

## Revisión previa a commit

1. `git diff --name-status` confirma cambios y scope.
2. `CHANGELOG.md` describe efecto final, no proceso de exploración.
3. No IDs de Azure DevOps/PR inventados.
4. No afirmar deploy realizado ni tests aprobados sin salida.
5. `git diff --check` y enlace relativo a ADR si realmente existe.

## Gate final

- [ ] Unreleased section reflects actual diff
- [ ] release section only with verified version/date
- [ ] breaking changes have migration note
- [ ] security claims cite tested remediation
- [ ] no fabricated ticket/PR/commit
- [ ] public note hides secrets/PII

## Ejemplo de nota de migración verificable

```markdown
### Changed
- API de activos: `GET /api/v1/assets` admite filtro opcional `countryCode` sin modificar la estructura del resultado.

### Security
- [Solo cuando se probó] El acceso a activos valida permiso y pertenencia al tenant antes de consultar datos.
```

Estas entradas **son demostrativas**; no deben insertarse sin un diff y pruebas que demuestren su veracidad.

## Reglas ante casos límite

- `Unreleased` vacío: no inventar entradas ni versionado, mantener sección vacía si política lo permite.
- Cherry-picks: evitar duplicar cambios que ya figuran publicados en versión anterior.
- Varios commits del mismo feature: consolidar como una entrada orientada al consumidor.
- Release candidate o rollback: indicar qué se publicó realmente, sin retroescribir fecha anterior.
- Fix técnico oculto al usuario: documentar solo si impacta estabilidad, seguridad, performance o soporte.
- Superseded ADR: referenciar el ADR reemplazante si hubo decisión aprobada, no borrar el anterior.
