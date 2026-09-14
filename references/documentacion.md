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

`gate.py close --status done` lo ejecuta automaticamente despues de cerrar. Si
`--publicar-atlassian` falla, `gate.py` revierte el cierre provisional y vuelve a
sincronizar para que PRD/SDD no digan que una feature incompleta esta hecha.

## Contrato de edicion

El usuario conserva todo contenido manual fuera del bloque generado:

```markdown
<!-- harness-flow:features:start -->
...
<!-- harness-flow:features:end -->
```

El script crea el bloque si falta, reemplaza solo ese bloque si existe y no toca
`.env`, `docs/constitution.md` ni secciones manuales del PRD.

## Relacion con Confluence

`atlassian.py push --feature <id>` embebe `docs/prd/PRD-master.md` y `docs/sdd.md`
en la pagina Confluence de la feature cuando esos archivos existen. Sin token, el
mismo cuerpo queda como intent `confluence-upsert` en `harness/outbox/`.
