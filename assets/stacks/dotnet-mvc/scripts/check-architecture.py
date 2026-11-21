#!/usr/bin/env python3
"""Validador normativo del portal web .NET MVC (CALPIL, stack dotnet-mvc).

El portal presenta y captura datos; no tiene base de datos ni reglas de negocio.
Este verificador lee el codigo fuente, igual que `ArchitectureTests` de la
plantilla, y vale para cualquier nombre de proyecto.

Mide:
1. Composition root: existe un `Program.cs`.
2. Controllers (`Controllers/*.cs`): llegan a los datos solo por una interfaz
   `I*Api`; sin `HttpClient`, sin el cliente concreto y sin acceso a datos.
3. Vistas (`Views/**/*.cshtml`): solo presentan; sin `@inject`, `Html.Raw` ni
   scripts, estilos o manejadores en linea (la CSP los bloquea).
4. Sin acceso a datos: ningun paquete ni `using` de un proveedor de base de datos.
5. CSP sin `'unsafe-inline'` ni `'unsafe-eval'`.
6. Tests deterministas: sin `Thread.Sleep`.
7. Platform transversal (`Platform/*.cs`): no conoce features. Una feature es un
   `XController`; Platform no lo referencia, no dibuja vistas fuera de
   `Views/Shared/` ni usa modelos con el nombre de una feature (`X...Model`,
   tambien en singular: `PagosController` -> `PagoViewModel`). Puede usar
   vistas compartidas, modelos transversales y rutas como `/Home/Error`.

NO mide (queda al review): reglas de negocio dentro de un controller, cambios
de estado por GET, uso de `[AllowAnonymous]` e `[IgnoreAntiforgeryToken]`, y la
validacion de `returnUrl`.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ACCESO_A_DATOS = ("Microsoft.Data", "Dapper", "Microsoft.EntityFrameworkCore", "EntityFramework",
                  "Npgsql", "System.Data")

USING_RE = re.compile(r"^\s*(?:global\s+)?using\s+(?:static\s+)?([A-Za-z0-9_.]+)\s*;", re.MULTILINE)
COMENTARIO_RE = re.compile(r"//.*?$|/\*.*?\*/", re.MULTILINE | re.DOTALL)
COMENTARIO_RAZOR_RE = re.compile(r"@\*.*?\*@", re.DOTALL)
SLEEP_RE = re.compile(r"\bThread\.Sleep\s*\(")
PAQUETE_RE = re.compile(r"<Package(?:Reference|Version)\s+Include=[\"']([^\"']+)[\"']", re.IGNORECASE)
CLIENTE_RE = re.compile(r"\bclass\s+(\w+)\b[^{;]*?:[^{;]*\bI\w*Api\b")
CSP_RE = re.compile(r"'unsafe-(?:inline|eval)'")
VISTA_RE = re.compile(r"(?:~/)?\bViews/([A-Za-z0-9_]+)/")

EN_CONTROLLER = re.compile(r"\bHttpClient\b|\bHttpRequestMessage\b|\bSystem\.Net\.Http\b"
                           r"|\bSqlConnection\b|\bDbContext\b")
EN_VISTA = re.compile(r"@inject\b|Html\.Raw|<script(?![^>]*\bsrc=)[^>]*>|<style\b|\sstyle=\"|\son[a-z]+=\"",
                      re.IGNORECASE)


def _es_test(rel: Path) -> bool:
    return any("Test" in p for p in rel.parts)


def _fuentes(root: Path, patron: str) -> list[Path]:
    return sorted(f for f in root.glob(patron)
                  if not {"obj", "bin", "wwwroot"} & set(f.relative_to(root).parts[:-1]))


def _es_proveedor(nombre: str) -> bool:
    return any(nombre.lower() == p.lower() or nombre.lower().startswith(p.lower() + ".")
               for p in ACCESO_A_DATOS)


def _singular(nombre: str) -> str:
    for sufijo in ("es", "s"):
        if nombre.endswith(sufijo) and len(nombre) > len(sufijo) + 2:
            return nombre[: -len(sufijo)]
    return nombre


def _infracciones_platform(rel: str, codigo: str, features: set[str]) -> list[str]:
    """Platform es transversal: no conoce controllers, vistas ni modelos de una feature."""
    hallados: list[str] = []
    for carpeta in sorted({m.group(1) for m in VISTA_RE.finditer(codigo)} - {"Shared"}):
        hallados.append(f"vista ~/Views/{carpeta}/")
    for feature in sorted(features):
        if re.search(rf"\b{re.escape(feature)}Controller\b", codigo):
            hallados.append(f"controller {feature}Controller")
        nombres = sorted({feature, _singular(feature)}, key=len, reverse=True)
        patron = rf"\b(?:{'|'.join(map(re.escape, nombres))})(?:[A-Z]\w*)?(?:ViewModel|Model|Form)\b"
        for modelo in sorted(set(re.findall(patron, codigo))):
            hallados.append(f"modelo {modelo} de {feature}")
    return [f"{rel}: Platform no conoce features ({h}); lo transversal no depende de una pagina"
            for h in hallados]


def check_dotnet_mvc(root: Path) -> tuple[list[str], list[str]]:
    """Devuelve (errores, advertencias)."""
    errors: list[str] = []
    warnings: list[str] = []
    fuentes = [f for f in _fuentes(root, "**/*.cs") if not _es_test(f.relative_to(root))]
    tests = [f for f in _fuentes(root, "**/*.cs") if _es_test(f.relative_to(root))]
    vistas = [f for f in _fuentes(root, "**/*.cshtml") if "Views" in f.relative_to(root).parts[:-1]]

    if not any(f.name == "Program.cs" for f in fuentes):
        errors.append("Composition root ausente: se esperaba 'src/<Proyecto>/Program.cs'")

    codigos = {f: COMENTARIO_RE.sub("", f.read_text(encoding="utf-8", errors="ignore")) for f in fuentes}
    clientes = sorted({n for codigo in codigos.values() for n in CLIENTE_RE.findall(codigo)})
    en_cliente = re.compile("|".join(rf"\b{re.escape(n)}\b" for n in clientes)) if clientes else None

    features = {f.name[: -len("Controller.cs")] for f in fuentes
                if "Controllers" in f.relative_to(root).parts[:-1] and f.name.endswith("Controller.cs")}

    controllers = 0
    for f, codigo in codigos.items():
        rel = f.relative_to(root).as_posix()
        for u in USING_RE.findall(codigo):
            if _es_proveedor(u):
                errors.append(f"{rel}: el portal no tiene acceso a datos (using {u}); "
                              "todo dato entra y sale por una interfaz I*Api")
        if CSP_RE.search(codigo):
            errors.append(f"{rel}: la CSP no admite 'unsafe-inline' ni 'unsafe-eval'; "
                          "el script o estilo va a un archivo de wwwroot")
        if "Platform" in f.relative_to(root).parts[:-1]:
            errors.extend(_infracciones_platform(rel, codigo, features))
        if "Controllers" not in f.relative_to(root).parts[:-1]:
            continue
        controllers += 1
        hallados = set(EN_CONTROLLER.findall(codigo))
        if en_cliente:
            hallados |= set(en_cliente.findall(codigo))
        for nombre in sorted(hallados):
            errors.append(f"{rel}: el controller llega a los datos solo por una interfaz I*Api "
                          f"(referencia a {nombre})")

    for f in vistas:
        texto = COMENTARIO_RAZOR_RE.sub("", f.read_text(encoding="utf-8", errors="ignore"))
        for hallado in sorted({m.group(0).strip() for m in EN_VISTA.finditer(texto)}):
            errors.append(f"{f.relative_to(root).as_posix()}: la vista solo presenta; sin servicios, "
                          f"HTML crudo ni codigo en linea ({hallado})")

    for proyecto in _fuentes(root, "**/*.csproj") + _fuentes(root, "**/Directory.Packages.props"):
        rel = proyecto.relative_to(root)
        if _es_test(rel):
            continue
        for paquete in PAQUETE_RE.findall(proyecto.read_text(encoding="utf-8", errors="ignore")):
            if _es_proveedor(paquete):
                errors.append(f"{rel.as_posix()}: el portal no tiene acceso a datos (paquete '{paquete}')")

    for f in tests:
        if SLEEP_RE.search(f.read_text(encoding="utf-8", errors="ignore")):
            errors.append(f"{f.relative_to(root).as_posix()}: 'Thread.Sleep' prohibido en pruebas "
                          "deterministas; usa sincronizacion explicita")

    sin_medir = [nombre for nombre, n in (("Controllers/*.cs", controllers), ("Views/**/*.cshtml", len(vistas)))
                 if n == 0]
    if sin_medir:
        warnings.append("Sin archivos " + ", ".join(sin_medir) + ": esos limites NO se midieron")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificador de arquitectura del portal .NET MVC (CALPIL)")
    parser.add_argument("--repo", default=".", help="Ruta de la raiz del repositorio a verificar")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    errors, warnings = check_dotnet_mvc(repo)

    for w in warnings:
        print(f"[WARN] {w}")
    if errors:
        print(f"[X] Fallo normativo: {len(errors)} infraccion(es) del patron MVC del portal .NET:")
        for e in errors:
            print(f"  - {e}")
        return 1

    if warnings:
        print("[OK] Patron MVC del portal .NET validado en lo que se pudo medir (ver avisos).")
    else:
        print("[OK] Patron MVC del portal .NET validado: controllers por I*Api, vistas que solo "
              "presentan, sin acceso a datos y tests deterministas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
