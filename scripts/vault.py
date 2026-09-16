#!/usr/bin/env python3
"""Genera docs/vault/ (Obsidian) desde el estado del proceso y el grafo.

Idempotente: reescribe solo lo generado. Los archivos que escribas a mano
dentro de vault/notas/ no se tocan.

  vault.py build [--con-grafo]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path  # noqa: F401  (lo usa la carga de lecciones)

sys.path.insert(0, str(Path(__file__).parent))
from comun import (cubre_acs, impl_path, load_backlog, now_iso, paths,  # noqa: E402
                   review_path, sello_revision, slugify, spec_acs, spec_estado,
                   spec_path)

AVISO = "<!-- generado por harness-flow vault.py — no editar a mano -->"


def esc(s: str) -> str:
    return str(s).replace("[[", "").replace("]]", "").replace("|", "-")


# Config base del vault. Se SIEMBRA (solo si el archivo no existe) para que el
# vault se vea igual en todas tus maquinas sin configurarlo a mano. Una vez
# sembrado es tuyo: Obsidian lo reescribe al vuelo y vault.py no lo vuelve a
# tocar. Para volver al default: borra docs/vault/.obsidian y regenera.
SEMILLA_OBSIDIAN: dict[str, dict] = {
    # Markdown estricto: wikilinks relativos al vault y sin "ayudas" que
    # reescriban los .md generados.
    "app.json": {
        "newLinkFormat": "shortest",
        "useMarkdownLinks": False,
        "attachmentFolderPath": "notas/adjuntos",
        "alwaysUpdateLinks": True,
        "showUnsupportedFiles": True,
        "defaultViewMode": "preview",
        "livePreview": True,
        "readableLineLength": True,
        "strictLineBreaks": False,
        "promptDelete": True,
        "newFileLocation": "folder",
        "newFileFolderPath": "notas",
    },
    "appearance.json": {
        "theme": "obsidian",          # oscuro
        "accentColor": "#4c8dff",
        "baseFontSize": 15,
        "showInlineTitle": True,
        "showViewHeader": True,
    },
    # Plugins de nucleo: no hay nada que descargar, vienen con Obsidian.
    "core-plugins.json": {
        "file-explorer": True,
        "global-search": True,
        "switcher": True,
        "graph": True,
        "backlink": True,
        "outgoing-link": True,
        "tag-pane": True,
        "properties": True,
        "outline": True,
        "word-count": True,
        "command-palette": True,
        "editor-status": True,
        "bookmarks": True,
        "file-recovery": True,
        "templates": False,
        "daily-notes": False,
        "canvas": False,
        "slides": False,
        "audio-recorder": False,
        "zk-prefixer": False,
        "random-note": False,
        "workspaces": False,
        "markdown-importer": False,
        "note-composer": False,
        "slash-command": False,
        "sync": False,
        "publish": False,
        "webviewer": False,
    },
    # Vista de grafo util de entrada: features y servicios coloreados, y la
    # carpeta grafo/ fuera para que no ahogue el dibujo.
    "graph.json": {
        "collapse-filter": False,
        "search": "-path:grafo",
        "showTags": False,
        "showAttachments": False,
        "hideUnresolved": True,
        "showOrphans": True,
        "collapse-color-groups": False,
        "colorGroups": [
            {"query": "path:features", "color": {"a": 1, "rgb": 5021439}},
            {"query": "path:servicios", "color": {"a": 1, "rgb": 5025616}},
            {"query": "path:lecciones", "color": {"a": 1, "rgb": 16745472}},
            {"query": "path:notas", "color": {"a": 1, "rgb": 12633088}},
        ],
        "collapse-display": False,
        "showArrow": True,
        "textFadeMultiplier": -0.3,
        "nodeSizeMultiplier": 1.2,
        "lineSizeMultiplier": 1,
        "collapse-forces": False,
        "centerStrength": 0.5,
        "repelStrength": 11,
        "linkStrength": 1,
        "linkDistance": 260,
        "scale": 0.8,
    },
    # Dataview es un plugin de comunidad: esto solo lo deja HABILITADO para
    # cuando lo instales desde Obsidian. No lo descarga (seria bajar binarios
    # de terceros a tu repo sin que lo pidas).
    "community-plugins.json": ["dataview"],
}


def sembrar_obsidian(v) -> tuple[int, bool]:
    """Escribe la config base del vault. Devuelve (archivos nuevos, primera vez)."""
    import json as _json

    od = v / ".obsidian"
    od.mkdir(parents=True, exist_ok=True)

    # Obsidian reescribe estos en cada sesion (posicion de paneles, cache).
    # Versionarlos llenaria tus diffs de ruido sin aportar nada.
    gi = od / ".gitignore"
    if not gi.exists():
        gi.write_text("\n".join([
            "# ruido de sesion de Obsidian: no versionar",
            "workspace.json",
            "workspace-mobile.json",
            "cache/",
            "plugins/",
            "themes/",
        ]) + "\n", encoding="utf-8")

    marca = od / ".harness-seed"
    primera = not marca.exists()
    nuevos = 0
    for nombre, contenido in SEMILLA_OBSIDIAN.items():
        destino = od / nombre
        if destino.exists():
            continue  # ya es tuyo: Obsidian manda
        destino.write_text(
            _json.dumps(contenido, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        nuevos += 1
    if nuevos:
        marca.write_text(
            "Config base sembrada por harness-flow vault.py.\n"
            "Los archivos de .obsidian/ NO se vuelven a tocar: son tuyos y\n"
            "Obsidian los reescribe al usarlos. Para volver al default,\n"
            "borra esta carpeta y ejecuta vault.py de nuevo.\n",
            encoding="utf-8")
    return nuevos, primera


def main() -> None:
    ap = argparse.ArgumentParser()
    # 'build' es el unico modo; se acepta como palabra opcional para que
    # `vault.py build` y `vault.py` sean equivalentes.
    ap.add_argument("cmd", nargs="?", default="build", choices=["build"])
    ap.add_argument("--con-grafo", action="store_true", dest="con_grafo")
    ap.add_argument("--sin-config", action="store_true", dest="sin_config",
                    help="no sembrar docs/vault/.obsidian (config de Obsidian)")
    a = ap.parse_args()
    p = paths(); data = load_backlog(p)
    v = p["vault"]
    for d in ("features", "lecciones", "servicios", "notas"):
        (v / d).mkdir(parents=True, exist_ok=True)

    cfg_nuevos, cfg_primera = (0, False)
    if not a.sin_config:
        cfg_nuevos, cfg_primera = sembrar_obsidian(v)

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

    # --- lecciones (son SKILLS de Hermes, no archivos del repo) ---
    sys.path.insert(0, str(Path(__file__).parent))
    from leccion import buscar as buscar_leccion
    clases = sorted({x["leccion"] for x in data["features"]
                     if x.get("leccion") and x["leccion"] != "ninguna"})
    for clase in clases:
        usada = [f"[[Feature-{x['id']}]]" for x in data["features"]
                 if x.get("leccion") == clase]
        sm = buscar_leccion(clase)
        origen = (f"Skill de Hermes: `{clase}`" if sm
                  else f"**FALTA**: la skill `{clase}` no esta instalada aqui")
        # slugify: el valor viene del backlog sin sanitizar y Path resuelve '..',
        # asi que una leccion '../../../README' pisaba archivos del repo.
        destino = (v / "lecciones" / f"{slugify(clase)}.md").resolve()
        if not str(destino).startswith(str((v / "lecciones").resolve()) + os.sep):
            raise SystemExit(f"[!!] leccion con ruta fuera del vault: {clase!r}")
        destino.write_text("\n".join([
            "---", "tipo: leccion", "tags: [harness, leccion]", "---", AVISO, "",
            f"# {esc(clase)}", "",
            origen, "",
            "_Vive en tus skills de Hermes y viaja contigo entre proyectos;",
            "aqui solo queda la traza de donde se aplico._", "",
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
        f"- Lecciones aplicadas: {len(clases)}",
        "", "## En curso", "",
        *([f"- [[Feature-{f['id']}]] — {esc(f.get('name',''))} ({f.get('status')})"
           for f in abiertas] or ["_nada abierto_"]),
        "", "## Microservicios", "",
        *[f"- [[{esc(s)}]]" for s in servicios],
    ]) + "\n", encoding="utf-8")
    escritos += 1

    print(f"[ok] vault regenerado: {escritos} notas en {v}")
    if cfg_nuevos:
        print(f"[ok] config de Obsidian sembrada ({cfg_nuevos} archivos en .obsidian/)")
        if cfg_primera:
            print("[i]  tema oscuro, grafo coloreado por carpeta y wikilinks cortos.")
            print("[i]  Dataview queda habilitado: instalalo en Obsidian ->")
            print("     Settings > Community plugins > Browse > Dataview.")
    print(f"[i]  abrelo en Obsidian con 'Open folder as vault' -> {v}")


if __name__ == "__main__":
    main()
