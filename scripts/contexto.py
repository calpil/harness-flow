#!/usr/bin/env python3
"""Contexto del proyecto: grafo combinado, hub y vault, con briefing compacto.

  contexto.py estado [--json]
  contexto.py refrescar [--forzar] [--max-horas N] [--sin-vault] [--sin-hub]
  contexto.py brief --feature <id> [--max-lineas N] [--max-relacionados N]

Por que existe: la raiz del arnes puede ser UN repo (p.ej. el front) mientras
los microservicios viven en otra raiz del disco. Con un solo graphify-out el
grafo no ve la mitad del sistema y las consultas vuelven vacias o con ruido de
la mitad equivocada. Las raices se DECLARAN en harness/grafos.json y se
combinan con `graphify merge-graphs`; nada se autodetecta en silencio.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (SERVICE_RE, ac_comandos, ac_costuras, bloqueos_feature,  # noqa: E402
                   get_feature, grafos_config, graph_path, impl_path,
                   load_backlog, now_iso, paths, raices_grafo,
                   requiere_declarados, review_path, spec_ac_lineas, spec_acs,
                   spec_path)
from comun import micros_declarados as _micros_declarados  # noqa: E402

# Relaciones que dicen "esto usa aquello". `contains`/`method` son estructura
# interna: inflan el brief sin explicar acoplamiento.
REL_UTILES = {"imports", "imports_from", "calls", "references", "implements",
              "depends_on", "uses", "shares_data_with", "re_exports",
              "dynamic_import"}


# --- frescura ---------------------------------------------------------------

def _edad_h(f: Path) -> float | None:
    return None if not f.exists() else (time.time() - f.stat().st_mtime) / 3600


# `graphify update` sin cambios sale 0 y NO reescribe graph.json: medir la raiz
# solo por el mtime del grafo la dejaba "vencida" para siempre aunque estuviera
# al dia. `refrescar` deja este sello al lado cuando el update sale bien, y la
# edad de la raiz es la del MAS NUEVO de los dos (un sello viejo no rejuvenece).
SELLO_VERIFICADO = ".harness_verificado"


def _edad_raiz_h(g: Path) -> float | None:
    if not g.exists():
        return None
    sello = g.parent / SELLO_VERIFICADO
    mtime = g.stat().st_mtime
    if sello.exists():
        mtime = max(mtime, sello.stat().st_mtime)
    return (time.time() - mtime) / 3600


def _vault_vencido(p: dict) -> bool:
    """El vault sale del backlog y de spec/evidencia/review, no del grafo.

    Mirar solo la edad del grafo lo dejaba mostrando estados viejos toda la
    feature: con el grafo fresco, `start` no lo regeneraba, y aprobar un spec
    o sellar un review tampoco. Vencido = el Indice es anterior a su fuente
    mas nueva.
    """
    indice = p["vault"] / "Indice.md"
    if not indice.exists():
        return True
    fuentes = [p["backlog"], *p["docs"].glob("spec-feature-*.md"),
               *p["docs"].glob("impl-*.md"), *p["docs"].glob("review-*.md")]
    nueva = max((f.stat().st_mtime for f in fuentes if f.exists()), default=0)
    return indice.stat().st_mtime < nueva


def estado_contexto(p: dict) -> dict:
    cfg = grafos_config(p)
    raices = raices_grafo(p)
    comb = graph_path(p)
    out = {
        "max_horas": cfg.get("max_horas", 12),
        "combinado": {"path": str(comb), "edad_h": _edad_h(comb),
                      "existe": comb.exists()},
        "raices": [],
        # El vault NO entra en 'vencidas': eso es lo que dice si el brief (grafo
        # y hub) miente, y el brief no lee el vault.
        "vault": {"path": str(p["vault"]), "existe": p["vault"].exists(),
                  "edad_h": _edad_h(p["vault"] / "Indice.md"),
                  "vencido": _vault_vencido(p)},
        "graphify": bool(shutil.which("graphify")),
        # Lectura de un archivo local: estado no llama al daemon. No entra en
        # 'vencidas': el brief y el vault no dependen de cbm.
        "cbm_pendientes": _cbm_pendientes(p),
        # Estado en vivo (no lo guardado): un daemon sin socket se ve al arrancar la
        # sesion aunque ningun cierre haya quedado pendiente todavia. Una lectura de
        # `ps` y `lsof`; vacio si cbm esta apagado o no esta instalado.
        "cbm_daemon_sin_socket": (_cbm_daemon_sin_socket()
                                  if not _cbm_desactivado() and shutil.which("codebase-memory-mcp")
                                  else []),
    }
    for r in raices:
        g = r["path"] / "graphify-out" / "graph.json"
        out["raices"].append({
            "nombre": r["nombre"], "path": str(r["path"]),
            "graph": str(g), "existe": g.exists(), "edad_h": _edad_raiz_h(g),
            "declarada": r.get("declarada", True),
        })
    vencidas = [r["nombre"] for r in out["raices"]
                if not r["existe"] or (r["edad_h"] or 0) > out["max_horas"]]
    if not out["combinado"]["existe"] and len(out["raices"]) > 1:
        vencidas.append("(combinado)")
    elif out["combinado"]["existe"] and len(out["raices"]) > 1:
        # el combinado tiene que ser POSTERIOR a cada raiz o miente.
        for r in out["raices"]:
            if r["edad_h"] is not None and out["combinado"]["edad_h"] is not None \
                    and out["combinado"]["edad_h"] > r["edad_h"]:
                vencidas.append("(combinado)")
                break
    out["vencidas"] = sorted(set(vencidas))
    out["fresco"] = not out["vencidas"]
    return out


def _estado_vault(e: dict) -> str:
    if not e["vault"]["existe"]:
        return "ausente (vault.py build)"
    return "desactualizado (vault.py build)" if e["vault"]["vencido"] else "ok"


def cmd_estado(args) -> None:
    p = paths()
    e = estado_contexto(p)
    if args.json:
        print(json.dumps(e, ensure_ascii=False, indent=2))
        return
    print("== Contexto del proyecto ==")
    if not e["graphify"]:
        print("   [!] graphify no esta en el PATH: el grafo no se puede refrescar aqui.")
    for r in e["raices"]:
        edad = "ausente" if not r["existe"] else f"{r['edad_h']:.1f}h"
        marca = "" if r["existe"] and r["edad_h"] <= e["max_horas"] else "  <- vencido"
        origen = "" if r["declarada"] else "  (raiz del arnes, no declarada)"
        print(f"   grafo[{r['nombre']}]: {edad}{marca}{origen}")
    c = e["combinado"]
    if len(e["raices"]) > 1:
        edad_c = "ausente" if not c["existe"] else f"{c['edad_h']:.1f}h"
        print(f"   combinado: {edad_c}  {c['path']}")
    print(f"   vault: {_estado_vault(e)}")
    for linea in lineas_cbm_pendiente(e["cbm_pendientes"], e["cbm_daemon_sin_socket"]):
        print("  " + linea)
    if e["fresco"]:
        print("   [ok] contexto fresco")
    else:
        print(f"   [!] vencido: {', '.join(e['vencidas'])}\n"
              "       corre: contexto.py refrescar")


# --- refresco ---------------------------------------------------------------

def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                           timeout=1800)
        return r.returncode, (r.stdout + r.stderr).strip()
    except FileNotFoundError:
        return 127, f"no encontrado: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timeout: {' '.join(cmd)}"


def _desactivado() -> bool:
    """HARNESS_SIN_CONTEXTO=1 apaga el refresco automatico.

    Existe para CI y para tests del propio arnes: refrescar el grafo lanza
    graphify sobre el arbol real, que en un test es carisimo y ajeno a lo que
    se esta probando. No cambia el veredicto de ningun gate.
    """
    return os.environ.get("HARNESS_SIN_CONTEXTO", "").strip() not in ("", "0", "false")


def _grafo_utilizable(g: Path) -> tuple[bool, str]:
    """Decide si un grafo recien generado sirve, sin confiar en el exit code.

    graphify puede salir 0 y no dejar nada util: raiz sin codigo que reconozca,
    escritura interrumpida, JSON truncado. Contar esos casos como exito es el
    falso verde: el parte dice "actualizada" y el merge posterior corre sobre
    datos viejos sin que nadie se entere.
    """
    if not g.exists():
        return False, f"no dejo el grafo en {g}"
    try:
        datos = json.loads(g.read_text(encoding="utf-8"))
    except OSError as exc:
        return False, f"el grafo no se puede leer: {exc}"
    except ValueError as exc:
        return False, f"el grafo no es JSON valido: {exc}"
    if not isinstance(datos, dict):
        return False, "el grafo no es un objeto JSON"
    if not datos.get("nodes"):
        return False, "el grafo quedo sin nodos"
    dentro = _nodos_en_node_modules(datos["nodes"])
    if dentro:
        return False, (f"el grafo indexo {dentro} nodos dentro de node_modules: "
                       "agrega node_modules/ a .graphifyignore o actualiza graphify")
    return True, ""


def _nodos_en_node_modules(nodos: list) -> int:
    """Nodos cuyo archivo fuente cuelga de un directorio node_modules (a cualquier
    profundidad; separador / o \\). graphify y cbm lo excluyen por diseno; esto
    existe para que una version nueva que lo rompa no pase en silencio."""
    n = 0
    for nodo in nodos:
        if not isinstance(nodo, dict):
            continue
        ruta = str(nodo.get("source_file") or nodo.get("file") or "")
        if "node_modules" in ruta.replace("\\", "/").split("/"):
            n += 1
    return n


def _cbm_desactivado() -> bool:
    """HARNESS_SIN_CBM=1 apaga solo el indexado de codebase-memory-mcp."""
    return os.environ.get("HARNESS_SIN_CBM", "").strip() not in ("", "0", "false")


def _cbm_cli(tool: str, args: dict, cwd: Path) -> tuple[int, str]:
    return _run(["codebase-memory-mcp", "cli", "--quiet", tool,
                 json.dumps(args)], cwd)


RAMAS_CBM = ("develop", "main", "master", "release", "release/*", "release-*")


def _git_out(raiz: Path, *args: str) -> str | None:
    code, out = _run(["git", "-C", str(raiz), *args], raiz)
    return out.strip() if code == 0 else None


def _rama_indexable(raiz: Path, permitidas) -> tuple[bool, str]:
    """cbm indexa solo ramas estables en la raiz real, nunca un worktree.

    Un worktree de feature es trabajo en curso: indexarlo mete en el grafo
    codigo que aun no se integro y, peor, lo deja bajo otro proyecto que nadie
    limpia. Se decide por git, no por el nombre de la carpeta.
    """
    from fnmatch import fnmatch
    gitdir = _git_out(raiz, "rev-parse", "--absolute-git-dir")
    comun = _git_out(raiz, "rev-parse", "--git-common-dir")
    if gitdir is None or comun is None:
        return False, "no es un repo git: no se puede probar la rama"
    comun_abs = Path(comun) if Path(comun).is_absolute() else raiz / comun
    if Path(gitdir).resolve() != comun_abs.resolve():
        # En la raiz real ambos coinciden; en un worktree el gitdir cuelga de
        # <repo>/.git/worktrees/<n> y el common-dir apunta al .git principal.
        return False, "es un worktree (trabajo en desarrollo)"
    rama = _git_out(raiz, "branch", "--show-current")
    if not rama:
        return False, "HEAD desacoplado: no hay rama"
    if not any(fnmatch(rama, pat) for pat in permitidas):
        return False, f"rama '{rama}' no es develop/release/main/master"
    return True, rama


# El daemon de cbm es UN proceso compartido por todas las sesiones y agentes de la
# maquina (y su watcher reindexa por su cuenta). Que no atienda en un momento dado
# es transitorio; el cierre no puede depender de eso ni un agente improvisar la
# salida. Por eso: se evita llamarlo si no hay nada nuevo, se reintenta con espera
# creciente, y si sigue sin atender se anota como PENDIENTE y se reintenta solo.
CBM_ESTADO = ".cbm_estado.json"
CBM_INTENTOS = 3
CBM_ESPERA_S = 5.0            # base de la espera: 5s, 15s, 45s...
CBM_ENFRIAMIENTO_S = 600      # entre reintentos AUTOMATICOS de un pendiente

# Lo que reintentar no arregla: seguir golpeando solo suma carga al daemon.
CBM_PERMANENTE = ("fingerprint_mismatch", "different build", "binary image",
                  "different cache directory", "conflicting cbm process",
                  "likely dead", "allow-root", "no encontrado")
# Lo que si pasa con el tiempo: daemon ocupado, arrancando, parandose o con otra
# mutacion del mismo proyecto en curso. Son los textos del propio binario.
CBM_TRANSITORIO = ("could not accept this client", "connection capacity",
                   "could not start", "is stopping", "connection failed",
                   "session initialization failed", "startup failed",
                   "blocked by another mutation", "another index operation",
                   "coordination could not be verified", "worker_cancelled",
                   "timeout:")


CAUSA_SIN_SOCKET = "daemon_sin_socket"   # el proceso vive pero su socket ya no existe


def _env_num(nombre: str, defecto: float) -> float:
    try:
        return float(os.environ.get(nombre, "").strip() or defecto)
    except ValueError:
        return defecto


def _cbm_estado_path(p: dict) -> Path:
    return p["root"] / "graphify-out" / CBM_ESTADO


def _cbm_estado(p: dict) -> dict:
    """Sello de lo ya indexado y de lo pendiente. Es un atajo, no una verdad:
    ausente o ilegible = vacio, y lo peor que pasa es indexar de mas."""
    try:
        d = json.loads(_cbm_estado_path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    d = d if isinstance(d, dict) else {}
    d.setdefault("indexado", {})
    d.setdefault("pendientes", {})
    return d


def _cbm_pendientes(p: dict) -> dict:
    """{nombre: pendiente} de lo que el arnes va a reintentar. Vacio si cbm esta
    apagado o ya no esta instalado: decir "se reintenta solo" cuando nada lo va a
    reintentar seria una mentira que nadie corregiria."""
    if _cbm_desactivado() or not shutil.which("codebase-memory-mcp"):
        return {}
    return {v.get("nombre", k): v for k, v in _cbm_estado(p)["pendientes"].items()}


def _cbm_guardar(p: dict, estado: dict) -> None:
    f = _cbm_estado_path(p)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        tmp.replace(f)
    except OSError:
        pass  # sin sello solo se pierde el atajo; nunca tumba el refresco


def _cbm_huella(raiz: Path) -> tuple[str, bool] | None:
    """(HEAD, arbol limpio). None si git no responde: sin huella no hay atajo."""
    head = _git_out(raiz, "rev-parse", "HEAD")
    sucio = _git_out(raiz, "status", "--porcelain")
    if not head or sucio is None:
        return None
    return head, not sucio


def _cbm_clasificar(code: int, out: str) -> str:
    """'permanente', 'transitorio' o 'desconocido'. Lo desconocido se trata como
    fallo visible, igual que antes: solo se difiere lo que se SABE transitorio."""
    bajo = out.lower()
    if code == 127 or any(m in bajo for m in CBM_PERMANENTE):
        return "permanente"
    if code == 124 or any(m in bajo for m in CBM_TRANSITORIO):
        return "transitorio"
    return "desconocido"


def _cbm_indexar_raiz(raiz: Path, intentos: int) -> tuple[bool, str, str, int, str]:
    """(ok, ultimo_error, clase, intentos_usados, salida_del_exito). Reintenta solo
    lo transitorio."""
    espera = _env_num("HARNESS_CBM_ESPERA_S", CBM_ESPERA_S)
    err, clase = "", "desconocido"
    for n in range(1, max(intentos, 1) + 1):
        code, out = _cbm_cli("index_repository", {"repo_path": str(raiz)}, raiz)
        # El exit code solo no alcanza: se exige el status que reporta la tool.
        if code == 0 and '"status":"indexed"' in out.replace(" ", ""):
            return True, "", "", n, out
        err = out[-300:] or f"exit {code}"
        clase = _cbm_clasificar(code, out)
        if clase != "transitorio":
            return False, err, clase, n, ""
        if n < intentos:
            time.sleep(espera * 3 ** (n - 1) * random.uniform(0.8, 1.2))
    return False, err, clase, max(intentos, 1), ""


def _tiene_node_modules(raiz: Path, profundidad: int = 4) -> bool:
    """Hay un node_modules en la raiz o dentro de sus primeros niveles (monorepos)."""
    base = len(raiz.parts)
    for d, dirs, _ in os.walk(raiz):
        if "node_modules" in dirs:
            return True
        dirs[:] = [x for x in dirs if x not in (".git", "graphify-out")
                   and len(Path(d).parts) - base < profundidad]
    return False


def _cbm_node_modules_indexado(raiz: Path, salida: str) -> str | None:
    """Motivo si cbm pudo haber indexado node_modules; None si no hay indicio.

    cbm lo excluye por diseno y no se puede re-incluir ni con `!node_modules/` en
    .cbmignore (comprobado en 0.11.0); esto lo vigila para que un cambio de version
    no lo rompa en silencio. No llama al daemon: lee `excluded` del propio resultado
    del indexado. Sin ese dato, o con la lista truncada, no afirma nada.
    """
    if not _tiene_node_modules(raiz):
        return None
    try:
        ex = json.loads(salida).get("excluded")
    except (ValueError, AttributeError):
        return None
    if not isinstance(ex, dict):
        return None
    dirs = ex.get("dirs") or []
    if any(Path(str(d)).name == "node_modules" for d in dirs) or ex.get("truncated"):
        return None
    return f"cbm no excluyo node_modules (excluded.dirs={dirs[:6]})"


def _cbm_en_enfriamiento(pendiente: dict | None) -> bool:
    if not pendiente:
        return False
    tope = _env_num("HARNESS_CBM_ENFRIAMIENTO_S", CBM_ENFRIAMIENTO_S)
    return (time.time() - float(pendiente.get("ts") or 0)) < tope


def _cbm_daemon_sin_socket() -> list[int]:
    """Pids de daemons cbm vivos sin socket: ningun cliente puede conectar, pero el
    proceso sostiene el lock, asi que tampoco arranca otro. Reintentar solo gasta 30 s
    por intento. Una lectura de `ps` y de `lsof`; nunca toca el daemon."""
    try:
        import cbm_procesos
        if cbm_procesos.ES_WINDOWS:
            return []
        return cbm_procesos.daemon_sin_socket(cbm_procesos.leer_procesos()[0])
    except (OSError, subprocess.SubprocessError, ValueError):
        return []


def _cbm_diagnostico(sin_socket: list[int] | None = None) -> dict:
    """Foto barata de la maquina cuando cbm no atiende. No toca el daemon.

    Deja datos en vez de hipotesis: el "no acepta clientes" tiene mas de una causa
    (daemon ocupado, o vivo pero sin socket) y el texto del cliente es el mismo.
    Es telemetria: cualquier fallo al medir se omite.
    """
    d: dict = {"at": now_iso()}
    cbm: list = []
    try:
        d["carga"] = [round(x, 1) for x in os.getloadavg()]
    except (OSError, AttributeError):
        pass
    try:
        import cbm_procesos
        cbm, _ = cbm_procesos.leer_procesos()
        roles: dict[str, int] = {}
        for p in cbm:
            roles[p["rol"]] = roles.get(p["rol"], 0) + 1
        d["procesos"] = roles
        d["rss_cbm_mb"] = round(sum(p["rss_mb"] for p in cbm))
        d["sesiones_cortadas"] = len(cbm_procesos.enlaces_cortados(
            [p["pid"] for p in cbm if p["rol"] == "sesion"]))
        sin_socket = cbm_procesos.daemon_sin_socket(cbm) if sin_socket is None else sin_socket
        log = cbm_procesos.cache_dir() / "logs" / "cbm-daemon.log"
        with open(log, "rb") as fh:  # solo la cola: el log crece sin limite
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - 65536))
            cola = fh.read().decode("utf-8", "replace")
        d["log_64KB"] = {m: cola.count(f"msg={m}")
                         for m in ("watcher.changed", "daemon.start", "ui.unavailable")}
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    if sin_socket:
        d[CAUSA_SIN_SOCKET] = list(sin_socket)
        try:
            import cbm_procesos
            d["runtime_dir"] = cbm_procesos.huella_runtime(sin_socket[0])
            d["daemon_desde"] = next((p.get("etime") for p in cbm if p["pid"] == sin_socket[0]), None)
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    if sys.platform == "darwin":
        try:
            r = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True,
                               text=True, timeout=5)
            m = re.search(r"used = ([\d.]+)M", r.stdout)
            if m:
                d["swap_usado_mb"] = round(float(m.group(1)))
        except (OSError, subprocess.SubprocessError):
            pass
    return d


def _resumen_diagnostico(d: dict) -> str:
    partes = []
    if "procesos" in d:
        partes.append(f"{d['procesos'].get('sesion', 0)} sesiones cbm "
                      f"({d.get('sesiones_cortadas', 0)} cortadas)")
    if "carga" in d:
        partes.append(f"carga {d['carga'][0]}")
    if "swap_usado_mb" in d:
        partes.append(f"swap {d['swap_usado_mb']} MB")
    if d.get("log_64KB"):
        partes.append(f"{d['log_64KB'].get('watcher.changed', 0)} reindexados del watcher en el log reciente")
    rt = d.get("runtime_dir") or {}
    if rt.get("dir_mtime"):
        partes.append(f"carpeta del daemon cambio por ultima vez {rt['dir_mtime']}"
                      + (f", daemon vivo desde hace {d['daemon_desde']}" if d.get("daemon_desde") else ""))
    return ", ".join(partes)


def lineas_cbm_pendiente(pendientes: dict, sin_socket: list[int] | None = None) -> list[str]:
    """Texto para quien lee el cierre: que paso, que NO hacer y cuando se resuelve.

    `sin_socket` son los daemons sin socket medidos AHORA (estado/arranque). Con None
    (el cierre) se usa lo que dejo la foto del fallo; con una lista, esa lista manda:
    si ya reiniciaron el daemon, un pendiente viejo no puede seguir acusandolo.
    """
    if sin_socket is None:
        sin_socket = sorted({pid for v in (pendientes or {}).values()
                             for pid in (v.get("diagnostico") or {}).get(CAUSA_SIN_SOCKET, [])})
    if not pendientes and not sin_socket:
        return []
    cuales = ", ".join(f"{n} ({(v.get('motivo') or '?')[:110]})"
                       for n, v in pendientes.items())
    if sin_socket:
        pids = ", ".join(map(str, sorted(sin_socket)))
        cab = ([f"[i]  cbm pendiente (el cierre no depende de el): {cuales}."] if pendientes else [])
        return cab + [
            f"{'     ' if cab else '[!]  '}El daemon cbm (pid {pids}) esta vivo pero su socket "
            "ya no existe: ningun cliente nuevo puede conectar y esto NO se arregla solo.",
            "     Reintentar no sirve. Avisa a la persona usuaria: reiniciarlo corta cbm en las "
            "sesiones conectadas hasta `/mcp`, asi que no lo hagas por tu cuenta.",
            "     Con su aprobacion: `contexto.py limpiar-cbm --reiniciar-daemon` (`--solo-avisar` "
            "muestra a quien afecta). El pendiente se reintenta solo despues."] + _lineas_diagnostico(pendientes)
    return [f"[i]  cbm pendiente (el cierre no depende de el): {cuales}.",
            "     El arnes lo reintenta solo en el proximo `worktree start` o cierre."
            " No lo reintentes a mano",
            "     ni toques el daemon (`daemon stop`, kill a mano): puede cortar el"
            " indexado en curso y las sesiones MCP conectadas.",
            "     Para procesos huerfanos: `contexto.py limpiar-cbm` (mata solo los"
            " que no tienen sesion viva)."] + _lineas_diagnostico(pendientes)


def _lineas_diagnostico(pendientes: dict) -> list[str]:
    for v in pendientes.values():
        resumen = _resumen_diagnostico(v.get("diagnostico") or {})
        if resumen:
            return [f"     Al fallar: {resumen}."]
    return []


def cbm_indexar(p: dict, parte: dict, verboso: bool, *, forzar=False,
                intentos: int | None = None, respetar_enfriamiento=False) -> None:
    """Indexa (o reindexa) cada raiz declarada en codebase-memory-mcp.

    Complementa a graphify, no lo reemplaza. `index_repository` es incremental:
    la primera vez sobre una raiz indexa el proyecto entero y despues solo lo
    que cambio, asi que el mismo llamado sirve para "primera vez" y para
    "tras implementar una feature". Nunca lanza ni bloquea.

    Cada raiz termina en una de cuatro: al dia (HEAD sin cambios y arbol limpio
    desde el ultimo indexado: ni se llama al daemon), indexada, PENDIENTE (el
    daemon no atendio tras reintentar: queda anotado y se reintenta solo; no es
    un fallo) o fallo (algo que reintentar no arregla, o desconocido: va a
    `fallos` y alguien lo mira). Si una raiz queda pendiente el daemon esta mal
    para todas, asi que las que faltan se anotan sin llamarlo: cinco raices no
    pagan cinco veces la espera.
    """
    cbm = parte["cbm"] = {"indexadas": [], "nuevas": [], "omitido": None,
                          "ramas_omitidas": {}, "al_dia": [], "pendientes": {}}
    if _cbm_desactivado():
        cbm["omitido"] = "HARNESS_SIN_CBM"
        return
    if not shutil.which("codebase-memory-mcp"):
        cbm["omitido"] = "codebase-memory-mcp no esta en el PATH"
        if verboso:
            print("   cbm: omitido (codebase-memory-mcp no esta en el PATH)")
        return
    intentos = intentos or int(_env_num("HARNESS_CBM_INTENTOS", CBM_INTENTOS))
    permitidas = tuple(grafos_config(p).get("ramas_indexables") or RAMAS_CBM)
    estado = _cbm_estado(p)
    raices = raices_grafo(p)
    claves = {str(Path(r["path"])) for r in raices}
    for k in [k for k in estado["pendientes"] if k not in claves]:
        del estado["pendientes"][k]  # raiz que ya no se declara

    plan = []
    for r in raices:
        raiz, nombre = Path(r["path"]), r["nombre"]
        clave = str(raiz)
        ok, motivo = _rama_indexable(raiz, permitidas)
        if not ok:
            cbm["ramas_omitidas"][nombre] = motivo
            if verboso:
                print(f"   cbm index {nombre}: omitido ({motivo})")
            continue
        huella = _cbm_huella(raiz)
        sello = estado["indexado"].get(clave) or {}
        if not forzar and huella and huella[1] and sello.get("head") == huella[0]:
            cbm["al_dia"].append(nombre)
            estado["pendientes"].pop(clave, None)
            if verboso:
                print(f"   cbm index {nombre}: al dia (HEAD {huella[0][:7]}, "
                      "sin llamar al daemon)")
            continue
        previo = estado["pendientes"].get(clave)
        # Con el daemon sin socket no hay nada que enfriar: re-mirar es una lectura de
        # lsof, y en cuanto lo reinicien el siguiente refresco ya indexa.
        if (respetar_enfriamiento and _cbm_en_enfriamiento(previo)
                and (previo or {}).get("causa") != CAUSA_SIN_SOCKET):
            cbm["pendientes"][nombre] = previo
            if verboso:
                print(f"   cbm index {nombre}: pendiente, en espera antes de reintentar")
            continue
        plan.append((r, raiz, clave, huella))

    if plan:
        sin_socket = _cbm_daemon_sin_socket()
        circuito_abierto = bool(sin_socket)
        motivo_circuito = ("daemon no disponible (sin llamarlo de nuevo)" if not sin_socket else
                           f"daemon cbm (pid {', '.join(map(str, sin_socket))}) vivo pero sin "
                           "socket: ningun cliente puede conectar")
        diag = None
        for r, raiz, clave, huella in plan:
            nombre = r["nombre"]
            previo = estado["pendientes"].get(clave) or {}
            # "Nueva" sale del sello local, no de `list_projects`: esa tool
            # abrevia las rutas (@2+sufijo), asi que buscar la ruta en su salida
            # nunca coincidia, y la llamada solo daba otra ocasion de esperar al daemon.
            nueva = clave not in estado["indexado"]
            if circuito_abierto:
                ok, clase, usados = False, "transitorio", 0
                err = motivo_circuito
            else:
                ok, err, clase, usados, salida = _cbm_indexar_raiz(raiz, intentos)
            if ok:
                indicio = _cbm_node_modules_indexado(raiz, salida)
                if indicio:
                    parte["fallos"].append(
                        f"cbm index {nombre}: {indicio}; excluyelo con .cbmignore "
                        "(node_modules/) o revisa la version de cbm")
                cbm["indexadas"].append(nombre)
                if nueva:
                    cbm["nuevas"].append(nombre)
                estado["pendientes"].pop(clave, None)
                # Solo sella si el arbol estaba limpio y sigue igual: un indexado
                # con cambios sin commit no prueba que HEAD este al dia.
                estable = bool(huella and huella[1] and _cbm_huella(raiz) == huella)
                estado["indexado"][clave] = {
                    "nombre": nombre, "at": now_iso(),
                    "head": huella[0] if estable else None}
                resultado = "completo (primera vez)" if nueva else "incremental"
            elif clase == "transitorio":
                if diag is None:
                    diag = _cbm_diagnostico(sin_socket or None)
                    previas = estado.get("diagnosticos") or []
                    estado["diagnosticos"] = (previas + [{"raiz": nombre, "motivo": err, **diag}])[-20:]
                circuito_abierto = True
                pend = {"nombre": nombre, "motivo": err, "ts": time.time(),
                        "desde": previo.get("desde") or now_iso(),
                        "intentos": int(previo.get("intentos") or 0) + usados,
                        "diagnostico": diag}
                if diag.get(CAUSA_SIN_SOCKET):
                    pend["causa"] = CAUSA_SIN_SOCKET
                estado["pendientes"][clave] = pend
                cbm["pendientes"][nombre] = pend
                resultado = (f"PENDIENTE ({usados} intento(s); se reintenta solo)"
                             if not pend.get("causa") else
                             "PENDIENTE (daemon vivo sin socket: no se arregla solo, ver abajo)")
            else:
                estado["pendientes"].pop(clave, None)
                parte["fallos"].append(f"cbm index {nombre}: {err}")
                resultado = "FALLO"
            if verboso:
                print(f"   cbm index {nombre}: {resultado}")
    _cbm_guardar(p, estado)
    if cbm["pendientes"]:
        if any((v.get("diagnostico") or {}).get(CAUSA_SIN_SOCKET)
               for v in cbm["pendientes"].values()):
            cbm["accion"] = ("el daemon cbm esta vivo sin socket y no se arregla solo: avisa a la "
                             "persona usuaria y, con su aprobacion, "
                             "`contexto.py limpiar-cbm --reiniciar-daemon`")
        else:
            cbm["accion"] = ("pendiente: se reintenta solo en el proximo worktree start o "
                             "cierre; no lo reintentes a mano ni toques el daemon "
                             "(daemon stop / kill)")


def _drenar_cbm(p: dict) -> None:
    """Reintenta, una vez y con enfriamiento, lo que un cierre dejo pendiente."""
    if not _cbm_pendientes(p):
        return
    parte = {"fallos": []}
    cbm_indexar(p, parte, verboso=True, intentos=1, respetar_enfriamiento=True)
    for x in parte["fallos"]:
        print(f"[!] {x}")
    for linea in lineas_cbm_pendiente(parte["cbm"]["pendientes"]):
        print(linea)


def refrescar(p: dict, *, forzar=False, max_horas=None, con_vault=True,
              con_hub=True, verboso=True) -> dict:
    """Actualiza grafos vencidos, combina, deriva al hub y regenera el vault.

    Nunca lanza: devuelve un parte con lo que se hizo y lo que fallo. Un
    refresco fallido no debe tumbar el flujo, pero TAMPOCO puede reportarse
    como exito: el parte lo dice y quien llama decide.

    HARNESS_SIN_CONTEXTO NO se mira aqui: esa variable apaga el refresco
    AUTOMATICO (start/close), no una invocacion explicita. Si apagara esta
    tambien, `contexto.py refrescar` mentiria en silencio en CI.
    """
    e = estado_contexto(p)
    tope = max_horas if max_horas is not None else e["max_horas"]
    parte = {"at": now_iso(), "actualizadas": [], "omitidas": [],
             "fallos": [], "combinado": None, "hub": None, "vault": None}

    # Independiente de graphify: se indexa aunque graphify falte.
    cbm_indexar(p, parte, verboso, forzar=forzar)

    if not shutil.which("graphify"):
        parte["fallos"].append("graphify no esta en el PATH")
        # El vault no necesita graphify (sale del backlog y los docs): cortar
        # aqui lo dejaba sin regenerar nunca en una maquina sin graphify. El
        # hub si se salta: derivaria del mismo grafo viejo.
        if con_vault:
            _construir_vault(p, parte, verboso)
        return parte

    for r in e["raices"]:
        raiz = Path(r["path"])
        vencido = forzar or not r["existe"] or (r["edad_h"] or 0) > tope
        if not vencido:
            parte["omitidas"].append(r["nombre"])
            continue
        sub = "update" if r["existe"] else "extract"
        cmd = ["graphify", sub, str(raiz)] + (["--code-only"] if sub == "extract" else [])
        code, out = _run(cmd, raiz)
        # exit 0 no alcanza: graphify puede salir limpio sin dejar el grafo
        # (raiz sin codigo reconocible, permisos, escritura a medias). Si lo
        # contaramos por el codigo de salida, el parte diria "actualizadas" y
        # el merge de mas abajo se saltearia en silencio sobre datos viejos.
        ok, motivo = (False, "") if code != 0 else _grafo_utilizable(Path(r["graph"]))
        if code != 0:
            parte["fallos"].append(f"graphify {sub} {r['nombre']}: {out[-400:]}")
        elif not ok:
            parte["fallos"].append(
                f"graphify {sub} {r['nombre']}: salio 0 pero {motivo}")
        else:
            parte["actualizadas"].append(r["nombre"])
            # Verificado al dia aunque graphify no haya reescrito nada.
            (Path(r["graph"]).parent / SELLO_VERIFICADO).write_text(
                now_iso() + "\n", encoding="utf-8")
        if verboso:
            print(f"   graphify {sub} {r['nombre']}: {'ok' if ok else 'FALLO'}")

    # Combinar solo si hay mas de una raiz declarada. Ojo: se comparan los
    # grafos PRESENTES contra los DECLARADOS. Si una raiz no dejo el suyo,
    # 'len(grafos) > 1' podia ser falso y el merge se salteaba sin dejar
    # rastro: el parte quedaba con combinado=None y sin un solo fallo, o
    # peor, combinaba un subconjunto silencioso y el briefing salia mocho.
    declaradas = [Path(r["graph"]) for r in e["raices"]]
    grafos = [g for g in declaradas if g.exists()]
    faltantes = [str(g) for g in declaradas if not g.exists()]
    if len(declaradas) > 1 and faltantes:
        parte["fallos"].append(
            "no se combina el grafo: faltan " + ", ".join(faltantes))
        if verboso:
            print(f"   merge-graphs: OMITIDO, faltan {len(faltantes)} grafo(s)")
    elif len(grafos) > 1:
        destino = graph_path(p)
        destino.parent.mkdir(parents=True, exist_ok=True)
        # cwd neutro y rutas ABSOLUTAS: graphify etiqueta los repos por el
        # nombre del directorio y con rutas relativas los etiqueta como 'repo'.
        code, out = _run(["graphify", "merge-graphs", *[str(g) for g in grafos],
                          "--out", str(destino)], Path(destino.parent))
        parte["combinado"] = str(destino) if code == 0 else None
        if code != 0:
            parte["fallos"].append(f"merge-graphs: {out[-400:]}")
        elif verboso:
            print(f"   merge-graphs -> {destino.name}: ok")

    if con_hub:
        code, out = _run([sys.executable, str(Path(__file__).parent / "hub.py"),
                          "derivar-graphify"], p["root"])
        parte["hub"] = "ok" if code == 0 else out[-300:]
        if code != 0:
            parte["fallos"].append(f"hub derivar-graphify: {out[-300:]}")
        elif verboso:
            print("   hub derivar-graphify: ok")

    if con_vault:
        _construir_vault(p, parte, verboso)
    return parte


def _construir_vault(p: dict, parte: dict, verboso: bool) -> None:
    code, out = _run([sys.executable, str(Path(__file__).parent / "vault.py"),
                      "build"], p["root"])
    parte["vault"] = "ok" if code == 0 else out[-300:]
    if code != 0:
        parte["fallos"].append(f"vault build: {out[-300:]}")
    elif verboso:
        print("   vault build: ok")


def refrescar_si_vencido(p: dict, *, etiqueta: str, bloqueante=False) -> dict | None:
    """Gancho para worktree start / gate close. Avisa, no miente, no bloquea."""
    if _desactivado():
        print(f"[i]  HARNESS_SIN_CONTEXTO: sin refresco automatico ({etiqueta}).")
        return None
    e = estado_contexto(p)
    if e["fresco"] and not e["vault"]["vencido"]:
        _drenar_cbm(p)  # el grafo fresco no dice nada de un cbm que quedo pendiente
        print(f"[i]  contexto fresco ({etiqueta}); no hay nada que refrescar.")
        return None
    if e["fresco"]:
        # Solo cambio el backlog o un doc: regenerar el vault basta, sin
        # relanzar el merge de grafos ni el hub.
        _drenar_cbm(p)
        print(f"[i]  grafo fresco, vault desactualizado; regenerandolo antes de {etiqueta}...")
        parte = {"at": now_iso(), "fallos": [], "vault": None}
        _construir_vault(p, parte, verboso=True)
    else:
        print(f"[i]  contexto vencido ({', '.join(e['vencidas'])}); refrescando antes de {etiqueta}...")
        parte = refrescar(p, con_vault=True, con_hub=True)
    if parte["fallos"]:
        print("[!] el refresco de contexto no quedo completo:")
        for x in parte["fallos"]:
            print(f"     - {x}")
        if bloqueante:
            sys.exit("[!!] contexto no refrescado y se pidio bloqueante")
    for linea in lineas_cbm_pendiente((parte.get("cbm") or {}).get("pendientes")):
        print(linea)
    return parte


def cmd_refrescar(args) -> None:
    p = paths()
    parte = refrescar(p, forzar=args.forzar, max_horas=args.max_horas,
                      con_vault=not args.sin_vault, con_hub=not args.sin_hub)
    print(json.dumps(parte, ensure_ascii=False, indent=2))
    sys.exit(1 if parte["fallos"] else 0)


def cmd_cbm(args) -> None:
    parte = {"fallos": []}
    cbm_indexar(paths(), parte, verboso=True, forzar=args.forzar)
    print(json.dumps(parte, ensure_ascii=False, indent=2))
    # Omitido (sin binario / apagado) o pendiente no son exito silencioso: este
    # es el comando explicito, asi que sale con 1. El cierre automatico no.
    sys.exit(1 if parte["fallos"] or parte["cbm"]["omitido"]
             or parte["cbm"]["pendientes"] else 0)


def cmd_limpiar_cbm(args) -> None:
    import cbm_procesos
    if args.reiniciar_daemon:
        sys.exit(cbm_procesos.reiniciar_daemon(solo_avisar=args.solo_avisar))
    sys.exit(cbm_procesos.limpiar(matar_huerfanos=not args.solo_avisar))


# --- briefing compacto ------------------------------------------------------

def _cargar_grafo(p: dict):
    g = graph_path(p)
    if not g.exists():
        return None
    try:
        return json.loads(g.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _servicio_de(src: str) -> str | None:
    m = SERVICE_RE.search(str(src or "").replace("\\", "/"))
    return m.group(1) if m else None


def superficie(graph: dict, micros: list[str], tope=12) -> dict:
    """Archivos del/los micros con mas acoplamiento HACIA AFUERA.

    El grafo crudo (`graphify query`) devuelve decenas de nodos sin jerarquia y
    se trunca a mitad de camino. Aqui se agrega por archivo y se ordena por
    aristas utiles que cruzan el limite del archivo: es lo que un implementer o
    un revisor necesita mirar primero, en una fraccion de los tokens.

    El ambito puede no ser un microservicio: 'admin', 'landing' o
    'projects/portal' son carpetas del monorepo y no matchean SERVICE_RE. Se
    cae a coincidencia por ruta antes que devolver vacio; un ambito que no
    engancha nada se reporta en 'sin_match' en vez de fingir un grafo pobre.
    """
    nodes = {n.get("id"): n for n in graph.get("nodes", [])}
    edges = graph.get("edges") or graph.get("links") or []
    ambitos = [m.strip("/").replace("\\", "/") for m in micros if m.strip("/")]

    def ambito_de(src: str) -> str | None:
        ruta = str(src or "").replace("\\", "/")
        if not ambitos:
            return _servicio_de(ruta)
        for a in ambitos:
            if a == _servicio_de(ruta) or re.search(
                    rf"(^|/){re.escape(a)}(/|$)", ruta):
                return a
        return None

    dentro, salientes = {}, {}
    vistos: set[str] = set()
    for e in edges:
        rel = str(e.get("relation") or e.get("type") or "").lower()
        if rel not in REL_UTILES:
            continue
        ns, nt = nodes.get(e.get("source")), nodes.get(e.get("target"))
        if not ns or not nt:
            continue
        fs, ft = ns.get("source_file") or "", nt.get("source_file") or ""
        if fs == ft or not fs or not ft:
            # Un nodo sin source_file no ubica nada: contarlo produce filas
            # "a --references--> " que ocupan lugar y no dicen adonde ir.
            continue
        ss, st = ambito_de(fs), ambito_de(ft)
        if ambitos and ss is None and st is None:
            continue
        for x in (ss, st):
            if x:
                vistos.add(x)
        if ss is not None:
            dentro[fs] = dentro.get(fs, 0) + 1
            if st != ss:
                # Solo interesa lo que CRUZA el limite del ambito: dentro de un
                # mismo servicio el acoplamiento ya lo resume 'archivos'.
                salientes[(fs, ft, rel)] = salientes.get((fs, ft, rel), 0) + 1
        if st is not None and st != ss:
            dentro[ft] = dentro.get(ft, 0) + 1
    top_arch = sorted(dentro.items(), key=lambda x: -x[1])[:tope]
    top_cross = sorted(salientes.items(), key=lambda x: -x[1])[:tope]
    return {"archivos": top_arch, "cruces": top_cross,
            "n_archivos": len(dentro), "n_cruces": len(salientes),
            "sin_match": [a for a in ambitos if a not in vistos]}


def _impacto_hub(micro: str) -> list[str]:
    code, out = _run([sys.executable, str(Path(__file__).parent / "hub.py"),
                      "impacto", "--microservicio", micro], Path.cwd())
    if code != 0:
        return [f"(hub no disponible: {out.splitlines()[0][:120] if out else 'sin salida'})"]
    return [l for l in out.splitlines() if l.strip()]


def _impacto_compacto(proyecto: str, micro: str) -> list[str]:
    """Una linea por servicio en vez del reporte entero del hub.

    `hub.py impacto` imprime cabecera, secciones y una linea por dependencia:
    x4 servicios son ~40 lineas para decir dos listas de nombres. El brief se
    lee entero en cada arranque, asi que aqui gana la densidad.
    """
    nombre = micro.split("/")[-1]
    filas = _impacto_hub(f"{proyecto}/{nombre}")
    rompe, depende, seccion = [], [], None
    for l in filas:
        s = l.strip()
        if s.startswith("Si tocas esto"):
            seccion = rompe
        elif s.startswith("Depende de"):
            seccion = depende
        elif s.startswith(("<-", "->")) and seccion is not None:
            seccion.append(s[2:].split("[")[0].strip().split("/")[-1])
        elif "no disponible" in s:
            return [f"  [{nombre}] {s}"]
    if not rompe and not depende:
        return [f"  [{nombre}] sin dependencias declaradas en el hub"]
    return [f"  [{nombre}] rompe a: {', '.join(rompe) or '-'} | usa: {', '.join(depende) or '-'}"]


def _lecciones(data: dict | None = None) -> list[str]:
    """Lecciones RELEVANTES: las que este proyecto ya declaro en algun cierre.

    `leccion.py list` enumera todas las skills instaladas del perfil (>100 en
    una maquina usada): pegarlas en cada brief es ruido caro que empuja fuera
    lo que si importa. El indice completo sigue a un comando de distancia.
    """
    usadas = sorted({str(f["leccion"]) for f in (data or {}).get("features", [])
                     if f.get("leccion") and f["leccion"] != "ninguna"})
    code, out = _run([sys.executable, str(Path(__file__).parent / "leccion.py"),
                      "list"], Path.cwd())
    if code != 0:
        return [f"{c}  (no se pudo verificar si esta instalada)" for c in usadas]
    catalogo = {}
    for ln in out.splitlines():
        if ln.startswith("   ") and "lineas" in ln:
            nombre = ln.strip().split()[0].split("/")[-1]
            catalogo[nombre] = ln.strip()
    filas = []
    for c in usadas:
        filas.append(catalogo.get(c, f"{c}  <- FALTA: declarada en un cierre pero no instalada"))
    return filas


# Documentos que registran una decision ya tomada: cambian lo que se puede
# disenar, y el spec es el momento de enterarse.
PREFIJOS_DECISION = ("decision", "enmienda", "acta", "adr", "errata")


def _docs_humanos(p: dict) -> list[Path]:
    """Los .md de docs/ que escribio alguien: sin .git/.obsidian ni el vault
    generado (sale del mismo backlog que el brief), pero con vault/notas/."""
    docs = p["docs"]
    out: list[Path] = []
    for raiz, dirs, archivos in os.walk(docs):
        rel = Path(raiz).relative_to(docs).parts
        dirs[:] = [d for d in dirs if not d.startswith(".")
                   and (rel != ("vault",) or d == "notas")]
        if rel == ("vault",):
            continue
        out += [Path(raiz) / a for a in archivos if a.endswith(".md")]
    return out


def _menciona(texto: str, nombres: list[str]) -> bool:
    # Con borde: 'admin' no debe enganchar 'administrador' ni 'front-admin'.
    return any(re.search(rf"(?<![\w-]){re.escape(n)}(?![\w-])", texto)
               for n in nombres)


def _relacionados(p: dict, data: dict, f: dict, micros: list[str],
                  tope: int) -> list[str]:
    """Rutas de docs/ que conviene abrir ANTES de disenar. Solo rutas.

    Buscar por nombre de servicio a secas no sirve: en un proyecto real
    `ms-tenant-service` aparece en 539 archivos (~2,7M tokens). Aqui se
    recorren NOMBRES de archivo y solo se lee el texto de los pocos que son
    decisiones o notas propias; el resto del ranking sale del backlog.
    """
    if tope <= 0:
        return []
    fid = str(f["id"])
    tok = re.compile(rf"(?:^|[-_]){re.escape(fid)}(?:[-_]|$)")
    propios = {spec_path(p, f).resolve(), impl_path(p, f).resolve()}  # ya en el pie
    docs = sorted(_docs_humanos(p), key=lambda q: -q.stat().st_mtime)

    def rel(q: Path) -> str:
        return q.relative_to(p["root"]).as_posix()

    def leer(q: Path) -> str:
        try:
            return q.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    notas, de_esta, decisiones = [], [], []
    vistos: set[str] = set()
    for q in docs:
        partes = q.relative_to(p["docs"]).parts
        if partes[:2] == ("vault", "notas"):
            t = leer(q)
            if re.search(rf"Feature-{re.escape(fid)}(?!\d)", t) or _menciona(t, micros):
                notas.append(("tuya", rel(q)))
            continue
        # la primera carpeta o archivo cuyo nombre lleva el id: una carpeta
        # entera de artefactos de la feature es UNA entrada, no veinte.
        i = next((k for k, x in enumerate(partes)
                  if tok.search(Path(x).stem if k == len(partes) - 1 else x)), None)
        if i is not None and q.resolve() not in propios:
            ruta = (p["docs"].joinpath(*partes[:i + 1]))
            clave = rel(ruta) + ("/" if i < len(partes) - 1 else "")
            if clave not in vistos:
                vistos.add(clave)
                de_esta.append(("feature", clave))
            continue
        if q.stem.lower().startswith(PREFIJOS_DECISION):
            t = leer(q)
            if re.search(rf"#{re.escape(fid)}\b", t) or _menciona(t, micros):
                decisiones.append(("decision", rel(q)))

    previas = []
    comunes = set(micros)
    otras = [x for x in data["features"] if str(x.get("id")) != fid
             and x.get("status") == "done" and comunes & set(_micros_declarados(x))]
    for x in sorted(otras, key=lambda x: str(x.get("closed_at") or ""), reverse=True):
        doc = next((d for d in (review_path(p, x), spec_path(p, x)) if d.exists()), None)
        if doc:
            svc = ", ".join(sorted(comunes & set(_micros_declarados(x))))
            previas.append(("previa", f"{rel(doc)}  (#{x['id']} "
                                      f"{str(x.get('name', ''))[:50]}; {svc})"))

    # Cupo por tipo en orden de prioridad: lo tuyo, lo de esta feature, las
    # decisiones y al final las features vecinas (las hay por decenas).
    filas, sobran = [], 0
    for grupo, cupo in ((notas, 2), (de_esta, 3), (decisiones, 3), (previas, 3)):
        toma = grupo[:max(0, min(cupo, tope - len(filas)))]
        filas += toma
        sobran += len(grupo) - len(toma)
    if not filas:
        return []
    L = ["", "documentos relacionados (solo rutas; abre los que toquen el diseno):"]
    L += [f"  {tipo:<8}  {ruta}" for tipo, ruta in filas]
    if sobran:
        L.append(f"  (+{sobran} mas sin listar)")
    return L


def cmd_brief(args) -> None:
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, args.feature)
    proyecto = data.get("project") or p["root"].name
    e = estado_contexto(p)
    sp = spec_path(p, f)
    stext = sp.read_text(encoding="utf-8") if sp.exists() else ""
    acs = spec_acs(stext)
    cmds = ac_comandos(stext)
    costuras = ac_costuras(stext)
    micros = _micros_declarados(f)

    L: list[str] = []
    L.append(f"== BRIEF #{f['id']} {f.get('name')} ({proyecto}) ==")
    L.append(f"estado: {f.get('status')} · rama: {f.get('branch') or '-'} · "
             f"worktree: {f.get('worktree') or '(sin worktree)'}")
    reqs = requiere_declarados(f)
    if reqs:
        bloq = bloqueos_feature(data, f)
        estado_dep = f"[!] bloqueada por {', '.join(bloq)}" if bloq else "ok (todas cerradas)"
        L.append(f"dependencias: {', '.join(reqs)} -> {estado_dep}")
    if not e["fresco"]:
        L.append(f"[!] contexto VENCIDO ({', '.join(e['vencidas'])}): lo de abajo "
                 "puede no reflejar el arbol actual. Corre contexto.py refrescar.")
    if e["cbm_pendientes"]:
        L.append("[i] el indice de codebase-memory-mcp esta atrasado en "
                 f"{', '.join(e['cbm_pendientes'])}: orienta menos; confirma leyendo el archivo.")

    L.append("")
    L.append(f"AC ({len(acs)}):")
    lineas_ac = spec_ac_lineas(stext)
    for ac in acs:
        L.append(f"  {lineas_ac.get(ac, ac)[:200]}")
        if ac in costuras:
            L.append(f"      costura: {costuras[ac]}")
        if ac in cmds:
            L.append(f"      comando: {cmds[ac]}")

    reglas = [k for k, v in data["rules"].items()
              if k.startswith("require_") and v]
    L.append("")
    L.append("reglas activas: " + (", ".join(reglas) or "ninguna"))
    L.append("rutas protegidas (NO editar): " +
             ", ".join(data["rules"].get("rutas_protegidas", [])))

    # Lo que el PRD/SDD dice de esta feature; el revisor no lo recibe por la
    # misma razon que no recibe los relacionados.
    if getattr(args, "con_producto", True):
        import producto
        L += producto.lineas_brief(p, data, f)

    if micros:
        L.append("")
        L.append("impacto cross-repo (Memory Hub):")
        for m in micros[:4]:
            L += _impacto_compacto(proyecto, m)

    g = _cargar_grafo(p)
    if g is None:
        L.append("")
        L.append(f"[!] sin grafo en {graph_path(p)}: corre contexto.py refrescar")
    else:
        s = superficie(g, micros, tope=args.max_archivos)
        L.append("")
        L.append(f"superficie de contacto (grafo, {len(g.get('nodes', []))} nodos; "
                 f"{s['n_archivos']} archivos y {s['n_cruces']} cruces, top {args.max_archivos}):")
        for arch, n in s["archivos"]:
            L.append(f"  {n:>4}  {arch}")
        if s["sin_match"]:
            L.append("  [!] sin nodos en el grafo: " + ", ".join(s["sin_match"]) +
                     " (ambito mal declarado o raiz de grafo faltante en harness/grafos.json)")
        if s["cruces"]:
            L.append("  cruces entre servicios/paquetes:")
            for (fs, ft, rel), n in s["cruces"]:
                L.append(f"    {fs} --{rel}--> {ft}  (x{n})")

    lec = _lecciones(data)
    if lec:
        instaladas = [x for x in lec if "FALTA" not in x]
        faltan = [x.split("  <-")[0] for x in lec if "FALTA" in x]
        L.append("")
        L.append("lecciones ya aplicadas aqui (leelas si tocan tu caso; "
                 "catalogo completo: leccion.py list):")
        L += [f"  {x}" for x in instaladas[:args.max_lecciones]]
        if faltan:
            # Declaradas en un cierre pero sin SKILL instalada: no se pueden
            # leer, y nombrarlas una por linea gasta el brief sin aportar.
            L.append(f"  ({len(faltan)} declaradas sin skill instalada: "
                     f"{', '.join(faltan[:4])}{' ...' if len(faltan) > 4 else ''})")

    # 0 lo apaga: el revisor juzga spec contra codigo, no la historia.
    L += _relacionados(p, data, f, micros, getattr(args, "max_relacionados", 8))

    ip = impl_path(p, f)
    pie = ["",
           f"spec: {sp if sp.exists() else '(AUSENTE)'}",
           f"evidencia: {ip if ip.exists() else '(aun no existe)'}",
           "",
           "Este brief es un INDICE, no evidencia: abre los archivos que cites."]

    if args.max_lineas and len(L) + len(pie) > args.max_lineas:
        # El recorte va por el MEDIO: truncar por el final se comia las rutas
        # de spec y evidencia, que son justo lo que el agente tiene que abrir.
        cupo = max(1, args.max_lineas - len(pie) - 1)
        recorte = len(L) - cupo
        L = L[:cupo] + [f"... {recorte} linea(s) recortadas (sube --max-lineas)"]
    print("\n".join(L + pie))


def main() -> None:
    ap = argparse.ArgumentParser(description="Contexto (grafo/hub/vault) del harness-flow")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("estado"); s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_estado)
    s = sub.add_parser("refrescar")
    s.add_argument("--forzar", action="store_true")
    s.add_argument("--max-horas", type=float, dest="max_horas")
    s.add_argument("--sin-vault", action="store_true", dest="sin_vault")
    s.add_argument("--sin-hub", action="store_true", dest="sin_hub")
    s.set_defaults(fn=cmd_refrescar)
    s = sub.add_parser("cbm", help="indexa/reindexa las raices en codebase-memory-mcp")
    s.add_argument("--forzar", action="store_true",
                   help="reindexa aunque HEAD no haya cambiado desde el ultimo indexado")
    s.set_defaults(fn=cmd_cbm)
    s = sub.add_parser("limpiar-cbm", help="avisa que procesos cbm estan en uso y mata "
                                           "solo los huerfanos")
    s.add_argument("--solo-avisar", action="store_true", dest="solo_avisar")
    s.add_argument("--reiniciar-daemon", action="store_true", dest="reiniciar_daemon",
                   help="termina el daemon cbm SOLO si su socket desaparecio (vivo pero "
                        "inalcanzable) y comprueba que un cliente nuevo conecta; con "
                        "--solo-avisar dice a quien afectaria")
    s.set_defaults(fn=cmd_limpiar_cbm)
    s = sub.add_parser("brief"); s.add_argument("--feature", required=True)
    s.add_argument("--max-lineas", type=int, default=90, dest="max_lineas")
    s.add_argument("--max-archivos", type=int, default=12, dest="max_archivos")
    s.add_argument("--max-lecciones", type=int, default=12, dest="max_lecciones")
    s.add_argument("--max-relacionados", type=int, default=8, dest="max_relacionados",
                   help="rutas de docs/ relacionadas (0 = sin la seccion)")
    s.add_argument("--sin-producto", action="store_false", dest="con_producto",
                   help="sin la seccion del PRD/SDD (el briefing del revisor la omite)")
    s.set_defaults(fn=cmd_brief)
    a = ap.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
