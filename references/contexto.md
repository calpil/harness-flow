# Contexto: grafo, hub y vault

Detalle de `contexto.py`. El resumen y los comandos del dia a dia estan en
`SKILL.md`; aqui esta lo que se consulta cuando algo no cuadra.

El grafo y el Memory Hub son el ahorro de tokens del flujo: si estan frescos,
un implementer o un revisor arranca con un indice (el brief) en vez de leer el
repo a ciegas. Si estan viejos, mienten — y nadie los refrescaba solo. El vault
no entra en esa cuenta: es el panel de Obsidian para el humano y ningun rol lo
lee; se refresca para que no muestre estados viejos.

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
reconstruye todo. Sin graphify en el PATH reporta el fallo y salta grafo y hub,
pero regenera igual el vault: no depende del grafo. Nunca lanza excepcion:
devuelve un parte JSON y sale con exit≠0 si algo fallo, asi que **un refresco a
medias no se reporta como exito**.

`HARNESS_SIN_CONTEXTO=1` apaga el refresco **automatico** (los ganchos de
`start`/`close`), para CI y para los tests del propio arnes, que si no lanzarian
un `graphify update` real sobre el arbol y tardan minutos. **No** apaga
`contexto.py refrescar`: un comando explicito que devolviera un parte vacio y en
verde seria una mentira.

Cuando se refresca solo:

- `worktree.py start` — antes de que el implementer toque nada: refresca si
  esta vencido e imprime el brief de la feature. Si solo el vault esta viejo
  (backlog, spec, evidencia o review mas nuevos que su `Indice.md`), regenera
  solo el vault, sin relanzar graphify ni el hub. `--sin-contexto` lo salta.
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

**Documentos relacionados.** Al final, hasta 8 rutas de `docs/` (el vault de
Obsidian), sin contenido, para que el leader sepa que abrir antes de disenar:

| Tipo | Que es | Como se encuentra |
|---|---|---|
| `tuya` | nota tuya en `docs/vault/notas/` | enlaza `[[Feature-<id>]]` o nombra un servicio de la feature |
| `feature` | archivo o carpeta con el id en el nombre | `decisiones-137.md`, `review-144-pre-integral.md`, `artefactos-159/` |
| `decision` | `decision*`, `enmienda*`, `acta*`, `adr*`, `errata*` | su texto nombra `#<id>` o un servicio de la feature |
| `previa` | review (o spec) de una feature cerrada del mismo servicio | backlog, la mas reciente primero |

Buscar en `docs/` por nombre de servicio a secas no sirve: en un proyecto real
`ms-tenant-service` aparece en 539 archivos (~2,7M tokens). Por eso se recorren
nombres de archivo y solo se lee el texto de decisiones y notas; las notas
generadas del vault no entran (salen del mismo backlog que el brief). Cupo por
tipo en ese orden de prioridad; lo que no entra se cuenta en `(+N mas sin
listar)`. `--max-relacionados 0` quita la seccion, y el briefing del revisor la
quita siempre: el revisor juzga spec contra codigo, no la historia.

El brief es un INDICE, no evidencia: ningun AC se da por cumplido porque el
brief lo mencione. Si el contexto esta vencido, tanto el brief como el briefing
del revisor lo dicen en la primera linea en vez de fingir estar al dia.



## codebase-memory-mcp (consulta estructural, complementa a graphify)

[DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp):
servidor MCP local que indexa el codigo en un grafo persistente (funciones,
llamadas, rutas HTTP). Graphify sigue siendo la fuente del brief, el hub y el
vault; cbm se suma para **consultar** y se **reindexa** tras implementar.

**Instalacion** (una vez por maquina; configura solo los clientes detectados:
Claude Code, Codex, Hermes, Grok, Kimi, etc.):

```bash
curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash
```

Reinicia el agente despues. Hermes lo registra en `mcp_servers` de
`~/.hermes/config.yaml`. Sin binario en el PATH el arnes lo omite y lo dice.

**Consultar** (antes de leer archivos a ciegas): `list_projects` /
`index_status`, `search_graph(name_pattern=...)`, `trace_path(function_name=...,
direction=inbound|outbound|both)`, `get_code_snippet`, `detect_changes`. Un
agente sin MCP (subagente aislado) puede usar la CLI:
`codebase-memory-mcp cli --quiet search_graph '{"project":"<p>","name_pattern":".*Foo.*"}'`.
El resultado es un indice, no evidencia: un AC no se da por cumplido por un nodo.

**Reindexar**: `contexto.py cbm` (o `refrescar`, o el `close --status done`)
llama `index_repository` por cada raiz de `harness/grafos.json` (o la raiz del
arnes). La primera vez sobre una raiz indexa el proyecto entero; despues es
incremental, que cubre la feature recien integrada. Exige `"status":"indexed"`,
no solo exit 0. Nunca bloquea el cierre; si falla, queda en el parte.
`HARNESS_SIN_CBM=1` lo apaga (CI y tests del arnes).

**El daemon es compartido y a veces no atiende.** Un solo daemon sirve a todas las
sesiones y agentes de la maquina (Claude, Hermes, Codex, Grok, Kimi...) y su
watcher reindexa por su cuenta cada cambio de git; con varias sesiones abiertas
puede tardar mas de 30 s en aceptar un cliente (`could not accept this client`,
`connection capacity reached`, `blocked by another mutation`). Eso es
transitorio, y el arnes lo trata asi en vez de dejarlo como un fallo que cada
agente resuelve a su manera:

| Situacion de una raiz | Que hace el arnes | Parte (`cbm.*`) |
|---|---|---|
| HEAD igual al ultimo indexado y arbol limpio | no llama al daemon | `al_dia` |
| indexa | sella HEAD (solo si el arbol estaba limpio) | `indexadas` |
| daemon ocupado/arrancando/parandose | 3 intentos con espera 5 s, 15 s; si sigue, **PENDIENTE** | `pendientes` (no es fallo) |
| ya fallo una raiz por esto | las demas quedan pendientes sin llamarlo (5 raices no pagan 5 esperas) | `pendientes` |
| daemon **vivo pero sin socket** | pendiente al instante, sin llamarlo ni esperar; **no se arregla solo** | `pendientes` (`causa: daemon_sin_socket`) |
| build distinto, ruta no indexable, binario ausente | un solo intento, fallo visible | `fallos` |
| error que no reconoce | un solo intento, fallo visible (no se difiere lo que no se entiende) | `fallos` |

Un pendiente queda en `graphify-out/.cbm_estado.json` (local, ignorado por git), se
muestra en `estado.py`, `contexto.py estado` y el brief, y **se reintenta solo** en el
siguiente `worktree start` o cierre, una vez y con 10 min de enfriamiento. No
cambia `fresco`/`vencidas` ni el exit code del cierre: el brief y el vault no
dependen de cbm. `contexto.py cbm` (comando explicito) si sale con 1 mientras haya
pendientes, y `--forzar` reindexa aunque HEAD no haya cambiado.

**Un agente que ve "cbm pendiente" no hace nada.** No reintenta en bucle y, sobre
todo, **no mata el daemon ni sus procesos a mano**. La unica excepcion es el aviso de
"daemon vivo sin socket" (siguiente seccion): ahi el agente avisa a la persona usuaria y
solo con su aprobacion corre `limpiar-cbm --reiniciar-daemon`. Lo que se verifico: `daemon stop`
ordenado se NIEGA mientras haya sesiones MCP conectadas ("NOT stopped -- N committed
client(s) still use it"), asi que no es el riesgo; el riesgo es matar el proceso
(`kill`, `pkill`): el daemon es de todas las sesiones, eso cancela el indexado en
curso y deja a cada sesion con su servidor MCP vivo pero sin daemon, que se cierra en
su siguiente consulta (la sesion se queda sin cbm hasta reconectar). En el log del
daemon aparece como `stop_requested` + un `connection_end` por sesion. Si hace falta
mirar, es solo lectura: `codebase-memory-mcp daemon status` y `contexto.py estado`.

**Procesos cbm sobrantes: `contexto.py limpiar-cbm [--solo-avisar]`.** Lista cada
proceso cbm como `EN USO` o `HUERFANO` y mata solo los huerfanos. Huerfano es lo
unico que se prueba: su padre murio y el sistema lo reasigno al init. Un servidor
MCP cuya sesion sigue viva es `EN USO` aunque este inactivo o tenga el enlace con el
daemon roto: no hay forma de saber si esa sesion lo va a necesitar, y matarlo la deja
con cbm caido. El daemon tampoco se toca nunca, salvo el caso probado de abajo. Seguridad: nunca mata a este mismo
comando ni a sus ancestros, vuelve a leer el comando justo antes del `kill` (si el
pid ya es otro programa, no lo toca) y usa SIGTERM antes de SIGKILL. Tambien borra los
`*.db.stage.*` del cache (~100 MB cada uno) con mas de 1 h, pero solo si no hay
daemon, worker ni cli de cbm vivos. No esta soportado en Windows (usa `ps`).

**Sesiones con cbm cortado.** `limpiar-cbm` marca ademas `| enlace al daemon CORTADO`
en las sesiones EN USO cuyo servidor MCP perdio su socket hacia el daemon (en `lsof` el
descriptor de datos, fd >= 3, dice `->(none)`; uno sano apunta a un peer). Se comprobo
tumbando a la fuerza un daemon de prueba aislado: el servidor sigue vivo y falla en su
siguiente consulta. **No se arregla desde fuera**: esa sesion tiene que reconectar el
MCP (en Claude Code, `/mcp`) o reiniciarse; matar su servidor solo adelanta el fallo.
Verificado en macOS; donde `lsof` no muestre `(none)` no detecta nada y no avisa de mas.

**Daemon vivo pero sin socket (visto el 2026-10-29).** Es la causa de un
"30 s sin aceptar cliente" que **no mejora esperando**. El proceso del daemon sigue
vivo y sostiene el lock, pero sus archivos `.sock`, `.anc` y `.sock.identity` ya no
existen en el directorio de coordinacion (`/private/tmp/cbm-daemon-<uid>/`; uno sano
los tiene). Sintomas, todos a la vez: `daemon status` dice `not running` (el hook de
augmentation avisa "no CBM daemon is running"), todo cliente nuevo falla tras 30 s con
`CBM daemon is active or starting but could not accept this client within 30000 ms`
(el mismo texto que un daemon ocupado) y el servidor MCP de una sesion nueva da
`CONNECT_TIMEOUT`. No se recupera solo: `daemon stop` no lo alcanza y ningun otro
daemon puede arrancar porque el lock es suyo; las sesiones que ya estaban conectadas
conservan su enlace abierto, las nuevas no pueden conectar. El arnes lo detecta antes de llamar al daemon (el
proceso tiene sockets unix abiertos y NINGUNA de sus rutas existe; sin datos de `lsof`
no acusa), deja la raiz pendiente en 0,1 s en vez de gastar 3 intentos de 30 s, y dice
el remedio. Se reevalua en cada refresco (es una lectura de `lsof`, no hay que enfriar).

`contexto.py limpiar-cbm --reiniciar-daemon [--solo-avisar]` es lo unico que toca el
daemon: **solo si esta probado sin socket** (lo confirma dos veces con 1 s de pausa; un
daemon que conserva su socket se rechaza y se remite a `daemon stop`). Antes de matar
lista las sesiones conectadas que perderan cbm hasta `/mcp` (las ya cortadas no), termina
al daemon y a sus workers (SIGTERM, luego SIGKILL; nunca sesiones) y comprueba que un
cliente nuevo conecta (`cli list_projects`). No usa `daemon start`: deja un daemon
**permanente**; el primer cliente levanta uno efimero. `--solo-avisar` solo muestra a
quien afectaria. Cuando reiniciar lo decide la persona usuaria, no el agente.

Que lo causa **no esta establecido**. Descartado: que un cliente que da timeout contra
un daemon ocupado borre los sockets (se congelo un daemon de prueba aislado con SIGSTOP,
un cliente espero 30 s y fallo con otro mensaje -- `endpoint is held by pid N ... likely
dead` --, y al reanudarlo el daemon respondio y conservaba sus archivos), y el limpiador
de `/tmp` de macOS (sockets mas viejos de `/tmp` sobreviven). Si reaparece, el
`Al fallar:` del pendiente y `diagnosticos` en `.cbm_estado.json` guardan el momento.

**Cuando el daemon no atiende, el arnes deja evidencia.** Un "30 s sin aceptar
cliente" tiene mas de una causa (ocupado, o vivo sin socket) y el texto del cliente es
el mismo; los disparadores de la saturacion no se pudieron reproducir (ni con un cierre
real de 5 raices ni con sondas concurrentes). Al quedar una raiz pendiente se guarda una
foto barata, sin tocar el daemon: carga, swap, procesos cbm por rol, sesiones cortadas,
pids de daemons sin socket y cuantos reindexados del watcher hay en la cola del log. Sale en `estado`/el cierre
como `Al fallar: ...` y las ultimas 20 quedan en `diagnosticos` de
`graphify-out/.cbm_estado.json`. Si el aviso reaparece, esos datos dicen si fue carga,
memoria, churn del watcher o sesiones cortadas, en vez de adivinar.

**`node_modules` no se indexa, ni en cbm ni en graphify.** Las dos herramientas lo
excluyen por diseno, a cualquier profundidad y con o sin `.gitignore`. Comprobado en
cbm 0.11.0 y graphify 0.9.73 con un repo de prueba con `node_modules` suelto y anidado
(`packages/web/node_modules`) y sin `.gitignore`; y en los 8 proyectos que cbm tenia
indexados (dos fronts incluidos) hay 0 nodos dentro de `node_modules`. cbm ni siquiera
deja re-incluirlo con `!node_modules/` en `.cbmignore`, y un `.graphifyignore` solo puede
excluir mas. Aun asi el arnes lo vigila, para que una version nueva que lo rompa no pase
en silencio y sin llamadas extra al daemon:

- graphify: `refrescar` da por fallido el update (y no sella la raiz) si `graph.json` trae
  nodos cuyo archivo cuelga de un `node_modules`.
- cbm: si la raiz tiene un `node_modules` (en sus 4 primeros niveles) y el `excluded` del
  propio resultado del indexado no lo lista, va a `fallos` con el remedio (`.cbmignore`).
  Con `excluded.dirs` truncada, o sin ese dato, no afirma nada: la ausencia no es prueba.

Otros directorios de dependencias o artefactos que un front puede tener **no** estan
cubiertos por igual. En un repo SIN `.gitignore` se colaron: en ambas herramientas
`.pnpm`, `jspm_packages`, `.nx`, `.vite`, `out`, `www`, `public`, `.output`, `.firebase`,
`playwright-report`, `test-results`; solo en graphify `bower_components`, `.pnpm-store`,
`.yarn/cache`, `.yarn/releases`, `vendor`, `coverage`, `tmp`, `deploy`, `.vercel`,
`.netlify`; solo en cbm `build` y `storybook-static`. Ambas respetan `.gitignore` (graphify
tiene `--no-gitignore`), que en un front normal ya los cubre. Si alguno estorba, se excluye
por proyecto con `.cbmignore` / `.graphifyignore` (sintaxis gitignore); el arnes no
modifica repos ajenos por su cuenta.

Variables: `HARNESS_CBM_INTENTOS` (3), `HARNESS_CBM_ESPERA_S` (5, base del
backoff), `HARNESS_CBM_ENFRIAMIENTO_S` (600).

**Solo ramas estables, nunca worktrees.** Se indexa una raiz solo si esta parada
en `develop`, `main`, `master` o `release`/`release/*`/`release-*`. Un worktree de
feature se omite siempre, aunque su rama se llame `develop`: es trabajo en curso,
y indexarlo meteria codigo sin integrar bajo un proyecto que nadie limpia. Se
decide con git (`--git-common-dir` vs `--absolute-git-dir`), no por el nombre de
la carpeta. HEAD desacoplado o una carpeta sin git tambien se omiten. Lo omitido
queda en `cbm.ramas_omitidas` del parte con su motivo. Para cambiar la lista:
`"ramas_indexables": ["develop", "main"]` en `harness/grafos.json` (acepta globs).
Consecuencia: lo que cierra una feature se ve en cbm cuando el cierre integra y
la raiz queda en la rama estable; hasta entonces el indice no tiene su trabajo.
