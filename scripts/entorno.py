#!/usr/bin/env python3
"""Detecta H (scripts de la skill) y PY (python de Hermes) en Windows/Linux/macOS.

Uso tipico al abrir sesion, sin hardcodear rutas por SO:

    eval "$(python <skill>/scripts/entorno.py --shell)"      # bash/zsh
    python <skill>/scripts/entorno.py --powershell | iex     # PowerShell

Sin flags imprime un diagnostico legible. Exit!=0 si algo no se pudo resolver.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ES_WINDOWS = os.name == "nt"


def scripts_dir() -> Path:
    """El directorio de scripts de ESTA skill (donde vive este archivo)."""
    return Path(__file__).resolve().parent


def hermes_home() -> Path | None:
    """Raiz de datos de Hermes (~/.hermes y equivalentes historicos)."""
    env = os.environ.get("HERMES_HOME")
    if env and Path(env).is_dir():
        return Path(env)
    # la skill vive en <hermes_home>/skills/<categoria>/harness-flow/scripts
    for padre in scripts_dir().parents:
        if padre.name == "skills" and padre.parent.is_dir():
            return padre.parent
    home = Path.home()
    candidatos = [
        home / ".hermes",
        home / "AppData" / "Local" / "hermes",                # Windows
        home / ".local" / "share" / "hermes",                 # Linux (XDG)
        home / "Library" / "Application Support" / "hermes",  # macOS
    ]
    for c in candidatos:
        if c.is_dir():
            return c
    return None


def _bin_python(venv: Path) -> Path:
    """bin/python en POSIX, Scripts/python.exe en Windows."""
    return venv / ("Scripts/python.exe" if ES_WINDOWS else "bin/python")


def _desde_launcher() -> Path | None:
    """Lee el interprete del launcher `hermes` del PATH (el mas fiable)."""
    launcher = shutil.which("hermes") or shutil.which("hermes-agent")
    if not launcher:
        return None
    try:
        texto = Path(launcher).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    for m in re.finditer(r'(?P<q>["\']?)(?P<ruta>[^"\'\s]*?(?:pythonw\.exe|python\.exe|python3(?:\.\d+)?|python))(?P=q)(?=[\s"\']|$)',
                         texto):
        cand = Path(os.path.expandvars(m.group("ruta"))).expanduser()
        if cand.is_absolute() and cand.exists():
            return cand
    return None


def python_hermes() -> Path | None:
    """El interprete donde viven las dependencias (psycopg), no el del sistema."""
    env = os.environ.get("HERMES_PYTHON")
    if env and Path(env).exists():
        return Path(env)
    # si ya estamos corriendo dentro del venv de Hermes, ese mismo sirve
    actual = Path(sys.executable)
    if tiene_psycopg(actual):
        return actual
    v = _desde_launcher()
    if v and v.exists():
        return v
    hh = hermes_home()
    if hh:
        for venv in (hh / "hermes-agent" / "venv", hh / "venv", hh / ".venv"):
            p = _bin_python(venv)
            if p.exists():
                return p
    return None


def tiene_psycopg(py: Path) -> bool:
    try:
        r = subprocess.run([str(py), "-c", "import psycopg"],
                           capture_output=True, timeout=30)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--shell", action="store_true", help="exports para bash/zsh (usar con eval)")
    g.add_argument("--powershell", action="store_true", help="asignaciones para PowerShell")
    ap.add_argument("--instalar-deps", action="store_true",
                    help="instala psycopg[binary] en el python de Hermes si falta")
    args = ap.parse_args()

    h = scripts_dir()
    py = python_hermes()

    if args.instalar_deps:
        if not py:
            print("[!!] no encuentro el python de Hermes; define HERMES_PYTHON", file=sys.stderr)
            return 1
        if tiene_psycopg(py):
            print(f"[ok] psycopg ya presente en {py}")
        else:
            r = subprocess.run([str(py), "-m", "pip", "install", "psycopg[binary]"])
            if r.returncode != 0:
                return r.returncode
            print(f"[ok] psycopg instalado en {py}")

    if args.shell:
        if not py:
            print("echo '[!!] no encuentro el python de Hermes; define HERMES_PYTHON' >&2",
                  file=sys.stdout)
            return 1
        print(f'export H="{h}"')
        print(f'export PY="{py}"')
        return 0

    if args.powershell:
        if not py:
            print("Write-Error '[!!] no encuentro el python de Hermes; define HERMES_PYTHON'")
            return 1
        print(f'$H = "{h}"')
        print(f'$PY = "{py}"')
        return 0

    so = "Windows" if ES_WINDOWS else sys.platform
    print(f"SO            : {so}")
    print(f"HERMES_HOME   : {hermes_home() or '(no encontrado)'}")
    print(f"H  (scripts)  : {h}")
    print(f"PY (python)   : {py or '(no encontrado)'}")
    if not py:
        print("\n[!!] sin python de Hermes: define HERMES_PYTHON con la ruta al interprete.")
        return 1
    ok = tiene_psycopg(py)
    print(f"psycopg       : {'ok' if ok else 'FALTA -> corre con --instalar-deps'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
