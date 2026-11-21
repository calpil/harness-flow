# Obsidian en el harness-flow

## Qué es el vault aquí

El vault es **`docs/`**, versionado con el proyecto; las notas generadas viven en
`docs/vault/`. Son archivos `.md` con wikilinks; Obsidian solo los lee. No hay
servidor ni base de datos: Obsidian NO se conecta a Postgres.

Las notas generadas en `docs/vault/` (features, servicios, lecciones, índice) son
un panel visual para ti, no una entrada de evidencia: ningún rol confía en ellas
en vez del código o del backlog. En cambio, **tus notas manuales en
`docs/vault/notas/`** (cuando enlazan `[[Feature-<id>]]` o nombran un servicio) y
los documentos de decisión en `docs/` (`decision*`, `adr*`, `enmienda*`, `acta*`,
`errata*`) **sí los rescata `contexto.py brief`** en su sección `documentos
relacionados` para que Leader e Implementer los abran antes de diseñar.

**Sincronización automática:** además de `worktree.py start` y `gate.py close`,
los gates rápidos (`add.py`, `gate.py approve-spec`, `sellar-tests`, `enmienda`,
`revision`, `verify`, `producto.py aprobar` y `hallazgo.py`) regeneran el vault
en silencio cuando `docs/vault/` ya existe (salvo con `HARNESS_SIN_CONTEXTO=1`).

¿Por qué `docs/` y no `docs/vault/`? Obsidian no abre archivos fuera de la
carpeta del vault, y spec, evidencia y review viven en `docs/`: con el vault en
`docs/vault/` esos enlaces no llevaban a ningún lado.

## ¿Cuesta algo?

No. Obsidian es gratis para uso personal y **no requiere cuenta** para abrir un
vault local. De pago son Sync (innecesario: el vault viaja por Git, que además
da historial y diffs) y Publish. La licencia comercial aplica a empresas de más
de dos personas usándolo para trabajo.

## Abrirlo

Obsidian → "Open folder as vault" → apuntar a `<proyecto>/docs/`.

Si lo abrías antes en `docs/vault/`, queda una `docs/vault/.obsidian/` de esa
época: `vault.py build` lo avisa. Bórrala cuando abras `docs/` (copia antes a
`docs/.obsidian/` lo que hayas ajustado a mano).

## Config sembrada automáticamente

`vault.py build` **siembra** `docs/.obsidian/` la primera vez, para que el
vault se vea igual en todas tus máquinas sin configurarlo a mano:

| Archivo | Qué fija |
|---|---|
| `app.json` | wikilinks cortos (no rutas Markdown), notas nuevas en `vault/notas/`, vista previa |
| `appearance.json` | tema oscuro, acento azul, tamaño de fuente |
| `core-plugins.json` | grafo, backlinks, búsqueda, propiedades, outline ON; daily-notes/canvas/sync OFF |
| `graph.json` | grafo coloreado por carpeta (features azul, servicios verde, lecciones naranja) y `vault/grafo/` excluido para que no lo ahogue |
| `community-plugins.json` | lista inicial vacia; los plugins opcionales se instalan y habilitan en Obsidian |
| `.gitignore` | ignora `workspace.json`, `cache/`, `plugins/`, `themes/` — ruido de sesión |

**Siembra, no impone.** Un archivo que ya existe nunca se sobrescribe: en cuanto
Obsidian o tú tocáis la config, es vuestra y `vault.py` no la vuelve a mirar.
Para volver al default: borrar `docs/.obsidian/` y regenerar. Para no
sembrar nada: `vault.py build --sin-config`.

Dataview es gratis y open source, pero hay que instalarlo y habilitarlo desde
Obsidian (Settings → Community plugins → Browse → Dataview). La skill no baja
binarios de terceros a tu repo.

## Qué genera `vault.py build`

```
docs/                        <- raiz del vault (spec, tests, impl, review, verify, prd/, sdd.md)
  .obsidian/                 <- config sembrada
  vault/
    Indice.md                <- panorama: PRD/SDD, features abiertas, hallazgos abiertos, servicios, lecciones
    features/Feature-<id>.md <- AC como checklist, enlaces a spec/tests/evidencia/review/verify/PRD/SDD y hallazgos
    lecciones/<clase>.md     <- lección + en qué features se usó
    servicios/<nombre>.md    <- microservicio + features que lo tocan
    grafo/<nodo>.md          <- solo con --con-grafo (notas planas por nodo)
    grafo-obsidian/          <- solo con --con-grafo-obsidian (`graphify export obsidian`: notas + .canvas)
    notas/                   <- TUYAS. El script nunca las toca y el brief las rescata si nombran la feature o servicio.
```

En la nota de feature, una casilla marcada indica que la evidencia declara el
AC y cita `archivo:linea`. El veredicto de `verify` y el review se consultan por
separado. El indice separa estados desconocidos de las features abiertas.

Hay una nota de servicio por cada repo git de la raíz del arnés y de las raíces
de `harness/grafos.json` (menos `docs/` y `harness/`), y por cada nombre que el
backlog declara en `microservicios` aunque no sea un repo: un enlace sin nota es
un callejón sin salida. Los nombres se normalizan como en el brief
(`demo/ms-foo-service` → `ms-foo-service`, comentarios entre paréntesis fuera).

Los wikilinks generados llevan la ruta desde `docs/`
(`[[vault/lecciones/x|x]]`): en cuanto `docs/` tiene otro `.md` con el mismo
nombre, el nombre pelado es ambiguo.

Todo lo generado lleva una marca `generado por harness-flow vault.py`. Es
idempotente y borra lo generado que ya no corresponde (feature borrada, servicio
renombrado; `grafo/` solo cuando la corrida pasa `--con-grafo`); lo que no lleva
el aviso no se toca. Si una nota manual ocupa una ruta generada, `build` falla
y te pide moverla a `vault/notas/`. Escribe tus notas ahi y enlaza a
`[[Feature-3]]` desde ahí.

## `--con-grafo` y `--con-grafo-obsidian`

- `--con-grafo`: genera una nota plana por nodo de `graphify-out/graph.json` en `docs/vault/grafo/` (tope 2000). Dos nodos con el mismo nombre reciben archivos distintos; los enlaces se limitan a los nodos incluidos en ese tope.
- `--con-grafo-obsidian`: delega a `graphify export obsidian --graph <grafo> --dir docs/vault/grafo-obsidian/` para exportar notas agrupadas por comunidad más el mapa `.canvas` nativo de Obsidian (requiere `graphify` en el PATH y un grafo generado).

Ambos inflan el vault: úsalos cuando quieras explorar arquitectura, no en cada build automático (la config sembrada de `graph.json` excluye `-path:vault/grafo -path:vault/grafo-obsidian` del grafo principal).

## Relación con Postgres

Son dos consumidores del mismo origen, no están conectados entre sí:

```
codigo --graphify--> graph.json --+--> vault.py  --> docs/vault/ --> Obsidian (docs/)
                                  |
                                  +--> hub.py derivar-graphify --> Postgres
```

Si quieres ver datos del hub en Obsidian, la vía es generar `.md` desde una
consulta (como hace `vault.py`), no conectar Obsidian a la base.

## Plugins útiles

- **Dataview**: consulta el frontmatter (`tipo: feature`, `estado: done`). Ej:
  `TABLE estado FROM "vault/features" WHERE estado != "done"`.
- **Graph Analysis**: mide centralidad sobre los wikilinks.

No son necesarios: el vault funciona sin plugins.
