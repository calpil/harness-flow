#!/usr/bin/env python3
"""Mecanismo 1 (Feedback Loop): los AC de verificacion manual los comprueba primero el agente.

Un AC que la lista de tests cubre solo con `verificacion manual` no lo mide
ningun test. Antes iba directo al usuario por formulario, y `close` cerraba sin
constancia de que alguien lo hubiera mirado. Ahora el agente lo comprueba en la
aplicacion (el Feature Map dice como llegar: `feature_map.py buscar`) y deja la
evidencia. Al usuario le llegan solo los que el agente no pudo comprobar.

  comprobacion.py pendientes --feature <id>
  comprobacion.py registrar --feature <id> --ac AC-n --resultado ok|falla|no-pude \
        --como '<que hice en la app>' --observado '<que vi>' --evidencia <archivo>
  comprobacion.py registrar --feature <id> --ac AC-n --resultado ok|falla \
        --usuario --yes --por <nombre> [--observado '<que dijo>']

- El agente registra que hizo, que vio y un archivo de evidencia (la captura, la
  salida del comando o la respuesta). Queda su huella, no el archivo.
- Lo que no pudo comprobar se registra con `--resultado no-pude` y va al usuario
  en UN formulario. Su respuesta se registra con `--usuario --yes --por`; el
  agente no puede registrar por el usuario.
- `gate.py close` exige una comprobacion `ok` por cada AC solo manual, en las
  features cuyo spec se aprobo con la regla (`autocomprobacion` en el backlog).
  Una comprobacion anterior a una enmienda del spec no vale.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import (  # noqa: E402
    bitacora, enmiendas_posteriores, get_feature, load_backlog, n_enmiendas, now_iso, paths,
    save_backlog, sign, spec_acs, spec_path, tests_path,
)

# La regla entra con la primera aprobacion del spec (gate.py approve-spec): a una
# feature en curso no se le cambia a mitad de camino. La usa tambien feature_map.py.
MARCA = "autocomprobacion"
RESULTADOS = ("ok", "falla", "no-pude")
_COMENTARIO_RE = re.compile(r"<!--.*?-->", re.S)
_ITEM_RE = re.compile(r"^[^\S\n]*[-*][^\S\n]*(AC-\d+)[^\S\n]*:[^\S\n]*(\S[^\n]*)$", re.M)


def _normal(texto: str) -> str:
    plano = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return " ".join(plano.lower().split())


def acs_solo_manuales(lista: str) -> list[str]:
    """AC que la lista de tests cubre SOLO con `verificacion manual`: ningun test los mide."""
    por_ac: dict[str, list[str]] = {}
    for ac, nombre in _ITEM_RE.findall(_COMENTARIO_RE.sub("", lista)):
        por_ac.setdefault(ac, []).append(nombre)
    return [ac for ac, nombres in por_ac.items()
            if all(_normal(n).startswith("verificacion manual") for n in nombres)]


def _lista(p: dict, f: dict) -> str:
    tp = tests_path(p, f)
    return tp.read_text(encoding="utf-8") if tp.is_file() else ""


def estado_ac(f: dict, ac: str) -> tuple[str, str]:
    """(estado, explicacion) de la comprobacion de un AC manual: ok | falla | usuario | pendiente."""
    c = (f.get("comprobaciones") or {}).get(ac)
    if not isinstance(c, dict):
        return "pendiente", "nadie lo comprobo"
    if enmiendas_posteriores(f, c.get("enmiendas")):
        return "pendiente", "se comprobo antes de la ultima enmienda del spec"
    quien = "el usuario" if c.get("quien") == "usuario" else "el agente"
    if c.get("resultado") == "ok":
        return "ok", f"comprobado por {quien} ({c.get('at')})"
    if c.get("resultado") == "falla":
        return "falla", f"la comprobacion de {quien} FALLO: {c.get('observado') or '-'}"
    return "usuario", f"el agente no pudo comprobarlo ({c.get('como') or '-'})"


def fallos_de_cierre(p: dict, f: dict) -> list[str]:
    """Por que close no acepta los AC de verificacion manual de la feature."""
    if not f.get(MARCA):
        return []
    orden = f"comprobacion.py registrar --feature {f['id']} --ac"
    fallos = []
    for ac in acs_solo_manuales(_lista(p, f)):
        estado, por_que = estado_ac(f, ac)
        if estado == "pendiente":
            fallos.append(f"feedback-loop: {ac} es de verificacion manual y {por_que}: compruebalo TU en la "
                          f"aplicacion (feature_map.py buscar) y registralo ({orden} {ac} --resultado ok "
                          "--como ... --observado ... --evidencia <archivo>)")
        elif estado == "falla":
            fallos.append(f"feedback-loop: {ac}: {por_que}. Corrige y vuelve a comprobar")
        elif estado == "usuario":
            fallos.append(f"feedback-loop: {ac}: {por_que}. Pidele al usuario que lo mire (un formulario con "
                          f"todos los pendientes) y registra su respuesta ({orden} {ac} --resultado ok "
                          "--usuario --yes --por <su nombre>)")
    return fallos


def lineas_brief(p: dict, f: dict) -> list[str]:
    """Para el bloque FEATURE MAP Y FEEDBACK LOOP del brief: a quien le toca cada AC manual."""
    import normas
    manuales = acs_solo_manuales(_lista(p, f))
    base = normas.comando("comprobacion.py", "registrar", "--feature", str(f["id"]), "--ac", "<AC-n>",
                          "--resultado", "ok", "--como", "<que hice>", "--observado", "<que vi>",
                          "--evidencia", "<archivo>")
    if manuales:
        cabeza = f"  AC de verificacion manual ({', '.join(manuales)}): compruebalos TU primero en la app y registra cada uno: "
    else:
        cabeza = "  AC de verificacion manual: si la lista de tests deja alguno, compruebalo TU primero en la app y registralo: "
    return [cabeza + base,
            "  al usuario le llegan, en UN formulario, solo los que no pudiste comprobar (--resultado no-pude); "
            "su respuesta se registra con --usuario --yes --por <su nombre>. \"Listo\" se dice despues de verlo "
            "funcionar."]


def cmd_pendientes(args) -> None:
    p = paths()
    f = get_feature(load_backlog(p), args.feature)
    manuales = acs_solo_manuales(_lista(p, f))
    if not manuales:
        print(f"[i]  la lista de tests de #{f['id']} no deja ningun AC solo con verificacion manual")
        return
    for ac in manuales:
        estado, por_que = estado_ac(f, ac)
        marca = {"ok": "[ok]", "falla": "[!!]", "usuario": "[usuario]", "pendiente": "[ ]"}[estado]
        print(f"  {marca} {ac}: {por_que}")
    if not f.get(MARCA):
        print("[i]  el spec de esta feature se aprobo antes de la regla: close no exige estas comprobaciones")


def cmd_registrar(args) -> None:
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, args.feature)
    sp = spec_path(p, f)
    acs = spec_acs(sp.read_text(encoding="utf-8")) if sp.is_file() else []
    if args.ac not in acs:
        sys.exit(f"[!!] {args.ac} no es un AC del spec de #{f['id']} ({', '.join(acs) or 'sin spec'})")
    registro = {"resultado": args.resultado, "como": (args.como or "").strip(),
                "observado": (args.observado or "").strip(), "at": now_iso(), "enmiendas": n_enmiendas(f)}
    if args.usuario:
        if args.resultado == "no-pude":
            sys.exit("[!!] --usuario registra lo que el usuario vio: ok o falla")
        quien = (args.por or "").strip()
        if not args.yes or not quien:
            sys.exit("[!!] la respuesta del usuario se registra con su SI: --usuario --yes --por <su nombre>.\n"
                     "     PREGUNTALE con un formulario que vio; no la registres por el.")
        registro.update(quien="usuario", por=quien)
    else:
        if args.yes or args.por:
            sys.exit("[!!] --yes y --por son del usuario: usalos con --usuario")
        if not registro["como"]:
            sys.exit("[!!] falta --como: que hiciste en la aplicacion (o por que no pudiste)")
        if args.resultado != "no-pude":
            if not registro["observado"]:
                sys.exit("[!!] falta --observado: que viste en la aplicacion")
            if not args.evidencia:
                sys.exit("[!!] falta --evidencia <archivo>: la captura, la salida del comando o la "
                         "respuesta que viste. Una comprobacion sin evidencia es una afirmacion.")
            evidencias = []
            for e in args.evidencia:
                ruta = Path(e).expanduser().resolve()
                if not ruta.is_file() or ruta.stat().st_size == 0:
                    sys.exit(f"[!!] la evidencia no existe o esta vacia: {e}")
                evidencias.append(sign(ruta))
            registro["evidencia"] = evidencias
        registro["quien"] = "agente"
    f.setdefault("comprobaciones", {})[args.ac] = registro
    save_backlog(p, data)
    quien = f"el usuario ({registro['por']})" if args.usuario else "el agente"
    bitacora(p, f"comprobacion #{f['id']} {args.ac}: {args.resultado} por {quien}")
    print(f"[ok] {args.ac} de #{f['id']}: {args.resultado} (por {quien})")
    if args.resultado == "falla":
        print("[i]  Corrige y vuelve a comprobar. Tras dos intentos sin verde es la parada (4): pregunta.")
    elif args.resultado == "no-pude":
        print("[i]  Junta los AC que no pudiste comprobar y pidele al usuario, en UN formulario, que los mire.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Los AC de verificacion manual los comprueba primero el agente")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("pendientes"); s.add_argument("--feature", required=True); s.set_defaults(fn=cmd_pendientes)
    s = sub.add_parser("registrar")
    s.add_argument("--feature", required=True)
    s.add_argument("--ac", required=True)
    s.add_argument("--resultado", required=True, choices=RESULTADOS)
    s.add_argument("--como", help="que se hizo en la aplicacion")
    s.add_argument("--observado", help="que se vio")
    s.add_argument("--evidencia", action="append", help="captura, salida o respuesta (repetible)")
    s.add_argument("--usuario", action="store_true", help="lo que respondio el usuario")
    s.add_argument("--yes", action="store_true")
    s.add_argument("--por")
    s.set_defaults(fn=cmd_registrar)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
