#!/usr/bin/env python3
"""Procesos de codebase-memory-mcp: cuales estan en uso y cuales son huerfanos.

  contexto.py limpiar-cbm [--solo-avisar]

Por que existe: cada sesion de agente lanza su propio servidor MCP de cbm, el
daemon lanza workers de indexado y el cierre del arnes lanza `cli`. Si una sesion
muere mal o el daemon se para a la fuerza, quedan procesos sin padre y archivos
`.db.stage.*` de ~100 MB. Esto mata SOLO lo que se puede probar huerfano. Un
proceso cuya sesion sigue viva se reporta EN USO y no se toca, aunque su enlace
con el daemon este roto: eso lo decide quien tiene la sesion abierta. El daemon
tampoco se toca nunca (pararlo corta indexados y las sesiones de los demas).
"""
from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

EXE = "codebase-memory-mcp"
ES_WINDOWS = os.name == "nt"
GRACIA_S = 5                 # entre SIGTERM y SIGKILL
STAGE_MIN_EDAD_S = 3600      # un indexado vivo no deja un .stage de mas de una hora sin proceso


def rol(args: list[str]) -> str:
    """Que es un proceso cbm segun sus argumentos."""
    if "--cbm-daemon-internal" in args or "--cbm-daemon-permanent" in args:
        return "daemon"
    if "--index-worker" in args:
        return "worker"
    if args[:1] == ["cli"]:
        return "cli"
    if not args:
        return "sesion"      # servidor MCP por stdio de una sesion de agente
    return "otro"            # hook-augment, config, install: viven segundos


def leer_procesos() -> tuple[list[dict], dict[int, tuple[int, str]]]:
    """(procesos cbm, todos): todos mapea pid -> (ppid, comando) para ubicar al padre."""
    r = subprocess.run(["ps", "-axo", "pid=,ppid=,etime=,rss=,command="],
                       capture_output=True, text=True, timeout=30)
    todos: dict[int, tuple[int, str]] = {}
    cbm: list[dict] = []
    for ln in r.stdout.splitlines():
        partes = ln.split(None, 4)
        if len(partes) < 5 or not partes[0].isdigit() or not partes[1].isdigit():
            continue
        pid, ppid, etime, rss, cmd = int(partes[0]), int(partes[1]), partes[2], partes[3], partes[4]
        todos[pid] = (ppid, cmd)
        toks = cmd.split()
        if toks and os.path.basename(toks[0]) == EXE:
            cbm.append({"pid": pid, "ppid": ppid, "etime": etime, "cmd": cmd,
                        "rss_mb": int(rss or 0) / 1024, "rol": rol(toks[1:])})
    return cbm, todos


def protegidos(todos: dict[int, tuple[int, str]], yo: int | None = None) -> set[int]:
    """Este proceso y toda su ascendencia: jamas se matan."""
    out, pid = set(), yo if yo is not None else os.getpid()
    while pid and pid not in out:
        out.add(pid)
        pid = todos.get(pid, (0, ""))[0]
    return out


def clasificar(procesos: list[dict], todos: dict[int, tuple[int, str]],
               protegidos_: set[int]) -> list[dict]:
    """Agrega 'estado' (EN USO | HUERFANO) y 'motivo' a cada proceso.

    Huerfano = su padre murio y el sistema lo reasigno al init (ppid 1). Es lo
    unico que se prueba: un padre vivo cuenta como uso aunque el proceso este
    inactivo, porque no hay forma de saber si la sesion lo va a necesitar.
    """
    out = []
    for p in procesos:
        padre = todos.get(p["ppid"], (0, "?"))[1].split()[0:1]
        padre = os.path.basename(padre[0]) if padre else "?"
        if p["pid"] in protegidos_:
            estado, motivo = "EN USO", "es este mismo comando"
        elif p["rol"] == "daemon":
            estado, motivo = "EN USO", "daemon compartido: pararlo es decision tuya (daemon stop)"
        elif p["rol"] == "otro":
            estado, motivo = "EN USO", "proceso corto"
        elif p["ppid"] in (0, 1):
            estado, motivo = "HUERFANO", "su padre murio"
        else:
            estado, motivo = "EN USO", f"padre vivo: {padre} (pid {p['ppid']})"
        out.append({**p, "estado": estado, "motivo": motivo})
    return out


def cache_dir() -> Path:
    return Path(os.environ.get("CBM_CACHE_DIR") or Path.home() / ".cache" / "codebase-memory-mcp")


def stage_abandonado(procesos: list[dict], cache: Path | None = None,
                     ahora: float | None = None) -> list[Path]:
    """Restos de `.db.stage.*`. Con un daemon, worker o cli vivo no se toca nada:
    podria ser un indexado en curso."""
    if any(p["rol"] in ("daemon", "worker", "cli") for p in procesos):
        return []
    cache = cache or cache_dir()
    ahora = ahora if ahora is not None else time.time()
    try:
        return sorted(f for f in cache.glob("*.db.stage.*")
                      if f.is_file() and ahora - f.stat().st_mtime > STAGE_MIN_EDAD_S)
    except OSError:
        return []


def _vivo(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _comando(pid: int) -> str | None:
    r = subprocess.run(["ps", "-o", "command=", "-p", str(pid)],
                       capture_output=True, text=True, timeout=10)
    return r.stdout.strip() or None


def matar(p: dict, *, kill=os.kill, vivo=_vivo, comando=_comando, dormir=time.sleep) -> str:
    """SIGTERM y, si sigue vivo tras la gracia, SIGKILL. Devuelve que paso."""
    actual = comando(p["pid"])
    if actual is None:
        return "ya no existia"
    if actual != p["cmd"]:
        # El pid se reutilizo para otro programa entre la lectura y el kill.
        return "el pid ahora es otro programa: no se toca"
    kill(p["pid"], signal.SIGTERM)
    for _ in range(GRACIA_S * 4):
        if not vivo(p["pid"]):
            return "matado"
        dormir(0.25)
    kill(p["pid"], signal.SIGKILL)
    dormir(0.25)
    return "matado (SIGKILL)" if not vivo(p["pid"]) else "NO SE PUDO MATAR"


def limpiar(*, matar_huerfanos=True, **inyectado) -> int:
    """Imprime el estado de cada proceso cbm y, salvo --solo-avisar, quita lo huerfano."""
    if ES_WINDOWS:
        print("[i]  limpiar-cbm usa `ps`: no esta soportado en Windows.")
        return 0
    procesos, todos = leer_procesos()
    filas = clasificar(procesos, todos, protegidos(todos))
    print("== procesos de codebase-memory-mcp ==")
    if not filas:
        print("   (ninguno)")
    fallos = 0
    for p in filas:
        accion = ""
        if p["estado"] == "HUERFANO" and matar_huerfanos:
            accion = " -> " + matar(p, **inyectado)
            fallos += "NO SE PUDO" in accion
        print(f"   {p['estado']:<8} pid={p['pid']:<6} {p['rol']:<7} {p['rss_mb']:>6.0f}MB "
              f"{p['etime']:>11}  {p['motivo']}{accion}")
    huerfanos = [p for p in filas if p["estado"] == "HUERFANO"]
    if not huerfanos:
        print("[ok] ninguno es huerfano: nada que matar.")
    elif not matar_huerfanos:
        print(f"[i]  {len(huerfanos)} huerfano(s); sin --solo-avisar se matarian.")
    restos = stage_abandonado(procesos)
    for f in restos:
        mb = f.stat().st_size / 1048576
        if matar_huerfanos:
            try:
                f.unlink()
                estado = "borrado"
            except OSError as exc:
                estado, fallos = f"no se pudo borrar: {exc}", fallos + 1
        else:
            estado = "se borraria"
        print(f"   RESTO    {f.name}  {mb:.0f}MB  ({estado})")
    return 1 if fallos else 0
