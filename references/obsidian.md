# Obsidian en el harness-flow

## Qué es el vault aquí

El vault es **`docs/`**, versionado con el proyecto; las notas generadas viven en
`docs/vault/`. Son archivos `.md` con wikilinks; Obsidian solo los lee. No hay
servidor ni base de datos: Obsidian NO se conecta a Postgres.

Es un panel para ti, no una entrada del flujo: ningún rol (leader, implementer,
revisor) lo lee. El índice del agente es `contexto.py brief`, que sale del grafo
y del hub.

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
| `community-plugins.json` | deja Dataview **habilitado** (no lo descarga) |
| `.gitignore` | ignora `workspace.json`, `cache/`, `plugins/`, `themes/` — ruido de sesión |

**Siembra, no impone.** Un archivo que ya existe nunca se sobrescribe: en cuanto
Obsidian o tú tocáis la config, es vuestra y `vault.py` no la vuelve a mirar.
Para volver al default: borrar `docs/.obsidian/` y regenerar. Para no
sembrar nada: `vault.py build --sin-config`.

Dataview es gratis y open source, pero hay que instalarlo desde dentro de
Obsidian (Settings → Community plugins → Browse → Dataview). La skill no baja
binarios de terceros a tu repo.

## Qué genera `vault.py build`

```
docs/                        <- raiz del vault (spec, impl, review, prd/, sdd.md)
  .obsidian/                 <- config sembrada
  vault/
    Indice.md                <- panorama: features abiertas, servicios, lecciones
    features/Feature-<id>.md <- AC como checklist, enlaces a spec/evidencia/review
    lecciones/<clase>.md     <- lección + en qué features se usó
    servicios/<nombre>.md    <- microservicio + features que lo tocan
    grafo/<nodo>.md          <- solo con --con-grafo
    notas/                   <- TUYAS. El script nunca las toca.
```

Hay una nota de servicio por cada repo git de la raíz del arnés y de las raíces
de `harness/grafos.json` (menos `docs/` y `harness/`), y por cada nombre que el
backlog declara en `microservicios` aunque no sea un repo: un enlace sin nota es
un callejón sin salida. Los nombres se normalizan como en el brief
(`demo/ms-foo-service` → `ms-foo-service`, comentarios entre paréntesis fuera).

Los wikilinks generados llevan la ruta desde `docs/`
(`[[vault/lecciones/x|x]]`): en cuanto `docs/` tiene otro `.md` con el mismo
nombre, el nombre pelado es ambiguo.

Todo lo generado lleva `<!-- generado por harness-flow vault.py -->`. Es
idempotente y borra lo generado que ya no corresponde (feature borrada, servicio
renombrado; `grafo/` solo cuando la corrida pasa `--con-grafo`); lo que no lleva
el aviso no se toca. Escribe tus notas en `vault/notas/` y enlaza a
`[[Feature-3]]` desde ahí.

## `--con-grafo`

Genera una nota por nodo de `graphify-out/graph.json` (tope 2000). Da un mapa
navegable del código, pero infla el vault: úsalo cuando quieras explorar
arquitectura, no en cada build.

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
