#!/usr/bin/env python3
"""Genera docs/vault/ (Obsidian) desde el estado del proceso y el grafo.

Idempotente: reescribe solo lo generado. Los archivos que escribas a mano
dentro de vault/notas/ no se tocan.

  vault.py build [--con-grafo]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (cubre_acs, impl_path, load_backlog, now_iso, paths,  # noqa: E402
                   review_path, sello_revision, slugify, spec_acs, spec_estado,
                   spec_path)

AVISO = "<!-- generado por harness-flow vault.py — no editar a mano -->"


def esc(s: str) -> str:
    return str(s).replace("[[", "").replace("]]", "").replace("|", "-")


def main() -> None:
    ap = argparse.ArgumentParser()
    # 'build' es el unico modo; se acepta como palabra opcional para que
    # `vault.py build` y `vault.py` sean equivalentes.
    ap.add_argument("cmd", nargs="?", default="build", choices=["build"])
    ap.add_argument("--con-grafo", action="store_true", dest="con_grafo")
    a = ap.parse_args()
    p = paths(); data = load_backlog(p)
    v = p["vault"]
    for d in ("features", "lecciones", "servicios", "notas"):
        (v / d).mkdir(parents=True, exist_ok=True)
    (v / ".obsidian").mkdir(exist_ok=True)

    proyecto = data.get("project", p["root"].name)
    escritos = 0

    # --- una nota por feature ---
    for f in data["features"]:
        fid = f["id"]
        sp = spec_path(p, f)
        acs, estado = [], "sin spec"
        if sp.exists():
            t = sp.read_text(encoding="utf-8")
            acs, estado = spec_acs(t), spec_estado(t)
        ip, rp = impl_path(p, f), review_path(p, f)
        sello = sello_revision(rp.read_text(encoding="utf-8")) if rp.exists() else None
        faltan: list[str] = []
        if ip.exists():
            _, faltan = cubre_acs(ip.read_text(encoding="utf-8"), acs)

        micros = f.get("microservicios") or []
        cuerpo = [
            "---",
            f"tipo: feature",
            f"id: {fid}",
            f"estado: {f.get('status')}",
            f"spec: {estado}",
            f"kind: {f.get('kind','feature')}",
            "tags: [harness, feature]",
            "---",
            AVISO, "",
            f"# Feature #{fid} — {esc(f.get('name',''))}", "",
            f"Estado: **{f.get('status')}** · spec **{estado}**"
            + (f" · review **{sello}**" if sello else ""), "",
            "## Criterios de aceptacion", "",
        ]
        if acs:
            for ac in acs:
                marca = "x" if ac not in faltan and ip.exists() else " "
                cuerpo.append(f"- [{marca}] {ac}")
        else:
            cuerpo.append("_El spec no declara AC._")
        cuerpo += ["", "## Documentos", ""]
        for etiqueta, path in (("Spec", sp), ("Evidencia", ip), ("Review", rp)):
            if path.exists():
                rel = path.relative_to(p["root"]).as_posix()
                cuerpo.append(f"- {etiqueta}: [{path.name}](../../../{rel})")
        if micros:
            cuerpo += ["", "## Microservicios", ""]
            cuerpo += [f"- [[{esc(m)}]]" for m in micros]
        if f.get("leccion"):
            cuerpo += ["", f"Leccion: [[{esc(f['leccion'])}]]"]
        if f.get("branch"):
            cuerpo += ["", f"Rama: `{f['branch']}`"]
        (v / "features" / f"Feature-{fid}.md").write_text(
            "\n".join(cuerpo) + "\n", encoding="utf-8")
        escritos += 1

    # --- lecciones ---
    for lf in sorted(p["lecciones"].glob("*.md")) if p["lecciones"].exists() else []:
        usada = [f"[[Feature-{x['id']}]]" for x in data["features"]
                 if x.get("leccion") == lf.stem]
        rel = lf.relative_to(p["root"]).as_posix()
        (v / "lecciones" / f"{lf.stem}.md").write_text("\n".join([
            "---", "tipo: leccion", "tags: [harness, leccion]", "---", AVISO, "",
            f"# {esc(lf.stem)}", "",
            f"Fuente: [{lf.name}](../../../{rel})", "",
            "## Usada en", "",
            *(usada or ["_todavia no se declaro en ningun cierre_"]),
        ]) + "\n", encoding="utf-8")
        escritos += 1

    # --- servicios (repos git de la raiz) ---
    servicios = sorted(d.name for d in p["root"].iterdir()
                       if d.is_dir() and (d / ".git").exists() and d.name != "harness")
    for s in servicios:
        feats = [f"[[Feature-{x['id']}]]" for x in data["features"]
                 if s in (x.get("microservicios") or [])]
        (v / "servicios" / f"{s}.md").write_text("\n".join([
            "---", "tipo: microservicio", "tags: [harness, servicio]", "---", AVISO, "",
            f"# {esc(s)}", "", f"Repo: `{s}/`", "", "## Features que lo tocan", "",
            *(feats or ["_ninguna registrada_"]),
        ]) + "\n", encoding="utf-8")
        escritos += 1

    # --- nodos del grafo (opt-in: genera muchos archivos) ---
    if a.con_grafo and p["graph"].exists():
        g = json.loads(p["graph"].read_text(encoding="utf-8"))
        gd = v / "grafo"; gd.mkdir(exist_ok=True)
        nodes = g.get("nodes", [])
        por_id = {n.get("id"): n for n in nodes}
        vecinos: dict[str, list] = {}
        for e in g.get("edges", []) or g.get("links", []):
            s, t = e.get("source"), e.get("target")
            rel = e.get("relation") or e.get("type") or "rel"
            vecinos.setdefault(s, []).append((rel, t))
            vecinos.setdefault(t, []).append((f"<- {rel}", s))
        for n in nodes[:2000]:
            nid = n.get("id"); lbl = esc(n.get("label") or nid)
            nombre = slugify(lbl)[:60] or "nodo"
            links = [f"- {rel} [[{slugify(esc(por_id.get(o,{}).get('label') or o))[:60]}]]"
                     for rel, o in vecinos.get(nid, [])[:40]]
            (gd / f"{nombre}.md").write_text("\n".join([
                "---", "tipo: nodo", f"comunidad: {n.get('community_name') or n.get('community','')}",
                "tags: [grafo]", "---", AVISO, "",
                f"# {lbl}", "", f"Tipo: `{n.get('type','')}`",
                f"Fuente: `{n.get('source_file','')}`", "", "## Conexiones", "",
                *(links or ["_sin aristas_"]),
            ]) + "\n", encoding="utf-8")
            escritos += 1

    # --- indice ---
    abiertas = [f for f in data["features"] if f.get("status") not in ("done", "superseded")]
    (v / "Indice.md").write_text("\n".join([
        "---", "tipo: indice", "tags: [harness]", "---", AVISO, "",
        f"# {esc(proyecto)}", "", f"Actualizado: {now_iso()}", "",
        f"- Features: {len(data['features'])} ({len(abiertas)} abiertas)",
        f"- Microservicios: {len(servicios)}",
        f"- Lecciones: {len(list(p['lecciones'].glob('*.md'))) if p['lecciones'].exists() else 0}",
        "", "## En curso", "",
        *([f"- [[Feature-{f['id']}]] — {esc(f.get('name',''))} ({f.get('status')})"
           for f in abiertas] or ["_nada abierto_"]),
        "", "## Microservicios", "",
        *[f"- [[{esc(s)}]]" for s in servicios],
    ]) + "\n", encoding="utf-8")
    escritos += 1

    print(f"[ok] vault regenerado: {escritos} notas en {v}")
    print(f"[i]  abrelo en Obsidian con 'Open folder as vault' -> {v}")


if __name__ == "__main__":
    main()
