#!/usr/bin/env python3
"""Validador normativo de arquitectura hexagonal en .NET / C# (CALPIL).

Verifica:
1. Pureza del Dominio: proyectos/carpetas Domain sin dependencias de transporte (ASP.NET Core), persistencia (Dapper, EF, Npgsql) ni bases de datos.
2. Aislamiento de Application: proyectos/carpetas Application sin referencias a Infrastructure o WebApi.
3. Tests deterministas: sin llamadas a Thread.Sleep en proyectos de tests.
4. Composition Root: existencia de Program.cs en WebApi o src/.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FORBIDDEN_DOMAIN_USINGS = [
    "Microsoft.AspNetCore",
    "Dapper",
    "Npgsql",
    "Microsoft.EntityFrameworkCore",
    "System.Data",
]

FORBIDDEN_DOMAIN_PACKAGES = [
    "dapper",
    "npgsql",
    "microsoft.aspnetcore",
    "microsoft.entityframeworkcore",
]

FORBIDDEN_APPLICATION_USINGS = [
    "Microsoft.AspNetCore.Mvc",
]

USING_RE = re.compile(r'^\s*using\s+([A-Za-z0-9_.]+)\s*;', re.MULTILINE)
SLEEP_RE = re.compile(r'\bThread\.Sleep\s*\(')
PROJECT_REF_RE = re.compile(r'<ProjectReference\s+Include=["\']([^"\']+)["\']', re.IGNORECASE)
PACKAGE_REF_RE = re.compile(r'<PackageReference\s+Include=["\']([^"\']+)["\']', re.IGNORECASE)


def extract_usings(cs_source: str) -> list[str]:
    return [m.group(1) for m in USING_RE.finditer(cs_source)]


def check_dotnet_architecture(root_dir: Path) -> tuple[list[str], list[str]]:
    """Devuelve (errores, advertencias)."""
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Composition Root (Program.cs)
    program_files = list({p for p in root_dir.glob("**/Program.cs") if "obj" not in p.parts and "bin" not in p.parts})
    if not program_files:
        errors.append("Composition Root ausente: se esperaba 'src/**/*.WebApi/Program.cs' o 'Program.cs'")
    else:
        has_webapi_program = any(any("webapi" in p_part.lower() or "api" in p_part.lower() for p_part in p.parts) for p in program_files)
        if not has_webapi_program:
            warnings.append(f"Composition Root no canónico: encontrado en {[str(p.relative_to(root_dir)) for p in program_files]}, se recomienda bajo WebApi/")

    # 2. Domain & Application Projects (.csproj y .cs)
    cs_files = [f for f in root_dir.glob("**/*.cs") if "obj" not in f.parts and "bin" not in f.parts]
    csproj_files = [f for f in root_dir.glob("**/*.csproj") if "obj" not in f.parts and "bin" not in f.parts]

    # Verificar proyectos .csproj
    for csproj in csproj_files:
        rel = csproj.relative_to(root_dir)
        text = csproj.read_text(encoding="utf-8", errors="ignore")
        p_refs = PROJECT_REF_RE.findall(text)
        pkg_refs = [pkg.lower() for pkg in PACKAGE_REF_RE.findall(text)]

        # Proyecto Domain
        if "Domain" in csproj.stem and "Test" not in csproj.stem:
            for pref in p_refs:
                pref_norm = pref.replace("\\", "/")
                if any(k in pref_norm for k in ["Application", "Infrastructure", "WebApi", "Api"]):
                    errors.append(f"{rel}: el proyecto Domain no debe referenciar otros proyectos ('{pref}')")
            for pkg in pkg_refs:
                for forbidden in FORBIDDEN_DOMAIN_PACKAGES:
                    if pkg == forbidden or pkg.startswith(forbidden + "."):
                        errors.append(f"{rel}: el proyecto Domain no debe incluir el paquete externo '{pkg}'")

        # Proyecto Application
        elif "Application" in csproj.stem and "Test" not in csproj.stem:
            for pref in p_refs:
                pref_norm = pref.replace("\\", "/")
                if any(k in pref_norm for k in ["Infrastructure", "WebApi"]):
                    errors.append(f"{rel}: el proyecto Application no debe referenciar capas externas ('{pref}')")

    # Verificar código fuente .cs
    for cs in cs_files:
        rel = cs.relative_to(root_dir)
        parts = rel.parts
        is_test = any("Test" in p for p in parts) or cs.name.endswith("Test.cs") or cs.name.endswith("Tests.cs")

        try:
            content = cs.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            warnings.append(f"No se pudo leer {rel}: {exc}")
            continue

        usings = extract_usings(content)

        # Regla: Dominio puro (debe pertenecer al directorio/proyecto Domain, no Application ni Infrastructure)
        dir_parts = [p for p in parts[:-1]]
        is_domain = any("Domain" in p for p in dir_parts) and not any("Infrastructure" in p or "Application" in p or "WebApi" in p for p in dir_parts) and not is_test
        if is_domain:
            for u in usings:
                for forbidden in FORBIDDEN_DOMAIN_USINGS:
                    if u == forbidden or u.startswith(forbidden + "."):
                        errors.append(f"{rel}: Domain no permite dependencia externa '{u}'")
                if "Application" in u or "Infrastructure" in u or "WebApi" in u:
                    errors.append(f"{rel}: Domain no debe acoplarse a capas externas ('{u}')")

        # Regla: Application aislado
        is_application = any("Application" in p for p in dir_parts) and not any("Infrastructure" in p or "WebApi" in p for p in dir_parts) and not is_test
        if is_application:
            for u in usings:
                for forbidden in FORBIDDEN_APPLICATION_USINGS:
                    if u == forbidden or u.startswith(forbidden + "."):
                        errors.append(f"{rel}: Application no debe importar '{u}'")
                if "Infrastructure" in u or "WebApi" in u:
                    errors.append(f"{rel}: Application no debe importar adaptadores concretos ('{u}')")

        # Regla: Tests deterministas
        if is_test:
            if SLEEP_RE.search(content):
                errors.append(f"{rel}: uso de 'Thread.Sleep' prohibido en pruebas deterministas; usar mocks, FakeClock o sincronización explícita")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificador de arquitectura .NET Hexagonal (CALPIL)")
    parser.add_argument("--repo", default=".", help="Ruta de la raíz del repositorio a verificar")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    errors, warnings = check_dotnet_architecture(repo)

    if warnings:
        print("[!] Advertencias de arquitectura:")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"[X] Fallo normativo: {len(errors)} infracción(es) de límites hexagonales .NET:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("[OK] Arquitectura hexagonal .NET validada: Pureza de Dominio, Aislamiento de Application y Tests Deterministas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
