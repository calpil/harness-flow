#!/usr/bin/env python3
"""Validador normativo de la API .NET en capas por feature (CALPIL, stack dotnet-layered).

Un solo proyecto, una carpeta por feature y una clase por capa:
Controller -> Service -> Repository. El compilador no impide saltarse capas; este
verificador lee el codigo fuente, igual que `LayeringTests` de la plantilla, y
vale para cualquier nombre de proyecto.

Mide:
1. Composition root: existe un `Program.cs`.
2. Controllers (`*Controller.cs`): sin acceso a datos ni repositorios.
3. Services (`*Service.cs`): sin HTTP ni SQL.
4. Repositories (`*Repository.cs`): sin HTTP ni services.
5. SQL parametrizado: un repositorio no interpola valores en una cadena SQL
   (solo constantes `const` del propio archivo).
6. Una carpeta por feature: sin carpetas por capa (`Controllers/`, `Services/`,
   `Repositories/`), Platform no referencia features y una feature no usa el
   repositorio de otra.
7. Sin ORM: ningun paquete de Entity Framework ni NHibernate.
8. Tests deterministas: sin `Thread.Sleep`.

NO mide (queda al review): SQL armado por concatenacion (`"..." + valor`), reglas
de negocio dentro de un controller, y el contenido de las migraciones.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

DATOS = ("Dapper", "Microsoft.Data", "System.Data")
CARPETAS_POR_CAPA = {"Controllers": "*Controller.cs", "Services": "*Service.cs",
                     "Repositories": "*Repository.cs"}
ORM = ("microsoft.entityframeworkcore", "entityframework", "nhibernate")
NO_SON_FEATURES = {"Platform", "Properties", "bin", "obj", "wwwroot"}

USING_RE = re.compile(r"^\s*(?:global\s+)?using\s+(?:static\s+)?([A-Za-z0-9_.]+)\s*;", re.MULTILINE)
COMENTARIO_RE = re.compile(r"//.*?$|/\*.*?\*/", re.MULTILINE | re.DOTALL)
LINEA_COMENTADA_RE = re.compile(r"^\s*//.*$", re.MULTILINE)
SLEEP_RE = re.compile(r"\bThread\.Sleep\s*\(")
PAQUETE_RE = re.compile(r"<Package(?:Reference|Version)\s+Include=[\"']([^\"']+)[\"']", re.IGNORECASE)
CONST_RE = re.compile(r"\bconst\s+string\s+(\w+)")
HUECO_RE = re.compile(r"(?<!\{)\{([A-Za-z_][A-Za-z0-9_.]*)(?:[,:][^{}]*)?\}(?!\})")
SQL_RE = re.compile(r"\b(?:SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|MERGE|EXEC(?:UTE)?)\b", re.IGNORECASE)
INTERPOLADAS = (
    re.compile(r'\$"""(.*?)"""', re.DOTALL),
    re.compile(r'(?:\$@|@\$)"((?:[^"]|"")*)"'),
    re.compile(r'\$"((?:[^"\\\n]|\\.)*)"'),
)

EN_CONTROLLER = re.compile(r"\b\w*Repository\b|\bSqlConnection\w*\b")
EN_SERVICE = re.compile(r"\bHttpContext\b|\bIActionResult\b|\bControllerBase\b|\bStatusCodes\b|\bSqlConnection\w*\b")
EN_REPOSITORY = re.compile(r"\bHttpContext\b|\bIActionResult\b|\bControllerBase\b|\b\w+Service\b")


def _es_test(rel: Path) -> bool:
    return any("Test" in p for p in rel.parts)


# Se vacian al empezar cada medicion: el disco y el .gitignore cambian entre una y otra.
_CON_GIT: dict[Path, bool] = {}
_IGNORADOS: dict[Path, frozenset[str]] = {}


def _tiene_git(carpeta: Path) -> bool:
    if carpeta not in _CON_GIT:
        _CON_GIT[carpeta] = (carpeta / ".git").exists()
    return _CON_GIT[carpeta]


def _ignorados(root: Path) -> frozenset[str]:
    """Lo que git ignora en `root`, relativo a el ('.local-dev/', 'Local.slnx'); vacio fuera de git."""
    _vistos = _IGNORADOS
    if root not in _vistos:
        try:
            salida = subprocess.run(["git", "-C", str(root), "ls-files", "--others", "--ignored",
                                     "--exclude-standard", "--directory"],
                                    capture_output=True, text=True, timeout=60)
            _vistos[root] = frozenset(salida.stdout.splitlines()) if salida.returncode == 0 else frozenset()
        except (OSError, subprocess.SubprocessError):
            _vistos[root] = frozenset()
    return _vistos[root]


def _en_otro_repo(root: Path, archivo: Path) -> bool:
    """Lo que no es codigo de este repo no se mide: un sub-repo o un worktree, o algo que git ignora.

    Un sub-repo o un worktree es una carpeta con su propio `.git`. Sin esto, la raiz de un
    proyecto multi-repo media el codigo de cada repo hermano con la norma de la raiz, el de
    cada worktree de feature una vez mas, y un script local ignorado (`.local-dev/`) como si
    fuera del producto.
    """
    partes = archivo.relative_to(root).parts
    ignorados = _ignorados(root)
    if ignorados and ("/".join(partes) in ignorados
                      or any("/".join(partes[:i]) + "/" in ignorados for i in range(1, len(partes)))):
        return True
    return any(_tiene_git(root.joinpath(*partes[:i])) for i in range(1, len(partes)))


SIN_CODIGO_PROPIO = ("Sin codigo .NET propio: todo vive en sub-repos o worktrees (carpetas con su propio .git), "
                     "que se miden en su repo. Aqui no se midio nada.")


def _solo_en_otros_repos(root: Path, patrones: tuple[str, ...] = ("**/*.cs", "**/*.csproj")) -> bool:
    """La carpeta no tiene codigo .NET propio y sus sub-repos o worktrees si (la raiz de un multi-repo)."""
    en_otros = False
    for patron in patrones:
        for f in root.glob(patron):
            if {"obj", "bin"} & set(f.relative_to(root).parts[:-1]):
                continue
            if not _en_otro_repo(root, f):
                return False
            en_otros = True
    return en_otros


def _fuentes(root: Path, patron: str) -> list[Path]:
    return sorted(f for f in root.glob(patron)
                  if not {"obj", "bin"} & set(f.relative_to(root).parts[:-1])
                  and not _en_otro_repo(root, f))


def _prohibido(using: str, prefijos: tuple[str, ...]) -> bool:
    return any(using == p or using.startswith(p + ".") for p in prefijos)


def _de_datos(using: str) -> bool:
    """Dapper, ADO.NET o la plataforma de base de datos del propio proyecto."""
    return _prohibido(using, DATOS) or ".Platform.Database" in "." + using


def _capa(nombre: str) -> str | None:
    """Capa de un archivo por su nombre; una interfaz (`I*Repository.cs`) no es una capa."""
    if re.match(r"I[A-Z]", nombre):
        return None
    for capa in ("Controller", "Service", "Repository"):
        if nombre.endswith(capa + ".cs"):
            return capa
    return None


def _interpolaciones_sql(fuente: str) -> list[str]:
    """Huecos `{valor}` dentro de una cadena interpolada que es SQL y no son `const` del archivo."""
    constantes = set(CONST_RE.findall(fuente))
    texto = LINEA_COMENTADA_RE.sub("", fuente)
    huecos: list[str] = []
    for patron in INTERPOLADAS:
        for m in patron.finditer(texto):
            if SQL_RE.search(m.group(1)):
                huecos += [h for h in HUECO_RE.findall(m.group(1)) if h not in constantes]
        texto = patron.sub('""', texto)
    return huecos


def check_dotnet_layered(root: Path) -> tuple[list[str], list[str]]:
    """Devuelve (errores, advertencias)."""
    errors: list[str] = []
    warnings: list[str] = []
    _CON_GIT.clear()
    _IGNORADOS.clear()
    if _solo_en_otros_repos(root):
        return errors, [SIN_CODIGO_PROPIO]
    fuentes = [f for f in _fuentes(root, "**/*.cs") if not _es_test(f.relative_to(root))]
    tests = [f for f in _fuentes(root, "**/*.cs") if _es_test(f.relative_to(root))]

    programas = [f for f in fuentes if f.name == "Program.cs"]
    if not programas:
        errors.append("Composition root ausente: se esperaba 'src/<Proyecto>/Program.cs'")

    medidas = {"Controller": 0, "Service": 0, "Repository": 0}
    repos_por_feature: dict[Path, set[str]] = {}
    for f in fuentes:
        if _capa(f.name) == "Repository" or re.match(r"I[A-Z]\w*Repository\.cs$", f.name):
            repos_por_feature.setdefault(f.parent, set()).add(f.stem)

    for f in fuentes:
        rel = f.relative_to(root).as_posix()
        fuente = f.read_text(encoding="utf-8", errors="ignore")
        codigo = COMENTARIO_RE.sub("", fuente)
        usings = USING_RE.findall(codigo)
        capa = _capa(f.name)
        if capa:
            medidas[capa] += 1

        if capa == "Controller":
            for u in usings:
                if _de_datos(u):
                    errors.append(f"{rel}: el controller no toca la capa de datos (using {u})")
            for nombre in sorted(set(EN_CONTROLLER.findall(codigo))):
                errors.append(f"{rel}: el controller solo conoce el service (referencia a {nombre})")
        elif capa == "Service":
            for u in usings:
                if _prohibido(u, ("Microsoft.AspNetCore",)) or _de_datos(u):
                    errors.append(f"{rel}: el service no conoce HTTP ni SQL (using {u})")
            for nombre in sorted(set(EN_SERVICE.findall(codigo))):
                errors.append(f"{rel}: el service no conoce HTTP ni SQL (referencia a {nombre})")
        elif capa == "Repository":
            for u in usings:
                if _prohibido(u, ("Microsoft.AspNetCore",)):
                    errors.append(f"{rel}: el repositorio no conoce HTTP (using {u})")
            for nombre in sorted(set(EN_REPOSITORY.findall(codigo))):
                errors.append(f"{rel}: el repositorio no conoce HTTP ni services (referencia a {nombre})")
            for hueco in sorted(set(_interpolaciones_sql(fuente))):
                errors.append(f"{rel}: SQL con el valor '{{{hueco}}}' interpolado; usa un parametro "
                              "(@Nombre). Solo se interpola una constante del propio repositorio")

        # Platform es transversal: no conoce features (carpetas hermanas de Platform/).
        partes = f.relative_to(root).parts
        if "Platform" in partes[:-1]:
            proyecto = root.joinpath(*partes[:partes.index("Platform")])
            features = {d.name for d in proyecto.iterdir()
                        if d.is_dir() and d.name not in NO_SON_FEATURES and not d.name.startswith(".")}
            for u in usings:
                if u.split(".")[-1] in features:
                    errors.append(f"{rel}: Platform no referencia features (using {u})")

        # Una feature no usa el repositorio de otra: llama a su service.
        ajenos = {n for carpeta, nombres in repos_por_feature.items() if carpeta != f.parent
                  for n in nombres}
        propios = repos_por_feature.get(f.parent, set())
        if f.name != "Program.cs" and "Platform" not in partes[:-1]:
            for nombre in sorted(ajenos - propios):
                if re.search(rf"\b{re.escape(nombre)}\b", codigo):
                    errors.append(f"{rel}: usa el repositorio de otra feature ({nombre}); "
                                  "si necesita sus datos, llama a su service")

    for carpeta, patron in CARPETAS_POR_CAPA.items():
        for d in sorted({f.parent for f in fuentes if f.parent.name == carpeta and f.match(patron)}):
            errors.append(f"{d.relative_to(root).as_posix()}/: carpeta por capa; la norma es una "
                          "carpeta por feature con sus tres capas dentro")

    for proyecto in _fuentes(root, "**/*.csproj") + _fuentes(root, "**/Directory.Packages.props"):
        rel = proyecto.relative_to(root)
        if _es_test(rel):
            continue
        for paquete in PAQUETE_RE.findall(proyecto.read_text(encoding="utf-8", errors="ignore")):
            if any(paquete.lower() == o or paquete.lower().startswith(o + ".") for o in ORM):
                errors.append(f"{rel.as_posix()}: ORM prohibido ('{paquete}'); el acceso a datos es "
                              "Dapper + Microsoft.Data.SqlClient")

    for f in tests:
        if SLEEP_RE.search(f.read_text(encoding="utf-8", errors="ignore")):
            errors.append(f"{f.relative_to(root).as_posix()}: 'Thread.Sleep' prohibido en pruebas "
                          "deterministas; usa FakeTimeProvider o sincronizacion explicita")

    sin_medir = [capa for capa, n in medidas.items() if n == 0]
    if sin_medir:
        warnings.append("Sin archivos " + ", ".join(f"*{c}.cs" for c in sin_medir)
                        + ": los limites de esa(s) capa(s) NO se midieron")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificador de arquitectura .NET en capas por feature (CALPIL)")
    parser.add_argument("--repo", default=".", help="Ruta de la raiz del repositorio a verificar")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    errors, warnings = check_dotnet_layered(repo)

    for w in warnings:
        print(f"[WARN] {w}")
    if errors:
        print(f"[X] Fallo normativo: {len(errors)} infraccion(es) de la arquitectura en capas .NET:")
        for e in errors:
            print(f"  - {e}")
        return 1

    if warnings:
        print("[OK] Arquitectura en capas .NET validada en lo que se pudo medir (ver avisos).")
    else:
        print("[OK] Arquitectura en capas .NET validada: Controller -> Service -> Repository, "
              "SQL parametrizado, una carpeta por feature y tests deterministas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
