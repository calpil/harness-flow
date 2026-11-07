# harness-flow

Framework de desarrollo guiado por especificación (*spec-driven development*) con **gates ejecutables determinísticos** para proyectos monorepo y multi-repo, diseñado para agentes de inteligencia artificial: [Hermes Agent](https://hermes-agent.nousresearch.com), [Claude Code](https://code.claude.com), OpenAI GPT/Codex, Google Antigravity (AGY) / Gemini CLI, Grok y Kimi Code.

Es el puerto directo del arnés original en Rust (`harness_process`) a un entorno nativo de agentes: **sin binarios que compilar por sistema operativo, sin instaladores por proyecto y con dependencias mínimas** (Python estándar, más `psycopg` opcional para el grafo Postgres compartido).

Los scripts detectan automáticamente el host y el sistema operativo (macOS, Linux y Windows). Lo único que se adapta entre agentes son los mecanismos de lanzamiento del subagente revisor y las rutas de memoria procedural.

---

## Qué hace (Capacidades Implementadas)

### 1. Flujo Estricto en 4+1 Roles & TDD Vertical
Prohíbe el desarrollo horizontal por capas y las promesas sin verificar en el chat. Cada historia se implementa como un incremento observable de punta a punta (*Vertical Slice*):

- **Rol 0: Producto (`producto.py`)**: Redacta borradores en `docs/borrador-prd.md` y `docs/borrador-sdd.md`. Aplica el cuestionario de las **4 decisiones costosas de cambiar** (multi-tenant, roles/permisos, offline/sync, multi-idioma/moneda), descompone el backlog en 10–15 candidatas verticales `F-n` con un *walking skeleton* inicial (`F-1`), y ejecuta el ritual de aprobación explícita `--yes` que sella `docs/prd/PRD-master.md` y `docs/sdd.md` como rutas protegidas.
- **Rol 1: Leader (`gate.py approve-spec`, `templates/spec.md`)**: Toma una candidata `F-n` y redacta el spec con 2 a 3 Criterios de Aceptación (AC) en formato Given/When/Then. Declara obligatoriamente la **costura pública de prueba** (`[costura: endpoint|servicio|ui|integracion|manual]`). Si el spec debe cambiar tras haber iniciado trabajo, exige una **enmienda formal** (`gate.py enmienda`) que invalida automáticamente verificaciones y reviews previos.
- **Rol 2: Implementer (`implementer.md`, `worktree.py`)**: Trabaja aislado en un `git worktree` dedicado. Aplica TDD vertical estricto (`1 test en costura pública -> Red -> código mínimo -> Green -> Refactor`) con 5 paradas XP inmediatas ante desvíos. Ofrece dos modos:
  - *Subagente delegado (por defecto)*: ejecución autónoma con amnesia deliberada y brief compacto de contexto.
  - *Modo Pair interactivo (`--pair`)*: la IA actúa como Driver y el humano como Navigator en la sesión principal, avanzando micro-ciclo a micro-ciclo con confirmación explícita.
  - Registra citas verificables `archivo:linea` en `docs/impl-<id>.md`.
- **Rol 3: Reviewer Aislado (`revisor.md`, `revision.py`)**: Subagente independiente lanzado con el briefing autocontenido de `revision.py --briefing`. Contrasta las citas contra el código real, audita la integridad de los tests (prohíbe tests tautológicos o relajar aserciones viejas) y utiliza `codebase-memory-mcp` (`search_graph`, `trace_path`) para orientarse sin modificar código. Sella formalmente desde la sesión principal (`gate.py revision --veredicto approved|changes_requested|blocked`) con un tope de 2 rondas.
- **Rol 4: Cierre (`gate.py close`)**: En monorepos ejecuta `git merge --no-ff`. En multi-repos sin `.git` valida la integración manual (`--integrated`). Archiva el progreso en `harness/progress/archive/`, sincroniza la documentación generada en `docs/prd/` y `docs/sdd.md`, ejecuta los runners post-merge medidos y valida el registro de la lección procedural en `leccion.py`.

### 2. Verificadores Post-Merge Medidos Multi-Toolchain
Los tests de feature solo miden su propio worktree; no pueden anticipar choques de integración entre ramas paralelas. El arnés mide el **delta de rojos** contra una foto tomada antes del merge:
- **Go (`postmerge_medido.py`, `postmerge_exec.py`)**: Procesa `go test -json` instrumentado con bandera `-exec`. Detecta fallos nuevos discriminados por `(paquete, test)`, abortando ante paquetes que no compilan, `panic` en `init()` o tests eliminados (exit 2).
- **Frontend / Angular / TypeScript (`postmerge_frontend.py`)**: Ejecuta suites bajo Angular 22, Vitest 4 y `node:test` mediante reporters dedicados (`frontend_vitest_reporter.mjs`, `frontend_node_reporter.mjs`).
- **Infraestructura Terraform (`postmerge_terraform.py`)**: Valida código HCL con `terraform fmt`, `terraform validate` y `terraform test`.
- *Nota:* El script antiguo `scripts/postmerge.py` ha sido completamente retirado y neutralizado para prevenir falsos verdes por parsing de regex.

### 3. Memoria Procedural Cruzada entre Agentes (`leccion.py`)
Las lecciones aprendidas son memoria del usuario, no del agente donde se descubrieron:
- Escanea y valida lecciones en todas las raíces de agentes de la máquina: `~/.hermes/skills`, `~/.claude/skills`, `~/.gemini/config/skills`, `~/.gemini/skills`, `~/.agents/skills`, `~/.codex/skills`, `~/.grok/skills` y `~/.kimi-code/skills`.
- Espejado bidireccional (`leccion.py espejar`): traslada lecciones creadas en Claude Code hacia Hermes y deja symlinks para mantenerlas sincronizadas.
- El cierre (`gate.py close --leccion <clase>`) exige que la lección exista físicamente en alguna raíz activa.

### 4. Telemetría y Monitoreo Forense de MCP (`cbm_procesos.py`, `contexto.py`)
- Monitorea el daemon de `codebase-memory-mcp` y sus trabajadores.
- Identifica y elimina procesos huérfanos reasignados a `PID 1` y archivos temporales abandonados (`*.db.stage.*`).
- Detecta sockets cortados (`->(none)`) y recupera daemons huérfanos de socket mediante `--reiniciar-daemon`. En Windows opera con *no-op* seguro para evitar falsos positivos.
- Extrae resúmenes contextuales compactos por feature combinando el backlog, objetivos del PRD, decisiones del SDD y dependencias cruzadas.

### 5. Memory Hub Postgres & Visualización en Obsidian
- **Memory Hub (`hub.py`)**: Grafo relacional multi-repo compartido entre máquinas (`graph_nodes`, `graph_edges`) sobre PostgreSQL con `psycopg`. Responde a consultas de impacto transversal antes de diseñar specs.
- **Vault Obsidian (`vault.py`)**: Genera un cuadro de mando de notas interconectadas en `docs/vault/` para visualizar el backlog vivo, el estado de cada feature, specs y decisiones de arquitectura (con grafo estructural opt-in mediante `--con-grafo`).

### 6. Sincronización Remota con Atlassian (`atlassian.py`)
- Si existe `harness/atlassian.json`, sincroniza issues en Jira, subtasks por AC y páginas vivas en Confluence con el spec, la evidencia y el review formal al invocar `gate.py close --publicar-atlassian`.

---

## Políticas de Modelos y Reasoning Effort

El arnés gestiona el modelo y el esfuerzo cognitivo según el proveedor del agente (ver detalles en [`references/modelos.md`](references/modelos.md)):

| Host / Proveedor | Rol 0 (Producto) y Rol 1 (Leader) | Rol 2 (Implementer) | Rol 3 (Reviewer Aislado) | Rol 4 (Cierre) |
| :--- | :--- | :--- | :--- | :--- |
| **Claude 5.5** (Claude Code / Hermes) | `claude-opus-5-5` (`xhigh`) | `claude-sonnet-5-5` (`high` / `xhigh`) | `claude-opus-5-5` (`xhigh` / `high` seg.) | `claude-opus-5-5` (`xhigh`) |
| **OpenAI GPT-6** (Codex / Hermes) | `gpt-6-astra` (`medium` / `high`) | `gpt-6-astra` (`medium` / `high`) | `gpt-6-astra` (`high`) | `gpt-6-astra` (`medium`) |
| **Gemini 4 Argon** (AGY / Hermes) | `gemini-4-argon` (`high`) | `gemini-4-argon` (`high`) | `gemini-4-argon` (`high`, subagente `self`) | `gemini-4-argon` (`high`) |
| **Grok** | Modelo de sesión | Sesión (`--pair` o autónomo) | Subagente `spawn_subagent` (espera id) | Gates locales |
| **Kimi Code** | Sesión principal | Sesión (`--pair` o autónomo) | Subagente `Agent` (`subagent_type: revisor`) | Gates locales |

---

## Instalación y Configuración por Host

La skill se distribuye como un repositorio git clonado en el directorio de skills de tu agente, sin instaladores propietarios.

### 1. Hermes Agent
Clona en el perfil activo (por defecto `default`):
```bash
git clone https://github.com/calpil/harness-flow.git ~/.hermes/skills/software-development/harness-flow
```

### 2. Claude Code
Clona en las skills de Claude Code (o crea un enlace simbólico desde el clon de Hermes):
```bash
git clone https://github.com/calpil/harness-flow.git ~/.claude/skills/harness-flow
# O enlace simbólico:
ln -s ~/.hermes/skills/software-development/harness-flow ~/.claude/skills/harness-flow
```
Claude Code carga automáticamente la capa nativa declarada en `.claude-plugin/plugin.json`:
- Subagentes: `harness-flow:revisor` (Opus 5.5 con herramientas MCP habilitadas) e `harness-flow:implementer` (Sonnet 5.5).
- Comandos: `/harness-flow:estado`, `/harness-flow:producto`, `/harness-flow:spec`, `/harness-flow:implementar`, `/harness-flow:review`, `/harness-flow:cierre`.
- Permisos configurados en `.claude/settings.json` para ejecutar sin interrupciones el entorno virtual y los scripts del arnés.

### 3. Google Antigravity (AGY) y Gemini CLI
AGY descubre skills globales en `~/.gemini/config/skills/`, mientras que Gemini CLI lee `~/.agents/skills/`:
```bash
ln -s ~/.hermes/skills/software-development/harness-flow ~/.gemini/config/skills/harness-flow
# Para Gemini CLI / Codex:
ln -s ~/.hermes/skills/software-development/harness-flow ~/.agents/skills/harness-flow
```

### 4. OpenAI GPT / Codex CLI
Codex lee `~/.agents/skills/` y `$CODEX_HOME/skills` (`~/.codex/skills`):
```bash
git clone https://github.com/calpil/harness-flow.git ~/.agents/skills/harness-flow
```
Incluye metadata de invocación automática en `agents/openai.yaml`.

### 5. Grok y Kimi Code
- **Grok**: lee `~/.agents/skills` y `~/.grok/skills` (ver [`references/grok.md`](references/grok.md)).
- **Kimi Code**: instala como plugin desde el TUI con `/plugins install <ruta-del-clone>` o symlink en `~/.kimi-code/skills/` (manifiesto [`kimi.plugin.json`](kimi.plugin.json)).

### 6. Entornos Windows
En Windows, crea un junction de directorio sin requerir elevación de privilegios:
```cmd
mklink /J "%USERPROFILE%\.claude\skills\harness-flow" "%LOCALAPPDATA%\hermes\skills\software-development\harness-flow"
```
Recomendado: instalar **Git for Windows** para utilizar sintaxis Bash estándar. Si se ejecuta en PowerShell puro, los comandos soportan invocación nativa mediante `python <skill>\scripts\entorno.py --powershell | Invoke-Expression`.

### Instalación de Dependencias del Hub
El script `entorno.py` configura automáticamente el entorno virtual neutro `~/.harness-flow/venv` con `psycopg`:
```bash
python3 ~/.hermes/skills/software-development/harness-flow/scripts/entorno.py --instalar-deps
```

---

## Flujo Operativo en un Proyecto

### 1. Inicialización de Entorno en la Sesión
Define las variables `$H` (directorio de scripts) y `$PY` (intérprete virtual) en tu terminal:
```bash
# bash / zsh (macOS / Linux)
eval "$(python3 <ruta-skill>/scripts/entorno.py --shell)"

# PowerShell (Windows)
python <ruta-skill>\scripts\entorno.py --powershell | Invoke-Expression
```
*(En Claude Code, AGY, Codex y Grok, ejecuta el comando y el script en la misma llamada de herramienta bash/terminal).*

### 2. Arranque de Sesión
Antes de realizar cualquier acción sustantiva, consulta el panorama del proyecto:
```bash
$PY "$H/estado.py"
```

### 3. Ciclo de Vida de una Feature (Monorepo)
```bash
# 1. Crear feature vinculada a candidata F-n del PRD
$PY "$H/add.py" --name "Checkout con cupon" --prd docs/prd/PRD-master.md --candidata F-3

# 2. Iniciar worktree aislado
$PY "$H/worktree.py" start --feature 1

# 3. Redactar spec y aprobar con ritual explícito del usuario
$PY "$H/gate.py" approve-spec --feature 1 --yes

# 4. Implementar bajo TDD vertical (modo delegado o modo pair)
# En Claude Code: /harness-flow:implementar 1 --pair

# 5. Generar briefing de revisión y lanzar revisor aislado
$PY "$H/revision.py" --feature 1 --briefing
# Tras revisar el informe en docs/review-1.md, sellar veredicto:
$PY "$H/gate.py" revision --feature 1 --veredicto approved

# 6. Cierre con merge, postmerge medido y registro de lección
$PY "$H/gate.py" close --feature 1 --status done --to main --leccion checkout
```

### 4. Ciclo de Vida en Raíz Multi-Repo (sin `.git` en la raíz)
Para proyectos multi-servicio donde cada componente es un repositorio independiente:
```bash
# Registrar repositorios y worktrees involucrados
$PY "$H/worktree.py" register --feature 1 --manifest /ruta/registro.json

# Verificar criterios de aceptación y generar briefing de revisión
$PY "$H/gate.py" verify --feature 1
$PY "$H/revision.py" --feature 1 --briefing

# Sellar revisión y cerrar validando ancestría y postmerge en todos los destinos
$PY "$H/gate.py" revision --feature 1 --veredicto approved
$PY "$H/gate.py" close --feature 1 --status done --to develop \
  --integrated --postmerge /ruta/bases-postmerge.json --leccion checkout
```

---

## Estructura del Repositorio

```text
harness-flow/
├── SKILL.md                          <- Instrucciones maestras leídas por los agentes
├── README.md                         <- Documentación general de arquitectura y uso
├── .claude-plugin/plugin.json        <- Manifiesto del plugin skills-dir para Claude Code
├── .claude/settings.json             <- Permisos pre-autorizados para Claude Code
├── kimi.plugin.json                  <- Manifiesto de plugin para Kimi Code
├── agents/
│   ├── openai.yaml                   <- Metadata de invocación automática en GPT/Codex
│   ├── revisor.md                    <- Subagente revisor aislado (Opus 5.5, MCP activado)
│   └── implementer.md                <- Subagente implementador (Sonnet 5.5)
├── commands/                         <- Comandos slash para Claude Code (/harness-flow:*)
│   ├── estado.md, producto.md, spec.md, implementar.md, review.md, cierre.md
├── scripts/
│   ├── entorno.py                    <- Detección multi-host, resolución de $PY y $H
│   ├── estado.py                     <- Diagnóstico global de sesión, backlog y documentos
│   ├── gate.py                       <- Orquestador determinístico de gates (exit ≠ 0)
│   ├── comun.py, bloques.py          <- Parsing de ACs, firmas, hashes y manipulación segura
│   ├── init.py, add.py               <- Inicialización de proyecto y alta de features
│   ├── producto.py                   <- Rol 0: borradores y aprobación de PRD/SDD
│   ├── documentacion.py              <- Sincronización de bloques generados en PRD/SDD
│   ├── worktree.py, multirepo.py     <- Aislamiento de ramas y verificación multi-repo
│   ├── revision.py                   <- Generación del paquete de briefing para el revisor
│   ├── postmerge_medido.py           <- Runner post-merge medido para Go (JSON/-exec)
│   ├── postmerge_exec.py             <- Instrumentación de ejecución Go
│   ├── postmerge_frontend.py         <- Runner post-merge para Angular/Vitest/Node
│   ├── frontend_vitest_reporter.mjs  <- Reporter de integración Vitest
│   ├── frontend_node_reporter.mjs    <- Reporter de integración node:test
│   ├── postmerge_terraform.py        <- Runner post-merge para HCL/Terraform
│   ├── medicion_destino.py           <- Orquestador de mediciones pre y post merge
│   ├── cierre_local.py, retiros.py   <- Lógica de integración local y control de deprecaciones
│   ├── postmerge.py                  <- Stub neutralizado (aborto con exit 2 hacia runner medido)
│   ├── cbm_procesos.py               <- Telemetría forense y gestión de procesos CBM
│   ├── contexto.py                   <- Cálculo de frescura del grafo y generación de briefs
│   ├── leccion.py                    <- Memoria procedural cruzada entre agentes de la máquina
│   ├── hub.py                        <- Integración con Memory Hub Postgres
│   ├── vault.py                      <- Generación del vault de Obsidian en docs/vault/
│   └── atlassian.py                  <- Sincronización con Jira y Confluence
├── templates/                        <- Plantillas oficiales de spec, prd, sdd y enmiendas
├── docs/
│   └── explicacion-y-diagnostico.md  <- Informe de auditoría exhaustiva y estado de salud
├── references/                       <- Documentación especializada por host y subsistema
│   ├── hosts.md, modelos.md, vertical-slice.md, contexto.md, lecciones-del-arnes.md
│   ├── multirepo.md, claude.md, openai.md, grok.md, kimi.md, entorno.md
│   ├── hub.md, obsidian.md, atlassian.md, documentacion.md
└── tests/                            <- Suite exhaustiva de tests unitarios y de regresión
```

---

## Verificación y Calidad

El arnés se valida de forma continua mediante suites de tests unitarios en Python que cubren:
- Determinismo de gates y firmas criptográficas (`test_gates.py`, `test_firmas.py`).
- Flujo de documentos y control de rutas protegidas (`test_prd_sdd_flujo.py`).
- Runners post-merge medidos (`test_measured_runner_go.py`, `test_terraform_runner.py`, `test_postmerge.py`).
- Detección de host y compatibilidad multi-host (`test_entorno.py`, `test_leccion_multihost.py`, `test_plugin_claude.py`).
- Monitor forense de procesos (`test_cbm_procesos.py`).

Para ejecutar las pruebas del arnés:
```bash
/Users/alan/.harness-flow/venv/bin/python -m unittest discover -s tests -p "test_*.py"
```

---

## Licencia

MIT
