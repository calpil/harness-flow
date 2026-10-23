#!/usr/bin/env python3
"""Alta de feature en el backlog y creacion del spec en draft.

  add.py --name "cobro idempotente" [--kind bug|task] [--microservicio a --microservicio b]
         [--prd docs/prd/PRD-master.md] [--candidata F-1]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (bitacora, load_backlog, now_iso, paths, save_backlog,  # noqa: E402
                   slugify, spec_path)

TEMPLATE = Path(__file__).parent.parent / "templates" / "spec.md"


def plantilla() -> str:
    """El bloque ```markdown de templates/spec.md; el resto del archivo es la guia del formato."""
    m = re.search(r"^```markdown\n(.*?)^```[^\S\n]*$", TEMPLATE.read_text(encoding="utf-8"), re.M | re.S)
    if m is None:
        sys.exit(f"[!!] {TEMPLATE} no trae el bloque ```markdown del spec")
    return m.group(1)


def main() -> None:
    import producto
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--kind", choices=["feature", "bug", "task"], default="feature")
    ap.add_argument("--microservicio", action="append", default=[])
    ap.add_argument("--prd")
    ap.add_argument("--candidata", help="la F-n de '## Features candidatas' del PRD que origina la feature")
    ap.add_argument("--acceptance", action="append", default=[])
    a = ap.parse_args()

    p = paths()
    data = load_backlog(p)
    slug = slugify(a.name)
    for f in data["features"]:
        if slugify(f.get("name", "")) == slug and f.get("status") not in ("done", "superseded"):
            sys.exit(f"[!!] ya existe la feature #{f['id']} '{f['name']}' abierta con el mismo nombre.")

    prd = a.prd or "docs/prd/PRD-master.md"
    if a.prd and a.prd.replace("\\", "/").removeprefix("./") != "docs/prd/PRD-master.md":
        sys.exit("[!!] --prd solo puede ser docs/prd/PRD-master.md: es el unico cuerpo que sella "
                 "producto.py aprobar. Una candidata F-n no es otro archivo; su historia la cuenta el spec.")
    linea = None
    if a.candidata:
        if not re.fullmatch(r"F-\d+", a.candidata):
            sys.exit(f"[!!] --candidata {a.candidata!r}: usa el id del PRD, por ejemplo F-1")
        texto = producto.texto_manual(p["root"] / prd)
        if texto is None:
            sys.exit(f"[!!] --candidata {a.candidata} sin PRD con cuerpo en {prd}: el rol producto va antes")
        linea = producto.candidata(texto, a.candidata)
        if linea is None:
            sys.exit(f"[!!] {a.candidata} no esta en '## Features candidatas' de {prd}")
        otras = [x for x in data["features"]
                 if x.get("prd_candidata") == a.candidata and x.get("status") != "superseded"]
        if otras:
            print(f"[i]  {a.candidata} ya la cubre " + ", ".join(f"#{x['id']}" for x in otras)
                  + ": esta feature sera otra parte de la misma candidata")

    fid = max([int(f["id"]) for f in data["features"]] or [0]) + 1
    f = {"id": fid, "name": a.name, "kind": a.kind,
         "microservicios": a.microservicio, "acceptance": a.acceptance,
         "status": "todo", "created_at": now_iso()}
    if a.prd or a.candidata:
        f["prd"] = prd
    if a.candidata:
        f["prd_candidata"] = a.candidata
    data["features"].append(f)
    save_backlog(p, data)

    sp = spec_path(p, f)
    if not sp.exists():
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(plantilla().replace("{{ID}}", str(fid)).replace("{{NAME}}", a.name)
                      .replace("{{PRD}}", prd)
                      .replace("{{CANDIDATA}}", linea or "ninguna declarada"),
                      encoding="utf-8")
    bitacora(p, f"add #{fid} '{a.name}' ({a.kind})"
             + (f" candidata {a.candidata}" if a.candidata else ""))
    print(f"[ok] feature #{fid} agregada")
    print(f"[ok] spec en draft: {sp}")
    try:
        import gate
        pendientes = [] if a.kind not in producto.TIPOS_EXIGIDOS else [
            f"{doc}: {m}" for doc in producto.requeridos(data["rules"])
            if (m := gate.motivo_doc(p, data, doc))]
    except ValueError as exc:
        pendientes = [str(exc)]
    if pendientes:
        print("[!]  approve-spec se va a negar (require_docs_al_dia): " + "; ".join(pendientes))
        print("     el rol producto va antes: producto.py borrador --doc prd|sdd")
    print("[i]  completa la historia y los AC-n, cita los O-n del PRD y las D-n del SDD,")
    print(f"     MUESTRASELO al usuario y solo con su SI corre: gate.py approve-spec --feature {fid} --yes")


if __name__ == "__main__":
    main()
