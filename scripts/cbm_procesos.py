#!/usr/bin/env python3
"""Procesos de codebase-memory-mcp: cuales estan en uso y cuales son huerfanos.

  contexto.py limpiar-cbm [--solo-avisar]
  contexto.py limpiar-cbm --reiniciar-daemon [--solo-avisar]

Por que existe: cada sesion de agente lanza su propio servidor MCP de cbm, el
daemon lanza workers de indexado y el cierre del arnes lanza `cli`. Si una sesion
muere mal o el daemon se para a la fuerza, quedan procesos sin padre y archivos
`.db.stage.*` de ~100 MB. Esto mata SOLO lo que se puede probar huerfano. Un
proceso cuya sesion sigue viva se reporta EN USO y no se toca, aunque su enlace
con el daemon este roto: eso lo decide quien tiene la sesion abierta. El daemon
tampoco se toca nunca (pararlo corta indexados y las sesiones de los demas),
con una sola excepcion que se prueba: el daemon HUERFANO DE SOCKET.

Daemon huerfano de socket: el proceso sigue vivo y sostiene el lock, pero su
socket ya no existe en disco. Ningun cliente nuevo puede conectarse (esperan 30 s y
fallan con "could not accept this client", el mismo texto que un daemon saturado),
`daemon stop` no lo alcanza y ningun otro daemon puede arrancar porque el lock es
suyo: no se arregla solo. `--reiniciar-daemon` lo termina, y solo a ese.
"""
from __future__ import annotations

import os
import re
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


def enlaces_cortados(pids: list[int]) -> set[int]:
    """Sesiones MCP cuyo enlace con el daemon esta cortado.

    El servidor MCP de una sesion mantiene un socket unix hacia el daemon. Si el
    daemon muere por la fuerza, el peer pasa a `->(none)` pero el servidor sigue
    vivo hasta su proxima consulta; en esa se cierra y la sesion se queda sin cbm.
    stdio (fd 0-2) tambien puede ser un socket, por eso solo cuentan fd >= 3.
    Verificado en macOS (lsof); donde lsof no muestre `(none)` no detecta nada,
    que es la direccion segura: no avisa de mas.
    """
    if not pids:
        return set()
    try:
        r = subprocess.run(["lsof", "-nP", "-p", ",".join(map(str, pids))],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return set()
    cortados = set()
    for ln in r.stdout.splitlines()[1:]:
        c = ln.split()
        m = re.match(r"(\d+)", c[3]) if len(c) > 7 else None
        if m and int(m.group(1)) >= 3 and c[4] == "unix" and c[-1] == "->(none)":
            cortados.add(int(c[1]))
    return cortados


def rutas_socket(pid: int) -> list[str]:
    """Rutas en disco de los sockets unix que tiene abiertos un proceso. Vacio si
    lsof no responde: sin dato no se afirma nada."""
    try:
        r = subprocess.run(["lsof", "-nP", "-U", "-a", "-p", str(pid)],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return []
    rutas = []
    for ln in r.stdout.splitlines()[1:]:
        m = re.search(r"\sunix\s.*?\s(/\S.*)$", ln)   # el NODE vacio mueve las columnas: se ancla en la ruta
        if m:
            rutas.append(m.group(1).strip())
    return rutas


def daemon_sin_socket(procesos: list[dict], *, rutas=rutas_socket,
                      existe=os.path.exists) -> list[int]:
    """Pids de daemons vivos cuyo socket ya no existe en disco.

    Un daemon sano deja sus sockets (`.sock`, `.anc`) en el directorio de
    coordinacion. Aqui se pide que NINGUNA de las rutas que tiene abiertas exista:
    si queda una, o si lsof no da rutas, no se acusa (la direccion segura, porque lo
    que sigue de esto es terminar el proceso). Verificado en macOS contra un daemon
    sano de prueba y contra el huerfano real.
    """
    out = []
    for p in procesos:
        if p["rol"] != "daemon":
            continue
        propias = rutas(p["pid"])
        if propias and not any(existe(r) for r in propias):
            out.append(p["pid"])
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


def limpiar(*, matar_huerfanos=True, enlaces=enlaces_cortados,
            sin_socket=daemon_sin_socket, **inyectado) -> int:
    """Imprime el estado de cada proceso cbm y, salvo --solo-avisar, quita lo huerfano."""
    if ES_WINDOWS:
        print("[i]  limpiar-cbm usa `ps`: no esta soportado en Windows.")
        return 0
    procesos, todos = leer_procesos()
    filas = clasificar(procesos, todos, protegidos(todos))
    vivas = [p["pid"] for p in filas if p["rol"] == "sesion" and p["estado"] == "EN USO"]
    cortadas = enlaces(vivas)
    print("== procesos de codebase-memory-mcp ==")
    if not filas:
        print("   (ninguno)")
    fallos = 0
    for p in filas:
        accion = ""
        if p["estado"] == "HUERFANO" and matar_huerfanos:
            accion = " -> " + matar(p, **inyectado)
            fallos += "NO SE PUDO" in accion
        corte = "  | enlace al daemon CORTADO" if p["pid"] in cortadas else ""
        print(f"   {p['estado']:<8} pid={p['pid']:<6} {p['rol']:<7} {p['rss_mb']:>6.0f}MB "
              f"{p['etime']:>11}  {p['motivo']}{corte}{accion}")
    huerfanos = [p for p in filas if p["estado"] == "HUERFANO"]
    if not huerfanos:
        print("[ok] ninguno es huerfano: nada que matar.")
    elif not matar_huerfanos:
        print(f"[i]  {len(huerfanos)} huerfano(s); sin --solo-avisar se matarian.")
    if cortadas:
        print(f"[!]  {len(cortadas)} sesion(es) con el enlace a cbm cortado: su proxima consulta "
              "cbm falla y su servidor MCP se cierra.\n"
              "     Siguen EN USO y no se matan: reconecta el MCP desde tu agente (en Claude Code "
              "`/mcp`) o reinicia la sesion.")
    huerfano_socket = sin_socket(procesos)
    if huerfano_socket:
        print(f"[!]  el daemon cbm (pid {', '.join(map(str, huerfano_socket))}) esta vivo pero su "
              "socket ya no existe: ningun cliente nuevo puede conectar y no se arregla solo.\n"
              "     Reinicialo con `contexto.py limpiar-cbm --reiniciar-daemon` (las sesiones "
              "conectadas pierden cbm hasta reconectar con `/mcp`).")
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


def _verificar_cliente(*, correr=None) -> tuple[bool, str]:
    """Un cliente nuevo tiene que conectar: es la prueba de que el reinicio sirvio.
    Lo arranca el propio cliente (efimero); aqui no se levanta ningun daemon."""
    t = time.time()
    try:
        r = (correr or subprocess.run)([EXE, "cli", "--quiet", "list_projects"], capture_output=True,
                   text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)[:200]
    if r.returncode == 0:
        return True, f"{time.time() - t:.1f} s"
    return False, ((r.stderr or r.stdout).strip()[-200:] or f"exit {r.returncode}")


def reiniciar_daemon(*, solo_avisar=False, leer=leer_procesos, detectar=daemon_sin_socket,
                     enlaces=enlaces_cortados, verificar=_verificar_cliente,
                     dormir=time.sleep, **inyectado) -> int:
    """Termina el daemon cbm SOLO si su socket desaparecio, y comprueba que un cliente
    nuevo conecta despues.

    Es la unica vez que el arnes toca el daemon: un daemon que conserva su socket es
    de todas las sesiones y se rechaza. Antes de actuar avisa que sesiones perderan
    cbm. No arranca ningun daemon (`daemon start` deja uno permanente): el primer
    cliente levanta uno efimero.
    """
    if ES_WINDOWS:
        print("[i]  limpiar-cbm usa `ps`: no esta soportado en Windows.")
        return 1
    procesos, todos = leer()
    daemons = [p for p in procesos if p["rol"] == "daemon"]
    if not daemons:
        print("[ok] no hay daemon cbm vivo: el proximo cliente arranca uno solo; nada que reiniciar.")
        return 0
    huerfanos = detectar(procesos)
    if huerfanos:
        dormir(1)  # un daemon que se esta parando tambien pierde el socket un instante
        huerfanos = [x for x in huerfanos if x in detectar(procesos)]
    if not huerfanos:
        pids = ", ".join(str(p["pid"]) for p in daemons)
        print(f"[ok] el daemon cbm (pid {pids}) conserva su socket: no esta huerfano, no se "
              "toca. Es de todas las sesiones; si de verdad hay que pararlo, hazlo con orden: "
              "`codebase-memory-mcp daemon stop`.")
        return 0

    victimas = [p for p in daemons if p["pid"] in huerfanos]
    hijos = [p for p in procesos if p["rol"] == "worker" and p["ppid"] in huerfanos]
    sesiones = [p for p in procesos if p["rol"] == "sesion"]
    cortadas = enlaces([p["pid"] for p in sesiones if p["ppid"] not in (0, 1)])
    conectadas = [p for p in sesiones if p["ppid"] not in (0, 1) and p["pid"] not in cortadas]

    print("== daemon cbm sin socket ==")
    for p in victimas:
        print(f"   pid={p['pid']}  vivo desde {p['etime']}, pero su socket ya no existe: ningun "
              "cliente nuevo puede conectar y `daemon stop` no lo alcanza")
    if conectadas:
        print(f"   Al reiniciarlo, {len(conectadas)} sesion(es) conectada(s) pierden cbm hasta "
              "reconectar el MCP (`/mcp` en Claude Code) o reiniciarse:")
        for p in conectadas:
            padre = todos.get(p["ppid"], (0, "?"))[1].split()[0:1]
            print(f"     pid={p['pid']}  padre: {os.path.basename(padre[0]) if padre else '?'} "
                  f"(pid {p['ppid']})")
    for p in hijos:
        print(f"   worker de indexado del daemon: pid={p['pid']} (se corta con el)")
    if solo_avisar:
        print("[i]  --solo-avisar: no se mato nada. Sin esa opcion, `--reiniciar-daemon` lo termina.")
        return 0

    fallos = 0
    for p in victimas + hijos:
        r = matar(p, dormir=dormir, **inyectado)
        fallos += "NO SE PUDO" in r
        print(f"   {p['rol']:<7} pid={p['pid']} -> {r}")
    if fallos:
        print("[!]  no se pudo terminar el daemon: no se verifica nada mas.")
        return 1
    ok, detalle = verificar()
    if not ok:
        print(f"[!]  el daemon se termino pero un cliente nuevo aun no conecta: {detalle}")
        return 1
    print(f"[ok] un cliente nuevo ya conecta ({detalle}). Las sesiones listadas arriba "
          "reconectan con `/mcp`; los cierres pendientes se reintentan solos.")
    return 0
