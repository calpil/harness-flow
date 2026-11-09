#!/usr/bin/env python3
"""Validador normativo de arquitectura hexagonal en Spring Boot / Java (CALPIL).

Verifica:
1. Composition Root: existencia de clase con @SpringBootApplication en src/main/java.
2. Pureza del Dominio: domain/** sin dependencias de Spring, JPA, Jackson o Cloud; Java puro.
3. Aislamiento de Application: application/** sin referencias a adaptadores (adapter/in, adapter/out).
4. Tests deterministas: sin llamadas a Thread.sleep en tests.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FORBIDDEN_DOMAIN_IMPORTS = [
    "org.springframework",
    "jakarta.persistence",
    "javax.persistence",
    "org.hibernate",
    "com.fasterxml.jackson",
    "org.apache.ibatis",
]

IMPORT_RE = re.compile(r'^\s*import\s+([A-Za-z0-9_.*]+);', re.MULTILINE)
SLEEP_RE = re.compile(r'\bThread\.sleep\s*\(')


def extract_imports(java_source: str) -> list[str]:
    return [m.group(1).strip() for m in IMPORT_RE.finditer(java_source)]


def check_springboot_architecture(root_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Composition Root
    java_files = [f for f in root_dir.glob("src/main/java/**/*.java") if "target" not in f.parts]
    has_app_annotation = False
    for jf in java_files:
        try:
            content = jf.read_text(encoding="utf-8", errors="ignore")
            if "@SpringBootApplication" in content:
                has_app_annotation = True
                break
        except Exception:
            pass

    if not has_app_annotation and java_files:
        warnings.append("Composition Root no canónico: no se encontró clase anotada con @SpringBootApplication en src/main/java/")

    # 2. Domain purity & Application isolation
    for jf in root_dir.glob("src/**/*.java"):
        if "target" in jf.parts:
            continue
        rel = jf.relative_to(root_dir)
        parts_lower = [p.lower() for p in rel.parts]
        is_test = "test" in parts_lower or jf.name.endswith("Test.java")

        try:
            content = jf.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            warnings.append(f"No se pudo leer {rel}: {exc}")
            continue

        imports = extract_imports(content)

        # Regla: Dominio puro
        if "domain" in parts_lower and not is_test:
            for imp in imports:
                for forbidden in FORBIDDEN_DOMAIN_IMPORTS:
                    if imp.startswith(forbidden):
                        errors.append(f"{rel}: Dominio no debe importar frameworks/JPA ('{imp}')")
                if "adapter" in imp.lower():
                    errors.append(f"{rel}: Dominio no debe acoplarse a adaptadores ('{imp}')")

        # Regla: Application aislado de adaptadores
        if "application" in parts_lower and not is_test:
            for imp in imports:
                if "adapter" in imp.lower() and not imp.endswith(".ports.."):
                    errors.append(f"{rel}: Application no debe importar adaptadores concretos ('{imp}')")

        # Regla: Tests deterministas
        if is_test and SLEEP_RE.search(content):
            errors.append(f"{rel}: uso de 'Thread.sleep' prohibido en pruebas deterministas; usar Awaitility o Clock")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificador de arquitectura Spring Boot Hexagonal (CALPIL)")
    parser.add_argument("--repo", default=".", help="Ruta de la raíz del repositorio a verificar")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    errors, warnings = check_springboot_architecture(repo)

    if warnings:
        print("[!] Advertencias de arquitectura:")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"[X] Fallo normativo: {len(errors)} infracción(es) de arquitectura Spring Boot:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("[OK] Arquitectura hexagonal Spring Boot validada: Dominio puro, Application aislada y Tests deterministas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
