# Segunda revision adversarial - Atlassian automatico

Veredicto: changes_requested
Bloqueantes: 0

## Verificacion ejecutada

- `python3 -m unittest discover -s tests && python3 -m compileall -q scripts && git diff --check`: PASS, 46 tests en 0.436s.
- Revision de diff completo: cambios tracked en `README.md`, `SKILL.md`, `references/atlassian.md`, `scripts/atlassian.py`, `scripts/gate.py`; archivos nuevos revisados `tests/test_atlassian.py`, `tests/test_gate_atlassian.py`, `REVIEW-atlassian-auto.md`.
- Pruebas propias con mocks y proyectos temporales para B1/B2/B3: no hicieron llamadas remotas reales.
- Busqueda de credenciales/coautores: no encontre credenciales reales ni `Co-authored-by`; solo placeholders documentados (`ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN`) y tokens falsos en tests.

## Estado de los hallazgos anteriores

### B1 - Resuelto

Cita: `scripts/atlassian.py:224-242`, `tests/test_atlassian.py:166-187`

El loop de subtasks ahora acumula `errores_subtasks`, guarda el backlog, sale con `sys.exit` si alguna subtask falla y solo despues llama a `sync_confluence`. Reproduccion propia: `B1_rc_nonzero=true`, `B1_wiki_called=false`, error `Jira rechazo subtask(s): AC-2 fallo (400): subtask invalida`.

### B2 - Resuelto

Cita: `scripts/atlassian.py:145-165`, `tests/test_atlassian.py:189-224`

Si existe `confluence_page_id`, el codigo hace `GET /wiki/rest/api/content/{id}?expand=version` y luego `PUT /wiki/rest/api/content/{id}`; no busca por titulo ni hace POST en el caso nominal aunque el titulo haya cambiado. Reproduccion propia: `B2_get_by_id=true`, `B2_title_search=false`, `B2_post=false`.

### B3 - Resuelto para el caso reportado

Cita: `scripts/gate.py:340-345`, `tests/test_gate_atlassian.py:77-86`

`close --publicar-atlassian` ahora valida que exista `harness/atlassian.json` antes de llamar a `git_merge` y antes de cambiar el backlog. Reproduccion propia sin binding: `B3_rc_nonzero=true`, `B3_merge_called=false`, `B3_status=in_progress`.

## Hallazgos nuevos

### Importante - Un fallo de `atlassian.cmd_push` deja la feature cerrada aunque `close --publicar-atlassian` sale rojo

Cita: `scripts/gate.py:415-440`

`cmd_close` marca `status`, `closed_at`, `integrado_en`, `merge_commit`, guarda el backlog y escribe bitacora en `scripts/gate.py:415-431`. Recien despues ejecuta `atlassian.cmd_push` en `scripts/gate.py:436-440`. Si el push falla por Jira/Confluence, el comando devuelve exit != 0 pero la feature ya quedo `done`.

Reproduccion propia con `git_merge` y `atlassian.cmd_push` mockeados:

```text
REG_close_rc_nonzero true
REG_status_after_push_failure done
REG_merge_commit_after_push_failure abc123
```

Esto no reabre B3: el caso exacto sin binding fue corregido. Pero mantiene el mismo modo de falso estado para errores remotos reales: el usuario pidio publicar como parte de `close`, recibio fallo, y el backlog afirma cierre local completo. Si la publicacion debe ser best-effort, el comando deberia declararlo y no hacer que el exit rojo parezca una transaccion fallida; si es parte del gate, debe evitar dejar `done` cuando el push no se completo.

## Comportamientos revisados sin hallazgo

- B1 ya no sincroniza Confluence tras fallo de subtask Jira.
- B2 usa `confluence_page_id` persistido en el caso nominal de titulo cambiado.
- B3 sin binding ya no toca merge ni backlog.
- `close` sin `--publicar-atlassian` sigue sin publicar remoto.
- La ruta sin token genera intents de outbox y no usa credenciales reales.
- No encontre coautores agregados ni secretos reales en el diff revisado.

## Archivos modificados por esta revision

- `REVIEW2-atlassian-auto.md`
