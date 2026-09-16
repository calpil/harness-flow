---
name: harness-flow
description: "Use in repos with harness/: spec-driven flow + gates."
---

# Harness Flow

Proceso spec-driven para proyectos multi-repo. Puerto del arnés Rust (`harness_process`) a un agente: sin binario, sin instalador, sin compilar por SO. El proceso vive aquí; los gates son scripts Python que devuelven exit≠0.

**Host-neutral**: funciona igual en Hermes, Claude Code y GPT/Codex. Lo único que cambia son las herramientas del agente (subagente y escritura de skills); los scripts se autodetectan. Ver "Equivalencias por host".

**Idioma: responde SIEMPRE en español.** Los documentos generados van en español, sin tildes en los nombres de archivo.

## Layout

El arnés NO se copia a cada repo. Una instalación por PROYECTO (raíz multi-repo), no por microservicio:

```
~/proyectos/adr/                 <- raíz multi-repo = "proyecto" en el hub
  harness/                       <- estado del proceso (versionado)
    feature_list.json            <- backlog + rules
    grafos.json                  <- raices de graphify a combinar (opcional)
    progress/current-<id>.md     <- estado vivo por feature
    progress/archive/current-<id>.md <- progreso archivado al cerrar done
    progress/history.md          <- bitácora append-only
    atlassian.json               <- sitio/proyecto/space (NUNCA credenciales)
  docs/                          <- specs, planes, evidencia, PRDs
  .agents/skills/                <- skills de GPT/Codex si se instala por repo
  docs/vault/                    <- vault Obsidian (versionado)
  graphify-out/                  <- grafo local (gitignored)
  ms-orders-service/             <- repo git propio = "microservicio"
  front-adr/
```

Credenciales del hub: `~/.harness-hub/.env` (fuera del repo, por máquina).

Los scripts viven en el directorio de esta skill y necesitan un intérprete con
las dependencias del hub (`psycopg`). Esa ruta cambia según el host, el SO y el
perfil, así que **no la hardcodees**: `entorno.py` la detecta.

```bash
# bash / zsh  (macOS, Linux)
eval "$(python3 <skill>/scripts/entorno.py --shell)"

# PowerShell (Windows)
python <skill>\scripts\entorno.py --powershell | Invoke-Expression
```

Eso define `H` (scripts), `PY` (intérprete con dependencias) y `HARNESS_HOST`
(`hermes`, `claude`, `gpt` o `generic`). A partir de ahí todos los comandos de este
documento funcionan tal cual en los tres SO y en los hosts soportados:

```bash
$PY "$H/estado.py"
```

Sin flags, `entorno.py` imprime un diagnóstico (SO, host, H, PY, si `psycopg`
está) y sale con exit≠0 si no puede resolver un intérprete usable. La falta de
`psycopg` solo es error con `--hub`: quien usa nada más los gates locales no
necesita el Memory Hub. `entorno.py --instalar-deps` instala
`psycopg[binary]` en el intérprete correcto (en Claude Code crea un venv propio
en `~/.harness-flow/venv` en vez de tocar el python del sistema).

Detecta en este orden: `HARNESS_PYTHON` → venv neutro (`HARNESS_VENV` o
`~/.harness-flow/venv`) → en host Hermes, `HERMES_PYTHON`/`HERMES_HOME`, el
launcher `hermes` del PATH y las rutas por SO → el propio intérprete. Si nada
resuelve, exporta `HARNESS_PYTHON` a mano. `--host claude|hermes|gpt|codex|generic` fuerza
el host cuando la detección no aplica. `codex` se normaliza a `gpt`.

## Arranque de sesión

Al entrar a un proyecto con `harness/feature_list.json`, ANTES de responder nada sustantivo:

```bash
$PY "$H/estado.py"
```

Muestra features abiertas, gates pendientes y edad del grafo. Si hay una feature `in_progress`, retómala; no arranques otra.

Al listar pendientes, contrasta el resumen con un conteo programatico de
`feature_list.json` por `status`. `estado.py` cuenta `todo`, `pending`,
`in_progress`, `blocked` y `review` como abiertas; solo `done` y `superseded`
como cerradas, con desglose separado. Los estados desconocidos o ausentes se
cuentan y muestran aparte: nunca calcules cierres como total menos abiertas.
No reescribas estados para cuadrar el resumen. Los gates y el aislamiento de
worktrees comprueban trabajo iniciado, no toda la cola pendiente.

## El flujo

Tres roles, en orden. No los saltes.

### 1. Leader — spec antes que código

1. Lee el backlog y `progress/current-<id>.md`. Consulta el grafo antes de leer archivos a ciegas:
   `$PY "$H/contexto.py" brief --feature <id>` (indice compacto: AC, reglas, lecciones,
   impacto del hub y superficie de contacto del grafo). Si el contexto esta vencido lo dice;
   refresca con `$PY "$H/contexto.py" refrescar`. Para una pregunta puntual que el brief no
   cubre, `graphify query "<pregunta>" --graph <combinado>`.
2. Consulta impacto cross-repo: `$PY "$H/hub.py" impacto --microservicio <proyecto>/<servicio>`.
3. Revisa lecciones aplicables: `$PY "$H/leccion.py" list` **antes** de diseñar.
4. Escribe `docs/spec-feature-<id>-<slug>.md` con `Estado: draft` usando `templates/spec.md`. Los AC-n en Given/When/Then son obligatorios.
5. **Ritual de aprobación**: MUESTRA el spec al usuario en el chat, PREGUNTA si lo aprueba, y solo con su SÍ explícito corre:
   `$PY "$H/gate.py" approve-spec --feature <id> --yes`
   Nunca apruebes por tu cuenta. El script se niega sin `--yes`.

### 2. Implementer — evidencia por AC

1. Verifica el gate: `$PY "$H/gate.py" check-spec --feature <id>` (exit≠0 si no está approved o está stale).
2. Trabaja DENTRO del worktree de la feature (`$PY "$H/worktree.py" start --feature <id>`).
3. Escribe evidencia en `docs/impl-<id>.md`: una fila por AC-n citando `archivo:linea`.

### 3. Reviewer — subagente aislado, veredicto sellado

El review NO lo haces tú mismo. Un revisor que recuerda haber escrito el código se aprueba solo; uno que solo ve spec + diff, no.

1. Arma el briefing: `$PY "$H/revision.py" --feature <id> --briefing`
2. Lanza el revisor con el subagente de tu host, pegando esa salida como contexto. Goal: "Revisa la feature #<id> y escribe docs/review-<id>.md". El subagente lee spec y código por su cuenta, no modifica nada más.
   - Hermes: `delegate_task` con la salida en `context`.
   - Claude Code: la tool `Task` con `subagent_type: general-purpose`, pegando la salida en el prompt.
   - GPT/Codex: `codex exec` o el revisor/subagente disponible, pegando el briefing; si no hay aislamiento real, decláralo.
   NO uses un fork de la sesión como revisor: hereda tu historial y con él el sesgo que el aislamiento evita.
3. Cuando vuelva, LEE tú `docs/review-<id>.md`. El veredicto del subagente es un autoinforme: verifica que cada fila cite `archivo:linea` real antes de sellar.
4. Sella:
   `$PY "$H/gate.py" revision --feature <id> --veredicto approved|changes_requested|blocked`
   El script estampa `Revisado: ...`. Un `Veredicto:` tipeado a mano NO cuenta.

Si el subagente no está disponible, `$PY "$H/revision.py" --feature <id>` da el paquete y revisas tú — dicéndolo explícitamente, porque el rigor baja.

### 4. Cierre

**Raiz multi-repo sin `.git`, con worktrees ya existentes:** usar el registro
estricto y el cierre de integracion MANUAL verificada; no inventar una rama o
`.git` en la raiz. Declarar TODOS los microservicios y SHAs en el manifiesto de
[`references/multirepo.md`](references/multirepo.md), sin autodetectar solo exitos:

```bash
$PY "$H/worktree.py" register --feature <id> --manifest <registro.json>
# Integracion externa autorizada + registro actualizado al tip destino;
# verify y revision INDEPENDIENTE ligados al mapa completo, despues:
$PY "$H/gate.py" close --feature <id> --status done --to <rama> \
  --integrated --postmerge /ruta/bases-postmerge.json --leccion <clase-existente>
```

`--integrated` NO hace merges: revalida repos/worktrees reales, limpieza,
ancestria y tips exactos. ANTES de done ejecuta suites completas sobre cada
destino: Go mediante `postmerge_medido.py` (JSON + exits reales -exec), o el
contrato Angular22/Vitest4+Node22 de ADR mediante `postmerge_frontend.py`, con
bases preintegracion genuinas y el mapa `--postmerge`. No acepta recibos PASS
manuales ni comandos genericos: protocolos ajenos/base ausente quedan bloqueados.
Para el contrato frontend, configuracion cerrada y evidencia durable, lee
`references/multirepo.md` (mismos CLI en Hermes y Claude, sin instalar dependencias).
Persiste `integraciones` POR REPO (fuente y destino),
no un `merge_commit` inventado. El recibo no da permisos de implementacion/docs
ni sustituye spec, review, verify, leccion, rutas protegidas o aislamiento.
Cambiar mapa/SHAs/spec/evidencia invalida los contextos de review y verify.
Ver la referencia para el caso ya integrado, protecciones y limites de la foto.

**Monorepo legacy (raiz Git sin registro multi-repo):**

```bash
python "$H/gate.py" close --feature <id> --status done --to <rama> --leccion <clase>
# si harness/atlassian.json existe y el usuario pidio publicar remoto:
python "$H/gate.py" close --feature <id> --status done --to <rama> \
  --leccion <clase> --publicar-atlassian
```

El gate exige, segun `rules`: spec approved y fresco, review approved, check limpio, leccion declarada. Se niega sin `--to`: PREGUNTALE al usuario a que rama integra.

`close` sin `--integrated` **ejecuta el merge de verdad** (`git merge --no-ff` de la rama de la feature en `--to`) y guarda el sha en `merge_commit`. Aborta sin tocar el backlog si el arbol esta sucio, la rama no existe o el merge conflictua: es preferible una feature que no cierra a un `done` sobre una rama que nunca entro. Integra LOCAL; publicar es aparte salvo que pases `--publicar-atlassian`, que luego corre `atlassian.py push` para sincronizar Jira y Confluence.

Cuando el cierre queda en `done`, el gate tambien:
- mueve `harness/progress/current-<id>.md` a `harness/progress/archive/current-<id>.md` si existe;
- guarda `progress_archive` en `feature_list.json`;
- sincroniza `docs/prd/PRD-master.md` y `docs/sdd.md` desde las features cerradas.

Ante fallo de sync/cierre local (tambien `--publicar-atlassian`), se restaura el
preestado byte-identico de backlog, PRD/SDD, progreso e historia; no se regeneran
documentos distintos como sustituto de rollback. Un merge Git ya hecho se
conserva y se informa. Atlassian puede haber publicado parcialmente: reconciliar
remoto antes de reintentar, sin prometer rollback remoto. Ver limites de caidas
y concurrencia en `references/multirepo.md`.

Verifica el resultado (`git log --oneline -1` en la rama destino) antes de dar por integrada una feature: el mensaje de un script no es evidencia de que el merge ocurrió.

## Gates (todos con exit≠0)

| Comando | Verifica |
| --- | --- |
| `gate.py check` | Todo el proceso; es el gate maestro |
| `gate.py check-spec --feature <id>` | Spec existe, `Estado: approved`, firma fresca |
| `gate.py approve-spec --feature <id> --yes` | Solo con SÍ del usuario; sella quién/cuándo |
| `gate.py revision --feature <id> --veredicto <v>` | Review responde por CADA AC-n con `archivo:linea` |
| `gate.py close --feature <id> --status done --to <rama>` | Todas las reglas activas |
| `postmerge.py base --repo <r> --guardar <j>` | Foto de los rojos ANTES del merge |
| `postmerge.py check --repo <r> --base <j>` | Rojos NUEVOS que agrego el merge (exit 1) |

**Despues de cada `close ... --to <rama>`, corre `postmerge.py`** sobre la rama
destino. Los AC de una feature miden su worktree y no pueden ver los choques
entre features. El gate compara nombres de test contra la base pre-merge y solo
falla por rojos NUEVOS, asi que la deuda tolerada no lo vuelve inservible:

```bash
$PY "$H/postmerge.py" base  --repo <ruta> --guardar /tmp/base-<svc>.json   # ANTES
$PY "$H/gate.py" close --feature <id> --status done --to develop --leccion <clase>
$PY "$H/postmerge.py" check --repo <ruta> --base /tmp/base-<svc>.json      # DESPUES
```

Si aparecen rojos nuevos: ficha el choque, no bajes la asercion que lo detecto.
Al verificar el exit a mano no uses un pipe (`| tail`): te devuelve el status
del tail, no el del gate.

Reglas en `harness/feature_list.json` → `rules`: `require_spec_approved`, `require_review`, `require_leccion`, `require_verify_green`, `require_docs_al_dia`.

**Rutas protegidas**: `docs/prd/**`, `docs/constitution.md`, `.env`. Son del USUARIO. Ningún agente las reescribe a mano — `documentacion.py sync` solo actualiza el bloque generado `harness-flow:features`, y `gate.py check` reporta violaciones fuera de ese contrato.

## Contexto: grafo, hub y vault (contexto.py)

El grafo, el Memory Hub y el vault son el ahorro de tokens del flujo: si estan
frescos, un implementer o un revisor arranca con un indice en vez de leer el
repo a ciegas. Si estan viejos, mienten — y nadie los refrescaba solo.

**Una raiz de grafo no alcanza cuando el proyecto vive en varios directorios.**
El arnes esta instalado en UNA raiz (p.ej. el front), pero los microservicios
pueden vivir en otro lado del disco. Con un solo `graphify-out`, `graphify
query "ms-foo ..."` devuelve nodos de la mitad equivocada o nada: el servicio
que preguntas ni siquiera esta en ese grafo. Se declaran en
`harness/grafos.json` (nunca autodetectado: barrer el disco mete repos ajenos
en tu grafo y en el hub):

```json
{
  "max_horas": 12,
  "raices": [
    {"nombre": "front",  "path": "."},
    {"nombre": "micros", "path": "~/GolandProjects/miproyecto"}
  ],
  "combinado": "graphify-out/merged-graph.json"
}
```

Con dos o mas raices, `comun.paths()["graph"]` apunta al **combinado**
(`graphify merge-graphs`), y ese es el grafo que ven `hub.py
derivar-graphify`, `vault.py` y el brief. Sin `grafos.json`, todo funciona
como antes contra `<raiz>/graphify-out/graph.json`.

```bash
$PY "$H/contexto.py" estado              # edad por raiz + combinado + vault
$PY "$H/contexto.py" refrescar           # update por raiz vencida, merge, hub, vault
$PY "$H/contexto.py" brief --feature <id>  # indice compacto para trabajar
```

`refrescar` solo toca lo vencido (`max_horas`, 12 por defecto); `--forzar`
reconstruye todo. Nunca lanza excepcion: devuelve un parte JSON y sale con
exit≠0 si algo fallo, asi que **un refresco a medias no se reporta como
exito**.

`HARNESS_SIN_CONTEXTO=1` apaga el refresco **automatico** (los ganchos de
`start`/`close`), para CI y para los tests del propio arnes, que si no lanzarian
un `graphify update` real sobre el arbol y tardan minutos. **No** apaga
`contexto.py refrescar`: un comando explicito que devolviera un parte vacio y en
verde seria una mentira.

Cuando se refresca solo:

- `worktree.py start` — antes de que el implementer toque nada: refresca si
  esta vencido e imprime el brief de la feature. `--sin-contexto` lo salta.
- `gate.py close --status done` — DESPUES del cierre (el arbol cambio, el grafo
  y el vault describen el codigo anterior). Fuera de la transaccion de
  rollback: si el refresco falla, avisa; no desarma un cierre ya hecho.
- `estado.py` reporta la edad por raiz y avisa si el contexto vencio.

**El brief reemplaza al `graphify query` crudo en el flujo.** Una consulta cruda
devuelve decenas de nodos planos y se trunca a mitad de camino; el brief agrega
por archivo, se queda con las relaciones de acoplamiento (`imports`, `calls`,
`references`, `implements`...; descarta `contains`/`method`, que son estructura
interna) y ordena por cuanto cruza el limite del archivo. Trae ademas los AC con
su comando, las reglas activas, las rutas protegidas, las lecciones instaladas y
el impacto cross-repo del hub. `revision.py --briefing` lo incrusta al principio
del paquete del revisor, con `--max-lineas-brief` para acotarlo.

El brief es un INDICE, no evidencia: ningun AC se da por cumplido porque el
brief lo mencione. Si el contexto esta vencido, tanto el brief como el briefing
del revisor lo dicen en la primera linea en vez de fingir estar al dia.

## Memory Hub Postgres

Mismo esquema que el arnés Rust (`graph_nodes`, `graph_edges`), así que el histórico se conserva. Credenciales de `~/.harness-hub/.env` (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`, `DB_SSL_MODE` por defecto `require`).

```bash
$PY "$H/hub.py" mapa                                    # panorama multi-proyecto
$PY "$H/hub.py" descubrir [--aplicar]                   # repos git bajo la raíz
$PY "$H/hub.py" impacto --microservicio <proy>/<svc>    # quién se rompe si toco esto
$PY "$H/hub.py" vincular --consumer <a> --target <b>
$PY "$H/hub.py" derivar-graphify                        # graphify-out/graph.json -> hub
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

Una lección es una **skill del agente** por CLASE de trabajo, nunca por id de feature. Vive en tu perfil (`~/.hermes/.../skills/`, `~/.claude/skills/` o `~/.agents/skills/`), no en el repo: viaja contigo entre proyectos y el agente la carga sola cuando aplica.

```bash
$PY "$H/leccion.py" list            # ANTES de diseñar
$PY "$H/leccion.py" ver <clase>
$PY "$H/leccion.py" plantilla <clase>   # esqueleto para skill_manage
```

`donde` lista las raíces en orden de precedencia (en Claude Code, la personal
gana a la del proyecto). `HARNESS_SKILLS_DIR` fuerza una raíz única.

Escribir y patchear: en Hermes con **`skill_manage`** (valida el frontmatter); en
Claude Code escribiendo `<raíz>/<clase>/SKILL.md` con frontmatter `name` +
`description`; en GPT/Codex escribiendo `~/.agents/skills/<clase>/SKILL.md` o
`<repo>/.agents/skills/<clase>/SKILL.md`. PATCHEA la lección que estuvo en juego antes de crear otra.

El gate de cierre verifica que la skill exista de verdad: `--leccion <clase>` con una skill inexistente bloquea el `close`.

NO captures: fallas de entorno, negativas sobre herramientas, errores transitorios, narrativas de tarea única, ni fracasos disfrazados de práctica.

## Documentacion PRD/SDD

`documentacion.py sync` crea o actualiza dos archivos versionados dentro de `docs/`:

```bash
$PY "$H/documentacion.py" sync
```

- `docs/prd/PRD-master.md`: vista de producto de las features con `status=done`.
- `docs/sdd.md`: vista tecnica de diseno implementado, con microservicios, merge, evidencia, review, progreso archivado y enlaces remotos si existen.

El script solo mantiene el bloque entre `<!-- harness-flow:features:start -->` y `<!-- harness-flow:features:end -->`; cualquier contenido manual fuera de ese bloque se preserva. Esto aplica igual en Hermes y Claude Code porque no usa herramientas del agente.

## Obsidian

`docs/vault/` dentro del repo, versionado. Se regenera desde el grafo y los docs del proceso:

```bash
$PY "$H/vault.py" build                # regenera docs/vault/ + siembra .obsidian/
$PY "$H/vault.py" build --sin-config   # sin tocar la config de Obsidian
```

La primera vez siembra `docs/vault/.obsidian/` (tema oscuro, grafo coloreado por
carpeta, wikilinks cortos, Dataview habilitado, `.gitignore` del ruido de
sesión). Nunca sobrescribe un archivo existente: en cuanto Obsidian o el usuario
tocan la config, es suya. Obsidian es gratis y no pide cuenta.

`contexto.py refrescar` ya corre `vault.py build` (y lo dispara `worktree.py
start` y `gate.py close --status done`), asi que en el flujo normal no hace
falta invocarlo a mano. Un `vault: ok` de `estado.py` solo dice que la carpeta
existe: la frescura la reporta `contexto.py estado`.

Enlaza specs ↔ AC ↔ evidencia ↔ lecciones ↔ nodos de graphify con wikilinks. Ver `references/obsidian.md`.

## GPT/Codex

La instalacion personal va en `~/.agents/skills/harness-flow`; por repo, en `<repo>/.agents/skills/harness-flow`. Codex/GPT puede invocarla implicitamente por `agents/openai.yaml` y explicitamente como skill. Ver `references/openai.md`.

`leccion.py` busca lecciones GPT/Codex en `.agents/skills` del repo hacia arriba, despues `~/.agents/skills` y por ultimo `/etc/codex/skills`. Si `harness-flow` entra por symlink desde `.agents/skills` al clone de Hermes, no mezcla skills de Hermes.

## Jira / Confluence

Solo si existe `harness/atlassian.json`. Sin ese archivo el flujo se comporta igual, sin tocar nada. Si el usuario quiere integrar y no hay binding, PREGUNTALE a que proyecto Jira y space pertenece el repo: no lo adivines. Mapeo y comandos en `references/atlassian.md`.

`atlassian.py push --feature <id>` crea/actualiza la historia Jira, subtasks por
AC y una pagina Confluence con PRD/SDD si existen, spec, evidencia y review. `gate.py close ...
--publicar-atlassian` dispara ese push automaticamente despues del cierre; sin
esa bandera, `close` solo avisa y no toca sistemas remotos.

## Reglas duras

- Todo hallazgo relevante se escribe en `harness/progress/`. Una respuesta en el chat no reemplaza evidencia persistida.
- `gate.py verify` corre desde la RAÍZ del proyecto, no desde el worktree de la feature. Si el código todavía vive sólo en su worktree, los AC miden un árbol que no lo contiene y salen rojos por un motivo falso. Integra primero (o corre los comandos a mano en el worktree y dilo); un rojo de verify sobre el árbol equivocado no es un veredicto sobre el código.
- Cuando varias features tocan el mismo artefacto, ciérralas en orden de dependencia: un AC que compara contra un respaldo pre-cambio queda obsoleto en cuanto otra feature aplica el suyo.
- **Los AC de una feature miden SU worktree, así que por construcción no ven los choques ENTRE features.** Varias ramas pueden estar verdes cada una y romperse al convivir en la rama de integración: dos migraciones que toman el mismo número, una que inserta una fila donde otra fija un conteo exacto, un CHECK que choca con un vocabulario ampliado. Después de cada `close ... --to <rama>`, corre la suite de integración COMPLETA sobre la rama destino y compara los rojos contra los que ya había antes del merge. Un `15/15 en verde` de `verify` es un veredicto sobre la rama de la feature, NO sobre la integración: no lo reportes como si lo fuera.
- **Migraciones numeradas + features en paralelo = colisión garantizada.** Cada rama toma "el siguiente número libre" que ve, y ve un árbol distinto. Antes de sellar el spec de una feature con migración, reserva el número contra la rama de integración, no contra el worktree. Al renumerar: `git mv` para conservar historia, regenerar los manifiestos con el comando del repo (suelen decir "GENERADO, no editar a mano") y verificar que el blob quede idéntico entre todos los repos que lo replican.
- **Los comandos de los AC nunca citan la carpeta compartida de un repo cuando hay features en paralelo.** Con varias features vivas, `/ruta/ms-foo` está parado en la rama de quien hizo checkout último, así que el AC mide un árbol ajeno: da verde falso si el `-run` no engancha nada, o rojo falso si la rama vecina tiene otro código. Escribe los comandos contra el worktree de la feature (`<repos>-wt/<id>/ms-foo`) y créalo antes de sellar el spec. Ya produjo ambos errores en el mismo proyecto el mismo día.
- Antes de creer un rojo de `verify`, comprueba en qué rama está cada repo que el AC toca (`git -C <ruta> branch --show-current`). Un rojo sobre el árbol equivocado no es un veredicto sobre el código, y un verde tampoco.
- El cuerpo manual del PRD y la constitution son del USUARIO. No los reescribas; `documentacion.py sync` solo puede tocar su bloque generado `harness-flow:features`.
- Aislamiento: una feature sin worktree bloquea a las demás sin worktree.
- No afirmes lo que no puedes comprobar. Si un gate no corrió, dilo.
- Los AC pueden declarar su comando de dos formas, ambas válidas:
  `- AC-1: ... \`verificar: pytest -q\`` o una línea `Comando: \`pytest -q\`` debajo del AC.
- La evidencia cubre un AC si la cita `archivo:linea` está en la **sección** del AC
  (encabezado `## AC-1` con la cita debajo), no necesariamente en la misma línea.
  Prosa sin cita nunca cuenta como cobertura.
- `psycopg` debe estar en el intérprete que resuelve `entorno.py` (`$PY`), no en el
  del proyecto ni en el python del sistema. Si `hub.py` tira `ModuleNotFoundError:
  psycopg`, casi siempre es que estás usando `python3` en vez de `$PY`. Diagnostica
  y arregla con el mismo script, sin rutas a mano: `python3 "$H/entorno.py"` y luego
  `python3 "$H/entorno.py" --instalar-deps`.

## Equivalencias por host

| Necesitas | Hermes | Claude Code | GPT/Codex |
| --- | --- | --- | --- |
| Subagente revisor aislado | `delegate_task` | tool `Task`, `subagent_type: general-purpose` | `codex exec`/revisor aislado disponible |
| Crear/patchear una lección | `skill_manage` | escribir `<raíz>/<clase>/SKILL.md` | escribir `~/.agents/skills/<clase>/SKILL.md` o `<repo>/.agents/skills/<clase>/SKILL.md` |
| Raíz de skills | `~/.hermes/skills` (o perfil) | `~/.claude/skills`, luego `.claude/skills` del proyecto | `.agents/skills` del repo, luego `~/.agents/skills`, luego `/etc/codex/skills` |
| Intérprete con `psycopg` | venv de Hermes | venv neutro `~/.harness-flow/venv` | venv neutro `~/.harness-flow/venv` |

Todo lo demás (gates, worktrees, specs, hub, vault, documentacion, atlassian) es Python puro y
se comporta idéntico en los hosts soportados. Si no puedes lanzar un subagente aislado, revisa tú mismo
con `revision.py --feature <id>` y **dilo explícitamente**: el rigor baja.
