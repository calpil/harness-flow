#!/usr/bin/env python3
"""Detecta host, H (scripts) y PY (Python) en Windows/Linux/macOS.

Uso tipico al abrir sesion, sin hardcodear rutas por SO:

    eval "$(python <skill>/scripts/entorno.py --shell)"      # bash/zsh
    python <skill>/scripts/entorno.py --powershell | iex     # PowerShell

Sin flags imprime un diagnostico legible. Exit!=0 si algo no se pudo resolver.
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ES_WINDOWS = os.name == "nt"


HOSTS_VALIDOS = ("hermes", "claude", "gpt", "codex", "gemini", "agy", "grok", "generic")

# GROK_AGENT lo pone el proceso de Grok. 0/false/off/no no cuentan: si no, un
# valor apagado seguido de la ruta del clone clasificaria la sesion como grok.
_MARCA_APAGADA = frozenset({"", "0", "false", "off", "no"})


def _canon_host(host: str) -> str:
    if host == "codex":
        return "gpt"
    if host == "agy":
        return "gemini"
    return host


def _marca_encendida(valor: str | None) -> bool:
    if valor is None:
        return False
    return valor.strip().lower() not in _MARCA_APAGADA


def _en_proceso_grok() -> bool:
    """True cuando este proceso es una sesion de Grok, no cuando el archivo vive ahi.

    El clone esta en ~/.hermes y Grok lo carga por symlink desde ~/.agents/skills.
    La ruta diria hermes o gpt. GROK_AGENT dice quien esta ejecutando.
    """
    return _marca_encendida(os.environ.get("GROK_AGENT"))


def host_agente() -> str:
    """Host de ejecucion, no necesariamente el dueno del archivo enlazado."""
    explicit = os.environ.get("HARNESS_HOST")
    if explicit:
        if explicit not in HOSTS_VALIDOS:
            raise ValueError("HARNESS_HOST debe ser " + ", ".join(HOSTS_VALIDOS))
        return _canon_host(explicit)
    # Antes que la ruta: Grok ejecuta el script del symlink o del clone.
    if _en_proceso_grok():
        return "grok"
    # No resolve(): un symlink en .grok, .gemini, .agents o .claude puede apuntar al clone de Hermes.
    for padre in Path(__file__).absolute().parents:
        if padre.name == "skills" and padre.parent.name == ".grok":
            return "grok"
    for padre in Path(__file__).absolute().parents:
        if padre.name == "skills" and (padre.parent.name == ".gemini" or padre.parent.parent.name == ".gemini"):
            return "gemini"
    for padre in Path(__file__).absolute().parents:
        if padre.name == "skills" and padre.parent.name == ".agents":
            return "gpt"
    if os.environ.get("CLAUDECODE") == "1" or os.environ.get("CLAUDE_CONFIG_DIR"):
        return "claude"
    for padre in Path(__file__).absolute().parents:
        if padre.name == "skills" and padre.parent.name == ".claude":
            return "claude"
    if os.environ.get("ANTIGRAVITY_AGENT") == "1" or os.environ.get("GEMINI_CLI"):
        return "gemini"
    if any(os.environ.get(k) for k in ("HERMES_HOME", "HERMES_PYTHON", "HERMES_SKILLS_DIR")):
        return "hermes"
    if _home_instalacion() is not None:
        return "hermes"
    return "generic"


def _home_instalacion() -> Path | None:
    for padre in Path(__file__).absolute().parents:
        if padre.name != "skills":
            continue
        home = padre.parent
        if home.name in (".hermes", "hermes") or (
            home.parent.name == "profiles" and home.parent.parent.name == ".hermes"
        ):
            return home
    return None


def scripts_dir() -> Path:
    """El directorio de scripts de ESTA skill (donde vive este archivo)."""
    return Path(__file__).resolve().parent


def hermes_home() -> Path | None:
    """Raiz de datos de Hermes (~/.hermes y equivalentes historicos)."""
    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env).expanduser().absolute()
    instalada = _home_instalacion()
    if instalada is not None:
        return instalada
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


def venv_neutro() -> Path:
    return Path(os.environ.get("HARNESS_VENV", str(Path.home() / ".harness-flow/venv"))).expanduser().absolute()


def python_harness() -> Path:
    """Python seleccionado; psycopg solo es necesario para el hub."""
    host = host_agente()
    env = os.environ.get("HARNESS_PYTHON")
    if env:
        py = Path(env).expanduser().absolute()
        if not py.is_file():
            raise ValueError("HARNESS_PYTHON no apunta a un archivo Python")
        return py
    actual = Path(sys.executable)
    neutral = _bin_python(venv_neutro())
    # Un venv neutro a medio instalar no debe ganarle a un interprete que si
    # trae psycopg: si no, una instalacion interrumpida degrada en silencio.
    if neutral.is_file() and (tiene_psycopg(neutral) or not tiene_psycopg(actual)):
        return neutral
    if tiene_psycopg(actual):
        return actual
    if host == "hermes":
        # Extras del host, DESPUES del venv neutro (el orden que documenta SKILL.md).
        env = os.environ.get("HERMES_PYTHON")
        if env:
            py = Path(env).expanduser().absolute()
            if py.is_file():
                return py
        v = _desde_launcher()
        if v and v.is_file():
            return v
        hh = hermes_home()
        if hh:
            for venv in (hh / "hermes-agent" / "venv", hh / "venv", hh / ".venv"):
                p = _bin_python(venv)
                if p.is_file():
                    return p
    return actual


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
    ap.add_argument("--host", choices=HOSTS_VALIDOS,
                    help="host explicito; gana sobre la autodeteccion")
    ap.add_argument("--hub", action="store_true",
                    help="exige psycopg (el Memory Hub Postgres): exit!=0 si falta")
    ap.add_argument("--instalar-deps", action="store_true",
                    help="instala psycopg[binary] en un venv, nunca en el Python global")
    args = ap.parse_args()

    if args.host:
        os.environ["HARNESS_HOST"] = args.host
    h = scripts_dir()
    try:
        host = host_agente()
        py = python_harness()
        probe = subprocess.run([str(py), "-c", "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"],
                               capture_output=True, timeout=30)
        if probe.returncode != 0:
            raise ValueError("PY requiere Python 3.10+ ejecutable; revisa HARNESS_PYTHON")
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"[!!] Python no disponible: {exc}", file=sys.stderr)
        return 1

    if args.instalar_deps:
        if tiene_psycopg(py):
            print(f"[ok] psycopg ya presente en {py}", file=sys.stderr)
        else:
            try:
                # Nunca se instala en un interprete que no sea el venv neutro:
                # ni el python del sistema (host hermes lo resolvia global) ni el
                # venv del proyecto del usuario, que quedaria contaminado.
                if py.resolve() != _bin_python(venv_neutro()).resolve():
                    venv = venv_neutro()
                    r = subprocess.run([str(py), "-m", "venv", str(venv)], stdout=sys.stderr)
                    if r.returncode != 0:
                        return r.returncode
                    py = _bin_python(venv)
                r = subprocess.run([str(py), "-m", "pip", "install", "psycopg[binary]"], stdout=sys.stderr)
                if r.returncode != 0:
                    return r.returncode
            except OSError as exc:
                print(f"[!!] no se pudo preparar el venv: {exc}", file=sys.stderr)
                return 1
            if not tiene_psycopg(py):
                print("[!!] pip termino pero psycopg no se puede importar", file=sys.stderr)
                return 1
            print(f"[ok] psycopg instalado en {py}", file=sys.stderr)

    if args.shell:
        for key, value in (("H", h), ("PY", py), ("HARNESS_HOST", host), ("HARNESS_PYTHON", py)):
            print(f"export {key}={shlex.quote(str(value))}")
        return 0

    if args.powershell:
        for key, value in (("H", h), ("PY", py), ("env:HARNESS_HOST", host), ("env:HARNESS_PYTHON", py)):
            literal = str(value).replace("'", "''")
            print(f"${key} = '{literal}'")
        return 0

    so = "Windows" if ES_WINDOWS else sys.platform
    print(f"SO            : {so}")
    print(f"HARNESS_HOST  : {host}")
    if host == "hermes":
        print(f"HERMES_HOME   : {hermes_home() or '(no encontrado)'}")
    print(f"H  (scripts)  : {h}")
    print(f"PY (python)   : {py or '(no encontrado)'}")

    ok = tiene_psycopg(py)
    print(f"psycopg (hub) : {'ok' if ok else 'FALTA -> --instalar-deps; gates locales disponibles'}")
    # Solo es un error si declaras que necesitas el hub: quien usa unicamente los
    # gates locales no debe recibir exit!=0 permanente de un diagnostico correcto.
    return 0 if (ok or not args.hub) else 1


if __name__ == "__main__":
    raise SystemExit(main())
