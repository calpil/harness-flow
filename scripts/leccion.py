#!/usr/bin/env python3
"""Memoria procedural por CLASE de trabajo (nunca por id de feature).

  leccion.py list
  leccion.py usar <clase>
  leccion.py nueva <clase> --titulo "..."
  leccion.py partir <clase> [--aplicar]
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import load_backlog, now_iso, paths  # noqa: E402

PLANTILLA = """# {titulo}

Clase de trabajo: {clase}

## Cuando aplica

<!-- El disparador: como reconoces que estas en esta clase de trabajo. -->

## Reglas

- <regla imperativa> — <por que>

## Referencias

<!-- El detalle por feature va en referencias/<tema>.md, no aqui. -->
"""


def dir_lecciones(p):
    d = p["lecciones"]; d.mkdir(parents=True, exist_ok=True); return d


def cmd_list(args) -> None:
    p = paths()
    d = dir_lecciones(p)
    tope = int(load_backlog(p)["rules"].get("leccion_max_lineas", 250))
    archivos = sorted(d.glob("*.md"))
    if not archivos:
        print("[i]  sin lecciones todavia. La primera se escribe al cerrar una feature.")
        return
    print(f"Lecciones ({len(archivos)}), tope {tope} lineas:\n")
    for f in archivos:
        n = len(f.read_text(encoding="utf-8").splitlines())
        titulo = next((l[2:] for l in f.read_text(encoding="utf-8").splitlines()
                       if l.startswith("# ")), f.stem)
        marca = "  <- SOBRE EL TOPE: parte antes de usarla" if n > tope else ""
        refs = len(list((d / f.stem / "referencias").glob("*.md"))) if (d / f.stem).exists() else 0
        print(f"   {f.stem:<45} {n:>4} lineas" +
              (f", {refs} refs" if refs else "") + marca)
        print(f"      {titulo}")
    print("\n[i]  PATCHEA la que estuvo en juego antes de crear otra.")


def cmd_usar(args) -> None:
    p = paths()
    f = dir_lecciones(p) / f"{args.clase}.md"
    if not f.exists():
        sys.exit(f"[!!] no existe {f}")
    tope = int(load_backlog(p)["rules"].get("leccion_max_lineas", 250))
    txt = f.read_text(encoding="utf-8")
    n = len(txt.splitlines())
    if n > tope:
        sys.exit(f"[!!] {args.clase} tiene {n} lineas (tope {tope}).\n"
                 "     Mueve el detalle a referencias/<tema>.md antes de usarla:\n"
                 f"     leccion.py partir {args.clase}")
    print(txt)


def cmd_nueva(args) -> None:
    p = paths()
    f = dir_lecciones(p) / f"{args.clase}.md"
    if f.exists():
        sys.exit(f"[!!] ya existe {f}. PATCHEALA en vez de crear otra.")
    f.write_text(PLANTILLA.format(titulo=args.titulo or args.clase, clase=args.clase),
                 encoding="utf-8")
    print(f"[ok] {f}")


def cmd_partir(args) -> None:
    p = paths()
    f = dir_lecciones(p) / f"{args.clase}.md"
    if not f.exists():
        sys.exit(f"[!!] no existe {f}")
    lines = f.read_text(encoding="utf-8").splitlines()
    tope = int(load_backlog(p)["rules"].get("leccion_max_lineas", 250))
    if len(lines) <= tope:
        print(f"[ok] {args.clase}: {len(lines)} lineas, bajo el tope ({tope}). Nada que partir.")
        return
    secciones = [(i, l) for i, l in enumerate(lines) if l.startswith("## ")]
    print(f"[!] {args.clase}: {len(lines)} lineas, {len(lines)-tope} sobre el tope.")
    print("    Secciones candidatas a mover a referencias/:")
    for i, (idx, titulo) in enumerate(secciones):
        fin = secciones[i+1][0] if i+1 < len(secciones) else len(lines)
        print(f"      {titulo[3:]:<50} {fin-idx:>4} lineas")
    print("\n[i]  esto informa; mover el detalle es decision tuya (y del usuario).")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    s = sub.add_parser("usar"); s.add_argument("clase"); s.set_defaults(fn=cmd_usar)
    s = sub.add_parser("nueva"); s.add_argument("clase"); s.add_argument("--titulo")
    s.set_defaults(fn=cmd_nueva)
    s = sub.add_parser("partir"); s.add_argument("clase")
    s.add_argument("--aplicar", action="store_true"); s.set_defaults(fn=cmd_partir)
    a = ap.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
