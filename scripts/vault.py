#!/usr/bin/env python3
"""Genera docs/vault/ (Obsidian) desde el estado del proceso y el grafo.

El vault de Obsidian es docs/ entero, no docs/vault/: asi spec, evidencia y
review quedan DENTRO y se enlazan con wikilinks (Obsidian no abre archivos
fuera de la carpeta del vault). Las notas generadas viven en docs/vault/.

Idempotente: reescribe solo lo generado y borra lo generado que ya no
corresponde. Los archivos que escribas a mano (sin el aviso) no se tocan.

  vault.py build [--con-grafo] [--sin-config]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path  # noqa: F401  (lo usa la carga de lecciones)

sys.path.insert(0, str(Path(__file__).parent))
from comun import (cubre_acs, impl_path, load_backlog, micros_declarados,  # noqa: E402
                   now_iso, paths, raices_grafo, review_path, sello_revision,
                   slugify, spec_acs, spec_estado, spec_path)

AVISO = "<!-- generado por harness-flow vault.py — no editar a mano -->"


def esc(s: str) -> str:
    return str(s).replace("[[", "").replace("]]", "").replace("|", "-")


def nota(nombre: str) -> str:
    """Nombre de archivo valido para Obsidian (y para Windows)."""
    return re.sub(r'[\\/:*?"<>|#^\[\]]+', "-", str(nombre)).strip(" .-") or "sin-nombre"


def enlace(ruta: str) -> str:
    """Wikilink con ruta desde la raiz del vault (docs/).

    El nombre pelado es ambiguo en cuanto docs/ tiene otro .md que se llama
    igual (pasa: copias de lecciones, borradores), y Obsidian resuelve al que
    le parezca. La ruta completa no.
    """
    corto = ruta.rsplit("/", 1)[-1]
    return f"[[{ruta}]]" if corto == ruta else f"[[{ruta}|{corto}]]"


def repos_de_las_raices(p: dict) -> dict[str, list[str]]:
    """Repos git de la raiz del arnes y de las raices de harness/grafos.json.

    Solo la raiz del arnes dejaba fuera a los micros cuando viven en otra
    carpeta del disco. docs/ y harness/ son del proceso, no microservicios.
    """
    try:
        raices = [p["root"]] + [r["path"] for r in raices_grafo(p)]
    except SystemExit as exc:
        print(f"[!] {exc}\n    el vault sigue solo con los repos de la raiz del arnes.")
        raices = [p["root"]]
    repos: dict[str, list[str]] = {}
    vistas: set[Path] = set()
    for raiz in raices:
        raiz = Path(raiz).resolve()
        if raiz in vistas or not raiz.is_dir():
            continue
        vistas.add(raiz)
        for d in sorted(raiz.iterdir()):
            if d.is_dir() and (d / ".git").exists() and d.name not in ("docs", "harness"):
                try:
                    donde = d.relative_to(p["root"]).as_posix()
                except ValueError:
                    donde = str(d).replace(str(Path.home()), "~", 1)
                repos.setdefault(d.name, []).append(donde)
    return repos


# Config base del vault. Se SIEMBRA (solo si el archivo no existe) para que el
# vault se vea igual en todas tus maquinas sin configurarlo a mano. Una vez
# sembrado es tuyo: Obsidian lo reescribe al vuelo y vault.py no lo vuelve a
# tocar. Para volver al default: borra docs/.obsidian y regenera.
SEMILLA_OBSIDIAN: dict[str, dict] = {
    # Markdown estricto: wikilinks relativos al vault y sin "ayudas" que
    # reescriban los .md generados. El vault es docs/: las notas propias van a
    # vault/notas, junto a las generadas.
    "app.json": {
        "newLinkFormat": "shortest",
        "useMarkdownLinks": False,
        "attachmentFolderPath": "vault/notas/adjuntos",
        "alwaysUpdateLinks": True,
        "showUnsupportedFiles": True,
        "defaultViewMode": "preview",
        "livePreview": True,
        "readableLineLength": True,
        "strictLineBreaks": False,
        "promptDelete": True,
        "newFileLocation": "folder",
        "newFileFolderPath": "vault/notas",
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
    # carpeta vault/grafo/ fuera para que no ahogue el dibujo.
    "graph.json": {
        "collapse-filter": False,
        "search": "-path:vault/grafo",
        "showTags": False,
        "showAttachments": False,
        "hideUnresolved": True,
        "showOrphans": True,
        "collapse-color-groups": False,
        "colorGroups": [
            {"query": "path:vault/features", "color": {"a": 1, "rgb": 5021439}},
            {"query": "path:vault/servicios", "color": {"a": 1, "rgb": 5025616}},
            {"query": "path:vault/lecciones", "color": {"a": 1, "rgb": 16745472}},
            {"query": "path:vault/notas", "color": {"a": 1, "rgb": 12633088}},
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
                    help="no sembrar docs/.obsidian (config de Obsidian)")
    a = ap.parse_args()
    p = paths(); data = load_backlog(p)
    v = p["vault"]
    for d in ("features", "lecciones", "servicios", "notas"):
        (v / d).mkdir(parents=True, exist_ok=True)

    cfg_nuevos, cfg_primera = (0, False)
    if not a.sin_config:
        cfg_nuevos, cfg_primera = sembrar_obsidian(p["docs"])

    proyecto = data.get("project", p["root"].name)
    escritas: set[Path] = set()

    def escribir(destino: Path, lineas: list[str]) -> None:
        destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        escritas.add(destino.resolve())

    def feature(fid) -> str:
        return enlace(f"vault/features/Feature-{fid}")

    def leccion_de(f: dict) -> str | None:
        # 'ninguna' es la declaracion explicita de que no hubo leccion: no
        # hay nota que enlazar.
        clase = f.get("leccion")
        return str(clase) if clase and clase != "ninguna" else None

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

        micros = micros_declarados(f)
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
                rel = path.relative_to(p["docs"]).with_suffix("").as_posix()
                cuerpo.append(f"- {etiqueta}: {enlace(rel)}")
        if micros:
            cuerpo += ["", "## Microservicios", ""]
            cuerpo += [f"- {enlace('vault/servicios/' + nota(m))}" for m in micros]
        clase = leccion_de(f)
        if clase:
            cuerpo += ["", f"Leccion: {enlace('vault/lecciones/' + slugify(clase))}"]
        if f.get("branch"):
            cuerpo += ["", f"Rama: `{f['branch']}`"]
        escribir(v / "features" / f"Feature-{fid}.md", cuerpo)

    # --- lecciones (son SKILLS de Hermes, no archivos del repo) ---
    from leccion import buscar as buscar_leccion
    clases = sorted({c for c in map(leccion_de, data["features"]) if c})
    for clase in clases:
        usada = [f"- {feature(x['id'])}" for x in data["features"]
                 if leccion_de(x) == clase]
        sm = buscar_leccion(clase)
        origen = (f"Skill de Hermes: `{clase}`" if sm
                  else f"**FALTA**: la skill `{clase}` no esta instalada aqui")
        # slugify: el valor viene del backlog sin sanitizar y Path resuelve '..',
        # asi que una leccion '../../../README' pisaba archivos del repo.
        destino = (v / "lecciones" / f"{slugify(clase)}.md").resolve()
        if not str(destino).startswith(str((v / "lecciones").resolve()) + os.sep):
            raise SystemExit(f"[!!] leccion con ruta fuera del vault: {clase!r}")
        escribir(destino, [
            "---", "tipo: leccion", "tags: [harness, leccion]", "---", AVISO, "",
            f"# {esc(clase)}", "",
            origen, "",
            "_Vive en tus skills de Hermes y viaja contigo entre proyectos;",
            "aqui solo queda la traza de donde se aplico._", "",
            "## Usada en", "",
            *(usada or ["_todavia no se declaro en ningun cierre_"]),
        ])

    # --- servicios: repos de las raices + lo que nombra el backlog ---
    # Cada nombre que una feature enlaza tiene su nota, sea o no un repo que se
    # encuentre en disco: un enlace sin nota es un callejon sin salida.
    servicios: dict[str, dict] = {}
    for nombre, rutas in repos_de_las_raices(p).items():
        s = servicios.setdefault(nota(nombre), {"nombre": nombre, "rutas": [], "features": []})
        s["rutas"] += rutas
    for x in data["features"]:
        for m in micros_declarados(x):
            s = servicios.setdefault(nota(m), {"nombre": m, "rutas": [], "features": []})
            s["features"].append(f"- {feature(x['id'])}")
    for clave, s in sorted(servicios.items()):
        repo = [f"Repo: `{r}/`" for r in s["rutas"]] or [
            "_No es un repo git de ninguna raiz declarada: lo nombra el backlog._"]
        escribir(v / "servicios" / f"{clave}.md", [
            "---", "tipo: microservicio", "tags: [harness, servicio]", "---", AVISO, "",
            f"# {esc(s['nombre'])}", "", *repo, "", "## Features que lo tocan", "",
            *(s["features"] or ["_ninguna registrada_"]),
        ])

    # --- nodos del grafo (opt-in: genera muchos archivos) ---
    con_grafo = a.con_grafo and p["graph"].exists()
    if con_grafo:
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
            links = [f"- {rel} " + enlace("vault/grafo/" + (
                         slugify(esc(por_id.get(o, {}).get("label") or o))[:60] or "nodo"))
                     for rel, o in vecinos.get(nid, [])[:40]]
            escribir(gd / f"{nombre}.md", [
                "---", "tipo: nodo", f"comunidad: {n.get('community_name') or n.get('community','')}",
                "tags: [grafo]", "---", AVISO, "",
                f"# {lbl}", "", f"Tipo: `{n.get('type','')}`",
                f"Fuente: `{n.get('source_file','')}`", "", "## Conexiones", "",
                *(links or ["_sin aristas_"]),
            ])

    # --- indice ---
    abiertas = [f for f in data["features"] if f.get("status") not in ("done", "superseded")]
    escribir(v / "Indice.md", [
        "---", "tipo: indice", "tags: [harness]", "---", AVISO, "",
        f"# {esc(proyecto)}", "", f"Actualizado: {now_iso()}", "",
        f"- Features: {len(data['features'])} ({len(abiertas)} abiertas)",
        f"- Microservicios: {len(servicios)}",
        f"- Lecciones aplicadas: {len(clases)}",
        "", "## En curso", "",
        *([f"- {feature(f['id'])} — {esc(f.get('name',''))} ({f.get('status')})"
           for f in abiertas] or ["_nada abierto_"]),
        "", "## Microservicios", "",
        *[f"- {enlace('vault/servicios/' + clave)}" for clave in sorted(servicios)],
    ])

    # --- lo generado que ya no corresponde (feature borrada, servicio que
    # cambio de nombre): quedaba para siempre, sin nada que lo enlace. Solo se
    # borra lo que lleva el aviso; grafo/ solo cuando esta corrida lo reescribio.
    borradas = 0
    for d in ["features", "lecciones", "servicios"] + (["grafo"] if con_grafo else []):
        for viejo in (v / d).glob("*.md"):
            if viejo.resolve() not in escritas and \
                    AVISO in viejo.read_text(encoding="utf-8", errors="replace"):
                viejo.unlink()
                borradas += 1

    print(f"[ok] vault regenerado: {len(escritas)} notas en {v}"
          + (f" ({borradas} obsoletas borradas)" if borradas else ""))
    if cfg_nuevos:
        print(f"[ok] config de Obsidian sembrada ({cfg_nuevos} archivos en docs/.obsidian/)")
        if cfg_primera:
            print("[i]  tema oscuro, grafo coloreado por carpeta y wikilinks cortos.")
            print("[i]  Dataview queda habilitado: instalalo en Obsidian ->")
            print("     Settings > Community plugins > Browse > Dataview.")
    if (v / ".obsidian").is_dir():
        print(f"[i]  {v / '.obsidian'} es de cuando el vault era docs/vault/.\n"
              "     Abre docs/ en Obsidian y borra esa carpeta.")
    print(f"[i]  abrelo en Obsidian con 'Open folder as vault' -> {p['docs']}")


if __name__ == "__main__":
    main()
