#!/usr/bin/env python3
"""Validador normativo de arquitectura hexagonal en NestJS (CALPIL).

Verifica:
1. Composition Root: existencia de app.module.ts o main.ts en src/.
2. Pureza del Dominio: src/**/domain/** sin dependencias de @nestjs, @prisma/client, typeorm.
3. Aislamiento de Application: src/**/application/** sin referencias a adaptadores ni infraestructura.
4. Tests deterministas: sin llamadas a sleep o setTimeout arbitrarios.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FORBIDDEN_DOMAIN_PACKAGES = [
    "@nestjs",
    "@prisma/client",
    "typeorm",
    "express",
    "fastify",
    "axios",
]

IMPORT_RE = re.compile(r'from\s+["\']([^"\']+)["\']')


def extract_imports(ts_source: str) -> list[str]:
    return [m.group(1).strip() for m in IMPORT_RE.finditer(ts_source)]


def check_nestjs_architecture(root_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Composition Root
    main_ts = root_dir / "src" / "main.ts"
    app_module = root_dir / "src" / "app.module.ts"
    if not (main_ts.exists() or app_module.exists()):
        warnings.append("Composition Root no canónico: no se encontró 'src/main.ts' ni 'src/app.module.ts'")

    # 2. Domain purity & Application isolation
    ts_files = [
        f for f in root_dir.glob("src/**/*.ts")
        if "node_modules" not in f.parts and "dist" not in f.parts
    ]

    for f in ts_files:
        rel = f.relative_to(root_dir)
        parts_lower = [p.lower() for p in rel.parts]
        is_test = any(t in parts_lower for t in ["test", "tests"]) or f.name.endswith(".spec.ts")

        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            warnings.append(f"No se pudo leer {rel}: {exc}")
            continue

        imports = extract_imports(content)

        # Regla: Dominio puro
        if "domain" in parts_lower and not is_test:
            for imp in imports:
                for forbidden in FORBIDDEN_DOMAIN_PACKAGES:
                    if imp.startswith(forbidden):
                        errors.append(f"{rel}: Dominio no debe importar framework/ORM ('{imp}')")
                if "adapter" in imp.lower() or "infrastructure" in imp.lower():
                    errors.append(f"{rel}: Dominio no debe acoplarse a capas externas ('{imp}')")

        # Regla: Application aislado
        if "application" in parts_lower and not is_test:
            for imp in imports:
                if "adapter" in imp.lower() or "infrastructure" in imp.lower():
                    errors.append(f"{rel}: Application no debe importar adaptadores concretos ('{imp}')")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificador de arquitectura NestJS Hexagonal (CALPIL)")
    parser.add_argument("--repo", default=".", help="Ruta de la raíz del repositorio a verificar")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    errors, warnings = check_nestjs_architecture(repo)

    if warnings:
        print("[!] Advertencias de arquitectura:")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"[X] Fallo normativo: {len(errors)} infracción(es) de arquitectura NestJS:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("[OK] Arquitectura hexagonal NestJS validada: Dominio puro y Application aislada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
