#!/usr/bin/env python3
"""Validador normativo de arquitectura Android Jetpack Compose Clean Architecture (CALPIL).

Verifica:
1. Pureza del Dominio: archivos en features/*/domain/** sin dependencias de android.*, androidx.compose, room ni capas data/presentation.
2. Aislamiento de Capas: la capa presentation no debe importar data.dto ni data.repository directamente.
3. Composition Root: presencia de CalpilApplication.kt o MainActivity.kt.
4. Testing determinista: sin llamadas a Thread.sleep en tests.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FORBIDDEN_DOMAIN_IMPORTS_PREFIXES = [
    "android.",
    "androidx.compose.",
    "androidx.room.",
    "androidx.lifecycle.",
]

FORBIDDEN_PRESENTATION_IMPORTS_SUBSTRINGS = [
    ".data.dto.",
    ".data.repository.",
]

IMPORT_RE = re.compile(r'^\s*import\s+([A-Za-z0-9_.*]+)', re.MULTILINE)
SLEEP_RE = re.compile(r'\bThread\.sleep\s*\(')


def check_android_architecture(root_dir: Path) -> tuple[list[str], list[str]]:
    """Devuelve (errores, advertencias)."""
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Composition Root (CalpilApplication.kt o MainActivity.kt)
    app_files = list(root_dir.glob("**/CalpilApplication.kt")) + list(root_dir.glob("**/MainActivity.kt"))
    if not app_files:
        errors.append("Composition Root ausente: se esperaba 'CalpilApplication.kt' o 'MainActivity.kt'")

    # 2. Verificar archivos Kotlin
    kt_files = [f for f in root_dir.glob("**/*.kt") if "build" not in f.parts and ".gradle" not in f.parts]

    for kf in kt_files:
        rel = kf.relative_to(root_dir)
        parts = rel.parts
        parts_lower = [p.lower() for p in parts]
        is_test = any("test" in p for p in parts_lower) or kf.name.endswith("Test.kt") or kf.name.endswith("Tests.kt")

        try:
            content = kf.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            warnings.append(f"No se pudo leer {rel}: {exc}")
            continue

        imports = IMPORT_RE.findall(content)

        # Regla A: Pureza del Dominio (domain)
        is_domain = "domain" in parts_lower and not is_test
        if is_domain:
            for imp in imports:
                for forbidden in FORBIDDEN_DOMAIN_IMPORTS_PREFIXES:
                    if imp.startswith(forbidden):
                        errors.append(f"{rel}: capa Domain no debe incluir la dependencia externa o impura '{imp}'")
                if ".data." in imp:
                    errors.append(f"{rel}: capa Domain no debe importar la capa data ('{imp}')")
                if ".presentation." in imp:
                    errors.append(f"{rel}: capa Domain no debe importar la capa presentation ('{imp}')")

        # Regla B: Aislamiento de Presentation
        is_presentation = "presentation" in parts_lower and not is_test
        if is_presentation:
            for imp in imports:
                for forbidden in FORBIDDEN_PRESENTATION_IMPORTS_SUBSTRINGS:
                    if forbidden in imp:
                        errors.append(f"{rel}: capa Presentation no debe importar detalles de data directamente ('{imp}'); debe consumir casos de uso de Domain")

        # Regla C: Determinismo en tests
        if is_test:
            if SLEEP_RE.search(content):
                errors.append(f"{rel}: sleep prohibido en tests; usar runTest y TestDispatcher determinista")

    return errors, warnings


def main() -> None:
    ap = argparse.ArgumentParser(description="Verificador de arquitectura Android Jetpack Compose Clean Architecture")
    ap.add_argument("--repo", default=".", help="Ruta al repositorio Android")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    errors, warnings = check_android_architecture(repo)

    if warnings:
        print("[i] Advertencias de arquitectura Android:")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print("[!] Violaciones de arquitectura Android:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("[ok] Arquitectura Android Jetpack Compose Clean Architecture conforme.")
    sys.exit(0)


if __name__ == "__main__":
    main()
