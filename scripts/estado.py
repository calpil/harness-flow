#!/usr/bin/env python3
"""Panorama del proyecto: que hay abierto, que gate falta, que tan viejo esta el grafo."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (cubre_acs, enmiendas_posteriores, impl_path, load_backlog,  # noqa: E402
                   paths, review_path, sello_revision, sig_fresh, spec_acs,
                   spec_estado, spec_path)

ABIERTOS = ("todo", "pending", "in_progress", "blocked", "review")
CERRADOS = ("done", "superseded")


def main() -> None:
    p = paths()
    data = load_backlog(p)
    print(f"== {data.get('project','(sin nombre)')} == {p['root']}")

    reglas = [k for k, v in data["rules"].items() if k.startswith("require_") and v]
    print(f"   reglas activas: {', '.join(reglas) or 'ninguna'}")

    if p["graph"].exists():
        edad = (time.time() - p["graph"].stat().st_mtime) / 3600
        marca = "" if edad < 24 else "  <- viejo, corre: contexto.py refrescar"
        print(f"   grafo: {p['graph'].name}, {edad:.1f}h de antiguedad{marca}")
    else:
        print(f"   grafo: ausente en {p['graph']} (corre: contexto.py refrescar)")
    vault = "ok" if p["vault"].exists() else "ausente (vault.py build)"
    try:
        import contexto
        est = contexto.estado_contexto(p)
        vault = contexto._estado_vault(est)
        if len(est["raices"]) > 1:
            partes = []
            for r in est["raices"]:
                edad_r = "ausente" if not r["existe"] else f"{r['edad_h']:.1f}h"
                partes.append(f"{r['nombre']}={edad_r}")
            print("   raices del grafo: " + ", ".join(partes))
        if not est["fresco"]:
            print(f"   [!] contexto vencido ({', '.join(est['vencidas'])}): "
                  "corre contexto.py refrescar")
    except Exception as exc:
        print(f"   [!] no se pudo evaluar el contexto: {exc}")
    print(f"   vault: {vault}")
    print(f"   jira:  {'configurado' if p['atlassian'].exists() else 'sin binding'}")
    try:
        import producto
        for doc, texto in producto.estado_documentos(p, data).items():
            print(f"   {doc}:   {texto}")
    except Exception as exc:
        print(f"   [!] no se pudo evaluar PRD/SDD: {exc}")

    abiertas = [f for f in data["features"] if f.get("status") in ABIERTOS]
    # Un estado nuevo o ausente no prueba un cierre; nunca contar por descarte.
    cerradas = [f for f in data["features"] if f.get("status") in CERRADOS]
    desconocidas = [f for f in data["features"]
                   if f.get("status") not in ABIERTOS + CERRADOS]
    resumen = f"\n   features: {len(abiertas)} abiertas, {len(cerradas)} cerradas"
    desglose = ", ".join(f"{sum(f.get('status') == s for f in cerradas)} {s}"
                         for s in CERRADOS)
    resumen += f" ({desglose})"
    if desconocidas:
        resumen += f", {len(desconocidas)} con estado desconocido"
    print(resumen + "\n")

    for f in desconocidas:
        print(f"   [!] #{f['id']} [{f.get('status')}] {f.get('name')}: "
              "estado desconocido; revisa status en feature_list.json")

    if not abiertas:
        if desconocidas:
            print("   Revisa los estados desconocidos antes de iniciar otra feature.")
        else:
            print("   Nada en curso. Para arrancar: add.py --name '<nombre>'")
        return

    for f in abiertas:
        _fila(p, f)

    print("\nSiguiente paso sugerido:")
    en_curso = [f for f in abiertas if f.get("status") == "in_progress"]
    pendientes = [f for f in abiertas if f.get("status") in ("todo", "pending")]
    if en_curso:
        print(f"   retoma la feature #{en_curso[0]['id']} (ya esta in_progress)")
    elif pendientes:
        fid = pendientes[0]["id"]
        print(f"   arranca la #{fid}: worktree.py start --feature {fid}")
    else:
        print("   revisa las features blocked/review antes de iniciar otra.")


def _fila(p, f) -> None:
    fid = f["id"]
    sp = spec_path(p, f)
    marcas = []
    acs: list[str] = []
    if not sp.exists():
        marcas.append("sin spec")
    else:
        t = sp.read_text(encoding="utf-8")
        acs = spec_acs(t)
        est = spec_estado(t)
        if est != "approved":
            marcas.append(f"spec {est}")
        elif not sig_fresh(sp, f.get("last_spec_sig")):
            marcas.append("spec sello invalido")
        else:
            marcas.append(f"spec ok ({len(acs)} AC)")

    ip = impl_path(p, f)
    if ip.exists():
        _, faltan = cubre_acs(ip.read_text(encoding="utf-8"), acs)
        marcas.append("evidencia ok" if not faltan else f"faltan {len(faltan)} AC")
    else:
        marcas.append("sin evidencia")

    rp = review_path(p, f)
    if rp.exists():
        s = sello_revision(rp.read_text(encoding="utf-8"))
        tarde = enmiendas_posteriores(f, f.get("last_review_enmiendas")) if s else []
        marcas.append(f"review {s or 'sin sello'}"
                      + (f" (anterior a {', '.join(tarde)})" if tarde else ""))
    else:
        marcas.append("sin review")

    wt = f.get("worktree")
    marcas.append(f"wt {Path(wt).name}" if wt else "SIN worktree")
    print(f"   #{fid} [{f.get('status')}] {f.get('name')}")
    print(f"        {' · '.join(marcas)}")


if __name__ == "__main__":
    main()
