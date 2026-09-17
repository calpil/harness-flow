#!/usr/bin/env python3
"""Contexto del proyecto: grafo combinado, hub y vault, con briefing compacto.

  contexto.py estado [--json]
  contexto.py refrescar [--forzar] [--max-horas N] [--sin-vault] [--sin-hub]
  contexto.py brief --feature <id> [--max-lineas N]

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
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (ac_comandos, get_feature, grafos_config, graph_path,  # noqa: E402
                   impl_path, load_backlog, now_iso, paths, raices_grafo,
                   spec_acs, spec_path)

SERVICE_RE = re.compile(r"(ms-[a-z0-9-]+-service|[a-z0-9-]+-ui|fn-[a-z0-9-]+)")
# Relaciones que dicen "esto usa aquello". `contains`/`method` son estructura
# interna: inflan el brief sin explicar acoplamiento.
REL_UTILES = {"imports", "imports_from", "calls", "references", "implements",
              "depends_on", "uses", "shares_data_with", "re_exports",
              "dynamic_import"}


# --- frescura ---------------------------------------------------------------

def _edad_h(f: Path) -> float | None:
    return None if not f.exists() else (time.time() - f.stat().st_mtime) / 3600


def estado_contexto(p: dict) -> dict:
    cfg = grafos_config(p)
    raices = raices_grafo(p)
    comb = graph_path(p)
    out = {
        "max_horas": cfg.get("max_horas", 12),
        "combinado": {"path": str(comb), "edad_h": _edad_h(comb),
                      "existe": comb.exists()},
        "raices": [],
        "vault": {"path": str(p["vault"]), "existe": p["vault"].exists(),
                  "edad_h": _edad_h(p["vault"] / "Indice.md")},
        "graphify": bool(shutil.which("graphify")),
    }
    for r in raices:
        g = r["path"] / "graphify-out" / "graph.json"
        out["raices"].append({
            "nombre": r["nombre"], "path": str(r["path"]),
            "graph": str(g), "existe": g.exists(), "edad_h": _edad_h(g),
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
    print(f"   vault: {'ok' if e['vault']['existe'] else 'ausente'}")
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
    return True, ""


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

    if not shutil.which("graphify"):
        parte["fallos"].append("graphify no esta en el PATH")
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
        code, out = _run([sys.executable, str(Path(__file__).parent / "vault.py"),
                          "build"], p["root"])
        parte["vault"] = "ok" if code == 0 else out[-300:]
        if code != 0:
            parte["fallos"].append(f"vault build: {out[-300:]}")
        elif verboso:
            print("   vault build: ok")
    return parte


def refrescar_si_vencido(p: dict, *, etiqueta: str, bloqueante=False) -> dict | None:
    """Gancho para worktree start / gate close. Avisa, no miente, no bloquea."""
    if _desactivado():
        print(f"[i]  HARNESS_SIN_CONTEXTO: sin refresco automatico ({etiqueta}).")
        return None
    e = estado_contexto(p)
    if e["fresco"]:
        print(f"[i]  contexto fresco ({etiqueta}); no hay nada que refrescar.")
        return None
    print(f"[i]  contexto vencido ({', '.join(e['vencidas'])}); refrescando antes de {etiqueta}...")
    parte = refrescar(p, con_vault=True, con_hub=True)
    if parte["fallos"]:
        print("[!] el refresco de contexto no quedo completo:")
        for x in parte["fallos"]:
            print(f"     - {x}")
        if bloqueante:
            sys.exit("[!!] contexto no refrescado y se pidio bloqueante")
    return parte


def cmd_refrescar(args) -> None:
    p = paths()
    parte = refrescar(p, forzar=args.forzar, max_horas=args.max_horas,
                      con_vault=not args.sin_vault, con_hub=not args.sin_hub)
    print(json.dumps(parte, ensure_ascii=False, indent=2))
    sys.exit(1 if parte["fallos"] else 0)


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


def _micros_declarados(f: dict) -> list[str]:
    """Nombres de servicio de la feature.

    El backlog real trae de todo: listas limpias, pero tambien una sola cadena
    con comas y comentarios entre parentesis ("admin, ms-payment-service
    (proxy)"). Se extraen los nombres de servicio reconocibles y, si no hay
    ninguno, se devuelve vacio para que el brief no filtre por un nombre que no
    existe en el grafo (filtrar por basura devuelve cero y parece un grafo
    vacio: el sintoma que trajo todo esto).
    """
    crudo = f.get("microservicios") or []
    if isinstance(crudo, str):
        crudo = [crudo]
    out: list[str] = []
    for item in crudo:
        for trozo in re.split(r"[,\n;]", str(item)):
            trozo = trozo.split("(")[0].strip().strip("/")
            if not trozo:
                continue
            m = SERVICE_RE.search(trozo)
            nombre = m.group(1) if m else trozo.split("/")[-1]
            if nombre and nombre not in out:
                out.append(nombre)
    return out


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
    micros = _micros_declarados(f)

    L: list[str] = []
    L.append(f"== BRIEF #{f['id']} {f.get('name')} ({proyecto}) ==")
    L.append(f"estado: {f.get('status')} · rama: {f.get('branch') or '-'} · "
             f"worktree: {f.get('worktree') or '(sin worktree)'}")
    if not e["fresco"]:
        L.append(f"[!] contexto VENCIDO ({', '.join(e['vencidas'])}): lo de abajo "
                 "puede no reflejar el arbol actual. Corre contexto.py refrescar.")

    L.append("")
    L.append(f"AC ({len(acs)}):")
    for ac in acs:
        linea = next((l.strip() for l in stext.splitlines()
                      if re.match(rf"\s*[-*]?\s*{re.escape(ac)}\s*:", l)), ac)
        L.append(f"  {linea[:200]}")
        if ac in cmds:
            L.append(f"      comando: {cmds[ac]}")

    reglas = [k for k, v in data["rules"].items()
              if k.startswith("require_") and v]
    L.append("")
    L.append("reglas activas: " + (", ".join(reglas) or "ninguna"))
    L.append("rutas protegidas (NO editar): " +
             ", ".join(data["rules"].get("rutas_protegidas", [])))

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
    s = sub.add_parser("brief"); s.add_argument("--feature", required=True)
    s.add_argument("--max-lineas", type=int, default=90, dest="max_lineas")
    s.add_argument("--max-archivos", type=int, default=12, dest="max_archivos")
    s.add_argument("--max-lecciones", type=int, default=12, dest="max_lecciones")
    s.set_defaults(fn=cmd_brief)
    a = ap.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
