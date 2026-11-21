#!/usr/bin/env python3
"""Wrapper y resolutor de aislamiento por proyecto para codebase-memory-mcp (CBM).

Resuelve dos problemas de usar un unico daemon global en `/tmp/cbm-daemon-<uid>`:
  1. Multiples proyectos en paralelo (DEREC, Online-Invoice, calpil-ingenieria...)
     comparten lock, cola de indexado y caidas: reiniciar uno corta a todos.
  2. En macOS, archivos regulares sin actividad en `/tmp` (como `.sock.identity`)
     pueden borrarse tras varios dias, dejando al daemon vivo pero "unverified".

Este modulo calcula un `CBM_RUNTIME_DIR` y `CBM_CACHE_DIR` deterministas y cortos
fuera de `/tmp` (`~/.cbm/p/<hash12>/{r,c}`, bien por debajo del limite macOS de
104 bytes para sockets UNIX `sun_path`), anclados a la raiz del proyecto:
  1. Ancestro con `harness/feature_list.json` (unifica todos los microservicios
     de un mismo proyecto multi-repo en un solo indice).
  2. Si no existe, raiz del repo git principal (resolviendo worktrees a su repo).
  3. Si no es git, el directorio de trabajo actual.

Uso como servidor MCP o CLI (reemplaza el proceso con `os.execvpe`, 0 RAM extra):
  cbm_proyecto.py                         # arranca codebase-memory-mcp stdio aislado
  cbm_proyecto.py cli --quiet list_projects '{}'

Comandos propios del arnes (prefijo `--harness-*`, no chocan con flags de CBM):
  cbm_proyecto.py --harness-info [--cwd <ruta>] [--json]
  cbm_proyecto.py --harness-env  [--cwd <ruta>]
  cbm_proyecto.py --harness-activar
  cbm_proyecto.py --harness-desactivar
  cbm_proyecto.py --harness-config-mcp
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

EXE = "codebase-memory-mcp"
MARCA_MODO_AISLADO = "modo-aislado"
# En macOS sockaddr_un.sun_path mide 104 bytes; CBM agrega `/cbm-daemon-<uid>/cbm-<16hex>.sock` (~42 bytes).
_MARGEN_SOCKET_CBM = 44
_LIMITE_SUN_PATH = 104


def base_cbm(base: Path | None = None) -> Path:
    """Directorio base persistente (fuera de /tmp) para daemons CBM aislados."""
    if base is not None:
        return Path(base).expanduser().resolve()
    env = os.environ.get("HARNESS_CBM_HOME", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / ".cbm").resolve()


def _git_common_root(ruta: Path) -> Path | None:
    """Raiz del repo git principal (resuelve worktrees a la raiz real)."""
    try:
        r_top = subprocess.run(
            ["git", "-C", str(ruta), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if r_top.returncode != 0 or not r_top.stdout.strip():
            return None
        top = Path(r_top.stdout.strip()).resolve()
        r_com = subprocess.run(
            ["git", "-C", str(ruta), "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=5,
        )
        if r_com.returncode == 0 and r_com.stdout.strip():
            com = Path(r_com.stdout.strip())
            if not com.is_absolute():
                com = (ruta / com).resolve()
            else:
                com = com.resolve()
            if com.name == ".git":
                return com.parent.resolve()
        return top
    except (OSError, subprocess.SubprocessError):
        return None


def _buscar_raiz_harness(inicio: Path) -> Path | None:
    """Sube desde `inicio` buscando `harness/feature_list.json`."""
    cur = inicio.resolve()
    for d in (cur, *cur.parents):
        if (d / "harness" / "feature_list.json").is_file():
            return d
    return None


def raiz_proyecto_cbm(cwd: Path | str | None = None) -> Path:
    """Resuelve la raiz canonica del proyecto para agrupar su daemon CBM.

    Prioridad:
      1. `HARNESS_CBM_PROJECT_ROOT` si esta definido.
      2. Ancestro con `harness/feature_list.json` desde `cwd`.
      3. Si `cwd` es un worktree git (`<repo>-wt/<feat>`), resuelve el repo
         principal y vuelve a buscar `harness/feature_list.json` hacia arriba.
      4. Raiz del repo git principal.
      5. `cwd` resuelto.
    """
    env_root = os.environ.get("HARNESS_CBM_PROJECT_ROOT", "").strip()
    if env_root:
        return Path(env_root).expanduser().resolve()

    inicio = Path(cwd).expanduser().resolve() if cwd is not None else Path.cwd().resolve()
    if inicio.is_file():
        inicio = inicio.parent

    h_directo = _buscar_raiz_harness(inicio)
    if h_directo is not None:
        return h_directo

    git_root = _git_common_root(inicio)
    if git_root is not None:
        h_desde_git = _buscar_raiz_harness(git_root)
        if h_desde_git is not None:
            return h_desde_git
        return git_root

    return inicio


def clave_proyecto(raiz: Path) -> str:
    return hashlib.sha256(str(raiz.resolve()).encode("utf-8")).hexdigest()[:12]


def rutas_proyecto(raiz: Path, *, base: Path | None = None) -> dict[str, Any]:
    """Calcula `runtime_dir` y `cache_dir` para `raiz` respetando el limite sun_path."""
    raiz = Path(raiz).resolve()
    b = base_cbm(base)
    clave = clave_proyecto(raiz)
    pdir = b / "p" / clave
    rdir = pdir / "r"
    cdir = pdir / "c"
    meta = pdir / "project.json"

    fallback_tmp = False
    if os.name != "nt" and len(str(rdir)) + _MARGEN_SOCKET_CBM > _LIMITE_SUN_PATH:
        uid = os.getuid() if hasattr(os, "getuid") else 0
        rdir = Path(f"/tmp/cbm-{uid}/{clave}")
        fallback_tmp = True

    return {
        "root": str(raiz),
        "name": raiz.name,
        "key": clave,
        "project_dir": str(pdir),
        "runtime_dir": str(rdir),
        "cache_dir": str(cdir),
        "meta_file": str(meta),
        "sun_path_estimado": len(str(rdir)) + _MARGEN_SOCKET_CBM,
        "fallback_tmp": fallback_tmp,
    }


def preparar_directorios(info: dict[str, Any]) -> dict[str, Any]:
    """Crea `runtime_dir` y `cache_dir` con permiso 0700 y registra `project.json`."""
    pdir = Path(info["project_dir"])
    rdir = Path(info["runtime_dir"])
    cdir = Path(info["cache_dir"])
    for d in (pdir, rdir, cdir):
        d.mkdir(parents=True, exist_ok=True)
        try:
            d.chmod(0o700)
        except OSError:
            pass
    meta = Path(info["meta_file"])
    contenido = json.dumps(
        {"root": info["root"], "name": info["name"], "key": info["key"],
         "runtime_dir": info["runtime_dir"], "cache_dir": info["cache_dir"]},
        ensure_ascii=False, indent=2,
    ) + "\n"
    destinos_meta = [meta]
    if info.get("fallback_tmp"):
        destinos_meta.append(rdir / "project.json")
    for destino in destinos_meta:
        try:
            if not destino.is_file() or destino.read_text(encoding="utf-8") != contenido:
                tmp = destino.with_suffix(".tmp")
                tmp.write_text(contenido, encoding="utf-8")
                tmp.replace(destino)
        except OSError:
            pass
    return info


def modo_aislado_activo(raiz: Path | None = None, *, base: Path | None = None) -> bool:
    """True si `contexto.py` debe hablar con el daemon aislado del proyecto.

    Precedencia:
      1. `HARNESS_CBM_GLOBAL=1` o `HARNESS_CBM_AISLADO=0|false|no` -> False.
      2. `HARNESS_CBM_AISLADO=1|true|yes` -> True.
      3. Si el usuario ya paso `CBM_RUNTIME_DIR` o `CBM_CACHE_DIR` -> False
         (se respeta el entorno explicito sin pisarlo).
      4. `harness/grafos.json` declara `"cbm_aislado": true|false`.
      5. Existe la marca global `~/.cbm/modo-aislado` (creada por `--harness-activar`).
      6. Ya existe `~/.cbm/p/<key>/project.json` para esta raiz (el wrapper ya corrio aqui).
    """
    if os.environ.get("HARNESS_CBM_GLOBAL", "").strip().lower() in ("1", "true", "yes", "on"):
        return False
    flag = os.environ.get("HARNESS_CBM_AISLADO", "").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    if flag in ("1", "true", "yes", "on"):
        return True
    if os.environ.get("CBM_RUNTIME_DIR") or os.environ.get("CBM_CACHE_DIR"):
        return False

    if raiz is not None:
        grafos = Path(raiz) / "harness" / "grafos.json"
        if grafos.is_file():
            try:
                cfg = json.loads(grafos.read_text(encoding="utf-8"))
                if isinstance(cfg, dict) and isinstance(cfg.get("cbm_aislado"), bool):
                    return cfg["cbm_aislado"]
            except (OSError, ValueError):
                pass

    b = base_cbm(base)
    if (b / MARCA_MODO_AISLADO).is_file():
        return True
    if raiz is not None:
        info = rutas_proyecto(raiz, base=b)
        if Path(info["meta_file"]).is_file():
            return True
    return False


def env_para_proyecto(raiz: Path, *, preparar: bool = True, base: Path | None = None) -> dict[str, str]:
    """Devuelve `{"CBM_RUNTIME_DIR": ..., "CBM_CACHE_DIR": ...}` para `raiz`."""
    info = rutas_proyecto(raiz, base=base)
    if preparar:
        preparar_directorios(info)
    return {
        "CBM_RUNTIME_DIR": info["runtime_dir"],
        "CBM_CACHE_DIR": info["cache_dir"],
    }


def env_si_aislado(raiz: Path | None, *, preparar: bool = True, base: Path | None = None) -> dict[str, str]:
    """Variables CBM del proyecto SOLO si el aislamiento esta activo; si no, `{}`."""
    if raiz is None or not modo_aislado_activo(raiz, base=base):
        return {}
    return env_para_proyecto(raiz, preparar=preparar, base=base)


def proyecto_de_socket(ruta_sock: str) -> dict[str, str] | None:
    """Dada la ruta de un socket dentro de `<base>/p/<key>/r/...`, lee `project.json`."""
    try:
        p = Path(ruta_sock)
        for anc in p.parents:
            meta = anc / "project.json"
            if meta.is_file():
                data = json.loads(meta.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("name"):
                    return {
                        "name": str(data["name"]),
                        "root": str(data.get("root") or ""),
                        "key": str(data.get("key") or anc.name),
                    }
    except (OSError, ValueError):
        pass
    return None


def activar_modo_aislado(activar: bool, *, base: Path | None = None) -> Path:
    b = base_cbm(base)
    marca = b / MARCA_MODO_AISLADO
    if activar:
        b.mkdir(parents=True, exist_ok=True)
        marca.write_text("1\n", encoding="utf-8")
    elif marca.exists():
        marca.unlink()
    return marca


def snippets_mcp(wrapper_path: Path | None = None) -> str:
    ruta = str((wrapper_path or Path(__file__).resolve()))
    py = sys.executable
    return f"""Configura el servidor MCP `codebase-memory-mcp` apuntando a este wrapper para
aislar un daemon por proyecto (fuera de `/tmp`, sin choques entre proyectos):

1. Claude Code (`~/.claude.json` -> `mcpServers`):
{{
  "codebase-memory-mcp": {{
    "command": "{py}",
    "args": ["{ruta}"]
  }}
}}

2. AGY / Antigravity (`~/.gemini/config/mcp_config.json`) y Gemini CLI (`~/.gemini/settings.json`):
{{
  "codebase-memory-mcp": {{
    "command": "{py}",
    "args": ["{ruta}"]
  }}
}}

3. Grok (`~/.grok/config.toml`) y OpenAI Codex (`~/.codex/config.toml`):
[mcp_servers.codebase-memory-mcp]
command = "{py}"
args = ["{ruta}"]

4. Hermes (`~/.hermes/config.yaml` -> `mcp_servers`):
codebase-memory-mcp:
  command: "{py}"
  args: ["{ruta}"]

Activa tambien el modo aislado para `contexto.py` (sincroniza CLI y MCP):
  {shlex.quote(py)} {shlex.quote(ruta)} --harness-activar
"""


def _exec_cbm(argv: list[str]) -> int:
    cbm_bin = shutil.which(EXE)
    if not cbm_bin:
        sys.stderr.write(f"[!!] {EXE} no esta en el PATH.\n")
        return 127

    env = dict(os.environ)
    if env.get("HARNESS_CBM_GLOBAL", "").strip().lower() not in ("1", "true", "yes", "on"):
        if not env.get("CBM_RUNTIME_DIR") and not env.get("CBM_CACHE_DIR"):
            raiz = raiz_proyecto_cbm()
            env.update(env_para_proyecto(raiz, preparar=True))

    os.execvpe(cbm_bin, [cbm_bin, *argv], env)
    return 0  # unreachable


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0].startswith("--harness-"):
        cmd = args[0]
        resto = args[1:]
        if cmd == "--harness-info":
            cwd = None
            as_json = False
            i = 0
            while i < len(resto):
                if resto[i] == "--cwd" and i + 1 < len(resto):
                    cwd = resto[i + 1]; i += 2
                elif resto[i] == "--json":
                    as_json = True; i += 1
                else:
                    i += 1
            raiz = raiz_proyecto_cbm(cwd)
            info = rutas_proyecto(raiz)
            info["modo_aislado_contexto"] = modo_aislado_activo(raiz)
            if as_json:
                print(json.dumps(info, ensure_ascii=False, indent=2))
            else:
                print(f"proyecto:              {info['name']} ({info['root']})")
                print(f"clave:                 {info['key']}")
                print(f"CBM_RUNTIME_DIR:       {info['runtime_dir']} (sun_path ~{info['sun_path_estimado']}B / 104B)")
                print(f"CBM_CACHE_DIR:         {info['cache_dir']}")
                print(f"modo aislado contexto: {'SI' if info['modo_aislado_contexto'] else 'NO (usa --harness-activar)'}")
            return 0
        if cmd == "--harness-env":
            cwd = resto[1] if len(resto) >= 2 and resto[0] == "--cwd" else None
            raiz = raiz_proyecto_cbm(cwd)
            env = env_para_proyecto(raiz, preparar=True)
            print(f"export CBM_RUNTIME_DIR={shlex.quote(env['CBM_RUNTIME_DIR'])}")
            print(f"export CBM_CACHE_DIR={shlex.quote(env['CBM_CACHE_DIR'])}")
            return 0
        if cmd == "--harness-activar":
            marca = activar_modo_aislado(True)
            print(f"[ok] modo CBM aislado por proyecto activado ({marca}).")
            print("     Ahora `contexto.py` usara el mismo daemon aislado que este wrapper.")
            return 0
        if cmd == "--harness-desactivar":
            marca = activar_modo_aislado(False)
            print(f"[ok] modo CBM aislado desactivado ({marca} eliminada): vuelve al daemon global.")
            return 0
        if cmd == "--harness-config-mcp":
            print(snippets_mcp())
            return 0
        sys.stderr.write(f"[!!] opcion desconocida: {cmd}\n")
        return 2

    return _exec_cbm(args)


if __name__ == "__main__":
    sys.exit(main())
