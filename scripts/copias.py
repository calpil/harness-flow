#!/usr/bin/env python3
"""Copias de la normativa de un stack instaladas en un repo: alcance real y vigencia.

Dos preguntas que `stack.py normalizar` no se hacia:

1. A QUE ARCHIVOS APLICA una regla. La plantilla trae `globs` con el layout
   canonico (`src/app/features/**`). Un repo cuyo codigo vive en otra ruta
   (`projects/*/src/app/`, `handlers/`) quedaba con una regla que no lo nombra.
   Aqui se mira primero donde esta el codigo del repo: si algun archivo queda
   fuera de los globs, la regla se amplia a `**/*.<ext>`. Se mide en cada
   normalizacion, asi que mover el codigo manana no deja la regla atras.

2. SI UNA COPIA ES VIEJA O ES DEL PROYECTO. Una copia distinta a la plantilla
   puede ser una version anterior (se actualiza) o una edicion del proyecto (se
   conserva y se avisa). Se distingue con dos pruebas, en este orden:
   - el registro de lo que el arnes instalo (`<git-dir>/harness-flow-copias.json`,
     fuera del arbol: no ensucia el repo ni se versiona);
   - el historial git de la plantilla: una copia igual a una version anterior
     nadie la edito.
   Sin ninguna de las dos pruebas la copia NO se toca.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

REGISTRO = "harness-flow-copias.json"
# Reglas que deben nombrar TODO el codigo del repo. Un stack puede declarar otra
# lista en manifest.normative.rules_cubren_codigo.
REGLAS_QUE_CUBREN_CODIGO = ("architecture.md", "security.md")
_DIRS_AJENOS = frozenset(("node_modules", "vendor", "dist", "build", "target", "bin", "obj",
                          "coverage", "__pycache__", "venv"))
_BASURA = frozenset((".DS_Store",))

FALTA, AL_DIA, VIEJA, MODIFICADA = "falta", "al_dia", "vieja", "modificada"


# --- archivos del repo -----------------------------------------------------

def _git(args: list[str], cwd: Path) -> tuple[int, str]:
    try:
        r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return r.returncode, r.stdout


def archivos_versionados(repo: Path) -> list[str]:
    """Rutas posix del repo: las versionadas si es git; si no, las que hay en disco.

    Vale tambien para una carpeta dentro de un repo (`api/` de un monorepo):
    `git ls-files` lista ahi las rutas relativas a esa carpeta.
    """
    code, out = _git(["ls-files", "-z"], repo) if repo.is_dir() else (1, "")
    versionadas = [x for x in out.split("\0") if x] if code == 0 else []
    if versionadas:
        return versionadas
    rutas: list[str] = []
    for actual, dirs, archivos in os.walk(str(repo)):
        dirs[:] = [d for d in dirs if d not in _DIRS_AJENOS and not d.startswith(".")]
        base = Path(actual).relative_to(repo).as_posix()
        rutas += [f if base == "." else f"{base}/{f}" for f in archivos]
    return rutas


def regex_glob(patron: str) -> re.Pattern:
    """Glob de rutas posix: `**/` cruza directorios (o ninguno), `*` no cruza `/`."""
    out, i = "", 0
    while i < len(patron):
        if patron.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif patron.startswith("**", i):
            out, i = out + ".*", i + 2
        elif patron[i] == "*":
            out, i = out + "[^/]*", i + 1
        else:
            out, i = out + re.escape(patron[i]), i + 1
    return re.compile(out + r"\Z")


def extensiones_de_codigo(manifest: dict) -> list[str]:
    """Extensiones que el stack llama codigo, sacadas de `layout.codigo` (`**/*.go` -> go)."""
    exts: list[str] = []
    for patron in (manifest.get("layout") or {}).get("codigo", []):
        m = re.search(r"\*\.(\w+)\Z", patron) if isinstance(patron, str) else None
        if m and m.group(1) not in exts:
            exts.append(m.group(1))
    return exts


def codigo_del_repo(rutas: list[str], exts: list[str], propios=()) -> list[str]:
    """Archivos con extension de codigo, vivan donde vivan.

    Fuera quedan lo de terceros (node_modules, vendor...), las carpetas ocultas
    (ahi viven las copias de skills) y los validadores que instala el arnes.
    """
    sufijos = tuple("." + e for e in exts)
    propios = set(propios)
    out = []
    for ruta in rutas:
        partes = ruta.split("/")
        if (ruta.endswith(sufijos) and ruta not in propios
                and not any(x in _DIRS_AJENOS or x.startswith(".") for x in partes[:-1])):
            out.append(ruta)
    return out


# --- alcance de una regla --------------------------------------------------

_GLOBS_RE = re.compile(r"^(globs:[ \t]*)(\[.*\])[ \t]*$", re.MULTILINE)


def leer_globs(texto: str) -> list[str] | None:
    """Los `globs` del frontmatter (lista en una linea); None si la regla no los declara."""
    if not texto.startswith("---"):
        return None
    partes = texto.split("---", 2)
    m = _GLOBS_RE.search(partes[1]) if len(partes) >= 3 else None
    if not m:
        return None
    try:
        valor = ast.literal_eval(m.group(2))
    except (ValueError, SyntaxError):
        return None
    return [x for x in valor if isinstance(x, str)] if isinstance(valor, list) else None


def ajustar_alcance(texto: str, codigo: list[str]) -> tuple[str, dict | None]:
    """(texto de la regla para ESTE repo, que se amplio).

    Si todo el codigo del repo cae en los globs de la plantilla, el texto vuelve
    igual, byte a byte. Si no, se agrega `**/*.<ext>` por cada extension con
    archivos sin cubrir: la regla nombra el codigo donde este.
    """
    globs = leer_globs(texto)
    if globs is None or not codigo:
        return texto, None
    patrones = [regex_glob(g) for g in globs]
    sin_cubrir = [r for r in codigo if not any(p.match(r) for p in patrones)]
    if not sin_cubrir:
        return texto, None
    agregados = sorted({"**/*." + r.rsplit(".", 1)[1] for r in sin_cubrir})
    nuevos = globs + [g for g in agregados if g not in globs]
    partes = texto.split("---", 2)
    cabecera = _GLOBS_RE.sub(lambda m: m.group(1) + json.dumps(nuevos, ensure_ascii=False),
                             partes[1], count=1)
    return "---".join([partes[0], cabecera, partes[2]]), {
        "sin_cubrir": len(sin_cubrir), "ejemplo": sorted(sin_cubrir)[0], "agregados": agregados}


# --- huellas ---------------------------------------------------------------

def huella(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def _blob(datos: bytes) -> str:
    """El id que git le da a ese contenido."""
    return hashlib.sha1(b"blob %d\0" % len(datos) + datos).hexdigest()


def archivos_de(carpeta: Path) -> dict[str, bytes]:
    """{ruta relativa: contenido} de una carpeta, sin caches ni basura del SO."""
    out = {}
    for f in sorted(carpeta.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts and f.name not in _BASURA:
            out[f.relative_to(carpeta).as_posix()] = f.read_bytes()
    return out


def huella_arbol(archivos: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    for rel in sorted(archivos):
        h.update(rel.encode() + b"\0" + huella(archivos[rel]).encode() + b"\0")
    return h.hexdigest()


# --- registro de lo instalado ----------------------------------------------

def ruta_registro(repo: Path) -> tuple[Path, str] | None:
    """(`<git-dir>/harness-flow-copias.json`, carpeta del repo dentro del arbol git).

    None si `repo` no esta en un arbol git. La carpeta es "." para un repo
    propio y `api` para una carpeta de un monorepo: cada una lleva su seccion.
    """
    if not repo.is_dir():
        return None
    code, out = _git(["rev-parse", "--git-path", REGISTRO, "--show-prefix"], repo)
    lineas = out.splitlines()
    if code != 0 or not lineas or not lineas[0].strip():
        return None
    ruta = Path(lineas[0].strip())
    prefijo = lineas[1].strip().rstrip("/") if len(lineas) > 1 else ""
    return (ruta if ruta.is_absolute() else repo / ruta), prefijo or "."


def _secciones(ruta: Path) -> dict[str, dict[str, str]]:
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    secciones = datos.get("repos") if isinstance(datos, dict) else None
    return {k: v for k, v in secciones.items() if isinstance(v, dict)} if isinstance(secciones, dict) else {}


def leer_registro(repo: Path) -> dict[str, str]:
    """{ruta de la copia: huella que el arnes dejo}; vacio si no hay registro."""
    donde = ruta_registro(repo)
    if donde is None:
        return {}
    seccion = _secciones(donde[0]).get(donde[1], {})
    return {k: v for k, v in seccion.items() if isinstance(v, str)}


def guardar_registro(repo: Path, copias: dict[str, str]) -> None:
    donde = ruta_registro(repo)
    if donde is None:
        return
    ruta, prefijo = donde
    secciones = _secciones(ruta)
    if secciones.get(prefijo) == copias:
        return
    secciones[prefijo] = dict(sorted(copias.items()))
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps({"version": 1, "repos": secciones}, indent=2) + "\n",
                        encoding="utf-8")
    except OSError:
        pass  # sin registro queda el historial de la plantilla como prueba


# --- historial de la plantilla ---------------------------------------------

_cache_raiz: dict[Path, Path | None] = {}
_cache_blobs: dict[tuple[Path, str], set[str] | None] = {}
_cache_arboles: dict[tuple[Path, str], list[dict[str, str]] | None] = {}


def _raiz_git(carpeta: Path) -> Path | None:
    if carpeta not in _cache_raiz:
        code, out = _git(["rev-parse", "--show-toplevel"], carpeta) if carpeta.is_dir() else (1, "")
        _cache_raiz[carpeta] = Path(out.strip()).resolve() if code == 0 and out.strip() else None
    return _cache_raiz[carpeta]


def _relativa(raiz: Path, ruta: Path) -> str | None:
    try:
        return ruta.resolve().relative_to(raiz).as_posix()
    except ValueError:
        return None


def fue_version_de_archivo(plantilla: Path, datos: bytes) -> bool | None:
    """True si `datos` es una version anterior (o la actual) de la plantilla.

    None si no se puede saber: la skill no es un clon git o no tiene historial.
    """
    raiz = _raiz_git(plantilla.parent)
    rel = _relativa(raiz, plantilla) if raiz else None
    if rel is None:
        return None
    clave = (raiz, rel)
    if clave not in _cache_blobs:
        code, out = _git(["log", "--format=", "--raw", "--no-abbrev", "--", rel], raiz)
        blobs: set[str] = set()
        for linea in out.splitlines() if code == 0 else []:
            campos = linea.split()
            if linea.startswith(":") and len(campos) >= 4:
                blobs.update(campos[2:4])
        _cache_blobs[clave] = blobs or None
    blobs = _cache_blobs[clave]
    return None if blobs is None else _blob(datos) in blobs


_cache_reglas: dict[tuple[Path, str], set[str] | None] = {}


def _sin_alcance(datos: bytes) -> str:
    """Huella de una regla sin su linea `globs`: el alcance lo calcula el arnes por repo."""
    texto = datos.decode("utf-8", errors="replace")
    if texto.startswith("---"):
        partes = texto.split("---", 2)
        if len(partes) >= 3:
            texto = "---".join([partes[0], _GLOBS_RE.sub("globs: []", partes[1], count=1), partes[2]])
    return huella(texto.encode("utf-8"))


def fue_version_de_regla(plantilla: Path, datos: bytes) -> bool | None:
    """Como `fue_version_de_archivo`, sin contar la linea `globs`.

    Una regla con el alcance ajustado por el arnes no esta en el historial tal
    cual: lo que prueba que nadie la edito es que su cuerpo si lo este.
    """
    if _sin_alcance(datos) == _sin_alcance(plantilla.read_bytes()):
        return True  # el cuerpo es el de la plantilla de hoy: solo cambia el alcance
    raiz = _raiz_git(plantilla.parent)
    rel = _relativa(raiz, plantilla) if raiz else None
    if rel is None:
        return None
    clave = (raiz, rel)
    if clave not in _cache_reglas:
        code, out = _git(["log", "--format=%H", "--", rel], raiz)
        versiones: set[str] = set()
        for commit in out.split() if code == 0 else []:
            try:
                r = subprocess.run(["git", "show", f"{commit}:{rel}"], cwd=str(raiz),
                                   capture_output=True, timeout=60)
            except (OSError, subprocess.TimeoutExpired):
                continue
            if r.returncode == 0:
                versiones.add(_sin_alcance(r.stdout))
        _cache_reglas[clave] = versiones or None
    versiones = _cache_reglas[clave]
    return None if versiones is None else _sin_alcance(datos) in versiones


def fue_version_de_carpeta(plantilla: Path, archivos: dict[str, bytes]) -> bool | None:
    """Como `fue_version_de_archivo`, para una carpeta entera (una skill)."""
    raiz = _raiz_git(plantilla)
    rel = _relativa(raiz, plantilla) if raiz else None
    if rel is None:
        return None
    clave = (raiz, rel)
    if clave not in _cache_arboles:
        code, out = _git(["log", "--format=%H", "--", rel], raiz)
        arboles = []
        for commit in out.split() if code == 0 else []:
            code2, lista = _git(["ls-tree", "-r", "-z", commit, "--", rel], raiz)
            if code2 != 0:
                continue
            arbol = {}
            for entrada in lista.split("\0"):
                meta, _, ruta = entrada.partition("\t")
                campos = meta.split()
                if len(campos) == 3 and campos[1] == "blob" and Path(ruta).name not in _BASURA:
                    arbol[ruta[len(rel) + 1:]] = campos[2]
            arboles.append(arbol)
        _cache_arboles[clave] = arboles or None
    arboles = _cache_arboles[clave]
    if arboles is None:
        return None
    actual = {r: _blob(d) for r, d in archivos.items()}
    return any(actual == a for a in arboles)


# --- estado de una copia ---------------------------------------------------

def estado(actual: str | None, esperado: str, registrada: str | None, fue_version) -> tuple[str, str]:
    """(estado, motivo) de una copia instalada.

    `actual` es su huella (None si no existe), `esperado` la que deberia tener,
    `registrada` la que el arnes dejo la ultima vez y `fue_version()` consulta
    el historial de la plantilla.
    """
    if actual is None:
        return FALTA, ""
    if actual == esperado:
        return AL_DIA, ""
    if registrada and actual == registrada:
        return VIEJA, "nadie la edito desde que el arnes la instalo"
    previa = fue_version()
    if previa:
        return VIEJA, "es una version anterior de la plantilla"
    if previa is None:
        return MODIFICADA, "no se pudo comprobar si es una version anterior (la skill no es un clon git)"
    return MODIFICADA, "el proyecto la edito"
