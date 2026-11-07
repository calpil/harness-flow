#!/usr/bin/env python3
"""postmerge.py - RETIRADO como gate post-merge. Usa postmerge_medido.py.

Este gate deducia el veredicto de un regex sobre la salida `-v` de `go test` y
NUNCA leia el exit code: daba VERDE con un paquete que no compila, con un panic
en init() y con tests borrados; ademas identificaba los tests por nombre sin
paquete, asi que un rojo nuevo se confundia con deuda tolerada de otro.

Se niega a opinar (exit 2) tanto por CLI como si alguien importa main()/correr(),
en vez de mentir. El reemplazo medido es postmerge_medido.py:

  postmerge_medido.py base  --repo <ruta> --guardar <json>
  postmerge_medido.py check --repo <ruta> --base <json>
"""
import sys
from typing import NoReturn


def _retirado() -> NoReturn:
    print("[!!] postmerge.py esta RETIRADO como gate: da verdes falsos "
          "(build roto, panic en init, tests borrados).", file=sys.stderr)
    print("     Usa postmerge_medido.py, que mide en vez de adivinar:",
          file=sys.stderr)
    print("     postmerge_medido.py base  --repo <ruta> --guardar <json>",
          file=sys.stderr)
    print("     postmerge_medido.py check --repo <ruta> --base <json>",
          file=sys.stderr)
    sys.exit(2)


def correr(repo: str = "", cmd: str = "") -> NoReturn:
    """Stub retirado: rechaza correr y redirige a postmerge_medido.py."""
    _retirado()


def main() -> NoReturn:
    """Stub retirado: rechaza correr y redirige a postmerge_medido.py."""
    _retirado()


if __name__ == "__main__":
    main()

