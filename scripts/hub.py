#!/usr/bin/env python3
"""Memory Hub PostgreSQL. MISMO esquema que el arnes Rust (graph_nodes /
graph_edges), asi que el historico existente se conserva y se sigue usando.

  hub.py mapa
  hub.py descubrir [--aplicar]
  hub.py impacto   --microservicio <proyecto>/<servicio>
  hub.py vincular  --consumer <a> --target <b> [--tipo DEPENDS_ON]
  hub.py registrar --agente <a> --accion <x> --artefacto <f> [--estado ok]
  hub.py derivar-graphify
  hub.py consultar --artefacto <id>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import hub_env, now_iso, paths  # noqa: E402

SERVICE_RE = re.compile(r"(ms-[a-z0-9-]+-service|[a-z0-9-]+-ui)")
DEP_RELATIONS = {"references", "implements", "shares_data_with",
                 "depends_on", "uses", "cites"}
# tipo de arista que el hub ya usa para dependencias entre microservicios
TIPO_DEPENDENCIA = "DEPENDE_DE"
CONVENTION_RE = re.compile(
    r"convention|policy|guideline|standard|lint|layout", re.IGNORECASE)


def conectar():
    try:
        import psycopg
    except ImportError:
        sys.exit("[!!] falta psycopg. Instala:  uv pip install 'psycopg[binary]'\n"
                 "     (o pip install 'psycopg[binary]')")
    e = hub_env()
    faltan = [k for k in ("DB_HOST", "DB_USER", "DB_PASSWORD") if not e.get(k)]
    if faltan:
        sys.exit(f"[!!] el Memory Hub requiere: {', '.join(faltan)}\n"
                 "     Ponlos en ~/.harness-hub/.env o en el entorno.")
    # Parametros sueltos, NO un DSN concatenado: en el formato keyword/value
    # un espacio, una comilla simple o una barra invertida en la password
    # parte la cadena y psycopg termina leyendo basura (o conectando a otro
    # host). psycopg escapa cada valor por su cuenta.
    conn = psycopg.connect(
        host=e["DB_HOST"], port=e["DB_PORT"], dbname=e["DB_NAME"],
        user=e["DB_USER"], password=e["DB_PASSWORD"],
        sslmode=e["DB_SSL_MODE"], connect_timeout=20)
    with conn.cursor() as cur:   # mismo DDL que el arnes Rust: IF NOT EXISTS
        cur.execute("""
            CREATE TABLE IF NOT EXISTS graph_nodes (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                props JSONB NOT NULL DEFAULT '{}'::jsonb
            );
            CREATE TABLE IF NOT EXISTS graph_edges (
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                type TEXT NOT NULL,
                props JSONB NOT NULL DEFAULT '{}'::jsonb,
                PRIMARY KEY (source, target, type)
            );""")
    conn.commit()
    return conn


def project_name(p: dict) -> str:
    import comun
    return comun.load_backlog(p).get("project") or p["root"].name


def qualify(project: str, name: str) -> str:
    return name if "/" in name else f"{project}/{name}"


def upsert_node(cur, nid: str, label: str, props: dict) -> None:
    from psycopg.types.json import Jsonb
    cur.execute(
        "INSERT INTO graph_nodes (id,label,props) VALUES (%s,%s,%s) "
        "ON CONFLICT (id) DO UPDATE SET label=EXCLUDED.label, "
        "props = graph_nodes.props || EXCLUDED.props",
        (nid, label, Jsonb(props)))


def upsert_edge(cur, etype: str, src: str, tgt: str, props: dict | None = None) -> None:
    from psycopg.types.json import Jsonb
    cur.execute(
        "INSERT INTO graph_edges (source,target,type,props) VALUES (%s,%s,%s,%s) "
        "ON CONFLICT (source,target,type) DO UPDATE SET "
        "props = graph_edges.props || EXCLUDED.props",
        (src, tgt, etype, Jsonb(props or {})))


# --- comandos --------------------------------------------------------------

def cmd_mapa(args) -> None:
    conn = conectar()
    e = hub_env()
    with conn.cursor() as cur:
        cur.execute("SELECT id,label,props FROM graph_nodes ORDER BY id")
        nodes = cur.fetchall()
        cur.execute("SELECT source,target,type FROM graph_edges")
        edges = cur.fetchall()
    micros = [n for n in nodes if n[1] == "Microservicio"]
    n_commits = sum(1 for _i, l, _p in nodes if l == "Commit")
    proyectos: dict[str, list] = {}
    for nid, _l, props in micros:
        proj = nid.split("/")[0] if "/" in nid else "(sin proyecto)"
        proyectos.setdefault(proj, []).append((nid.split("/")[-1], props or {}))
    deps = [x for x in edges if x[2] == TIPO_DEPENDENCIA]

    print(f"== Mapa del Hub PostgreSQL ({e['DB_NAME']}@{e['DB_HOST']}:{e['DB_PORT']}) ==")
    print(f"Proyectos: {len(proyectos)} | Microservicios: {len(micros)} | "
          f"Dependencias: {len(deps)} | Commits: {n_commits}\n")
    for proj in sorted(proyectos):
        print(f"[{proj}]")
        for name, props in sorted(proyectos[proj]):
            extra = []
            if props.get("commits"):
                extra.append(f"{props['commits']} commits")
            if props.get("transversal"):
                extra.append("transversal")
            print(f"   - {name}" + (f"  ({', '.join(extra)})" if extra else ""))
        print()
    conn.close()


def cmd_descubrir(args) -> None:
    p = paths()
    project = project_name(p)
    repos = sorted(d.name for d in p["root"].iterdir()
                   if d.is_dir() and (d / ".git").exists() and d.name != "harness")
    if not repos:
        print("[i]  no se encontraron repos git bajo la raiz")
        return
    print(f"Microservicios detectados en {project}: {len(repos)}")
    for r in repos:
        print(f"   - {r}")
    if not args.aplicar:
        print("\n[i]  solo lectura. Para registrarlos en el hub: --aplicar")
        return
    conn = conectar()
    with conn.cursor() as cur:
        upsert_node(cur, project, "Proyecto", {"root": str(p["root"])})
        for r in repos:
            nid = f"{project}/{r}"
            upsert_node(cur, nid, "Microservicio",
                        {"servicio": r, "proyecto": project,
                         "path": str(p["root"] / r)})
            upsert_edge(cur, "CONTIENE", project, nid)
    conn.commit(); conn.close()
    print(f"\n[ok] {len(repos)} microservicio(s) registrados en el hub")


def cmd_impacto(args) -> None:
    conn = conectar()
    target = args.microservicio
    with conn.cursor() as cur:
        cur.execute("SELECT source,type FROM graph_edges WHERE target=%s", (target,))
        entrantes = cur.fetchall()
        cur.execute("SELECT target,type FROM graph_edges WHERE source=%s", (target,))
        salientes = cur.fetchall()
        cur.execute("SELECT props FROM graph_nodes WHERE id=%s", (target,))
        row = cur.fetchone()
    if not row:
        print(f"[!] {target} no existe en el hub. Corre: hub.py descubrir --aplicar")
    consumidores = [s for s, t in entrantes if t == TIPO_DEPENDENCIA]
    print(f"== Impacto de {target} ==\n")
    print(f"Si tocas esto, se puede romper ({len(consumidores)}):")
    for s, t in entrantes:
        if t != "CONTIENE":
            print(f"   <- {s}  [{t}]")
    if not consumidores:
        print("   (nadie declarado depende de el)")
    print(f"\nDepende de ({len([1 for _x,t in salientes if t!='CONTIENE'])}):")
    for tg, t in salientes:
        if t != "CONTIENE":
            print(f"   -> {tg}  [{t}]")
    conn.close()


def cmd_vincular(args) -> None:
    p = paths(); project = project_name(p)
    c = qualify(project, args.consumer); t = qualify(project, args.target)
    conn = conectar()
    with conn.cursor() as cur:
        for nid in (c, t):
            upsert_node(cur, nid, "Microservicio",
                        {"servicio": nid.split("/")[-1],
                         "proyecto": nid.split("/")[0]})
        upsert_edge(cur, args.tipo, c, t, {"origen": "manual", "at": now_iso()})
    conn.commit(); conn.close()
    print(f"[ok] {c} --[{args.tipo}]--> {t}")


def cmd_registrar(args) -> None:
    p = paths(); project = project_name(p)
    conn = conectar()
    art = f"{project}/{args.artefacto}"
    with conn.cursor() as cur:
        upsert_node(cur, args.agente, "Agente", {})
        upsert_node(cur, art, "Artefacto",
                    {"estado": args.estado, "at": now_iso()})
        upsert_edge(cur, args.accion.upper(), args.agente, art,
                    {"estado": args.estado, "at": now_iso()})
    conn.commit(); conn.close()
    print(f"[Memoria] {args.agente} --[{args.accion}]--> {art} ({args.estado})")


def cmd_consultar(args) -> None:
    conn = conectar()
    with conn.cursor() as cur:
        cur.execute("SELECT id,label,props FROM graph_nodes WHERE id LIKE %s",
                    (f"%{args.artefacto}%",))
        rows = cur.fetchall()
    print(json.dumps([{"id": r[0], "label": r[1], "props": r[2]} for r in rows],
                     ensure_ascii=False, indent=2))
    conn.close()


def cmd_derivar_graphify(args) -> None:
    """graphify-out/graph.json -> dependencias entre microservicios en el hub.

    Misma heuristica que derive.rs: el servicio sale del source_file del nodo,
    y solo cuentan las relaciones de dependencia que no sean convenciones.
    """
    p = paths(); project = project_name(p)
    if not p["graph"].exists():
        print(f"[i]  no existe {p['graph']}; nada que derivar.")
        return
    g = json.loads(p["graph"].read_text(encoding="utf-8"))
    nodes = {n.get("id"): n for n in g.get("nodes", [])}

    def servicio(nid):
        n = nodes.get(nid)
        if not n:
            return None
        src = n.get("source_file") or ""
        m = SERVICE_RE.search(str(src).replace("\\", "/"))
        return f"{project}/{m.group(1)}" if m else None

    pares: dict[tuple[str, str], str] = {}
    for e in g.get("edges", []) or g.get("links", []):
        rel = str(e.get("relation") or e.get("type") or "").lower()
        if rel not in DEP_RELATIONS:
            continue
        s, t = servicio(e.get("source")), servicio(e.get("target"))
        if not s or not t or s == t:
            continue
        etiqueta = f"{nodes.get(e.get('source'),{}).get('label','')} {nodes.get(e.get('target'),{}).get('label','')}"
        if CONVENTION_RE.search(etiqueta):
            continue
        pares[(s, t)] = rel.upper()

    if not pares:
        print("[i]  el grafo no revelo dependencias entre microservicios.")
        return
    conn = conectar()
    with conn.cursor() as cur:
        upsert_node(cur, project, "Proyecto", {"graphify": str(p["graph"].parent)})
        for (s, t), rel in pares.items():
            for nid in (s, t):
                upsert_node(cur, nid, "Microservicio",
                            {"servicio": nid.split("/")[-1],
                             "proyecto": nid.split("/")[0]})
            upsert_edge(cur, TIPO_DEPENDENCIA, s, t,
                        {"origen": "graphify", "relacion": rel, "at": now_iso()})
    conn.commit(); conn.close()
    print(f"[ok] {len(pares)} dependencia(s) derivadas al hub:")
    for (s, t), rel in sorted(pares.items()):
        print(f"   {s} --[{rel}]--> {t}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Memory Hub PostgreSQL del harness-flow")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("mapa").set_defaults(fn=cmd_mapa)
    s = sub.add_parser("descubrir"); s.add_argument("--aplicar", action="store_true")
    s.set_defaults(fn=cmd_descubrir)
    s = sub.add_parser("impacto"); s.add_argument("--microservicio", required=True)
    s.set_defaults(fn=cmd_impacto)
    s = sub.add_parser("vincular"); s.add_argument("--consumer", required=True)
    s.add_argument("--target", required=True); s.add_argument("--tipo", default=TIPO_DEPENDENCIA)
    s.set_defaults(fn=cmd_vincular)
    s = sub.add_parser("registrar"); s.add_argument("--agente", required=True)
    s.add_argument("--accion", required=True); s.add_argument("--artefacto", required=True)
    s.add_argument("--estado", default="ok"); s.set_defaults(fn=cmd_registrar)
    s = sub.add_parser("consultar"); s.add_argument("--artefacto", required=True)
    s.set_defaults(fn=cmd_consultar)
    sub.add_parser("derivar-graphify").set_defaults(fn=cmd_derivar_graphify)
    args = ap.parse_args(); args.fn(args)


if __name__ == "__main__":
    main()
