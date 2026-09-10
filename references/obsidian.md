# Obsidian en el harness-flow

## Qué es el vault aquí

`docs/vault/` dentro del repo, versionado con el proyecto. Es una carpeta de
archivos `.md` con wikilinks; Obsidian solo la lee. No hay servidor ni base de
datos: Obsidian NO se conecta a Postgres.

## Abrirlo

Obsidian → "Open folder as vault" → apuntar a `<proyecto>/docs/vault/`.
La carpeta `.obsidian/` guarda la config y viaja por Git, así que el vault se ve
igual en Windows y macOS.

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
