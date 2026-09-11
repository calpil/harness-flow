#!/usr/bin/env python3
"""Memoria procedural: vive en las SKILLS de Hermes, no en el repo.

Una leccion es una skill de Hermes por CLASE de trabajo (nunca por id de
feature). Asi viaja contigo entre proyectos y Hermes la carga sola cuando
aplica, en vez de quedarse enterrada en el docs/ de un repo.

  leccion.py list                skills disponibles (candidatas a leccion)
  leccion.py ver <clase>         imprime la skill
  leccion.py existe <clase>      exit 0 si existe (lo usa el gate de cierre)
  leccion.py donde               raiz de skills detectada
  leccion.py plantilla <clase>   esqueleto para pasarle a skill_manage

El AGENTE escribe y patchea las lecciones con skill_manage(), no este script:
crear los archivos a mano se salta la validacion de frontmatter de Hermes.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

TOPE_LINEAS = 250


def skills_root() -> Path:
    """Raiz de skills de Hermes, respetando perfil y sistema operativo."""
    env = os.environ.get("HERMES_SKILLS_DIR")
    if env:
        return Path(env)
    home = os.environ.get("HERMES_HOME")
    if home and (Path(home) / "skills").is_dir():
        return Path(home) / "skills"
    # esta skill vive dentro de la raiz: .../skills/<categoria>/harness-flow/scripts
    for padre in Path(__file__).resolve().parents:
        if padre.name == "skills":
            return padre
    candidatos = [
        Path.home() / "AppData" / "Local" / "hermes" / "skills",                # Windows
        Path.home() / ".local" / "share" / "hermes" / "skills",                 # Linux
        Path.home() / "Library" / "Application Support" / "hermes" / "skills",  # macOS
        Path.home() / ".hermes" / "skills",
    ]
    for c in candidatos:
        if c.is_dir():
            return c
    sys.exit("[!!] no encuentro la raiz de skills de Hermes.\n"
             "     Define HERMES_HOME o HERMES_SKILLS_DIR.")


def buscar(clase: str) -> Path | None:
    """La skill <clase>, con o sin categoria intermedia."""
    raiz = skills_root()
    directo = raiz / clase / "SKILL.md"
    if directo.exists():
        return directo
    for hit in sorted(raiz.glob("*/" + clase + "/SKILL.md")):
        return hit
    return None


def descripcion(skill_md: Path) -> str:
    for ln in skill_md.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if s.startswith("description:"):
            return s.split(":", 1)[1].strip().strip('"').strip("'")
    return ""


def cmd_list(args) -> None:
    raiz = skills_root()
    print("Skills en " + str(raiz) + "\n")
    encontradas = sorted(raiz.glob("*/*/SKILL.md")) + sorted(raiz.glob("*/SKILL.md"))
    vistos: set[str] = set()
    for sm in encontradas:
        nombre = sm.parent.name
        if nombre in vistos or nombre == "harness-flow":
            continue
        vistos.add(nombre)
        n = len(sm.read_text(encoding="utf-8").splitlines())
        marca = "  <- sobre el tope: muevele detalle a references/" if n > TOPE_LINEAS else ""
        cat = sm.parent.parent.name
        prefijo = "" if cat == raiz.name else cat + "/"
        print("   %-46s %4d lineas%s" % (prefijo + nombre, n, marca))
        d = descripcion(sm)
        if d:
            print("      " + d[:100])
    if not vistos:
        print("   (ninguna todavia)")
    print("\n[i]  PATCHEA con skill_manage la que estuvo en juego antes de crear otra.")


def cmd_ver(args) -> None:
    sm = buscar(args.clase)
    if not sm:
        sys.exit("[!!] no existe la skill '%s' en %s" % (args.clase, skills_root()))
    txt = sm.read_text(encoding="utf-8")
    n = len(txt.splitlines())
    if n > TOPE_LINEAS:
        print("[!] %s: %d lineas (tope %d). Mueve el detalle a references/<tema>.md.\n"
              % (args.clase, n, TOPE_LINEAS), file=sys.stderr)
    print(txt)


def cmd_existe(args) -> None:
    sm = buscar(args.clase)
    if not sm:
        sys.exit("[!!] la leccion '%s' no existe como skill de Hermes.\n"
                 "     Raiz: %s\n"
                 "     Creala con skill_manage(action='create', name='%s'), o cierra con\n"
                 "     --leccion ninguna --leccion-motivo '<por que>'."
                 % (args.clase, skills_root(), args.clase))
    print("[ok] %s -> %s" % (args.clase, sm))


def cmd_donde(args) -> None:
    print(skills_root())


PLANTILLA = """---
name: {clase}
description: "Use when <disparador en una linea>. <que hace>."
---

# {clase}

## Cuando aplica

<El disparador: como reconoces que estas en esta clase de trabajo.>

## Reglas

- <regla imperativa> - <por que>

## Referencias

<El detalle largo va en references/<tema>.md, no aqui.>
"""


def cmd_plantilla(args) -> None:
    print(PLANTILLA.format(clase=args.clase))
    print("[i]  pasalo a skill_manage(action='create', name='%s', content=...)"
          % args.clase, file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description="Lecciones = skills de Hermes")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    s = sub.add_parser("ver"); s.add_argument("clase"); s.set_defaults(fn=cmd_ver)
    s = sub.add_parser("existe"); s.add_argument("clase"); s.set_defaults(fn=cmd_existe)
    sub.add_parser("donde").set_defaults(fn=cmd_donde)
    s = sub.add_parser("plantilla"); s.add_argument("clase"); s.set_defaults(fn=cmd_plantilla)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
