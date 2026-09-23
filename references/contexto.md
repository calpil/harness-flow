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

