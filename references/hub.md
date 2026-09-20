# Memory Hub Postgres

Detalle de `hub.py`. Lo imprescindible esta en `SKILL.md`.

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

