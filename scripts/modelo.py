#!/usr/bin/env python3
"""Modelo Claude de los roles Producto y Leader: Fable 5.2 u Opus 5.5.

Lo elige el USUARIO en un formulario, una vez por feature (o por documento, en
el rol producto, que corre antes de que existan features). Queda en el backlog
y los turnos siguientes de ese rol lo reutilizan en vez de volver a preguntar.

  modelo.py ver    --feature <id> | --doc prd|sdd
  modelo.py elegir --feature <id> | --doc prd|sdd  --modelo fable|opus

Por que un script y no una linea en el comando: el `model` del frontmatter de
un comando es fijo, y ningun comando puede cambiar el modelo de la sesion; solo
el usuario, con /model. Aqui se guarda lo que eligio y se dice con que modelo y
esfuerzo tiene que correr el rol; si la sesion no coincide, el rol lo aplica por
el turno con /harness-flow:usar-opus o usar-fable, sin pedirle nada al usuario.
Los demas roles no pasan por aqui: Cierre y Revisor van en Opus 5.5 y el
Implementer en Sonnet 5.5 (references/modelos.md).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import bitacora, get_feature, load_backlog, paths, save_backlog  # noqa: E402

# El esfuerzo sale de la guia de cada modelo: Fable 5.2 se empieza en high (por
# encima la mejora es desigual y cuesta mas); Opus 5.5 trae medium por defecto y
# estos roles deciden mucho con pocos tokens, por eso xhigh.
MODELOS = {
    "fable": {"id": "claude-fable-5-2", "nombre": "Claude Fable 5.2", "effort": "high",
              "sube": "xhigh solo ante un riesgo concreto de arquitectura, migracion o concurrencia"},
    "opus": {"id": "claude-opus-5-5", "nombre": "Claude Opus 5.5", "effort": "xhigh", "sube": None},
}
DOCS = ("prd", "sdd")


def _clave(args) -> tuple[str, str]:
    if bool(args.feature) == bool(args.doc):
        sys.exit("[!!] indica --feature <id> o --doc prd|sdd (uno de los dos)")
    return ("doc", args.doc) if args.doc else ("feature", str(args.feature))


def elegido(data: dict, tipo: str, valor: str) -> str | None:
    if tipo == "doc":
        return (data.get("modelos_claude") or {}).get(valor)
    return get_feature(data, valor).get("modelo_claude")


def _esfuerzo_sesion() -> str | None:
    """El esfuerzo de la sesion de Claude Code, si el host lo expone."""
    return (os.environ.get("CLAUDE_EFFORT") or "").strip().lower() or None


def _instrucciones(alias: str) -> list[str]:
    m = MODELOS[alias]
    lineas = [f"modelo: {alias} ({m['nombre']}, {m['id']})",
              f"esfuerzo: {m['effort']}" + (f" ({m['sube']})" if m["sube"] else "")]
    sesion = _esfuerzo_sesion()
    if sesion is None:
        lineas.append("esfuerzo de la sesion: no se pudo leer; compruebalo antes de seguir")
    elif sesion == m["effort"]:
        lineas.append(f"esfuerzo de la sesion: {sesion} (coincide)")
    elif alias == "fable" and sesion == "xhigh":
        lineas.append("esfuerzo de la sesion: xhigh (solo se justifica ante un riesgo concreto; "
                      "si no lo hay, pide /effort high)")
    else:
        lineas.append(f"esfuerzo de la sesion: {sesion} (NO coincide con {m['effort']})")
    lineas.append(f"si la sesion no esta en {m['nombre']} con esfuerzo {m['effort']}: aplicalo tu, "
                  f"invocando /harness-flow:usar-{alias} (fija modelo y esfuerzo por este turno); "
                  "no le pidas /model ni /effort al usuario")
    return lineas


def cmd_ver(args) -> None:
    tipo, valor = _clave(args)
    data = load_backlog(paths())
    alias = elegido(data, tipo, valor)
    que = f"documento {valor}" if tipo == "doc" else f"feature #{valor}"
    if alias not in MODELOS:
        print(f"modelo: sin elegir para {que}")
        print("PREGUNTA al usuario en un formulario: Fable 5.2 u Opus 5.5. No elijas por el.")
        print(f"luego: modelo.py elegir {'--doc ' + valor if tipo == 'doc' else '--feature ' + valor}"
              " --modelo fable|opus")
        sys.exit(3)
    print(f"elegido para {que}:")
    for linea in _instrucciones(alias):
        print(f"  {linea}")


def cmd_elegir(args) -> None:
    tipo, valor = _clave(args)
    p = paths()
    data = load_backlog(p)
    previo = elegido(data, tipo, valor)
    if tipo == "doc":
        data.setdefault("modelos_claude", {})[valor] = args.modelo
        que = f"documento {valor}"
    else:
        get_feature(data, valor)["modelo_claude"] = args.modelo
        que = f"feature #{valor}"
    save_backlog(p, data)
    if previo != args.modelo:
        bitacora(p, f"modelo claude de {que}: {args.modelo}" + (f" (antes {previo})" if previo else ""))
    print(f"[ok] {que}: {MODELOS[args.modelo]['nombre']}")
    for linea in _instrucciones(args.modelo):
        print(f"  {linea}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nombre, fn in (("ver", cmd_ver), ("elegir", cmd_elegir)):
        s = sub.add_parser(nombre)
        s.add_argument("--feature")
        s.add_argument("--doc", choices=DOCS)
        if nombre == "elegir":
            s.add_argument("--modelo", required=True, choices=sorted(MODELOS))
        s.set_defaults(fn=fn)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
