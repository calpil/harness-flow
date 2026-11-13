#!/usr/bin/env python3
"""Hallazgos: lo que se encuentra en el codigo mientras se trabaja en otra cosa.

Un hallazgo no abre una ficha. Cada ficha paga spec, lista de tests, review,
verify y cierre; un hallazgo se anota aqui y se resuelve DENTRO de una feature:
como AC antes de sellar el spec, como enmienda despues, o en la rama si no
cambia ningun AC. Una ficha nueva la decide el usuario (add.py --yes).

  hallazgo.py anotar --texto "..." [--feature <id>] [--microservicio m] [--origen "review de la #191"]
  hallazgo.py list [--feature <id>] [--todos]
  hallazgo.py mover --id H-3 (--feature <id> | --sin-feature)
  hallazgo.py resolver --id H-3 --como "E-1 de la #180"

Viven en `hallazgos` del backlog. Con --feature quedan en esa feature y `close`
se niega mientras sigan abiertos; sin --feature quedan en el proyecto, y el
brief de cada feature muestra los que tocan sus repos.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (bitacora, get_feature, load_backlog, micros_declarados, now_iso,  # noqa: E402
                   paths, save_backlog)

ABIERTAS = ("todo", "pending", "in_progress", "blocked", "review")
ABIERTO, RESUELTO = "abierto", "resuelto"
TOPE_TEXTO = 400


def todos(data: dict) -> list[dict]:
    return [h for h in data.get("hallazgos") or [] if isinstance(h, dict)]


def abiertos(data: dict) -> list[dict]:
    return [h for h in todos(data) if h.get("estado") == ABIERTO]


def de_la_feature(data: dict, fid) -> list[dict]:
    """Los hallazgos abiertos anotados en una feature."""
    return [h for h in abiertos(data) if str(h.get("feature")) == str(fid)]


def del_proyecto(data: dict, micros: list[str] | None = None) -> list[dict]:
    """Los hallazgos abiertos sin feature. Con `micros`, los que tocan esos repos
    y los que no declaran ninguno (pueden tocar cualquiera)."""
    sueltos = [h for h in abiertos(data) if h.get("feature") is None]
    if micros is None:
        return sueltos
    return [h for h in sueltos
            if not h.get("microservicios") or set(h["microservicios"]) & set(micros)]


def fila(h: dict) -> str:
    marcas = [x for x in (", ".join(h.get("microservicios") or []), h.get("origen")) if x]
    return f"{h['id']}" + (f" [{' · '.join(marcas)}]" if marcas else "") + f" {h['texto']}"


def features_donde_cabe(data: dict, micros: list[str], reqs: list[str], tope: int = 8) -> list[dict]:
    """Features abiertas donde un hallazgo puede entrar: las que nombra `reqs`,
    las que comparten un repo y, si no hay ninguna, todas las abiertas."""
    vivas = [f for f in data["features"] if f.get("status") in ABIERTAS]
    nombradas = {r.lstrip("#") for r in reqs if r.startswith("#")}
    primero = [f for f in vivas if str(f.get("id")) in nombradas]
    cerca = primero + [f for f in vivas if f not in primero
                       and micros and set(micros) & set(micros_declarados(f))]
    return (cerca or vivas)[:tope]


def lineas_brief(data: dict, f: dict, micros: list[str]) -> list[str]:
    """Lo que quien escribe el spec o implementa tiene que resolver aqui."""
    import normas
    suyos = de_la_feature(data, f["id"])
    sueltos = del_proyecto(data, micros) if micros else []
    if not suyos and not sueltos:
        return []
    L = [""]
    if suyos:
        L.append(f"HALLAZGOS ANOTADOS EN ESTA FEATURE ({len(suyos)} abiertos): se resuelven AQUI, "
                 "sin ficha nueva; close se niega mientras sigan abiertos")
        L += [f"  {fila(h)}" for h in suyos]
        if f.get("last_spec_sig"):
            L.append("  spec ya sellado: si cambia un AC es una enmienda (templates/enmienda.md, "
                     "gate.py enmienda); si no cambia ninguno, arreglalo en la rama y citalo en la evidencia")
        else:
            L.append("  spec sin sellar: escribe cada uno como AC o en el plan antes de pedir la aprobacion")
        L.append("  al resolver: " + normas.comando("hallazgo.py", "resolver", "--id", "<H-n>",
                                                   "--como", "<AC-n, E-n o commit>"))
    if sueltos:
        L.append(f"hallazgos del proyecto sin feature que tocan estos repos ({len(sueltos)}): "
                 "si tu cambio pasa por ahi, traelo a esta feature")
        L += [f"  {fila(h)}" for h in sueltos[:8]]
        if len(sueltos) > 8:
            L.append(f"  ... y {len(sueltos) - 8} mas: hallazgo.py list")
        L.append("  para traer uno: " + normas.comando("hallazgo.py", "mover", "--id", "<H-n>",
                                                      "--feature", str(f["id"])))
    return L


def linea_estado(data: dict) -> str | None:
    """Una linea para el arranque de sesion."""
    vivos = abiertos(data)
    if not vivos:
        return None
    por_feature: dict[str, int] = {}
    for h in vivos:
        if h.get("feature") is not None:
            por_feature[str(h["feature"])] = por_feature.get(str(h["feature"]), 0) + 1
    sueltos = sum(h.get("feature") is None for h in vivos)
    partes = [f"#{fid} ({n})" for fid, n in por_feature.items()]
    if sueltos:
        partes.append(f"sin feature ({sueltos})")
    return (f"{len(vivos)} abiertos: {', '.join(partes)}. Se resuelven dentro de una feature, "
            "no con fichas nuevas (hallazgo.py list)")


def _una_linea(valor: str, nombre: str) -> str:
    limpio = (valor or "").strip()
    if not limpio:
        sys.exit(f"[!!] {nombre} no puede quedar vacio")
    if any(c in limpio for c in "\n\r\x85  ") or len(limpio) > TOPE_TEXTO:
        sys.exit(f"[!!] {nombre} va en una sola linea de hasta {TOPE_TEXTO} caracteres: "
                 "el detalle va en el spec o en la propuesta de enmienda")
    return limpio


def _feature_abierta(data: dict, fid) -> dict:
    f = get_feature(data, fid)
    if f.get("status") not in ABIERTAS:
        sys.exit(f"[!!] la feature #{f['id']} esta en '{f.get('status')}': una feature cerrada no "
                 "recibe hallazgos.\n"
                 "     Anotalo en una feature abierta que toque ese codigo, o sin --feature para\n"
                 "     dejarlo en el proyecto. Una ficha nueva la decide el usuario.")
    return f


def _buscar(data: dict, hid: str) -> dict:
    for h in todos(data):
        if str(h.get("id", "")).upper() == hid.strip().upper():
            return h
    sys.exit(f"[!!] no existe el hallazgo {hid} (hallazgo.py list --todos)")


def _normal(texto: str) -> str:
    return re.sub(r"\W+", " ", texto.lower()).strip()


def cmd_anotar(args) -> None:
    p = paths()
    data = load_backlog(p)
    texto = _una_linea(args.texto, "--texto")
    f = _feature_abierta(data, args.feature) if args.feature is not None else None
    for h in abiertos(data):
        if _normal(h.get("texto", "")) == _normal(texto):
            sys.exit(f"[!!] ya esta anotado como {h['id']}"
                     + (f" en la #{h['feature']}" if h.get("feature") is not None else " en el proyecto"))
    n = max([int(m.group(1)) for h in todos(data)
             if (m := re.fullmatch(r"H-(\d+)", str(h.get("id", ""))))] or [0]) + 1
    h = {"id": f"H-{n}", "feature": f["id"] if f else None,
         "microservicios": list(args.microservicio), "texto": texto,
         "estado": ABIERTO, "at": now_iso()}
    if args.origen:
        h["origen"] = _una_linea(args.origen, "--origen")
    data.setdefault("hallazgos", []).append(h)
    save_backlog(p, data)
    donde = f"la #{f['id']} '{f.get('name')}'" if f else "el proyecto (sin feature)"
    bitacora(p, f"hallazgo {h['id']} anotado en {donde}: {texto}")
    print(f"[ok] {h['id']} anotado en {donde}")
    if f:
        print("[i]  se resuelve dentro de esa feature: como AC si el spec no esta sellado, como\n"
              "     enmienda si lo esta y cambia un AC, o en la rama si no cambia ninguno.")
    else:
        print("[i]  el brief de cada feature que toque esos repos lo va a mostrar. Si junta peso\n"
              "     con otros, el USUARIO decide si pasan a una sola ficha.")


def cmd_list(args) -> None:
    data = load_backlog(paths())
    filas = todos(data) if args.todos else abiertos(data)
    if args.feature is not None:
        filas = [h for h in filas if str(h.get("feature")) == str(args.feature)]
    if not filas:
        print("sin hallazgos" + ("" if args.todos else " abiertos"))
        return
    grupos: dict[str, list[dict]] = {}
    for h in filas:
        grupos.setdefault("sin feature" if h.get("feature") is None else f"#{h['feature']}", []).append(h)
    nombres = {str(f.get("id")): f.get("name") for f in data["features"]}
    for grupo, hs in grupos.items():
        print(grupo + (f" {nombres.get(grupo[1:], '')}" if grupo.startswith("#") else ""))
        for h in hs:
            cola = f"  -> resuelto: {h.get('como')}" if h.get("estado") == RESUELTO else ""
            print(f"  {fila(h)}{cola}")


def cmd_mover(args) -> None:
    p = paths()
    data = load_backlog(p)
    h = _buscar(data, args.id)
    if h.get("estado") != ABIERTO:
        sys.exit(f"[!!] {h['id']} ya esta resuelto ({h.get('como')})")
    f = None if args.sin_feature else _feature_abierta(data, args.feature)
    h["feature"] = f["id"] if f else None
    save_backlog(p, data)
    donde = f"la #{f['id']}" if f else "el proyecto (sin feature)"
    bitacora(p, f"hallazgo {h['id']} movido a {donde}")
    print(f"[ok] {h['id']} ahora esta en {donde}")


def cmd_resolver(args) -> None:
    p = paths()
    data = load_backlog(p)
    h = _buscar(data, args.id)
    if h.get("estado") != ABIERTO:
        sys.exit(f"[!!] {h['id']} ya esta resuelto ({h.get('como')})")
    h.update(estado=RESUELTO, como=_una_linea(args.como, "--como"), resuelto_at=now_iso())
    save_backlog(p, data)
    bitacora(p, f"hallazgo {h['id']} resuelto: {h['como']}")
    print(f"[ok] {h['id']} resuelto: {h['como']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("anotar", help="anota un hallazgo en una feature abierta o en el proyecto")
    s.add_argument("--texto", required=True)
    s.add_argument("--feature")
    s.add_argument("--microservicio", action="append", default=[])
    s.add_argument("--origen", help="de donde salio: 'review de la #191', 'al implementar la #188'")
    s.set_defaults(fn=cmd_anotar)
    s = sub.add_parser("list", help="hallazgos abiertos por feature")
    s.add_argument("--feature")
    s.add_argument("--todos", action="store_true", help="incluye los resueltos")
    s.set_defaults(fn=cmd_list)
    s = sub.add_parser("mover", help="pasa un hallazgo a otra feature abierta o al proyecto")
    s.add_argument("--id", required=True)
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--feature")
    g.add_argument("--sin-feature", action="store_true")
    s.set_defaults(fn=cmd_mover)
    s = sub.add_parser("resolver", help="cierra un hallazgo diciendo donde quedo")
    s.add_argument("--id", required=True)
    s.add_argument("--como", required=True,
                   help="donde quedo: 'AC-3', 'E-1 de la #180', un commit, o 'descartado: <motivo>'")
    s.set_defaults(fn=cmd_resolver)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
