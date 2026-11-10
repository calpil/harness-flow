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

## Que es un servicio

Los servicios salen de los repos reales del proyecto, con cualquier nombre: cada
repo dentro de una raiz de `harness/grafos.json` (o de la raiz del arnes), y la
propia raiz cuando es un repo, con el `nombre` que se le declaro (`front`).
`docs/` y `harness/` no cuentan, y un worktree tampoco: es trabajo en curso. Lo
usan `descubrir`, `derivar-graphify` y el brief.

`derivar-graphify` asigna cada nodo del grafo a un servicio por el primer
directorio de su `source_file`; el codigo de una raiz que es un repo va a esa
raiz. La convencion de antes (`ms-*-service`, `*-ui`) queda solo como ultimo
recurso para grafos sin repos conocidos. Filtra las relaciones
`references|implements|depends_on|uses|cites|shares_data_with`.

Las dependencias de origen graphify que ya no estan en el grafo se retiran del
hub, pero solo entre servicios que el grafo SI contiene: si un servicio falta
(raiz sin refrescar, merge a medias), sus aristas no se tocan. Las manuales
(`vincular`) y las de otros proyectos nunca se borran.

## Lecturas, fallos y como apagarlo

- `mapa`, `impacto` y `consultar` no crean tablas: un usuario de solo lectura
  puede usarlos. Solo los comandos que escriben aseguran el esquema.
- En el brief, un servicio que el hub no conoce sale como `NO esta en el hub`,
  distinto de `sin dependencias declaradas`. El brief consulta hasta 4 servicios
  y nombra los que deja fuera.
- Un fallo de conexion sale en una linea, sin traza.
- `HARNESS_SIN_HUB=1` impide toda conexion (`hub.py` se niega, `refrescar` anota
  `omitido`, el brief dice que no consulto). `HARNESS_SIN_CONTEXTO=1` tambien
  apaga la consulta del brief: los tests y el CI del arnes no abren la base real.

