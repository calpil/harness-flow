#!/usr/bin/env python3
"""Validador normativo de arquitectura Python Data Product (CALPIL).

Verifica:
1. Composition Root: existencia de main.py o app.py en src/.
2. Pureza del Dominio: domain/** sin dependencias de FastAPI, SQLAlchemy, requests o SQL connectors.
3. Tests deterministas: sin llamadas a time.sleep en tests.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

FORBIDDEN_DOMAIN_MODULES = [
    "fastapi",
    "sqlalchemy",
    "requests",
    "httpx",
    "flask",
    "django",
]

SLEEP_RE = re.compile(r'\btime\.sleep\s*\(')


def extract_imports(py_source: str) -> list[str]:
    imports = []
    try:
        tree = ast.parse(py_source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
    except Exception:
        pass
    return imports


def check_python_architecture(root_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Composition Root
    main_files = list(root_dir.glob("src/**/main.py")) + list(root_dir.glob("src/**/app.py"))
    if not main_files and list(root_dir.glob("src/**/*.py")):
        warnings.append("Composition Root no canónico: no se encontró 'main.py' ni 'app.py' bajo src/")

    # 2. Domain purity & tests deterministas
    py_files = [f for f in root_dir.glob("**/*.py") if "venv" not in f.parts and ".venv" not in f.parts]

    for pf in py_files:
        rel = pf.relative_to(root_dir)
        parts_lower = [p.lower() for p in rel.parts]
        is_test = "tests" in parts_lower or pf.name.startswith("test_") or pf.name.endswith("_test.py")

        try:
            content = pf.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            warnings.append(f"No se pudo leer {rel}: {exc}")
            continue

        imports = extract_imports(content)

        # Regla: Dominio puro
        if "domain" in parts_lower and not is_test:
            for imp in imports:
                for forbidden in FORBIDDEN_DOMAIN_MODULES:
                    if imp == forbidden or imp.startswith(forbidden + "."):
                        errors.append(f"{rel}: Dominio no debe importar framework/ORM ('{imp}')")
                if "adapter" in imp.lower() or "sources" in imp.lower() or "destinations" in imp.lower():
                    errors.append(f"{rel}: Dominio no debe acoplarse a adaptadores/fuentes ('{imp}')")

        # Regla: Tests deterministas
        if is_test and SLEEP_RE.search(content):
            errors.append(f"{rel}: uso de 'time.sleep' prohibido en tests deterministas; usar freeze_time o Clock fakes")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificador de arquitectura Python Data Product (CALPIL)")
    parser.add_argument("--repo", default=".", help="Ruta de la raíz del repositorio a verificar")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    errors, warnings = check_python_architecture(repo)

    if warnings:
        print("[!] Advertencias de arquitectura:")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"[X] Fallo normativo: {len(errors)} infracción(es) de arquitectura Python:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("[OK] Arquitectura Python Data Product validada: Dominio puro y Tests deterministas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
