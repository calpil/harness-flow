#!/usr/bin/env python3
"""Publica en la sesion de Grok las rules y skills del stack que toca el rol.

Grok carga `.grok/rules/*.md` y `.grok/skills/<nombre>/SKILL.md` del repo en
el que esta parada la sesion. No camina a un repo hermano: un front en la raiz
y un servicio fuera de ella dejaban al backend fuera de la sesion. El brief
imprimia el texto, y la skill no quedaba invocable.

Aqui cada rol escribe, en la raiz del arnes, en cada repo del conjunto y en
el worktree, una copia con nombre `<stack>--<skill>`. Grok la descubre aunque
el directorio este ignorado. `info/exclude` la deja fuera de git para que
`close` no vea el arbol sucio. Otra llamada sustituye el conjunto: lo que ese
rol no nombra se retira. Lo que el usuario puso en `.grok/` sin la marca no
se toca.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

MARCA = "harness-flow-grok"
MARCADOR = ".harness-flow-generada"
SESION = "harness-flow-sesion.md"
_PATRONES = (
    ".grok/rules/*--*",
    ".grok/rules/harness-flow-sesion.md",
    ".grok/skills/*--*",
)


def publicar(raiz: Path, por_stack: dict, rules: dict | None, rol: str,
             extras: list[Path] | None = None) -> list[str]:
    """Escribe el conjunto de este rol. Lista vacia si el host no es Grok.

    `por_stack` es el de contexto._por_stack: {stack: [(nombre, ruta)]}.
    Un conjunto vacio retira lo publicado antes en esos directorios.
    """
    import entorno
    if entorno.host_agente() != "grok":
        return []
    destinos = _destinos(raiz, por_stack, extras or [])
    if not destinos:
        return []
    piezas = _piezas(por_stack, rules)
    avisos: list[str] = []
    if not piezas:
        # Sin stack no se crea la sesion. Si una llamada anterior dejo copias
        # marcadas, se retiran: el rol que no toca un stack no lo deja cargado.
        retiradas = False
        for destino in destinos:
            try:
                if not _hay_marca(destino):
                    continue
                _retirar(destino, {})
                sesion = destino / ".grok" / "rules" / SESION
                if sesion.is_file():
                    sesion.unlink()
                retiradas = True
            except OSError as exc:
                avisos.append(f"[!] grok sesion: no se pudo retirar en {destino} ({exc})")
        if not retiradas:
            return avisos
        return avisos + [
            f"grok sesion ({rol}): ningun stack normativo; se retiraron las rules y skills de la sesion."]
    for destino in destinos:
        try:
            _excluir(destino)
            _escribir(destino, piezas, rol, por_stack)
            _retirar(destino, piezas)
        except OSError as exc:
            avisos.append(f"[!] grok sesion: no se pudo publicar en {destino} ({exc})")
    stacks = ", ".join(por_stack)
    donde = ", ".join(str(d / ".grok") for d in destinos)
    return avisos + [
        f"grok sesion ({rol}): rules y skills de {stacks} en {donde}. "
        "Grok las carga como rules y skills de esta sesion. "
        "Cada skill se llama <stack>--<nombre> y aplica solo a su stack."]


def _destinos(raiz: Path, por_stack: dict, extras: list[Path]) -> list[Path]:
    vistos: list[Path] = []

    def agregar(ruta: Path) -> None:
        try:
            ruta = ruta.resolve()
        except OSError:
            return
        if ruta.is_dir() and ruta not in vistos:
            vistos.append(ruta)

    agregar(raiz)
    for lista in por_stack.values():
        for _, ruta in lista:
            agregar(Path(ruta))
    for extra in extras:
        agregar(Path(extra))
    return vistos


def arboles_extra(raiz: Path, f: dict) -> list[Path]:
    """Worktrees de la feature, relativos a la raiz o absolutos."""
    crudos = [f.get("worktree")]
    for fila in (f.get("multi_repo") or {}).get("repos", []):
        crudos.append(fila.get("worktree"))
    hechos: list[Path] = []
    for crudo in crudos:
        if not crudo:
            continue
        for cand in (Path(str(crudo)), raiz / str(crudo)):
            if cand.is_dir():
                hechos.append(cand)
                break
    return hechos


def _piezas(por_stack: dict, rules: dict | None) -> dict[str, tuple[str, bytes]]:
    """{ruta relativa: (huella, bytes)} de rules y skills de este conjunto."""
    import contexto
    import stack
    piezas: dict[str, tuple[str, bytes]] = {}
    for sid, lista in por_stack.items():
        manifest = stack.cargar_manifest(sid)
        normativa = manifest.get("normative", {})
        repos = [ruta for _, ruta in lista]
        for nombre in normativa.get("rules", []):
            cuerpo, _ = contexto._texto_regla(repos, sid, nombre)
            if not cuerpo:
                continue
            texto = f"<!-- {MARCA} -->\n\n# {sid} / {nombre}\n\n{cuerpo}\n"
            rel = f".grok/rules/{sid}--{nombre}"
            piezas[rel] = (_huella_bytes(texto.encode()), texto.encode())
        excluidas = stack.skills_excluidas(rules, sid)
        for nombre in normativa.get("skills", []):
            if nombre in excluidas or "--" in nombre or "--" in sid:
                continue
            origen, _ = contexto._skill_md(repos, sid, nombre)
            if origen is None:
                continue
            carpeta = origen.parent
            rel = f".grok/skills/{sid}--{nombre}"
            piezas[rel] = (_huella_arbol(carpeta), b"")
    return piezas


def _escribir(destino: Path, piezas: dict[str, tuple[str, bytes]], rol: str,
              por_stack: dict) -> None:
    import contexto
    for sub in (destino / ".grok", destino / ".grok" / "rules", destino / ".grok" / "skills"):
        if _es_enlace(sub):
            raise OSError(f"{sub} es un enlace; no se escribe a traves de el")
    reglas = destino / ".grok" / "rules"
    reglas.mkdir(parents=True, exist_ok=True)
    sesion = _texto_sesion(rol, por_stack).encode()
    _poner(reglas / SESION, sesion)
    for rel, (huella, datos) in piezas.items():
        ruta = destino / rel
        if rel.startswith(".grok/rules/"):
            _poner(ruta, datos)
            continue
        marca = ruta / MARCADOR
        if marca.is_file() and marca.read_text(encoding="utf-8").strip() == huella:
            continue
        if ruta.exists() and not _es_nuestra(ruta):
            continue
        sid, nombre = ruta.name.split("--", 1)
        origen, _ = contexto._skill_md(
            [repo for _, repo in por_stack.get(sid, [])], sid, nombre)
        if origen is None:
            continue
        if ruta.exists():
            shutil.rmtree(ruta)
        shutil.copytree(origen.parent, ruta, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
        skill = ruta / "SKILL.md"
        skill.write_text(_parchear_skill(skill.read_text(encoding="utf-8"), sid, nombre),
                         encoding="utf-8")
        marca.write_text(huella + "\n", encoding="utf-8")


def _retirar(destino: Path, piezas: dict[str, tuple[str, bytes]]) -> None:
    reglas = destino / ".grok" / "rules"
    if reglas.is_dir() and not reglas.is_symlink():
        for ruta in reglas.glob("*.md"):
            rel = f".grok/rules/{ruta.name}"
            if rel in piezas or ruta.name == SESION:
                continue
            if MARCA in ruta.read_text(encoding="utf-8", errors="ignore")[:80]:
                ruta.unlink()
    skills = destino / ".grok" / "skills"
    if skills.is_dir() and not skills.is_symlink():
        for ruta in skills.iterdir():
            rel = f".grok/skills/{ruta.name}"
            marca = ruta / MARCADOR
            if not marca.is_file() or rel in piezas:
                continue
            shutil.rmtree(ruta)


def _texto_sesion(rol: str, por_stack: dict) -> str:
    lineas = [f"<!-- {MARCA} -->", "", "# Skills y rules de esta sesion", "",
              f"Rol: {rol}."]
    if not por_stack:
        lineas += ["", "Ningun stack normativo en este rol. Las copias anteriores de esta sesion se retiraron."]
        return "\n".join(lineas) + "\n"
    lineas.append("Stacks:")
    for sid, lista in por_stack.items():
        lineas.append(f"- {sid}: {', '.join(nombre for nombre, _ in lista)}")
    lineas += [
        "",
        "Estas rules y skills son las de este rol. Grok las carga desde `.grok/rules/` y `.grok/skills/`.",
        "El nombre de cada skill es `<stack>--<nombre>`. Aplica solo al repo de ese stack.",
        "Una skill de otro stack no se usa en este repo.",
        ""]
    return "\n".join(lineas)


def _parchear_skill(texto: str, sid: str, nombre: str) -> str:
    """El `name` queda unico entre stacks. La descripcion dice a cual pertenece."""
    nuevo = f"{sid}--{nombre}"
    prefijo = f"Stack {sid}."
    if not texto.startswith("---"):
        return f"---\nname: {nuevo}\ndescription: {prefijo}\n---\n\n<!-- {MARCA} -->\n\n{texto}"
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return texto
    salida: list[str] = []
    tiene_nombre = False
    prefijar_bloque = False
    for linea in partes[1].splitlines():
        if linea.startswith("name:"):
            salida.append(f"name: {nuevo}")
            tiene_nombre = True
            continue
        if linea.startswith("description:"):
            valor = linea.split(":", 1)[1].strip()
            if valor in ("", ">", "|", ">-", "|-"):
                salida.append(linea)
                prefijar_bloque = prefijo not in partes[1]
                continue
            if not valor.startswith(prefijo):
                linea = f"description: {prefijo} {valor}"
            salida.append(linea)
            continue
        if prefijar_bloque and linea.strip():
            salida.append(f"{linea[:len(linea) - len(linea.lstrip())]}{prefijo} {linea.strip()}")
            prefijar_bloque = False
            continue
        salida.append(linea)
    if not tiene_nombre:
        salida.insert(0, f"name: {nuevo}")
    cuerpo = partes[2]
    if MARCA not in cuerpo[:200]:
        cuerpo = f"\n<!-- {MARCA} -->\n{cuerpo}"
    return "---\n" + "\n".join(salida).strip("\n") + "\n---" + cuerpo


def _poner(ruta: Path, datos: bytes) -> None:
    if ruta.is_file() and ruta.read_bytes() == datos:
        return
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(datos)


def _hay_marca(destino: Path) -> bool:
    reglas = destino / ".grok" / "rules"
    if reglas.is_dir() and not reglas.is_symlink():
        for ruta in reglas.glob("*.md"):
            if MARCA in ruta.read_text(encoding="utf-8", errors="ignore")[:80]:
                return True
    skills = destino / ".grok" / "skills"
    if skills.is_dir() and not skills.is_symlink():
        return any((ruta / MARCADOR).is_file() for ruta in skills.iterdir() if ruta.is_dir())
    return False


def _es_nuestra(ruta: Path) -> bool:
    if (ruta / MARCADOR).is_file():
        return True
    skill = ruta / "SKILL.md"
    return skill.is_file() and MARCA in skill.read_text(encoding="utf-8", errors="ignore")[:2500]


def _excluir(destino: Path) -> None:
    """`info/exclude` local: la copia no entra en el commit ni ensucia `close`.

    El patron es relativo a la raiz del repo. Si el destino es un subdirectorio
    (un `api/` dentro del front), el patron lleva ese prefijo.
    """
    from comun import git
    code, top = git(["rev-parse", "--show-toplevel"], destino)
    code_ex, ruta = git(["rev-parse", "--git-path", "info/exclude"], destino)
    if code != 0 or code_ex != 0:
        return
    try:
        prefijo = destino.resolve().relative_to(Path(top.strip()).resolve()).as_posix()
    except ValueError:
        return
    prefijo = "" if prefijo == "." else prefijo + "/"
    exclude = Path(ruta.strip())
    if not exclude.is_absolute():
        exclude = destino / exclude
    previo = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
    faltan = [prefijo + p for p in _PATRONES if (prefijo + p) not in previo.splitlines()]
    if not faltan:
        return
    exclude.parent.mkdir(parents=True, exist_ok=True)
    cola = (("" if previo.endswith("\n") or not previo else "\n")
            + f"# {MARCA}\n" + "\n".join(faltan) + "\n")
    exclude.write_text(previo + cola, encoding="utf-8")


def _es_enlace(ruta: Path) -> bool:
    return ruta.is_symlink()


def _huella_bytes(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def _huella_arbol(carpeta: Path) -> str:
    h = hashlib.sha256()
    for ruta in sorted(p for p in carpeta.rglob("*") if p.is_file()):
        if "__pycache__" in ruta.parts or ruta.name == ".DS_Store":
            continue
        h.update(ruta.relative_to(carpeta).as_posix().encode())
        h.update(ruta.read_bytes())
    return h.hexdigest()
