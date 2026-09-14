# Tercera revision adversarial - Atlassian automatico

Veredicto: approved
Bloqueantes: 0

## Verificacion ejecutada

- `python3 -m unittest discover -s tests && python3 -m compileall -q scripts && git diff --check`: PASS, 47 tests en 0.421s.
- Revision acotada de `scripts/gate.py` alrededor de `cmd_close`, `scripts/atlassian.py`, `tests/test_gate_atlassian.py` y `tests/test_atlassian.py`.
- Reproducciones propias con mocks y proyectos temporales, sin llamadas remotas reales.

## Resultado del fix de rollback

### Aprobado - rollback de `close --publicar-atlassian` al fallar el push

Cita: `scripts/gate.py:339-347`, `scripts/gate.py:418-452`, `tests/test_gate_atlassian.py:88-102`

`cmd_close` toma una copia de los campos de cierre originales, valida el binding antes de mergear, guarda el cierre provisional, ejecuta `atlassian.cmd_push` y, si ese push sale con `SystemExit`, relee el backlog y revierte solo `status`, `closed_at`, `integrado_en`, `merge_commit`, `leccion`, `leccion_motivo` y `note`. No borra campos remotos que `atlassian.py` haya persistido parcialmente.

Reproduccion propia: mockee `git_merge` con `abc123` y `atlassian.cmd_push` para escribir `jira_key=ADR-7` y `jira_synced_at=partial` en `harness/feature_list.json` antes de fallar. Resultado: `rc=1`, `status=in_progress`, sin `closed_at`, sin `integrado_en`, sin `merge_commit`, y `jira_key=ADR-7` preservado.

## Hallazgos anteriores verificados

### B1 - Sigue resuelto

Cita: `scripts/atlassian.py:224-242`, `tests/test_atlassian.py:166-187`

El loop de subtasks acumula errores y hace `sys.exit` antes de `sync_confluence`. Reproduccion propia con fallo en la segunda subtask: `rc=1`, el error menciona `subtask`, y no hubo rutas `/wiki/` llamadas.

### B2 - Sigue resuelto

Cita: `scripts/atlassian.py:145-165`, `tests/test_atlassian.py:189-224`

Si existe `confluence_page_id`, se consulta `/wiki/rest/api/content/{id}?expand=version` y se actualiza esa pagina. La busqueda por titulo solo queda como fallback cuando no hay resultado por ID. Reproduccion propia con `confluence_page_id=999`: se hizo GET por ID y PUT a `/wiki/rest/api/content/999`; no se hizo busqueda por titulo ni POST.

### B3 - Sigue resuelto

Cita: `scripts/gate.py:343-347`, `tests/test_gate_atlassian.py:77-86`

`close --publicar-atlassian` sin `harness/atlassian.json` falla antes de ejecutar `git_merge` o tocar el backlog. Reproduccion propia sin binding: `rc=1`, `merge_calls=0`, `status=in_progress`, sin `merge_commit`.

## Hallazgos nuevos

No encontre hallazgos nuevos en el alcance de esta tercera revision.

## Archivos modificados por esta revision

- `REVIEW3-atlassian-auto.md`
