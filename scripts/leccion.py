#!/usr/bin/env python3
"""Memoria procedural: vive en las SKILLS del agente, no en el repo.

Una leccion es una skill por CLASE de trabajo (nunca por id de feature). Asi
viaja contigo entre proyectos y el agente la carga sola cuando aplica, en vez
de quedarse enterrada en el docs/ de un repo. Funciona con Hermes, Claude
Code, GPT/Codex, Grok y Kimi Code: la raiz de skills se detecta segun el host.

  leccion.py list                skills disponibles (candidatas a leccion)
  leccion.py ver <clase>         imprime la skill
  leccion.py existe <clase>      exit 0 si existe (lo usa el gate de cierre)
  leccion.py donde               raices de skills, en orden de precedencia
  leccion.py plantilla <clase>   esqueleto de SKILL.md

El AGENTE escribe y patchea las lecciones con la herramienta de su host
(skill_manage en Hermes; escribiendo el SKILL.md en Claude Code, GPT y Grok),
no este script. HARNESS_SKILLS_DIR fuerza una raiz unica si la deteccion no aplica.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

TOPE_LINEAS = 250


def _casa() -> Path:
    """HOME respetando el entorno (los tests lo redefinen); no cachea."""
    return Path(os.environ.get("HOME") or os.environ.get("USERPROFILE") or Path.home())


def _host() -> str:
    """Host de ejecucion. Un solo detector: el de entorno.py, para no divergir."""
    try:
        propio = Path(__file__).absolute().parent
        spec = importlib.util.spec_from_file_location("_harness_flow_entorno_runtime", propio / "entorno.py")
        if spec is None or spec.loader is None:
            raise ImportError("entorno.py no disponible")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.host_agente()
    except ValueError as exc:
        sys.exit("[!!] %s" % exc)
    except Exception:
        # entorno.py ausente o roto (copia parcial): heuristica minima equivalente
        # Misma precedencia que entorno.host_agente, por si entorno.py no carga.
        explicit = os.environ.get("HARNESS_HOST")
        if explicit:
            if explicit == "codex":
                return "gpt"
            if explicit == "agy":
                return "gemini"
            return explicit
        grok = os.environ.get("GROK_AGENT")
        if grok is not None and grok.strip().lower() not in ("", "0", "false", "off", "no"):
            return "grok"
        if any(os.environ.get(k, "").strip().lower() not in ("", "0", "false", "off", "no")
               for k in ("CODEX_THREAD_ID", "CODEX_SESSION_ID")):
            return "gpt"
        for padre in Path(__file__).absolute().parents:
            if padre.name == "skills" and padre.parent.name == ".grok":
                return "grok"
        for padre in Path(__file__).absolute().parents:
            if padre.name == "skills" and (padre.parent.name == ".gemini" or padre.parent.parent.name == ".gemini"):
                return "gemini"
        codex_home = os.environ.get("CODEX_HOME")
        codex_home = Path(codex_home).expanduser().absolute() if codex_home else None
        for padre in Path(__file__).absolute().parents:
            if padre.name == "skills" and (padre.parent.name in (".agents", ".codex")
                                           or padre.parent == codex_home):
                return "gpt"
        kimi_home = os.environ.get("KIMI_CODE_HOME")
        kimi_home = Path(kimi_home).expanduser().absolute() if kimi_home else None
        for padre in Path(__file__).absolute().parents:
            if padre.name == "skills" and padre.parent.name == ".kimi-code":
                return "kimi"
            if (padre.name == "managed" and padre.parent.name == "plugins"
                    and padre.parent.parent.name == ".kimi-code"):
                return "kimi"
            if kimi_home is not None and padre == kimi_home:
                return "kimi"
        if os.environ.get("CLAUDECODE") == "1" or os.environ.get("CLAUDE_CONFIG_DIR"):
            return "claude"
        for padre in Path(__file__).absolute().parents:
            if padre.name == "skills" and padre.parent.name == ".claude":
                return "claude"
        if os.environ.get("ANTIGRAVITY_AGENT") == "1" or os.environ.get("GEMINI_CLI"):
            return "gemini"
        if any(os.environ.get(k) for k in ("HERMES_HOME", "HERMES_PYTHON", "HERMES_SKILLS_DIR")):
            return "hermes"
        return "generic"


def _raices_claude() -> list[Path]:
    """Personal primero: en Claude Code la skill personal gana a la del proyecto."""
    cfg = os.environ.get("CLAUDE_CONFIG_DIR")
    base = Path(cfg) if cfg else _casa() / ".claude"
    raices = [base / "skills"]
    # proyectos: del mas cercano al mas lejano subiendo desde el cwd. El cwd puede
    # haber sido borrado (worktree eliminado): eso no debe reventar la deteccion.
    try:
        cwd = Path.cwd()
    except OSError:
        return raices
    for padre in [cwd, *cwd.parents]:
        raices.append(padre / ".claude" / "skills")
    return raices


def _repo_root(cwd: Path) -> Path | None:
    try:
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=str(cwd),
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return Path(r.stdout.strip()).resolve()


def _raices_gpt() -> list[Path]:
    """Codex/ChatGPT: repo .agents/skills cerca primero, luego user/admin."""
    raices: list[Path] = []
    try:
        cwd = Path.cwd()
        root = _repo_root(cwd)
        padres = [cwd, *cwd.parents]
        if root is not None:
            padres = [p for p in padres if p.resolve() == root or root in p.resolve().parents]
        else:
            padres = [cwd]
        for padre in padres:
            raices.append(padre / ".agents" / "skills")
    except OSError:
        pass
    raices.append(_casa() / ".agents" / "skills")
    codex_home = os.environ.get("CODEX_HOME")
    raices.append((Path(codex_home).expanduser() if codex_home else _casa() / ".codex") / "skills")
    raices.append(Path("/etc/codex/skills"))
    return raices


def _raices_grok() -> list[Path]:
    """Perfil personal de Grok. Una leccion no se commitea en el repo.

    Grok no escanea ~/.hermes/skills. Crear ahi (el clone, o el host equivocado
    hermes) deja una leccion que el gate encuentra y la sesion siguiente no carga.
    ~/.agents/skills tambien la lee, pero es la raiz de GPT: en grok se crea en
    la raiz nativa.
    """
    return [_casa() / ".grok" / "skills"]


def _raices_kimi() -> list[Path]:
    """Perfil personal de Kimi Code: $KIMI_CODE_HOME/skills (~/.kimi-code/skills),
    luego ~/.agents/skills, que Kimi tambien escanea.

    Una leccion es memoria del perfil, no del repo: no se crea en el
    .kimi-code/skills de un proyecto. Y sin _raiz_propia(): la copia managed del
    plugin no cuelga de una raiz 'skills', y crear en el clone de Hermes dejaba
    la leccion donde Kimi no la lee.
    """
    base = os.environ.get("KIMI_CODE_HOME")
    raices = [(Path(base).expanduser() if base else _casa() / ".kimi-code") / "skills"]
    raices.append(_casa() / ".agents" / "skills")
    return raices


def _raices_gemini() -> list[Path]:
    """Gemini / AGY: .gemini/skills y .agents/skills de repo, luego personal ~/.gemini/config/skills y ~/.agents/skills."""
    raices: list[Path] = []
    try:
        cwd = Path.cwd()
        root = _repo_root(cwd)
        padres = [cwd, *cwd.parents]
        if root is not None:
            padres = [p for p in padres if p.resolve() == root or root in p.resolve().parents]
        else:
            padres = [cwd]
        for padre in padres:
            raices.append(padre / ".gemini" / "skills")
            raices.append(padre / ".agents" / "skills")
    except OSError:
        pass
    raices.append(_casa() / ".gemini" / "config" / "skills")
    raices.append(_casa() / ".agents" / "skills")
    return raices


def _raices_otros_agentes() -> list[Path]:
    """Raices de los demas CLIs que leen SKILL.md, SOLO para buscar.

    Una leccion es memoria procedural del usuario, no del host. Si la escribes
    donde tu CLI la instala -- Codex en $CODEX_HOME/skills (~/.codex/skills),
    Grok en ~/.grok/skills, Kimi Code en $KIMI_CODE_HOME/skills
    (~/.kimi-code/skills) -- el gate no la encontraba y bloqueaba un cierre
    legitimo por el mero hecho de donde la tipeaste. Es el mismo bug que
    test_leccion_multihost.py mato entre Hermes/Claude/GPT, con las raices que
    aparecieron despues.

    No se usan para CREAR: eso sigue la precedencia del host detectado.
    """
    casa = _casa()
    raices = [casa / ".gemini" / "config" / "skills"]
    for var, defecto in (("CODEX_HOME", casa / ".codex"),
                         ("KIMI_CODE_HOME", casa / ".kimi-code")):
        base = os.environ.get(var)
        raices.append((Path(base) if base else defecto) / "skills")
    raices.append(casa / ".grok" / "skills")
    raices.append(casa / ".cursor" / "skills")   # Grok y Cursor la comparten
    raices.append(Path("/etc/codex/skills"))
    # Como _raices_gpt: el recorrido se corta en la raiz del repo. Subir hasta
    # / haria que una skill de un proyecto vecino satisfaga el gate de otro.
    try:
        cwd = Path.cwd()
    except OSError:
        return raices
    root = _repo_root(cwd)
    padres = [cwd]
    if root is not None:
        padres = [x for x in [cwd, *cwd.parents]
                  if x.resolve() == root or root in x.resolve().parents]
    for padre in padres:
        for marca in (".gemini", ".codex", ".grok", ".kimi-code", ".cursor"):
            raices.append(padre / marca / "skills")
    return raices


def _raices_hermes() -> list[Path]:
    env = os.environ.get("HERMES_SKILLS_DIR")
    if env:
        return [Path(env)]
    home = os.environ.get("HERMES_HOME")
    raices = [Path(home) / "skills"] if home else []
    casa = _casa()
    raices += [
        casa / "AppData" / "Local" / "hermes" / "skills",                # Windows
        casa / ".local" / "share" / "hermes" / "skills",                 # Linux
        casa / "Library" / "Application Support" / "hermes" / "skills",  # macOS
        casa / ".hermes" / "skills",
    ]
    return raices


def _raiz_propia() -> list[Path]:
    """La raiz que contiene a esta misma skill: .../skills/<cat>/harness-flow/scripts.

    absolute() y no resolve(): si la skill entra por symlink (p.ej.
    ~/.kimi-code/skills/harness-flow -> clone de Hermes), la raiz que el host
    escanea es la del enlace; resolverla devolvia la del clone, y una leccion
    creada ahi nace invisible para el host que la va a cargar.
    """
    for padre in Path(__file__).absolute().parents:
        if padre.name == "skills":
            return [padre]
    return []


def skills_roots(todos_los_hosts: bool = False) -> list[Path]:
    """Raices de skills en orden de precedencia, ya filtradas a las existentes.

    todos_los_hosts=True agrega las raices de los demas hosts al final, para
    BUSCAR. Una leccion es memoria procedural del usuario, no del host: si la
    escribiste desde Claude Code y cerras desde Hermes, el gate debe encontrarla
    igual, o bloquea un cierre legitimo por donde la tipeaste. Para CREAR se usa
    la precedencia del host (skills_roots() a secas), asi que una skill nueva
    sigue naciendo donde corresponde y no se cuela en un host ajeno.
    """
    override = os.environ.get("HARNESS_SKILLS_DIR")
    if override:
        raiz = Path(override)
        if not raiz.is_dir():
            sys.exit("[!!] HARNESS_SKILLS_DIR apunta a algo que no es un directorio: %s"
                     % raiz)
        return [raiz.resolve()]  # exclusivo: si lo defines, mandas tu

    host = _host()
    if host == "claude":
        # Precedencia oficial de Claude Code: personal gana a proyecto. No se anade
        # _raiz_propia(): con un symlink desde ~/.claude al clone de Hermes colaria
        # las skills de Hermes en un host que no es el suyo.
        candidatas = _raices_claude()
    elif host == "gpt":
        # Codex/ChatGPT usa .agents/skills. No se anade _raiz_propia(): un symlink
        # desde ~/.agents al clone de Hermes no debe colar las skills de Hermes.
        candidatas = _raices_gpt()
    elif host == "gemini":
        # Gemini / AGY usa .gemini/skills, .agents/skills y ~/.gemini/config/skills.
        candidatas = _raices_gemini()
    elif host == "grok":
        # No se anade _raiz_propia(): el script vive en el clone de Hermes o
        # entra por symlink desde .agents, y ninguna de las dos la carga Grok.
        candidatas = _raices_grok()
    elif host == "kimi":
        # No se anade _raiz_propia(): la copia managed del plugin no cuelga de
        # una raiz 'skills', y el symlink desde .kimi-code/skills YA apunta a la
        # primera raiz kimi. Crear en el clone de Hermes la dejaba invisible.
        candidatas = _raices_kimi()
    elif host == "hermes":
        # La raiz que contiene a esta skill va PRIMERO: si corres la copia instalada
        # en el perfil 'trabajo', mandan las skills de ese perfil, no las del default.
        candidatas = _raiz_propia() + _raices_hermes()
    else:
        candidatas = _raiz_propia() + _raices_hermes() + _raices_claude() + _raices_gpt() + _raices_gemini()

    if todos_los_hosts:
        # Al final: la precedencia del host propio se respeta, los demas son fallback.
        for extra in (_raiz_propia(), _raices_hermes(), _raices_claude(), _raices_gpt(),
                      _raices_gemini(), _raices_otros_agentes()):
            candidatas = candidatas + extra

    vistas: set[Path] = set()
    raices: list[Path] = []
    for c in candidatas:
        if not c.is_dir():
            continue
        real = c.resolve()  # /var vs /private/var, symlinks: una raiz fisica es una sola
        if real in vistas:
            continue
        vistas.add(real)
        # Se devuelve la ruta declarada (alias), no la resuelta: es la que el
        # host escanea. Crear en el objetivo de un symlink dejaria la leccion
        # donde el host no la lee (p.ej. skill de Kimi enlazada al clone de
        # Hermes). Para buscar da igual: el filesystem sigue el enlace.
        raices.append(c.absolute())
    if not raices:
        sys.exit("[!!] no encuentro ninguna raiz de skills (host=%s).\n"
                 "     Define HARNESS_SKILLS_DIR con la raiz correcta." % host)
    return raices


def skills_root() -> Path:
    """Compat: la raiz de mayor precedencia."""
    return skills_roots()[0]


def nombre_valido(clase: str) -> bool:
    """Un nombre de skill literal: sin separadores ni comodines de glob.

    Sin esto, buscar('*') casa con la primera skill que haya y `gate.py close
    --leccion '*'` pasaria el gate sin que exista ninguna leccion.
    """
    if not clase or clase in (".", ".."):
        return False
    prohibidos = set('/\\*?[]!')
    return not (prohibidos & set(clase))


def buscar(clase: str) -> Path | None:
    """La skill <clase>, con o sin categoria intermedia, en orden de precedencia.

    is_file() y no exists(): un directorio llamado SKILL.md daba el gate por
    cumplido y luego reventaba con IsADirectoryError al leerlo. Y se buscan dos
    niveles de categoria porque las skills instaladas anidadas (mlops/inference/
    llama-cpp) eran invisibles: el gate bloqueaba un cierre legitimo.
    """
    if not nombre_valido(clase):
        return None
    for raiz in skills_roots(todos_los_hosts=True):
        directo = raiz / clase / "SKILL.md"
        if directo.is_file():
            return directo
        for patron in ("*/" + clase + "/SKILL.md", "*/*/" + clase + "/SKILL.md"):
            for hit in sorted(raiz.glob(patron)):
                if hit.is_file():
                    return hit
    return None


def descripcion(skill_md: Path) -> str:
    for ln in skill_md.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if s.startswith("description:"):
            return s.split(":", 1)[1].strip().strip('"').strip("'")
    return ""


def cmd_list(args) -> None:
    raices = skills_roots(todos_los_hosts=True)
    vistos: set[str] = set()
    filas = 0
    for raiz in raices:
        print("Skills en " + str(raiz) + "\n")
        encontradas = sorted(raiz.glob("*/*/SKILL.md")) + sorted(raiz.glob("*/SKILL.md"))
        locales = 0
        for sm in encontradas:
            nombre = sm.parent.name
            if nombre in vistos or nombre == "harness-flow":
                continue
            vistos.add(nombre)
            locales += 1
            filas += 1
            n = len(sm.read_text(encoding="utf-8").splitlines())
            marca = "  <- sobre el tope: muevele detalle a references/" if n > TOPE_LINEAS else ""
            cat = sm.parent.parent.name
            prefijo = "" if cat == raiz.name else cat + "/"
            print("   %-46s %4d lineas%s" % (prefijo + nombre, n, marca))
            d = descripcion(sm)
            if d:
                print("      " + d[:100])
        if not locales:
            print("   (ninguna nueva aqui)")
        print("")
    if not filas:
        print("   (ninguna todavia)")
    print("[i]  PATCHEA la leccion que estuvo en juego antes de crear otra.")


def cmd_ver(args) -> None:
    sm = buscar(args.clase)
    if not sm:
        raices = "\n       ".join(str(r) for r in skills_roots(todos_los_hosts=True))
        sys.exit("[!!] no existe la skill '%s'.\n     Raices consultadas:\n       %s"
                 % (args.clase, raices))
    txt = sm.read_text(encoding="utf-8")
    n = len(txt.splitlines())
    if n > TOPE_LINEAS:
        print("[!] %s: %d lineas (tope %d). Mueve el detalle a references/<tema>.md.\n"
              % (args.clase, n, TOPE_LINEAS), file=sys.stderr)
    print(txt)


def cmd_existe(args) -> None:
    sm = buscar(args.clase)
    if not sm:
        raices = "\n       ".join(str(r) for r in skills_roots(todos_los_hosts=True))
        sys.exit("[!!] la leccion '%s' no existe como skill.\n"
                 "     Raices consultadas:\n       %s\n"
                 "     Creala (skill_manage en Hermes; SKILL.md en Claude Code, GPT o Grok), o cierra con\n"
                 "     --leccion ninguna --leccion-motivo '<por que>'."
                 % (args.clase, raices))
    print("[ok] %s -> %s" % (args.clase, sm))


def _raiz_grok_aunque_no_exista() -> Path | None:
    """~/.grok/skills aunque falte el directorio. 'donde' tiene que decir cual crear."""
    if os.environ.get("HARNESS_SKILLS_DIR"):
        return None
    if _host() != "grok":
        return None
    return _raices_grok()[0]


def cmd_donde(args) -> None:
    """La primera es donde se CREA; el resto solo se consultan al buscar.

    No puede morir si la raiz del host no existe todavia en disco: 'donde' es
    justo lo que corres para averiguar cual crear.
    """
    try:
        todas = skills_roots(todos_los_hosts=True)
    except SystemExit:
        todas = []
    try:
        propias = skills_roots()
    except SystemExit:
        propias = []
    ausente = None if propias else _raiz_grok_aunque_no_exista()
    if propias:
        print(propias[0])
    elif ausente is not None:
        print(ausente)
    else:
        print("[!] ninguna raiz propia del host existe todavia; creala tu.",
              file=sys.stderr)
    for raiz in todas:
        if propias and raiz == propias[0]:
            continue
        if ausente is not None and raiz == ausente:
            continue
        marca = "" if raiz in propias else "   # solo consulta (otro agente)"
        print(f"{raiz}{marca}")


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
    print("[i]  Hermes: skill_manage(action='create', name='%s', content=...)\n"
          "     Claude Code: escribelo en <raiz>/%s/SKILL.md (leccion.py donde)\n"
          "     GPT/Codex: escribelo en <raiz>/%s/SKILL.md, tipicamente ~/.agents/skills/%s/SKILL.md\n"
          "     Grok: escribelo en ~/.grok/skills/%s/SKILL.md (leccion.py donde)"
          % (args.clase, args.clase, args.clase, args.clase, args.clase), file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description="Lecciones = skills del agente")
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
