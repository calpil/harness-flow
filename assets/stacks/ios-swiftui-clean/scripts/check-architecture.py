#!/usr/bin/env python3
"""Validador normativo de arquitectura iOS SwiftUI Clean Architecture (CALPIL).

Verifica:
1. Pureza del Dominio: archivos en Sources/CalpilDomain/ sin dependencias de SwiftUI, UIKit, AppKit ni capas de datos/UI.
2. Aislamiento de Capas: CalpilUI no debe importar CalpilData directamente (solo consume puertos de CalpilDomain).
3. Composition Root: presencia de CalpilApp.swift o archivo con @main.
4. Testing determinista: sin llamadas arbitrarias a Task.sleep o Thread.sleep en tests.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FORBIDDEN_DOMAIN_IMPORTS = [
    "SwiftUI",
    "UIKit",
    "AppKit",
    "CoreData",
    "SwiftData",
    "CalpilUI",
    "CalpilData",
]

FORBIDDEN_UI_IMPORTS = [
    "CalpilData",
]

IMPORT_RE = re.compile(r'^\s*import\s+([A-Za-z0-9_]+)', re.MULTILINE)
SLEEP_RE = re.compile(r'\b(Task\.sleep|Thread\.sleep)\s*\(')


def check_ios_architecture(root_dir: Path) -> tuple[list[str], list[str]]:
    """Devuelve (errores, advertencias)."""
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Composition Root (CalpilApp.swift o @main)
    app_files = list(root_dir.glob("**/CalpilApp.swift")) + list(root_dir.glob("**/App.swift"))
    has_main = False
    for sf in root_dir.glob("**/*.swift"):
        if ".build" in sf.parts:
            continue
        try:
            txt = sf.read_text(encoding="utf-8", errors="ignore")
            if "@main" in txt:
                has_main = True
                break
        except Exception:
            pass

    if not app_files and not has_main:
        errors.append("Composition Root ausente: se esperaba 'Sources/CalpilApp/CalpilApp.swift' o estructura con '@main'")

    # 2. Verificar archivos Swift
    swift_files = [f for f in root_dir.glob("**/*.swift") if ".build" not in f.parts]

    for sf in swift_files:
        rel = sf.relative_to(root_dir)
        parts = rel.parts
        parts_lower = [p.lower() for p in parts]
        is_test = any("test" in p for p in parts_lower) or sf.name.endswith("Tests.swift")

        try:
            content = sf.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            warnings.append(f"No se pudo leer {rel}: {exc}")
            continue

        imports = IMPORT_RE.findall(content)

        # Regla A: Pureza del Dominio (CalpilDomain o domain)
        is_domain = any(p in ("calpildomain", "domain") for p in parts_lower) and not is_test
        if is_domain:
            for imp in imports:
                if imp in FORBIDDEN_DOMAIN_IMPORTS:
                    errors.append(f"{rel}: capa Domain no debe incluir la dependencia externa o impura '{imp}'")

        # Regla B: Aislamiento de UI (CalpilUI o presentation)
        is_ui = any(p in ("calpilui", "presentation", "ui") for p in parts_lower) and not is_test
        if is_ui:
            for imp in imports:
                if imp in FORBIDDEN_UI_IMPORTS:
                    errors.append(f"{rel}: capa UI no debe importar la capa de datos directamente ('{imp}'); debe consumir puertos de CalpilDomain")

        # Regla C: Determinismo en tests
        if is_test:
            if SLEEP_RE.search(content):
                errors.append(f"{rel}: sleep prohibido en tests; usar fakes en memoria y sincronización determinista")

    return errors, warnings


def main() -> None:
    ap = argparse.ArgumentParser(description="Verificador de arquitectura iOS SwiftUI Clean Architecture")
    ap.add_argument("--repo", default=".", help="Ruta al repositorio iOS")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    errors, warnings = check_ios_architecture(repo)

    if warnings:
        print("[i] Advertencias de arquitectura iOS:")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print("[!] Violaciones de arquitectura iOS:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("[ok] Arquitectura iOS SwiftUI Clean Architecture conforme.")
    sys.exit(0)


if __name__ == "__main__":
    main()
