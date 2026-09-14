# Revision adversarial - Atlassian automatico

Veredicto: changes_requested
Bloqueantes: 2

## Verificacion ejecutada

- `python3 -m unittest discover -s tests && python3 -m compileall -q scripts`: PASS, 43 tests en 0.414s.
- `git diff --check`: PASS.
- Revision de diff y archivos nuevos: `scripts/atlassian.py`, `scripts/gate.py`, `tests/test_atlassian.py`, `tests/test_gate_atlassian.py`, `README.md`, `SKILL.md`, `references/atlassian.md`.
- Busqueda de credenciales/coautores: no encontre credenciales reales ni `Co-authored-by`; solo placeholders documentados y tokens falsos en tests.

## Hallazgos

### Bloqueante - Fallos de subtasks Jira dejan el push en verde y publican Confluence igual

Cita: `scripts/atlassian.py:214-228`

El loop de AC solo imprime `subtask ... fallo` cuando Jira rechaza una subtask, pero no incrementa errores ni sale con error. Despues guarda backlog y llama `sync_confluence`. Resultado: una feature puede quedar con historia Jira creada, subtasks incompletas y pagina Confluence sincronizada, mientras `atlassian.py push` devuelve exit 0.

Reproduccion con API mockeada:

```text
REPRO_SUBTASK_FAIL_RC 0
REPRO_SUBTASK_FAIL_WIKI_CALLED True
REPRO_SUBTASK_FAIL_OUT_CONTAINS True
```

Esto viola el objetivo de que Jira se cree/actualice completo y hace falso verde ante error remoto parcial. Los tests actuales cubren error al actualizar la historia (`tests/test_atlassian.py:146-164`), pero no fallo de subtask.

### Bloqueante - `confluence_page_id` se guarda pero no se usa para actualizar; un cambio de titulo duplica paginas

Cita: `scripts/atlassian.py:142-163`, `references/atlassian.md:76-77`

La documentacion promete que `confluence_page_id` evita duplicados en un segundo `push`, pero `sync_confluence` busca solo por `spaceKey + title`. Si el nombre de la feature cambia, si el titulo remoto cambio, o si la busqueda no devuelve la pagina guardada, el codigo hace `POST /wiki/rest/api/content` aunque el backlog ya tenga `confluence_page_id`.

Reproduccion con backlog que ya contiene `confluence_page_id=999` y busqueda por titulo vacia:

```text
REPRO_PAGE_ID_IGNORED_RC 0
REPRO_PAGE_ID_IGNORED_POSTED True
REPRO_PAGE_ID_IGNORED_PUT_999 False
```

Debe preferir actualizar por `confluence_page_id` cuando existe, y solo crear/buscar por titulo cuando no hay id persistido. Si el id guardado devuelve 404/409, ese caso debe ser explicito y testeado.

### Importante - `close --publicar-atlassian` valida el binding despues de cerrar la feature

Cita: `scripts/gate.py:413-440`

`cmd_close` marca status, `closed_at`, `integrado_en`, `merge_commit`, guarda backlog y escribe bitacora antes de comprobar que existe `harness/atlassian.json`. Con `--publicar-atlassian` en un repo sin binding, el comando falla, pero deja la feature cerrada.

Reproduccion con `git_merge` mockeado:

```text
REPRO_CLOSE_NO_BINDING_FLAG_RC 1
REPRO_CLOSE_NO_BINDING_FLAG_STATUS done
REPRO_CLOSE_NO_BINDING_FLAG_ERR [!!] --publicar-atlassian exige harness/atlassian.json
```

La validacion de precondiciones para publicar deberia correr antes del merge y antes de modificar el backlog, o el cierre debe declarar que el push es best-effort y no parte atomica del comando.

## Comportamientos revisados sin hallazgo bloqueante

- Con token, el camino nominal crea historia Jira, subtasks y pagina Confluence; el test lo cubre en `tests/test_atlassian.py:64-98`.
- Con token y pagina existente por mismo titulo, actualiza Confluence con version +1 y no hace POST; cubierto en `tests/test_atlassian.py:100-128`.
- Sin token, la outbox incluye intent `confluence-upsert` y `jira-upsert`; cubierto en `tests/test_atlassian.py:130-144`.
- `close` sin `--publicar-atlassian` no llama `atlassian.cmd_push`; verificado con mock: `REPRO_CLOSE_DEFAULT_PUBLISHED []`.
- `close --publicar-atlassian` si llama `atlassian.cmd_push`; verificado con mock: `REPRO_CLOSE_FLAG_PUBLISHED ['7']`.

## Archivos modificados por esta revision

- `REVIEW-atlassian-auto.md`
