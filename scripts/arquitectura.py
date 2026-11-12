#!/usr/bin/env python3
"""Trinquete de arquitectura: el codigo heredado solo puede achicarse.

Un proyecto que adopta el arnes con mucho codigo ya escrito tiene dos malas
opciones: reestructurar todo antes de seguir (la Feature #0 como muro) o dejar
lo existente como esta y prometer que lo nuevo nacera bien (nada lo mide). Este
gate es la tercera: se MIDE cuanto codigo vive fuera de la norma del stack, se
sella esa medida como base, y desde ahi solo puede bajar.

  arquitectura.py inventario                      que hay dentro y fuera de la norma
  arquitectura.py base --yes                      sella la base (decision del usuario)
  arquitectura.py adoptar --yes                   sella la base y retira el muro de la #0
  arquitectura.py check [--feature <id>] [--ajustar]
  arquitectura.py siguiente [-n 10]               unidades heredadas, las mas tocadas primero
  arquitectura.py eximir --repo <r> --unidad <u> --motivo '<por que>' --yes

Que exige, con la base sellada (`harness/arquitectura-base.json`):

- Ninguna unidad gana archivos heredados, y no nacen unidades heredadas. Una
  feature se mide contra SU commit base, no contra la base global: asi dos
  features paralelas no se pisan cuando una normaliza lo que la otra aun trae.
- Un archivo heredado que la feature cambia en mas de `rules.arquitectura_umbral_lineas`
  lineas (50) tiene que salir de lo heredado en esa misma feature.
- Las violaciones del verificador del stack que no estaban en la base fallan.
- Tras `rules.arquitectura_cuota` (3) features de negocio aprobadas, approve-spec
  exige cerrar una de normalizacion (`add.py --kind normalizacion`) mientras
  queden unidades heredadas. Una de normalizacion que no vacia ninguna unidad
  ni baja las violaciones no cierra.

Que es "dentro de la norma" lo declara cada stack en `manifest.json` -> `layout`.
Un stack sin `layout` no se mide, y se dice: no devuelve verde.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from comun import (  # noqa: E402
    bitacora, get_feature, git, load_backlog, now_iso, paths, save_backlog,
)
import copias  # noqa: E402
import stack  # noqa: E402

UMBRAL_LINEAS = 50
CUOTA = 3
KIND_NORMALIZACION = "normalizacion"
_IGNORADOS = frozenset((".git", "node_modules", "vendor", "dist", "build", ".angular",
                        "__pycache__", ".venv", "venv"))


# --- layout: que rutas son codigo, y cuales estan dentro de la norma -------

_regex = copias.regex_glob


class Layout:
    def __init__(self, stack_id: str, bloque: dict):
        def lista(clave: str) -> list[re.Pattern]:
            valor = bloque.get(clave, [])
            if not isinstance(valor, list) or not all(isinstance(x, str) and x for x in valor):
                raise ValueError(f"manifest de {stack_id}: layout.{clave} debe ser una lista de patrones")
            return [_regex(x) for x in valor]

        self.stack_id = stack_id
        self.codigo = lista("codigo")
        self.excluir = lista("excluir")
        self.normalizado = lista("normalizado")
        if not self.codigo or not self.normalizado:
            raise ValueError(f"manifest de {stack_id}: layout necesita 'codigo' y 'normalizado'")
        self.unidad_tras = bloque.get("unidad_tras")

    def en_alcance(self, ruta: str) -> bool:
        return (any(r.match(ruta) for r in self.codigo)
                and not any(r.match(ruta) for r in self.excluir))

    def heredado(self, ruta: str) -> bool:
        return self.en_alcance(ruta) and not any(r.match(ruta) for r in self.normalizado)

    def unidad(self, ruta: str) -> str:
        """El directorio del archivo; con `unidad_tras`, el modulo que lo contiene."""
        partes = ruta.split("/")
        if self.unidad_tras and self.unidad_tras in partes[:-2]:
            return "/".join(partes[:partes.index(self.unidad_tras) + 2])
        return "/".join(partes[:-1]) or "."


def layout_de(stack_id: str) -> Layout | None:
    """None si el stack no declara layout: ese repo no se puede medir."""
    bloque = stack.cargar_manifest(stack_id).get("layout")
    return Layout(stack_id, bloque) if isinstance(bloque, dict) else None


def heredados_por_unidad(layout: Layout, rutas: list[str], exentas=()) -> dict[str, list[str]]:
    unidades: dict[str, list[str]] = {}
    for ruta in rutas:
        if layout.heredado(ruta):
            unidad = layout.unidad(ruta)
            if unidad not in exentas:
                unidades.setdefault(unidad, []).append(ruta)
    return {u: sorted(v) for u, v in sorted(unidades.items())}


def fuera_de_alcance(layout: Layout, rutas: list[str], stack_id: str) -> list[str]:
    """Archivos con extension de codigo que el layout no mira: ni dentro ni fuera de la norma.

    `layout.codigo` suele nombrar una ruta (`**/src/app/**/*.ts`, `src/**/*.py`).
    El codigo que vive en otra (una libreria en `projects/ui/src/lib`, un `app/`
    en vez de `src/`) no cuenta como heredado: NO se mide, y hay que decirlo.
    Los tests y lo que el layout excluye a proposito no entran.
    """
    manifest = stack.cargar_manifest(stack_id)
    validadores = stack.STACKS_DIR / stack_id / "scripts"
    propios = {f"scripts/{f.name}" for f in validadores.glob("*")} if validadores.is_dir() else set()
    codigo = copias.codigo_del_repo(rutas, copias.extensiones_de_codigo(manifest), propios)
    return [r for r in codigo
            if not any(x.match(r) for x in layout.codigo) and not any(x.match(r) for x in layout.excluir)]


# --- de donde salen las rutas ----------------------------------------------

def rutas_en_disco(repo: Path) -> list[str]:
    """Archivos versionados si es un repo git; si no, lo que hay en disco."""
    code, out = git(["ls-files", "-z"], repo)
    if code == 0 and (repo / ".git").exists():
        return [x for x in out.split("\0") if x]
    rutas = []
    for actual, dirs, archivos in os.walk(str(repo)):
        dirs[:] = [d for d in dirs if d not in _IGNORADOS]
        base = Path(actual).relative_to(repo).as_posix()
        rutas += [f if base == "." else f"{base}/{f}" for f in archivos]
    return rutas


def rutas_en_commit(arbol: Path, ref: str) -> list[str] | None:
    code, out = git(["ls-tree", "-r", "--name-only", "-z", ref], arbol)
    return [x for x in out.split("\0") if x] if code == 0 else None


def violaciones(repo: Path, stack_id: str) -> list[str] | None:
    """Violaciones del verificador del stack; None si no hay verificador."""
    script = stack.STACKS_DIR / stack_id / "scripts" / "check-architecture.py"
    if not script.is_file():
        return None
    r = subprocess.run([sys.executable, str(script), "--repo", str(repo)],
                       capture_output=True, text=True, timeout=300)
    if r.returncode == 0:
        return []
    lineas = [x[4:].strip() for x in (r.stdout + r.stderr).splitlines() if x.startswith("  - ")]
    # Sin el numero de linea: mover codigo de sitio no crea una violacion nueva.
    return sorted({re.sub(r":\d+:", ":", x) for x in lineas}) or ["el verificador fallo sin listar violaciones"]


# --- la base ---------------------------------------------------------------

def ruta_base(p: dict) -> Path:
    return p["harness"] / "arquitectura-base.json"


def modo_trinquete(p: dict) -> bool:
    return ruta_base(p).is_file()


def cargar_base(p: dict) -> dict:
    try:
        base = json.loads(ruta_base(p).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"[!!] {ruta_base(p).name} ilegible: {exc}")
    if not isinstance(base, dict) or not isinstance(base.get("repos"), dict):
        raise SystemExit(f"[!!] {ruta_base(p).name} no tiene la forma esperada (repos)")
    return base


def guardar_base(p: dict, base: dict) -> None:
    destino = ruta_base(p)
    tmp = destino.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(destino)


def clave_repo(p: dict, repo: Path) -> str:
    repo, raiz = repo.resolve(), p["root"].resolve()
    if repo == raiz:
        return "."
    return repo.relative_to(raiz).as_posix() if raiz in repo.parents else str(repo)


def destinos(p: dict) -> list[dict]:
    """Repos del proyecto con stack normativo: [{clave, path, stack, layout}]."""
    out = []
    for d in stack.detectar_todos_los_destinos(p["root"]):
        if d["stack"] == "generico":
            continue
        ruta = Path(d["path"])
        out.append({"clave": clave_repo(p, ruta), "path": ruta, "stack": d["stack"],
                    "layout": layout_de(d["stack"])})
    return out


def medir(repo: Path, stack_id: str, layout: Layout, exentas=()) -> dict:
    heredadas = heredados_por_unidad(layout, rutas_en_disco(repo), exentas)
    return {"stack": stack_id, "path": str(repo),
            "heredadas": {u: len(v) for u, v in heredadas.items()},
            "violaciones": violaciones(repo, stack_id) or []}


def sin_medir_por_carpeta(repo: Path, stack_id: str, layout: Layout) -> dict[str, int]:
    """{carpeta de primer nivel: archivos de codigo que el layout no mira}."""
    cuenta: dict[str, int] = {}
    for ruta in fuera_de_alcance(layout, rutas_en_disco(repo), stack_id):
        carpeta = "/".join(ruta.split("/")[:2]) if ruta.count("/") > 1 else (ruta.split("/")[0] if "/" in ruta else ".")
        cuenta[carpeta] = cuenta.get(carpeta, 0) + 1
    return dict(sorted(cuenta.items(), key=lambda x: (-x[1], x[0])))


def restantes(base: dict) -> tuple[int, int]:
    """(unidades heredadas, archivos heredados) que quedan en la base."""
    unidades = [n for r in base["repos"].values() for n in r.get("heredadas", {}).values()]
    return len(unidades), sum(unidades)


# --- evaluacion ------------------------------------------------------------

def arboles_feature(p: dict, data: dict, f: dict) -> list[tuple[Path, Path, str | None]]:
    """[(repo, arbol de la feature, commit base)] de lo que la feature toca."""
    if "multi_repo" in f:
        return [(Path(r["repo"]), Path(r["worktree"]), r.get("base_sha"))
                for r in f["multi_repo"].get("repos", [])]
    wt = f.get("worktree")
    arbol = Path(wt) if wt and Path(wt).is_dir() else p["root"]
    ref = f.get("base_sha") or f.get("base_branch") or data["rules"].get("rama_base") or "develop"
    code, out = git(["merge-base", ref, "HEAD"], arbol)
    return [(p["root"], arbol, out.strip() if code == 0 and out.strip() else None)]


def _lineas_cambiadas(arbol: Path, base_sha: str) -> dict[str, int]:
    code, out = git(["diff", "--numstat", "--no-renames", base_sha, "HEAD", "--"], arbol)
    cambios = {}
    for linea in out.splitlines() if code == 0 else []:
        partes = linea.split("\t", 2)  # los binarios traen "-" y no cuentan lineas
        if len(partes) == 3 and partes[0].isdigit() and partes[1].isdigit():
            cambios[partes[2]] = int(partes[0]) + int(partes[1])
    return cambios


def evaluar_feature(p: dict, data: dict, f: dict, base: dict) -> dict:
    """Lo que ESTA feature le hizo a lo heredado, medido contra su commit base."""
    umbral = int(data["rules"].get("arquitectura_umbral_lineas", UMBRAL_LINEAS))
    fallos: list[str] = []
    avisos: list[str] = []
    vaciadas: list[str] = []
    violaciones_resueltas = 0
    for repo, arbol, base_sha in arboles_feature(p, data, f):
        clave = clave_repo(p, repo)
        reg = base["repos"].get(clave)
        if reg is None:
            continue  # repo sin stack normativo: el trinquete no lo gobierna
        layout = layout_de(reg["stack"])
        if layout is None:
            avisos.append(f"{clave}: el stack {reg['stack']} no declara layout; NO se midio")
            continue
        antes_rutas = rutas_en_commit(arbol, base_sha) if base_sha else None
        ahora_rutas = rutas_en_commit(arbol, "HEAD")
        if antes_rutas is None or ahora_rutas is None:
            # Un gate que no puede medir no devuelve verdadero.
            fallos.append(f"{clave}: no se pudo leer el commit base ni HEAD de {arbol}; sin eso "
                          "no se sabe que agrego la feature")
            continue
        exentas = reg.get("exentas", {})
        antes = heredados_por_unidad(layout, antes_rutas, exentas)
        ahora = heredados_por_unidad(layout, ahora_rutas, exentas)
        for unidad, archivos in ahora.items():
            previos = set(antes.get(unidad, []))
            if len(archivos) > len(previos):
                nuevos = [a for a in archivos if a not in previos]
                que = "unidad heredada nueva" if not previos else "la unidad heredada crecio"
                fallos.append(f"{clave}: {que}: {unidad} (+{len(archivos) - len(previos)}): "
                              f"{', '.join(nuevos[:3])}{'...' if len(nuevos) > 3 else ''}. "
                              "El codigo nuevo nace dentro de la norma del stack")
        vaciadas += [f"{clave}:{u}" for u in antes if u not in ahora]
        heredados_hoy = {a for archivos in ahora.values() for a in archivos}
        for ruta, lineas in sorted(_lineas_cambiadas(arbol, base_sha).items()):
            if ruta in heredados_hoy and lineas > umbral:
                fallos.append(f"{clave}: {ruta} es heredado y la feature le cambio {lineas} lineas "
                              f"(umbral {umbral}): llevalo a la norma en esta feature o achica el cambio")
        hoy = violaciones(arbol, reg["stack"])
        if hoy is not None:
            conocidas = set(reg.get("violaciones", []))
            for v in hoy:
                if v not in conocidas:
                    fallos.append(f"{clave}: violacion nueva del verificador: {v}")
            violaciones_resueltas += len(conocidas - set(hoy))
    return {"fallos": fallos, "avisos": avisos, "vaciadas": vaciadas,
            "violaciones_resueltas": violaciones_resueltas}


def evaluar_global(p: dict, base: dict, completa: bool = True) -> dict:
    """Los checkouts del proyecto contra la base: detecta lo que crecio fuera del proceso.

    `completa=False` cuando `base` trae solo una parte de los repos: ahi no se
    avisa de los que faltan.
    """
    fallos, avisos, ajustes = [], [], {}
    actuales = {d["clave"]: d for d in destinos(p)} if completa else {}
    for clave, d in actuales.items():
        if clave not in base["repos"]:
            avisos.append(f"{clave}: repo con stack {d['stack']} que no esta en la base "
                          "(arquitectura.py base --ampliar --yes)")
    for clave, reg in base["repos"].items():
        repo = Path(reg["path"])
        layout = layout_de(reg["stack"])
        if layout is None or not repo.is_dir():
            avisos.append(f"{clave}: NO se midio ({'sin layout' if layout is None else 'no existe ' + str(repo)})")
            continue
        hoy = medir(repo, reg["stack"], layout, reg.get("exentas", {}))
        for unidad, n in hoy["heredadas"].items():
            tope = reg.get("heredadas", {}).get(unidad, 0)
            if n > tope:
                fallos.append(f"{clave}: {unidad} tiene {n} archivos heredados y la base admite {tope}")
        for v in hoy["violaciones"]:
            if v not in reg.get("violaciones", []):
                fallos.append(f"{clave}: violacion nueva del verificador: {v}")
        ajustes[clave] = hoy
    return {"fallos": fallos, "avisos": avisos, "ajustes": ajustes}


def ajustar(p: dict, base: dict, medidas: dict[str, dict]) -> int:
    """Aprieta la base con lo medido. Nunca la afloja: solo baja topes."""
    antes = restantes(base)[0]
    for clave, hoy in medidas.items():
        reg = base["repos"].get(clave)
        if reg is None:
            continue
        reg["heredadas"] = {u: min(n, hoy["heredadas"][u])
                            for u, n in reg.get("heredadas", {}).items() if u in hoy["heredadas"]}
        reg["violaciones"] = [v for v in reg.get("violaciones", []) if v in hoy["violaciones"]]
    guardar_base(p, base)
    return antes - restantes(base)[0]


# --- cuota de normalizacion ------------------------------------------------

def _estado(data: dict) -> dict:
    return data.setdefault("arquitectura", {"negocio_desde_normalizacion": []})


def cuota_bloquea(p: dict, data: dict, f: dict) -> str | None:
    """Motivo por el que approve-spec no sella esta feature de negocio, o None."""
    if not modo_trinquete(p) or f.get("kind", "feature") != "feature":
        return None
    cuota = int(data["rules"].get("arquitectura_cuota", CUOTA))
    unidades, archivos = restantes(cargar_base(p))
    ids = _estado(data).setdefault("negocio_desde_normalizacion", [])
    if cuota <= 0 or unidades == 0 or f["id"] in ids or len(ids) < cuota:
        return None
    return (f"cuota de normalizacion: ya se aprobaron {len(ids)} features de negocio "
            f"({', '.join('#' + str(i) for i in ids)}) desde la ultima normalizacion y quedan "
            f"{unidades} unidades heredadas ({archivos} archivos).\n"
            "     Cierra antes una feature de normalizacion:\n"
            "       arquitectura.py siguiente\n"
            "       add.py --kind normalizacion --name 'normalizar <unidad>'\n"
            "     La cuota es de rules.arquitectura_cuota; cambiarla es decision del usuario.")


def registrar_aprobacion(p: dict, data: dict, f: dict) -> None:
    if modo_trinquete(p) and f.get("kind", "feature") == "feature":
        ids = _estado(data).setdefault("negocio_desde_normalizacion", [])
        if f["id"] not in ids:
            ids.append(f["id"])


def en_curso_al_adoptar(data: dict, f: dict) -> bool:
    return f.get("id") in data.get("arquitectura", {}).get("exentas_en_curso", [])


def fallos_de_cierre(p: dict, data: dict, f: dict) -> tuple[list[str], list[str]]:
    """(fallos, avisos) del trinquete para `gate.py close --status done`."""
    if not modo_trinquete(p):
        return [], []
    if en_curso_al_adoptar(data, f):
        # No se le cambia la regla a una feature a mitad de camino: lo que agregue
        # a lo heredado entra a la base al cerrar, y queda en la bitacora.
        return [], [f"#{f['id']} ya estaba en curso al adoptar el trinquete: no se mide; "
                    "lo heredado que agregue entra a la base"]
    base = cargar_base(p)
    res = evaluar_feature(p, data, f, base)
    fallos = list(res["fallos"])
    avisos = list(res["avisos"])
    # Repos del proyecto donde la feature no registra arbol: no hay diff que medir.
    # Se mide su checkout contra la base, que es lo unico que se puede comprobar ahi.
    cubiertos = {clave_repo(p, repo) for repo, _, _ in arboles_feature(p, data, f)}
    resto = {"repos": {c: r for c, r in base["repos"].items() if c not in cubiertos}}
    mejoras = len(res["vaciadas"]) + res["violaciones_resueltas"]
    if resto["repos"]:
        otros = evaluar_global(p, resto, completa=False)
        fallos += [f"{x} (medido en el checkout del repo: la feature no registra arbol ahi)"
                   for x in otros["fallos"]]
        avisos.append(f"{len(resto['repos'])} repos se midieron por su checkout y no por el diff de la "
                      "feature: ahi no se comprueba el umbral de lineas")
        for clave, hoy in otros["ajustes"].items():
            reg = resto["repos"][clave]
            mejoras += len([u for u in reg.get("heredadas", {}) if u not in hoy["heredadas"]])
            mejoras += len([v for v in reg.get("violaciones", []) if v not in hoy["violaciones"]])
    if f.get("kind") == KIND_NORMALIZACION and not mejoras:
        fallos.append("es una feature de normalizacion y no vacio ninguna unidad heredada ni bajo "
                      "las violaciones de la base: no cuenta para la cuota")
    return fallos, avisos


def absorber(p: dict, base: dict) -> list[str]:
    """Sube la base hasta lo que hoy tienen los checkouts. Devuelve lo que subio."""
    subio = []
    for clave, reg in base["repos"].items():
        repo, layout = Path(reg["path"]), layout_de(reg["stack"])
        if layout is None or not repo.is_dir():
            continue
        hoy = medir(repo, reg["stack"], layout, reg.get("exentas", {}))
        for unidad, n in hoy["heredadas"].items():
            tope = reg.setdefault("heredadas", {}).get(unidad, 0)
            if n > tope:
                reg["heredadas"][unidad] = n
                subio.append(f"{clave}:{unidad} {tope}->{n}")
        nuevas = [v for v in hoy["violaciones"] if v not in reg.get("violaciones", [])]
        if nuevas:
            reg["violaciones"] = sorted(set(reg.get("violaciones", [])) | set(nuevas))
            subio += [f"{clave}: violacion '{v}'" for v in nuevas]
    if subio:
        guardar_base(p, base)
    return subio


def al_cerrar(p: dict, data: dict, f: dict) -> None:
    """Dentro del cierre, ya integrada la feature y antes de guardar el backlog."""
    if not modo_trinquete(p):
        return
    if f.get("kind") == KIND_NORMALIZACION:
        _estado(data)["negocio_desde_normalizacion"] = []
    if en_curso_al_adoptar(data, f):
        _estado(data)["exentas_en_curso"].remove(f["id"])
        subio = absorber(p, cargar_base(p))
        if subio:
            bitacora(p, f"arquitectura: #{f['id']} estaba en curso al adoptar; la base absorbe "
                     f"{len(subio)} cambios: {'; '.join(subio[:8])}{'...' if len(subio) > 8 else ''}")


# --- comandos --------------------------------------------------------------

def cmd_inventario(args) -> None:
    p = paths()
    total_u = total_a = total_s = 0
    salida = {}
    for d in destinos(p):
        if d["layout"] is None:
            print(f"{d['clave']} [{d['stack']}]: NO se mide (el stack no declara layout)")
            continue
        hoy = medir(d["path"], d["stack"], d["layout"])
        salida[d["clave"]] = hoy
        u, a = len(hoy["heredadas"]), sum(hoy["heredadas"].values())
        total_u, total_a = total_u + u, total_a + a
        print(f"{d['clave']} [{d['stack']}]: {u} unidades heredadas, {a} archivos; "
              f"{len(hoy['violaciones'])} violaciones del verificador")
        sin_medir = sin_medir_por_carpeta(d["path"], d["stack"], d["layout"])
        total_s += sum(sin_medir.values())
        if sin_medir:
            print(f"    [i] {sum(sin_medir.values())} archivos de codigo fuera del alcance del layout, "
                  "NO medidos" + ("" if args.detalle else " (--detalle los lista)"))
        if args.detalle:
            for unidad, n in sorted(hoy["heredadas"].items(), key=lambda x: -x[1]):
                print(f"    {n:>4}  {unidad}")
            for carpeta, n in sin_medir.items():
                print(f"    {n:>4}  {carpeta}  (sin medir)")
    print(f"TOTAL: {total_u} unidades heredadas, {total_a} archivos"
          + (f"; {total_s} archivos de codigo sin medir" if total_s else ""))
    if args.json:
        print(json.dumps(salida, ensure_ascii=False, indent=2))


def _sellar_base(p: dict, data: dict, ampliar: bool, motivo: str | None) -> dict:
    previa = cargar_base(p) if modo_trinquete(p) else None
    base: dict[str, Any] = {"version": 1, "repos": {}}
    for d in destinos(p):
        if d["layout"] is None:
            print(f"[!] {d['clave']}: el stack {d['stack']} no declara layout; queda fuera de la base")
            continue
        exentas = (previa or {}).get("repos", {}).get(d["clave"], {}).get("exentas", {})
        base["repos"][d["clave"]] = dict(medir(d["path"], d["stack"], d["layout"], exentas),
                                         exentas=exentas)
    if previa:
        crece = []
        for clave, reg in base["repos"].items():
            viejo = previa["repos"].get(clave, {})
            crece += [f"{clave}:{u}" for u, n in reg["heredadas"].items()
                      if n > viejo.get("heredadas", {}).get(u, 0)]
            crece += [f"{clave}: {v}" for v in reg["violaciones"]
                      if v not in viejo.get("violaciones", [])]
        if crece and not ampliar:
            raise SystemExit("[!!] re-sellar ahora AFLOJARIA la base:\n"
                             + "".join(f"     - {x}\n" for x in crece[:10]) +
                             "     El trinquete solo baja. Si el usuario decide admitirlo:\n"
                             "     arquitectura.py base --ampliar --motivo '<por que>' --yes")
        if crece and not (motivo or "").strip():
            raise SystemExit("[!!] --ampliar exige --motivo")
    u, a = restantes(base)
    base["inicial"] = (previa or {}).get("inicial") or {"unidades": u, "archivos": a, "at": now_iso()}
    base["sellada"] = {"at": now_iso(), **({"motivo": motivo} if motivo else {})}
    guardar_base(p, base)
    _estado(data)
    return base


def cmd_base(args) -> None:
    if not args.yes:
        sys.exit("[!!] base requiere --yes.\n"
                 "     Sellar la base es aceptar como deuda todo lo que hoy esta fuera de la\n"
                 "     norma. MUESTRALE el inventario al usuario (arquitectura.py inventario\n"
                 "     --detalle), PREGUNTALE, y solo con su SI corre este comando con --yes.")
    p = paths()
    data = load_backlog(p)
    base = _sellar_base(p, data, args.ampliar, args.motivo)
    save_backlog(p, data)
    u, a = restantes(base)
    bitacora(p, f"arquitectura: base sellada con {u} unidades heredadas ({a} archivos)"
             + (f"; ampliada: {args.motivo}" if args.ampliar else ""))
    print(f"[ok] base sellada: {u} unidades heredadas, {a} archivos, en {len(base['repos'])} repos.")


def cmd_adoptar(args) -> None:
    if not args.yes:
        sys.exit("[!!] adoptar requiere --yes: retira el bloqueo de la Feature #0 y pasa el\n"
                 "     proyecto al trinquete. Es decision del usuario.")
    p = paths()
    data = load_backlog(p)
    base = cargar_base(p) if modo_trinquete(p) else _sellar_base(p, data, False, None)
    liberadas = []
    for f in data["features"]:
        req = f.get("requiere")
        lista = req if isinstance(req, list) else ([] if req is None else [req])
        resto = [x for x in lista if str(x).lstrip("#") != "0"]
        if len(resto) != len(lista):
            liberadas.append(f["id"])
            if resto:
                f["requiere"] = resto
            else:
                f.pop("requiere", None)
    f0 = next((x for x in data["features"] if str(x.get("id")) == "0"), None)
    if f0 and f0.get("status") not in ("done", "superseded"):
        # Sigue viva como una rebanada de normalizacion mas: su trabajo no se pierde.
        f0["kind"] = KIND_NORMALIZACION
    # Lo que ya estaba en curso se termina con las reglas con las que empezo.
    en_curso = [x["id"] for x in data["features"]
                if x.get("status") in ("in_progress", "review", "blocked")
                and x.get("kind") != KIND_NORMALIZACION]
    _estado(data)["exentas_en_curso"] = en_curso
    save_backlog(p, data)
    u, a = restantes(base)
    bitacora(p, f"arquitectura: adoptado el trinquete ({u} unidades heredadas, {a} archivos); "
             f"{len(liberadas)} features liberadas de la #0")
    print(f"[ok] trinquete adoptado: {u} unidades heredadas, {a} archivos.")
    print(f"     features que ya no dependen de la #0 ({len(liberadas)}): "
          f"{', '.join('#' + str(i) for i in liberadas) or 'ninguna'}")
    if f0 and f0.get("kind") == KIND_NORMALIZACION:
        print("     la #0 sigue abierta como feature de normalizacion; ya no bloquea a las demas.")
    if en_curso:
        print(f"     en curso al adoptar, exentas hasta que cierren ({len(en_curso)}): "
              f"{', '.join('#' + str(i) for i in en_curso)}")


def cmd_check(args) -> None:
    p = paths()
    if not modo_trinquete(p):
        print("[i]  sin base de arquitectura: el trinquete no esta adoptado "
              "(arquitectura.py inventario; arquitectura.py adoptar --yes)")
        return
    data = load_backlog(p)
    base = cargar_base(p)
    if args.feature:
        f = get_feature(data, args.feature)
        res = evaluar_feature(p, data, f, base)
        if f.get("kind") == KIND_NORMALIZACION:
            print(f"[i]  #{f['id']} vacia {len(res['vaciadas'])} unidades y resuelve "
                  f"{res['violaciones_resueltas']} violaciones de la base")
    else:
        res = evaluar_global(p, base)
        if args.ajustar and not res["fallos"]:
            bajo = ajustar(p, base, res["ajustes"])
            if bajo:
                bitacora(p, f"arquitectura: base ajustada, {bajo} unidades menos")
                print(f"[ok] base ajustada: {bajo} unidades heredadas menos")
    for x in res["avisos"]:
        print(f"[!]  {x}")
    if res["fallos"]:
        print(f"[!!] arquitectura: {len(res['fallos'])} fallo(s) del trinquete:")
        for x in res["fallos"]:
            print(f"     - {x}")
        sys.exit(1)
    u, a = restantes(cargar_base(p))
    alcance = f"#{args.feature} contra su commit base" if args.feature else "los repos contra la base"
    print(f"[ok] arquitectura: {alcance}, sin crecimiento. Quedan {u} unidades heredadas ({a} archivos).")


def _toques(repo: Path, meses: int) -> dict[str, int]:
    code, out = git(["log", f"--since={meses} months ago", "--name-only", "--format="], repo)
    toques: dict[str, int] = {}
    for ruta in out.splitlines() if code == 0 else []:
        if ruta:
            toques[ruta] = toques.get(ruta, 0) + 1
    return toques


def cmd_siguiente(args) -> None:
    p = paths()
    if not modo_trinquete(p):
        sys.exit("[!!] sin base de arquitectura: corre antes arquitectura.py adoptar --yes")
    base = cargar_base(p)
    filas = []
    for clave, reg in base["repos"].items():
        repo, layout = Path(reg["path"]), layout_de(reg["stack"])
        if layout is None or not repo.is_dir():
            continue
        toques = _toques(repo, args.meses)
        por_unidad: dict[str, int] = {}
        for ruta, n in toques.items():
            if layout.heredado(ruta):
                unidad = layout.unidad(ruta)
                por_unidad[unidad] = por_unidad.get(unidad, 0) + n
        for unidad, archivos in reg.get("heredadas", {}).items():
            filas.append((por_unidad.get(unidad, 0), archivos, clave, unidad))
    filas.sort(key=lambda x: (-x[0], x[1]))
    print(f"Unidades heredadas, las mas tocadas en {args.meses} meses primero "
          f"({len(filas)} en total):")
    for toques, archivos, clave, unidad in filas[:args.n]:
        print(f"  {toques:>4} cambios  {archivos:>4} archivos  {clave}:{unidad}")
    print("\nPara normalizar una: add.py --kind normalizacion --name 'normalizar <unidad>'")


def cmd_eximir(args) -> None:
    if not args.yes:
        sys.exit("[!!] eximir requiere --yes: saca una unidad de la norma para siempre\n"
                 "     (codigo generado, por ejemplo). Es decision del usuario.")
    if not args.motivo.strip():
        sys.exit("[!!] eximir exige --motivo")
    p = paths()
    base = cargar_base(p)
    reg = base["repos"].get(args.repo)
    if reg is None:
        sys.exit(f"[!!] '{args.repo}' no esta en la base. Repos: {', '.join(base['repos'])}")
    if args.unidad not in reg.get("heredadas", {}):
        sys.exit(f"[!!] '{args.unidad}' no es una unidad heredada de {args.repo}")
    reg.setdefault("exentas", {})[args.unidad] = args.motivo.strip()
    reg["heredadas"].pop(args.unidad)
    guardar_base(p, base)
    bitacora(p, f"arquitectura: {args.repo}:{args.unidad} exenta de la norma: {args.motivo.strip()}")
    print(f"[ok] {args.repo}:{args.unidad} queda exenta.")


def resumen(p: dict, data: dict) -> str | None:
    """Una linea para estado.py; None si el proyecto no tiene stacks medibles."""
    if modo_trinquete(p):
        base = cargar_base(p)
        u, a = restantes(base)
        ini = (base.get("inicial") or {}).get("unidades")
        cuota = int(data["rules"].get("arquitectura_cuota", CUOTA))
        ids = data.get("arquitectura", {}).get("negocio_desde_normalizacion", [])
        partes = [f"{u} unidades heredadas ({a} archivos)" + (f" de {ini} al adoptar" if ini else "")]
        if cuota > 0 and u:
            partes.append(f"cuota {len(ids)}/{cuota}"
                          + (" <- toca una de normalizacion (arquitectura.py siguiente)"
                             if len(ids) >= cuota else ""))
        return "; ".join(partes)
    medibles = [d for d in destinos(p) if d["layout"] is not None]
    if not medibles:
        return None
    # Sin trinquete nada frena lo heredado: al menos se dice cuanto hay. Solo se
    # cuentan rutas (git ls-files); el verificador de cada stack no se corre aqui.
    unidades = archivos = 0
    for d in medibles:
        heredadas = heredados_por_unidad(d["layout"], rutas_en_disco(d["path"]))
        unidades += len(heredadas)
        archivos += sum(len(v) for v in heredadas.values())
    if not archivos:
        return "trinquete sin adoptar; 0 archivos fuera de la norma (arquitectura.py inventario)"
    return (f"[!] {archivos} archivos en {unidades} carpetas viven fuera de la norma del stack y nada "
            "los frena: trinquete sin adoptar (arquitectura.py inventario; adoptar --yes es del usuario)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("inventario")
    s.add_argument("--detalle", action="store_true"); s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_inventario)
    s = sub.add_parser("base")
    s.add_argument("--yes", action="store_true"); s.add_argument("--ampliar", action="store_true")
    s.add_argument("--motivo"); s.set_defaults(fn=cmd_base)
    s = sub.add_parser("adoptar"); s.add_argument("--yes", action="store_true")
    s.set_defaults(fn=cmd_adoptar)
    s = sub.add_parser("check"); s.add_argument("--feature")
    s.add_argument("--ajustar", action="store_true"); s.set_defaults(fn=cmd_check)
    s = sub.add_parser("siguiente"); s.add_argument("-n", type=int, default=10)
    s.add_argument("--meses", type=int, default=6); s.set_defaults(fn=cmd_siguiente)
    s = sub.add_parser("eximir"); s.add_argument("--repo", required=True)
    s.add_argument("--unidad", required=True); s.add_argument("--motivo", required=True)
    s.add_argument("--yes", action="store_true"); s.set_defaults(fn=cmd_eximir)
    args = ap.parse_args()
    try:
        args.fn(args)
    except ValueError as exc:
        sys.exit(f"[!!] {exc}")


if __name__ == "__main__":
    main()
