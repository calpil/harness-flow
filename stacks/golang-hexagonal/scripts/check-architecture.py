#!/usr/bin/env python3
"""Validador normativo de arquitectura hexagonal en Golang (CALPIL).

Verifica:
1. Pureza del Dominio: internal/*/domain/** sin frameworks, transporte (net/http, chi) ni SQL/pgx.
2. Aislamiento de Application: internal/*/application/** sin imports de adapter.
3. Tests deterministas: sin llamadas a time.Sleep en tests unitarios.
4. Composition Root: existencia de cmd/server/main.go o cmd/*/main.go.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FORBIDDEN_DOMAIN_IMPORTS = [
    "net/http",
    "github.com/go-chi/chi",
    "github.com/go-chi/chi/v5",
    "github.com/jackc/pgx",
    "github.com/jackc/pgx/v5",
    "database/sql",
    "github.com/jmoiron/sqlx",
    "gorm.io/gorm",
]

IMPORT_BLOCK_RE = re.compile(r'import\s*\((.*?)\)', re.DOTALL)
SINGLE_IMPORT_RE = re.compile(r'import\s+"([^"]+)"')
SLEEP_RE = re.compile(r'\btime\.Sleep\s*\(')


def extract_imports(go_source: str) -> list[str]:
    imports = []
    for match in IMPORT_BLOCK_RE.finditer(go_source):
        block = match.group(1)
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            m = re.search(r'"([^"]+)"', line)
            if m:
                imports.append(m.group(1))
    for match in SINGLE_IMPORT_RE.finditer(go_source):
        imports.append(match.group(1))
    return imports


def check_golang_architecture(root_dir: Path) -> tuple[list[str], list[str]]:
    """Devuelve (errores, advertencias)."""
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Composition Root
    cmd_dir = root_dir / "cmd"
    main_files = list(root_dir.glob("cmd/**/main.go"))
    if not main_files:
        errors.append("Composition Root ausente: se esperaba 'cmd/server/main.go' o 'cmd/*/main.go'")
    elif not (root_dir / "cmd" / "server" / "main.go").exists():
        warnings.append(f"Composition Root no canónico: encontrado en {[str(m.relative_to(root_dir)) for m in main_files]}, se recomienda 'cmd/server/main.go'")

    # 2. Internal layers
    internal_dir = root_dir / "internal"
    if not internal_dir.exists():
        errors.append("Directorio 'internal/' ausente: los límites hexagonales deben residir bajo 'internal/'")
        return errors, warnings

    for go_file in root_dir.glob("internal/**/*.go"):
        rel = go_file.relative_to(root_dir)
        parts = rel.parts  # ('internal', '<modulo>', '<capa>', ...)
        if len(parts) < 3:
            continue
        module = parts[1]
        layer = parts[2]

        if module in ("platform", "config", "shared"):
            continue

        try:
            content = go_file.read_text(encoding="utf-8")
        except Exception as exc:
            warnings.append(f"No se pudo leer {rel}: {exc}")
            continue

        is_test = go_file.name.endswith("_test.go")
        imports = extract_imports(content)

        # Regla: Dominio puro
        if layer == "domain":
            for imp in imports:
                for forbidden in FORBIDDEN_DOMAIN_IMPORTS:
                    if imp == forbidden or imp.startswith(forbidden + "/"):
                        errors.append(f"{rel}: domain no permite dependencia externa '{imp}'")

        # Regla: Application aislado de adaptadores
        if layer == "application":
            for imp in imports:
                if "/adapter" in imp:
                    errors.append(f"{rel}: application no debe importar adapters ('{imp}')")

        # Regla: Tests deterministas sin time.Sleep
        if is_test:
            for idx, line in enumerate(content.splitlines(), start=1):
                if SLEEP_RE.search(line) and not line.strip().startswith("//"):
                    errors.append(f"{rel}:{idx}: uso de time.Sleep prohibido en tests deterministas (usa sincronización, channels o fake clock)")

    return errors, warnings


def main() -> None:
    ap = argparse.ArgumentParser(description="Valida arquitectura hexagonal en Golang")
    ap.add_argument("--repo", default=".", help="Ruta del repositorio a inspeccionar")
    args = ap.parse_args()

    repo_path = Path(args.repo).resolve()
    errors, warnings = check_golang_architecture(repo_path)

    for w in warnings:
        print(f"[WARN] {w}", file=sys.stderr)

    if errors:
        print(f"[ARCH-ERROR] Se encontraron {len(errors)} violaciones de arquitectura hexagonal:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[ARCH-OK] Arquitectura hexagonal en Go verificada correctamente en {repo_path.name}.")
    sys.exit(0)


if __name__ == "__main__":
    main()
