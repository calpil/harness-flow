# Documentacion PRD / SDD

## Objetivo

`documentacion.py sync` mantiene documentos versionados en `docs/` a partir del
backlog y de las features ya implementadas (`status=done`). Es deterministico y
host-neutral: funciona igual cuando la skill corre desde Hermes o desde Claude
Code.

## Archivos

- `docs/prd/PRD-master.md`: vista de producto. Lista features cerradas y sus AC.
- `docs/sdd.md`: vista tecnica. Lista microservicios, rama, merge, evidencia,
  review, progreso archivado y enlaces remotos si existen.

## Uso

```bash
$PY "$H/documentacion.py" sync
```

`gate.py close --status done` lo ejecuta dentro del cierre provisional. Cualquier
fallo local restaura backlog, documentos, progreso, historia y outbox a sus bytes
previos; no genera documentos nuevos para aparentar rollback. Si Git ya mergeo,
se conserva y se informa. Atlassian puede tener efectos remotos parciales: la
restauracion local no los deshace; reconciliar antes de reintentar. Se requiere
un escritor exclusivo; no hay garantia durable ante SIGKILL/corte electrico.

## Contrato de edicion

El usuario conserva todo contenido manual fuera del bloque generado:

```markdown
<!-- harness-flow:features:start -->
...
<!-- harness-flow:features:end -->
```

El script crea el bloque si falta por completo, reemplaza solo ese bloque si
existe y conserva bytes manuales exactos (incluidos CRLF/espacios). Un marcador
parcial, duplicado o invertido bloquea; no se repara silenciosamente. El gate y
el registro multi-repo comparten esa excepcion exacta mediante `bloques.py`.
No toca `.env`, `docs/constitution.md` ni secciones manuales del PRD.

## Relacion con Confluence

`atlassian.py push --feature <id>` embebe `docs/prd/PRD-master.md` y `docs/sdd.md`
en la pagina Confluence de la feature cuando esos archivos existen. Sin token, el
mismo cuerpo queda como intent `confluence-upsert` en `harness/outbox/`.
