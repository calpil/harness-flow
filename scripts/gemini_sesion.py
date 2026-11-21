#!/usr/bin/env python3
"""Publica en la sesion de Gemini (AGY y Gemini CLI) las rules y skills del stack del rol.

AGY carga `.agents/rules/*.md` (con `trigger: always_on`) y `.agents/skills/<nombre>/SKILL.md`
subiendo desde el workspace hasta `.git`. Gemini CLI carga `.gemini/rules/*.md` y
`.gemini/skills/<nombre>/SKILL.md`. Ninguno camina hacia repos hermanos: una sesion abierta
en el front (ej. `angular-product`) no descubre en disco las rules/skills del backend
(`golang-hexagonal`, `dotnet-hexagonal`, etc.) que vive fuera del repo.

Este modulo sincroniza en `.agents/` y `.gemini/` de la raiz, cada repo del conjunto y
cada worktree:
  - `harness-flow-sesion.md` (con `trigger: always_on`), el rol activo, los stacks y el
    modelo Gemini 4 esperado (`Carbon High`, `Argon High` o `Hydrogen`).
  - `<stack>--<regla>.md` (con `trigger: always_on`) y `<stack>--<skill>/SKILL.md`.

Para cuidar el `defaultRulesBudget` de AGY (20.000 tokens / 24 KB por archivo), si un
destino YA tiene instalada y vigente la copia nativa sin prefijo de un stack (puesta por
`stack.py normalizar`), no duplica ese mismo stack en esa carpeta: solo agrega los stacks
hermanos y los que falten o esten desactualizados.

Toda copia lleva marca (`harness-flow-gemini` / `.harness-flow-generada`), se excluye en
`.git/info/exclude` para no ensuciar `git status` ni `gate.py close`, y el rol siguiente
retira lo que ya no toca. Lo que creo el usuario o `stack.py normalizar` nunca se toca.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

MARCA = "harness-flow-gemini"
MARCADOR = ".harness-flow-generada"
SESION = "harness-flow-sesion.md"
CARPETAS = (".agents", ".gemini")
_PATRONES = tuple(
    p
    for c in CARPETAS
    for p in (f"{c}/rules/*--*", f"{c}/rules/{SESION}", f"{c}/skills/*--*")
)


def publicar(raiz: Path, por_stack: dict, rules: dict | None, rol: str,
             extras: list[Path] | None = None) -> list[str]:
    """Escribe el conjunto de este rol en `.agents/` y `.gemini/`. Lista vacia fuera de Gemini."""
    import entorno
    if entorno.host_agente() != "gemini":
        return []
    destinos = _destinos(raiz, por_stack, extras or [])
    if not destinos:
        return []
    piezas_por_stack = _piezas_por_stack(por_stack, rules)
    avisos: list[str] = []
    if not piezas_por_stack:
        retiradas = False
        for destino in destinos:
            try:
                for carpeta in CARPETAS:
                    if not _hay_marca(destino, carpeta):
                        continue
                    _retirar(destino, carpeta, {})
                    sesion = destino / carpeta / "rules" / SESION
                    if sesion.is_file() and not sesion.is_symlink():
                        sesion.unlink()
                    retiradas = True
            except OSError as exc:
                avisos.append(f"[!] gemini sesion: no se pudo retirar en {destino} ({exc})")
        if not retiradas:
            return avisos
        return avisos + [
            f"gemini sesion ({rol}): ningun stack normativo; se retiraron las rules y skills de la sesion."]

    escritos: list[str] = []
    for destino in destinos:
        try:
            _excluir(destino)
            toco_algo = False
            for carpeta in CARPETAS:
                if _carpeta_es_enlace(destino, carpeta):
                    # En worktrees con `enlazar_normativa`, `.agents/rules` o `.gemini/rules`
                    # apuntan al checkout principal: no se escribe a traves del enlace.
                    continue
                piezas = _piezas_para_destino(destino, carpeta, piezas_por_stack)
                _escribir(destino, carpeta, piezas, rol, por_stack)
                _retirar(destino, carpeta, piezas)
                toco_algo = True
            if toco_algo:
                escritos.append(str(destino))
        except OSError as exc:
            avisos.append(f"[!] gemini sesion: no se pudo publicar en {destino} ({exc})")

    stacks = ", ".join(por_stack)
    donde = ", ".join(f"{d}/(.agents,.gemini)" for d in escritos) if escritos else "(enlaces delegados al checkout)"
    return avisos + [
        f"gemini sesion ({rol}): rules y skills de {stacks} en {donde}. "
        "AGY (.agents/) y Gemini CLI (.gemini/) las cargan en esta sesion sin duplicar "
        "las copias nativas ya vigentes. Cada skill de sesion se llama <stack>--<nombre>."]


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


def _piezas_por_stack(por_stack: dict, rules: dict | None) -> dict[str, dict[str, dict]]:
    """{sid: {'rules': {nombre: (huella, bytes)}, 'skills': {nombre: (huella, origen_dir)}}}."""
    import contexto
    import stack
    out: dict[str, dict[str, dict]] = {}
    for sid, lista in por_stack.items():
        manifest = stack.cargar_manifest(sid)
        normativa = manifest.get("normative", {})
        repos = [ruta for _, ruta in lista]
        reglas_map: dict[str, tuple[str, bytes]] = {}
        for nombre in normativa.get("rules", []):
            cuerpo, _ = contexto._texto_regla(repos, sid, nombre)
            if not cuerpo:
                continue
            texto = (
                "---\n"
                "trigger: always_on\n"
                "---\n"
                f"<!-- {MARCA} -->\n\n"
                f"# {sid} / {nombre}\n\n"
                f"{cuerpo}\n"
            )
            datos = texto.encode("utf-8")
            reglas_map[nombre] = (_huella_bytes(datos), datos)
        skills_map: dict[str, tuple[str, Path]] = {}
        excluidas = stack.skills_excluidas(rules, sid)
        for nombre in normativa.get("skills", []):
            if nombre in excluidas or "--" in nombre or "--" in sid:
                continue
            origen, _ = contexto._skill_md(repos, sid, nombre)
            if origen is None:
                continue
            carpeta = origen.parent
            skills_map[nombre] = (_huella_arbol(carpeta), carpeta)
        if reglas_map or skills_map:
            out[sid] = {"rules": reglas_map, "skills": skills_map}
    return out


def _ya_nativa_vigente(destino: Path, carpeta: str, sid: str, tipo: str, nombre: str) -> bool:
    """True si `destino` ya tiene esa regla/skill de `sid` instalada y vigente sin prefijo."""
    import stack
    if tipo == "rules":
        ruta = destino / carpeta / "rules" / nombre
        if not ruta.is_file():
            return False
        return bool(stack.copia_vigente(destino, sid, f"{carpeta}/rules/{nombre}"))
    ruta = destino / carpeta / "skills" / nombre / "SKILL.md"
    if not ruta.is_file():
        return False
    return bool(stack.copia_vigente(destino, sid, f"{carpeta}/skills/{nombre}"))


def _piezas_para_destino(destino: Path, carpeta: str,
                         piezas_por_stack: dict[str, dict[str, dict]]) -> dict[str, tuple[str, bytes | Path]]:
    """Mapa `{rel: (huella, datos_o_origen)}` filtrando lo que `destino` ya tiene nativo y vigente."""
    piezas: dict[str, tuple[str, bytes | Path]] = {}
    for sid, grupo in piezas_por_stack.items():
        for nombre, (huella, datos) in grupo["rules"].items():
            if _ya_nativa_vigente(destino, carpeta, sid, "rules", nombre):
                continue
            piezas[f"{carpeta}/rules/{sid}--{nombre}"] = (huella, datos)
        for nombre, (huella, origen_dir) in grupo["skills"].items():
            if _ya_nativa_vigente(destino, carpeta, sid, "skills", nombre):
                continue
            piezas[f"{carpeta}/skills/{sid}--{nombre}"] = (huella, origen_dir)
    return piezas


def _carpeta_es_enlace(destino: Path, carpeta: str) -> bool:
    for sub in (destino / carpeta, destino / carpeta / "rules", destino / carpeta / "skills"):
        if sub.is_symlink():
            return True
    return False


def _escribir(destino: Path, carpeta: str, piezas: dict[str, tuple[str, bytes | Path]],
              rol: str, por_stack: dict) -> None:
    reglas = destino / carpeta / "rules"
    reglas.mkdir(parents=True, exist_ok=True)
    sesion = _texto_sesion(rol, por_stack, carpeta).encode("utf-8")
    _poner(reglas / SESION, sesion)
    pref_rules = f"{carpeta}/rules/"
    for rel, (huella, carga) in piezas.items():
        ruta = destino / rel
        if rel.startswith(pref_rules):
            assert isinstance(carga, bytes)
            _poner(ruta, carga)
            continue
        assert isinstance(carga, Path)
        marca = ruta / MARCADOR
        if marca.is_file() and marca.read_text(encoding="utf-8").strip() == huella:
            continue
        if ruta.exists() and not _es_nuestra(ruta):
            continue
        sid, nombre = ruta.name.split("--", 1)
        if ruta.exists():
            shutil.rmtree(ruta)
        shutil.copytree(carga, ruta, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
        skill = ruta / "SKILL.md"
        skill.write_text(_parchear_skill(skill.read_text(encoding="utf-8"), sid, nombre),
                         encoding="utf-8")
        marca.write_text(huella + "\n", encoding="utf-8")


def _retirar(destino: Path, carpeta: str, piezas: dict[str, tuple[str, bytes | Path]]) -> None:
    reglas = destino / carpeta / "rules"
    if reglas.is_dir() and not reglas.is_symlink():
        for ruta in reglas.glob("*.md"):
            rel = f"{carpeta}/rules/{ruta.name}"
            if rel in piezas or ruta.name == SESION:
                continue
            if MARCA in ruta.read_text(encoding="utf-8", errors="ignore")[:200]:
                ruta.unlink()
    skills = destino / carpeta / "skills"
    if skills.is_dir() and not skills.is_symlink():
        for ruta in skills.iterdir():
            rel = f"{carpeta}/skills/{ruta.name}"
            marca = ruta / MARCADOR
            if not marca.is_file() or rel in piezas:
                continue
            shutil.rmtree(ruta)


def _texto_sesion(rol: str, por_stack: dict, carpeta: str) -> str:
    cliente = "AGY (Antigravity)" if carpeta == ".agents" else "Gemini CLI"
    lineas = [
        "---",
        "trigger: always_on",
        "---",
        f"<!-- {MARCA} -->",
        "",
        f"# Skills y rules de esta sesion ({cliente})",
        "",
        f"Rol: {rol}.",
    ]
    try:
        import modelo
        rol_modelo = "producto" if rol == "sdd" else ("implementer" if rol == "feature" else rol)
        if rol_modelo in modelo.GEMINI_4_ROLES:
            info = modelo.GEMINI_4_ROLES[rol_modelo]
            lineas.append(f"Modelo Gemini 4 para este rol: {info['nombre']} (`{info['id']}`, effort `{info['effort']}`).")
    except Exception:
        pass
    if not por_stack:
        lineas += ["", "Ningun stack normativo en este rol. Las copias anteriores de esta sesion se retiraron."]
        return "\n".join(lineas) + "\n"
    lineas.append("Stacks activos:")
    for sid, lista in por_stack.items():
        lineas.append(f"- {sid}: {', '.join(nombre for nombre, _ in lista)}")
    lineas += [
        "",
        f"Estas rules y skills complementan las nativas en `{carpeta}/rules/` y `{carpeta}/skills/`.",
        "Las de repos hermanos llevan el prefijo `<stack>--<nombre>` y aplican SOLO al repo de ese stack.",
        "Una skill de otro stack no se aplica en el repo equivocado.",
        "",
    ]
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


def _hay_marca(destino: Path, carpeta: str) -> bool:
    reglas = destino / carpeta / "rules"
    if reglas.is_dir() and not reglas.is_symlink():
        for ruta in reglas.glob("*.md"):
            if MARCA in ruta.read_text(encoding="utf-8", errors="ignore")[:200]:
                return True
    skills = destino / carpeta / "skills"
    if skills.is_dir() and not skills.is_symlink():
        return any((ruta / MARCADOR).is_file() for ruta in skills.iterdir() if ruta.is_dir())
    return False


def _es_nuestra(ruta: Path) -> bool:
    if (ruta / MARCADOR).is_file():
        return True
    skill = ruta / "SKILL.md"
    return skill.is_file() and MARCA in skill.read_text(encoding="utf-8", errors="ignore")[:2500]


def _excluir(destino: Path) -> None:
    """`info/exclude` local: la copia de sesion no entra en commits ni ensucia `close`."""
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
