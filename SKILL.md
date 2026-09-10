---
name: harness-flow
description: "Use in repos with harness/: spec-driven flow + gates."
---

# Harness Flow

Proceso spec-driven para proyectos multi-repo. Puerto del arnés Rust (`harness_process`) a Hermes: sin binario, sin instalador, sin compilar por SO. El proceso vive aquí; los gates son scripts Python que devuelven exit≠0.

**Idioma: responde SIEMPRE en español.** Los documentos generados van en español, sin tildes en los nombres de archivo.

## Layout

El arnés NO se copia a cada repo. Una instalación por PROYECTO (raíz multi-repo), no por microservicio:

```
~/proyectos/adr/                 <- raíz multi-repo = "proyecto" en el hub
  harness/                       <- estado del proceso (versionado)
    feature_list.json            <- backlog + rules
    progress/current-<id>.md     <- estado vivo por feature
    progress/history.md          <- bitácora append-only
    atlassian.json               <- sitio/proyecto/space (NUNCA credenciales)
  docs/                          <- specs, planes, evidencia, PRDs, lecciones
  docs/vault/                    <- vault Obsidian (versionado)
  graphify-out/                  <- grafo local (gitignored)
  ms-orders-service/             <- repo git propio = "microservicio"
  front-adr/
```

Credenciales del hub: `~/.harness-hub/.env` (fuera del repo, por máquina).

Los scripts viven en el directorio de esta skill. Define una vez por sesión:
`H=~/AppData/Local/hermes/skills/software-development/harness-flow/scripts` (macOS: `~/.local/share/hermes/skills/...`).

## Arranque de sesión

Al entrar a un proyecto con `harness/feature_list.json`, ANTES de responder nada sustantivo:

```bash
python "$H/estado.py"
```

Muestra features abiertas, gates pendientes y edad del grafo. Si hay una feature `in_progress`, retómala; no arranques otra.

## El flujo

Tres roles, en orden. No los saltes.

### 1. Leader — spec antes que código

1. Lee el backlog y `progress/current-<id>.md`. Consulta el grafo antes de leer archivos a ciegas:
   `graphify query "<pregunta>"` si existe `graphify-out/graph.json`.
2. Consulta impacto cross-repo: `python "$H/hub.py" impacto --microservicio <proyecto>/<servicio>`.
3. Revisa lecciones aplicables: `python "$H/leccion.py" list` **antes** de diseñar.
4. Escribe `docs/spec-feature-<id>-<slug>.md` con `Estado: draft` usando `templates/spec.md`. Los AC-n en Given/When/Then son obligatorios.
5. **Ritual de aprobación**: MUESTRA el spec al usuario en el chat, PREGUNTA si lo aprueba, y solo con su SÍ explícito corre:
   `python "$H/gate.py" approve-spec --feature <id> --yes`
   Nunca apruebes por tu cuenta. El script se niega sin `--yes`.

### 2. Implementer — evidencia por AC

1. Verifica el gate: `python "$H/gate.py" check-spec --feature <id>` (exit≠0 si no está approved o está stale).
2. Trabaja DENTRO del worktree de la feature (`python "$H/worktree.py" start --feature <id>`).
3. Escribe evidencia en `docs/impl-<id>.md`: una fila por AC-n citando `archivo:linea`.

### 3. Reviewer — veredicto sellado

1. Arma el paquete: `python "$H/revision.py" --feature <id>` (solo lectura).
2. Escribe `docs/review-<id>.md` con una fila por cada AC-n del spec, nombrándolo y citando `archivo:linea`.
3. Registra el veredicto:
   `python "$H/gate.py" revision --feature <id> --veredicto approved|changes_requested|blocked`
   El script estampa `Revisado: ...`. Un `Veredicto:` tipeado a mano NO cuenta.

### 4. Cierre

```bash
python "$H/gate.py" close --feature <id> --status done --to <rama> --leccion <clase>
```

El gate exige, según `rules`: spec approved y fresco, review approved, check limpio, lección declarada. Se niega sin `--to`: PREGÚNTALE al usuario a qué rama integra. Integra LOCAL; publicar es aparte.

## Gates (todos con exit≠0)

| Comando | Verifica |
| --- | --- |
| `gate.py check` | Todo el proceso; es el gate maestro |
| `gate.py check-spec --feature <id>` | Spec existe, `Estado: approved`, firma fresca |
| `gate.py approve-spec --feature <id> --yes` | Solo con SÍ del usuario; sella quién/cuándo |
| `gate.py revision --feature <id> --veredicto <v>` | Review responde por CADA AC-n con `archivo:linea` |
| `gate.py close --feature <id> --status done --to <rama>` | Todas las reglas activas |

Reglas en `harness/feature_list.json` → `rules`: `require_spec_approved`, `require_review`, `require_leccion`, `require_verify_green`, `require_docs_al_dia`.

**Rutas protegidas**: `docs/prd/**`, `docs/constitution.md`, `.env`. Son del USUARIO. Ningún agente las reescribe — `gate.py check` reporta la violación.

## Memory Hub Postgres

Mismo esquema que el arnés Rust (`graph_nodes`, `graph_edges`), así que el histórico se conserva. Credenciales de `~/.harness-hub/.env` (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`, `DB_SSL_MODE` por defecto `require`).

```bash
python "$H/hub.py" mapa                                    # panorama multi-proyecto
python "$H/hub.py" descubrir [--aplicar]                   # repos git bajo la raíz
python "$H/hub.py" impacto --microservicio <proy>/<svc>    # quién se rompe si toco esto
python "$H/hub.py" vincular --consumer <a> --target <b>
python "$H/hub.py" derivar-graphify                        # graphify-out/graph.json -> hub
```

Esquema real del hub (verificado contra la base en producción): las dependencias
entre microservicios son aristas de tipo **`DEPENDE_DE`**, y los commits son
**nodos con label `Commit`**, no una propiedad del microservicio. Las props de un
microservicio son `servicio`, `proyecto`, `path`. No inventes otro vocabulario:
el hub es compartido con el arnés Rust en la otra máquina y debe seguir cuadrando.
`props` se fusiona con `||`, así que nunca escribas claves de control (`_id`,
`_label`) dentro de `props`.

`derivar-graphify` detecta servicios con `(ms-[a-z0-9-]+-service|[a-z0-9-]+-ui)` sobre `source_file` y filtra relaciones `references|implements|depends_on|uses|cites|shares_data_with`.

## Lecciones (memoria procedural)

Por CLASE de trabajo, nunca por id de feature. `docs/lecciones/<clase>.md`.

```bash
python "$H/leccion.py" list                 # ANTES de diseñar
python "$H/leccion.py" usar <clase>
```

PATCHEA la lección que estuvo en juego antes de crear otra. NO captures: fallas de entorno, negativas sobre herramientas, errores transitorios, narrativas de tarea única, ni fracasos disfrazados de práctica.

## Obsidian

`docs/vault/` dentro del repo, versionado. Se regenera desde el grafo y los docs del proceso:

```bash
python "$H/vault.py" build
```

Enlaza specs ↔ AC ↔ evidencia ↔ lecciones ↔ nodos de graphify con wikilinks. Ver `references/obsidian.md`.

## Jira / Confluence

Solo si existe `harness/atlassian.json`. Sin ese archivo el flujo se comporta igual, sin tocar nada. Si el usuario quiere integrar y no hay binding, PREGÚNTALE a qué proyecto Jira y space pertenece el repo: no lo adivines. Mapeo y comandos en `references/atlassian.md`.

## Reglas duras

- Todo hallazgo relevante se escribe en `harness/progress/`. Una respuesta en el chat no reemplaza evidencia persistida.
- El cuerpo del PRD y la constitution son del USUARIO. No los reescribas.
- Aislamiento: una feature sin worktree bloquea a las demás sin worktree.
- No afirmes lo que no puedes comprobar. Si un gate no corrió, dilo.
- Los AC pueden declarar su comando de dos formas, ambas válidas:
  `- AC-1: ... \`verificar: pytest -q\`` o una línea `Comando: \`pytest -q\`` debajo del AC.
- La evidencia cubre un AC si la cita `archivo:linea` está en la **sección** del AC
  (encabezado `## AC-1` con la cita debajo), no necesariamente en la misma línea.
  Prosa sin cita nunca cuenta como cobertura.
- `psycopg` debe estar en el venv de Hermes, no en el del proyecto. Si `hub.py` se
  queja, instálalo con:
  `uv pip install --python "<venv de hermes>/Scripts/python.exe" "psycopg[binary]"`
  (el `python -m pip` del venv de Hermes no existe).
