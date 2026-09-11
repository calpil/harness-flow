# Obsidian en el harness-flow

## Qué es el vault aquí

`docs/vault/` dentro del repo, versionado con el proyecto. Es una carpeta de
archivos `.md` con wikilinks; Obsidian solo la lee. No hay servidor ni base de
datos: Obsidian NO se conecta a Postgres.

## ¿Cuesta algo?

No. Obsidian es gratis para uso personal y **no requiere cuenta** para abrir un
vault local. De pago son Sync (innecesario: el vault viaja por Git, que además
da historial y diffs) y Publish. La licencia comercial aplica a empresas de más
de dos personas usándolo para trabajo.

## Abrirlo

Obsidian → "Open folder as vault" → apuntar a `<proyecto>/docs/vault/`.

## Config sembrada automáticamente

`vault.py build` **siembra** `docs/vault/.obsidian/` la primera vez, para que el
vault se vea igual en todas tus máquinas sin configurarlo a mano:

| Archivo | Qué fija |
|---|---|
| `app.json` | wikilinks cortos (no rutas Markdown), notas nuevas en `notas/`, vista previa |
| `appearance.json` | tema oscuro, acento azul, tamaño de fuente |
| `core-plugins.json` | grafo, backlinks, búsqueda, propiedades, outline ON; daily-notes/canvas/sync OFF |
| `graph.json` | grafo coloreado por carpeta (features azul, servicios verde, lecciones naranja) y `grafo/` excluido para que no lo ahogue |
| `community-plugins.json` | deja Dataview **habilitado** (no lo descarga) |
| `.gitignore` | ignora `workspace.json`, `cache/`, `plugins/`, `themes/` — ruido de sesión |

**Siembra, no impone.** Un archivo que ya existe nunca se sobrescribe: en cuanto
Obsidian o tú tocáis la config, es vuestra y `vault.py` no la vuelve a mirar.
Para volver al default: borrar `docs/vault/.obsidian/` y regenerar. Para no
sembrar nada: `vault.py build --sin-config`.

Dataview es gratis y open source, pero hay que instalarlo desde dentro de
Obsidian (Settings → Community plugins → Browse → Dataview). La skill no baja
binarios de terceros a tu repo.

## Qué genera `vault.py build`

```
docs/vault/
  Indice.md                  <- panorama: features abiertas, servicios, lecciones
  features/Feature-<id>.md   <- AC como checklist, enlaces a spec/evidencia/review
  lecciones/<clase>.md       <- lección + en qué features se usó
  servicios/<repo>.md        <- microservicio + features que lo tocan
  grafo/<nodo>.md            <- solo con --con-grafo
  notas/                     <- TUYAS. El script nunca las toca.
```

Todo lo generado lleva `<!-- generado por harness-flow vault.py -->`. Es
idempotente: se puede correr cuantas veces quieras. Escribe tus notas propias en
`notas/` y enlaza a `[[Feature-3]]` desde ahí.

## `--con-grafo`

Genera una nota por nodo de `graphify-out/graph.json` (tope 2000). Da un mapa
navegable del código, pero infla el vault: úsalo cuando quieras explorar
arquitectura, no en cada build.

## Relación con Postgres

Son dos consumidores del mismo origen, no están conectados entre sí:

```
codigo --graphify--> graph.json --+--> vault.py  --> docs/vault/ --> Obsidian
                                  |
                                  +--> hub.py derivar-graphify --> Postgres
```

Si quieres ver datos del hub en Obsidian, la vía es generar `.md` desde una
consulta (como hace `vault.py`), no conectar Obsidian a la base.

## Plugins útiles

- **Dataview**: consulta el frontmatter (`tipo: feature`, `estado: done`). Ej:
  `TABLE estado FROM "features" WHERE estado != "done"`.
- **Graph Analysis**: mide centralidad sobre los wikilinks.

No son necesarios: el vault funciona sin plugins.
