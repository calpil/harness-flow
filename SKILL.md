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
   - Claude Code: la tool `Agent` con `subagent_type: harness-flow:revisor`, pegando la salida en el prompt.
     Ese subagente viene en la propia skill (`agents/revisor.md`); sin el, `general-purpose` sirve igual.
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
| `postmerge_medido.py base --repo <r> --guardar <j>` | Foto medida de los rojos ANTES del merge |
| `postmerge_medido.py check --repo <r> --base <j>` | Rojos NUEVOS, build roto o tests desaparecidos (exit 2) |

**Despues de cada `close ... --to <rama>`, corre `postmerge_medido.py`** sobre la
rama destino. Los AC de una feature miden su worktree y no pueden ver los choques
entre features. El gate compara `(paquete, test)` contra la base pre-merge y solo
falla por rojos NUEVOS, asi que la deuda tolerada no lo vuelve inservible:

```bash
$PY "$H/postmerge_medido.py" base  --repo <ruta> --guardar /tmp/base-<svc>.json   # ANTES
$PY "$H/gate.py" close --feature <id> --status done --to develop --leccion <clase>
$PY "$H/postmerge_medido.py" check --repo <ruta> --base /tmp/base-<svc>.json      # DESPUES
```

`postmerge.py` (el gate viejo de regex) **no sirve como gate**: deduce el veredicto
de `--- FAIL:` sobre la salida `-v` y nunca lee el exit code de `go test`, asi que
da VERDE con un paquete que no compila, con un `panic` en `init()`, y con tests
borrados; ademas identifica los tests por nombre sin paquete, con lo que un rojo
nuevo en un paquete se confunde con deuda tolerada de otro. Usa siempre la version
medida, que cubre los cuatro casos y valida la base contra repo/rama/comando/SHA.

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

`docs/vault/` dentro del repo, versionado. Se regenera desde los documentos del
proceso (features, specs, AC, evidencia, reviews, lecciones, servicios). Los
nodos del grafo NO entran por defecto: son opt-in con `--con-grafo`.

```bash
$PY "$H/vault.py" build                # regenera docs/vault/ + siembra .obsidian/
$PY "$H/vault.py" build --con-grafo    # ademas, una nota por nodo del grafo
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

Enlaza specs ↔ AC ↔ evidencia ↔ lecciones ↔ servicios con wikilinks.

**Los nodos de graphify solo aparecen con `--con-grafo`**, que ni el comando de
arriba ni el refresco automatico pasan: `contexto.py refrescar` corre `vault.py
build` pelado. Es deliberado, porque `--con-grafo` escribe una nota por nodo
(tope 2000) y eso en cada refresco ahoga el vault. Si esperas navegar del spec
al nodo de codigo y `docs/vault/grafo/` no existe, no es un fallo: es que nadie
paso la bandera. Corre `vault.py build --con-grafo` a mano cuando quieras ese
mapa. Ver `references/obsidian.md`.

## Claude Code

La instalacion personal va en `~/.claude/skills/harness-flow`; por repo, en
`<repo>/.claude/skills/harness-flow`. Sirve un symlink al clone de Hermes: Claude
Code lee `SKILL.md` a traves del enlace y `entorno.py` sigue detectando host
`claude` porque no resuelve el symlink.

El directorio trae `.claude-plugin/plugin.json`, asi que ademas carga como plugin
skills-dir y aporta piezas nativas que los otros hosts ignoran:

- subagente `harness-flow:revisor` (`agents/revisor.md`) para el paso 3 del flujo;
- comandos `/harness-flow:estado`, `:spec`, `:review`, `:cierre`.

**`$PY` y `$H` no sobreviven entre llamadas Bash**: cada llamada abre un shell
nuevo. Pega el `eval` al comando en la misma llamada, siempre.

**En Windows, instala Git for Windows.** Sin el, Claude Code no usa Bash y cae a
PowerShell: `eval "$(...)"` no existe ahi y el interprete se llama `python`, no
`python3`. Usa entonces `entorno.py --powershell | Invoke-Expression` y `& $PY`.
Para compartir un solo clone con Hermes no sirve `ln -s`: es `mklink /J`
(junction, sin permisos de administrador).

Detalles, rutas de Windows, verificacion de la instalacion y raices de lecciones
en [`references/claude.md`](references/claude.md).

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
- `gate.py verify` corre en el WORKTREE de la feature cuando existe (antes corría
  desde la raíz y medía la rama de integración: verde falso si el comando no
  engancha nada, rojo falso si develop tiene otro código). Si el worktree
  declarado no existe, `verify` **bloquea** en vez de caer a la raíz. Sin
  worktree, avisa que está midiendo la raíz. Un rojo sobre el árbol equivocado
  no es un veredicto sobre el código, y un verde tampoco.
- **La feature sale de `rules.rama_base` (por defecto `develop`), no del HEAD del
  repo.** `worktree.py start` resuelve la base explícitamente y crea la rama
  desde ese SHA; si la rama ya existía y no desciende de la base, aborta. La
  base queda registrada en `base_branch`/`base_sha` y es contra ella que
  `revision.py` calcula el diff (`merge-base base HEAD`, no `HEAD~1`: una
  feature son N commits, y `HEAD~1` le muestra al revisor sólo el último).
  `--base <rama>` para un caso puntual.
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
  Prosa sin cita nunca cuenta como cobertura. Una **mención** del AC en medio de
  una frase (`...que también cubre lo pedido en AC-1`) no abre sección: sólo
  cuentan las líneas que lo **declaran** (`## AC-1`, `- AC-1:`, `| AC-1 |`). Antes
  una mención heredaba la cita del AC vecino y daba por cubierto un AC sin
  evidencia, además de truncar la sección del AC que sí la tenía.
- `verify` sólo mide los AC que declaran comando. Si el spec tiene 12 AC y 3
  traen `verificar:`, un `3/3 en verde` **no** dice nada de los otros 9: el
  script ahora los lista como `NO se midieron` y `close` los repite como aviso.
  Ese hueco lo cubre la revisión, no el verify.
- El sello `Revisado:` sólo vale con la firma completa que estampa
  `gate.py revision` (veredicto · fecha ISO · autor · `estampado por gate.py
  revision`). Un `Revisado: approved - ok` escrito a mano ya no pasa.
- `close` rechaza un `last_verify` medido contra una firma de spec distinta de
  la vigente: si el spec cambió después de medir, hay que re-correr `verify`.
- `psycopg` debe estar en el intérprete que resuelve `entorno.py` (`$PY`), no en el
  del proyecto ni en el python del sistema. Si `hub.py` tira `ModuleNotFoundError:
  psycopg`, casi siempre es que estás usando `python3` en vez de `$PY`. Diagnostica
  y arregla con el mismo script, sin rutas a mano: `python3 "$H/entorno.py"` y luego
  `python3 "$H/entorno.py" --instalar-deps`.

## Lecciones del arnés sobre sí mismo

Salieron de auditar sus propios gates; todas tienen repro verificada.

- **Un gate que deduce el veredicto de un regex sobre texto no es un gate.** El
  `postmerge.py` viejo parseaba `--- FAIL:` de la salida `-v` y nunca leía el
  exit code: daba verde con build roto, con `panic` en `init()` y con tests
  borrados. Si un runner puede fallar sin imprimir la línea que buscás, medí el
  exit code y el inventario, no el texto.
- **Cuando existan dos versiones de un gate, la doc tiene que mandar a la buena.**
  Este SKILL.md documentaba el roto mientras `medicion_destino.py` usaba el
  medido: quien seguía la doc al pie de la letra usaba el que miente.
- **Un identificador de test sin su paquete colapsa tests distintos.** Identificá
  por `(paquete, test)`, o un rojo nuevo se confunde con deuda tolerada de otro.
- **Contar sólo los rojos nuevos deja pasar los tests que desaparecen.** Sin
  inventario de lo medido antes, borrar un test es indistinguible de arreglarlo.
- **Un conteo parcial nunca se reporta como total.** `verify` medía sólo los AC
  con comando y anunciaba `1/1 en verde` con 3 AC en el spec. Si mediste 3 de 12,
  decilo en la misma línea del verde.
- **Una medición vale para la firma con la que se tomó.** Si el spec cambia
  después del `verify`, el verde viejo habla de otro documento: re-medir.
- **Un sello contra falsificación debe exigir la firma entera.** Un
  `Revisado: approved - ok` tipeado a mano pasaba como sellado por el gate.
- **Una mención no es una declaración.** Al parsear documentos por secciones, una
  frase que nombra `AC-1` de pasada abría sección y heredaba la cita del AC
  vecino: daba por cubierto un AC sin evidencia y truncaba el que sí la tenía.
- **`exists()` no es `is_file()`**, y un glob de un solo nivel no ve las skills
  anidadas (`mlops/inference/llama-cpp`): el gate de lección bloqueaba cierres
  legítimos y aceptaba un directorio llamado `SKILL.md`.
- **Un valor del backlog que termina en una ruta necesita `slugify` + chequeo de
  contención.** Una lección `../../../README` pisaba archivos del repo.
- **En un cliente HTTP, el fallo de red debe tratarse como fallo en TODAS las
  ramas.** `code == 0` faltaba sólo en la creación de issue: persistía
  `jira_key: null` y el reintento duplicaba la issue en Jira.

## Cómo auditar este arnés

Los tests de regresión sólo valen si fallan contra el código previo: escribilos,
`git stash push` los scripts arreglados, correlos y confirmá que se ponen rojos.
Un test nuevo que pasa en ambos lados no está probando el arreglo.

La suite es **unittest**, no pytest, y hay que correrla desde `tests/`:
`cd tests && python3 -m unittest <módulo>`. Un `unittest discover` desde la raíz
cuelga y falla por path de import. Las suites multi-repo y de runner medido
tardan varios minutos: correlas en segundo plano.

Al auditar, sospechá de los tests existentes tanto como del código: cinco tests
de `test_postmerge.py` certificaban en verde el gate que mentía.

## Equivalencias por host

| Necesitas | Hermes | Claude Code | GPT/Codex |
| --- | --- | --- | --- |
| Subagente revisor aislado | `delegate_task` | tool `Agent`, `subagent_type: harness-flow:revisor` | `codex exec` en sesion nueva |
| Crear/patchear una lección | `skill_manage` | escribir `<raíz>/<clase>/SKILL.md` | escribir `~/.agents/skills/<clase>/SKILL.md` o `<repo>/.agents/skills/<clase>/SKILL.md` |
| Raíz de skills | `~/.hermes/skills` (o perfil) | `~/.claude/skills`, luego `.claude/skills` del proyecto | `.agents/skills` del repo, luego `~/.agents/skills`, luego `/etc/codex/skills` |
| Intérprete con `psycopg` | venv de Hermes | venv neutro `~/.harness-flow/venv` | venv neutro `~/.harness-flow/venv` |
| Atajos del flujo | — | `/harness-flow:estado\|spec\|review\|cierre` | — |

Todo lo demás (gates, worktrees, specs, hub, vault, documentacion, atlassian) es Python puro y
se comporta idéntico en los hosts soportados. Si no puedes lanzar un subagente aislado, revisa tú mismo
con `revision.py --feature <id>` y **dilo explícitamente**: el rigor baja.

### Otros CLIs que leen SKILL.md

No tienen host propio en `entorno.py` (se reportan como `gpt` si la skill está
bajo `.agents/skills`, o `generic`). Los gates funcionan igual; lo que cambia es
cómo lanzas el revisor. **No uses `codex exec` fuera de Codex.**

| CLI | Raíz de skills que lee | Subagente revisor |
| --- | --- | --- |
| Codex | `$CODEX_HOME/skills` (`~/.codex/skills`), `.agents/skills` | `codex exec` con el briefing en el prompt |
| Gemini CLI | `~/.agents/skills` (`gemini skills list` lo confirma) | subagente propio del CLI |
| Grok | `.grok/`, `.claude/`, `.cursor/`, `.agents/skills` | `--agent <archivo>` / `--agents <json>` |
| Kimi Code | `$KIMI_CODE_HOME/skills` (`~/.kimi-code/skills`), `~/.agents/skills` | tool `Agent` (`subagent_type`), o `kimi -p` en sesión nueva |

`~/.agents/skills` es el mínimo común múltiplo: los cuatro lo leen. Instala ahí
si usas más de un CLI. Para las lecciones, `leccion.py` **busca** en todas esas
raíces (incluidas `.codex`, `.grok` y `.kimi-code`) y **crea** en la del host
detectado; `leccion.py donde` marca cuál es cuál.
