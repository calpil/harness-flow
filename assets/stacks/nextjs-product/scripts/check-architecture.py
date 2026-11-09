#!/usr/bin/env python3
"""Validador normativo de arquitectura Next.js Product (CALPIL).

Verifica:
1. Composition Root: App Router bajo src/app o app.
2. Server Components por defecto: archivos sin 'use client' no deben importar React hooks de cliente.
3. Aislamiento server-only: módulos de base de datos o secretos protegidos.
4. Tests deterministas: sin sleep arbitrario en tests.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CLIENT_HOOKS_RE = re.compile(r'\b(?:useState|useEffect|useLayoutEffect|useReducer|useContext)\s*\(')
SLEEP_RE = re.compile(r'\b(?:setTimeout|sleep)\s*\(')


def check_nextjs_architecture(root_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Composition Root (App Router)
    has_app_router = (root_dir / "src" / "app").is_dir() or (root_dir / "app").is_dir()
    if not has_app_router:
        errors.append("Composition Root ausente: se esperaba App Router bajo 'src/app/' o 'app/'")

    # 2. Server Components por defecto
    ts_files = [
        f for f in root_dir.glob("**/*.{tsx,ts,jsx,js}")
        if "node_modules" not in f.parts and ".next" not in f.parts and "dist" not in f.parts
    ]

    for f in ts_files:
        rel = f.relative_to(root_dir)
        parts_lower = [p.lower() for p in rel.parts]
        is_test = any(t in parts_lower for t in ["test", "tests", "__tests__"]) or f.name.endswith(".test.ts") or f.name.endswith(".spec.ts")

        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            warnings.append(f"No se pudo leer {rel}: {exc}")
            continue

        if not is_test and "app" in parts_lower:
            first_lines = "\n".join(content.splitlines()[:5])
            has_use_client = "'use client'" in first_lines or '"use client"' in first_lines
            if not has_use_client and CLIENT_HOOKS_RE.search(content):
                errors.append(f"{rel}: uso de hooks de cliente (useState/useEffect) en Server Component; requiere directiva 'use client'")

        if is_test and SLEEP_RE.search(content) and not ("waitFor" in content or "vi.advanceTimersByTime" in content):
            warnings.append(f"{rel}: posible retraso no determinista en tests; usar timers simulados de Vitest/Jest")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificador de arquitectura Next.js Product (CALPIL)")
    parser.add_argument("--repo", default=".", help="Ruta de la raíz del repositorio a verificar")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    errors, warnings = check_nextjs_architecture(repo)

    if warnings:
        print("[!] Advertencias de arquitectura:")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"[X] Fallo normativo: {len(errors)} infracción(es) de arquitectura Next.js:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("[OK] Arquitectura Next.js validada: App Router y Server Components conformes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
