#!/usr/bin/env python3
"""Alta de feature en el backlog y creacion del spec en draft.

  add.py --name "cobro idempotente" [--kind bug|task] [--microservicio a --microservicio b]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (bitacora, load_backlog, now_iso, paths, save_backlog,  # noqa: E402
                   slugify, spec_path)

TEMPLATE = Path(__file__).parent.parent / "templates" / "spec.md"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--kind", choices=["feature", "bug", "task"], default="feature")
    ap.add_argument("--microservicio", action="append", default=[])
    ap.add_argument("--prd")
    ap.add_argument("--acceptance", action="append", default=[])
    a = ap.parse_args()

    p = paths()
    data = load_backlog(p)
    slug = slugify(a.name)
    for f in data["features"]:
        if slugify(f.get("name", "")) == slug and f.get("status") not in ("done", "superseded"):
            sys.exit(f"[!!] ya existe la feature #{f['id']} '{f['name']}' abierta con el mismo nombre.")

    fid = max([int(f["id"]) for f in data["features"]] or [0]) + 1
    f = {"id": fid, "name": a.name, "kind": a.kind,
         "microservicios": a.microservicio, "acceptance": a.acceptance,
         "status": "todo", "created_at": now_iso()}
    if a.prd:
        f["prd"] = a.prd
    data["features"].append(f)
    save_backlog(p, data)

    sp = spec_path(p, f)
    if not sp.exists():
        tpl = TEMPLATE.read_text(encoding="utf-8")
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(tpl.replace("{{ID}}", str(fid)).replace("{{NAME}}", a.name)
                      .replace("{{SLUG}}", slug)
                      .replace("{{PRD}}", a.prd or "docs/prd/PRD-master.md"),
                      encoding="utf-8")
    bitacora(p, f"add #{fid} '{a.name}' ({a.kind})")
    print(f"[ok] feature #{fid} agregada")
    print(f"[ok] spec en draft: {sp}")
    print("[i]  completa la historia y los AC-n, MUESTRASELO al usuario y solo con")
    print(f"     su SI corre: gate.py approve-spec --feature {fid} --yes")


if __name__ == "__main__":
    main()
