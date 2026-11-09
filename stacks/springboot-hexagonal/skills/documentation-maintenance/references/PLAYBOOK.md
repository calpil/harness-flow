# Documentation as Code / Link Integrity — Playbook técnico de ejecución


## Mapa canónico de ubicación

```text
README.md                           entrada principal / quick start
aGENTS.md / CLAUDE.md               normas de agentes
CHANGELOG.md                        historial de releases
.github/copilot-instructions.md     instrucciones Copilot
.github/prompts/*.prompt.md         invocaciones manuales
.agents/skills/*/SKILL.md / .claude/skills/*/SKILL.md  procedimientos reutilizables
docs/architecture/                  principios + ADR
docs/engineering/                   contribución, deps, testing
docs/operations/                    observabilidad, despliegue, runbooks
docs/quality/                       seguridad y verificación
```

La ubicación exacta debe contrastarse con el mapa que realmente escribe `organize-docs.sh`; esta tabla es guía, no promesa de que todas las rutas existen. Mantener `LICENCE.md` y avisos legales sin reubicación unilateral.

## Ordenar sin romper enlaces

1. Obtener `git status --short` y no aplicar si hay modificaciones ajenas sin respaldo.
2. Ejecutar `bash scripts/organize-docs.sh --dry-run` y leer todos los pares origen/destino.
3. Comprobar conflictos de nombres en destino; script no debe sobrescribir por defecto.
4. Aplicar solo después de revisar plan y comprobar enlaces desde todos los prompts y README.
5. Ejecutar una segunda vez el dry-run: sin moves propuestos implica idempotencia.
6. Actualizar referencias relativas en Markdown y scripts — una ruta existente no garantiza anchor existente.
7. Revisar `git diff --check`, `python3 scripts/validate-copilot-customizations.py`.

## Manual de documentación técnica

Para cada operación publicar: prerequisitos, configuración (sin secretos), paso a paso, comando Linux/macOS/Windows cuando varíe, ejemplo de salida esperada etiquetado *ejemplo*, fallback/rollback, troubleshooting, propietario y fecha de verificación si se conoce.

La documentación normativa debe separar “política CALPIL” de “demostración del template”. No convertir `SecurityConfig.permitAll` en ejemplo de producción, ni elevar el ejemplo WorkItems a estándar de dominio.

## Detección de drift

- `pom.xml` vs `VERSIONS.md` y `DEPENDENCIES.md`.
- Contrato HTTP real vs README/OpenAPI/curl.
- Changelog master de Liquibase vs inventario de SQL.
- Instrucciones `.github/copilot-instructions.md` vs árbol de skills (`.agents/skills` / `.claude/skills`).
- Changelog vs commits efectivos y estado `Unreleased`.

Si hay conflicto, privilegiar fuente técnica (código y configuración ejecutable), levantar corrección de política/ADR cuando corresponda y no borrar evidencias históricas.

## Gate final

- [ ] root minimal after moves
- [ ] dry run lists all relocations without collision
- [ ] anchors/relative links resolve
- [ ] README and generated docs consistent with code
- [ ] second dry-run idempotent
- [ ] legal/old evidence unchanged

## Matriz de enlaces y verificación

| Cambio | Origen que debe revisarse | Cómo detectar drift |
|---|---|---|
| Movido `VERSIONS.md` | README, prompts Maven, scripts | `rg 'VERSIONS.md' --glob '*.md'` |
| Migración ADR | índice `docs/adr`, links a status | index validator |
| Nuevas skills | README, AGENTS, copilot instructions | validador de skills |
| Nuevos endpoints | docs API, ejemplos curl, README | test de contrato + curl |
| Cambios profile/env | .env.example, Helm docs, operaciones | comparación de properties reales |

### Política de mantenimiento

- La misma regla se define en **un** documento normativo y se referencia desde los demás.
- Un procedimiento que requiere credenciales documenta dónde obtenerlas sin incluir valores ni PAT.
- Un comando ejemplar lleva etiqueta `ejemplo` si no está probado.
- Si código y documentación contradicen un ADR aceptado, levantar desviación/supersession antes de editar el ADR.
- Los documentos legales, archivo de licencia y avisos conservan nombre/ubicación salvo requerimiento expreso.
- En una actualización periódica comparar todos los enlaces movidos y detectar obsolescencia por versión.
