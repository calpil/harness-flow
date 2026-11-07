#!/usr/bin/env python3
"""Validador normativo de arquitectura hexagonal en Rust (CALPIL).

Verifica:
1. Composition Root: existencia de 'crates/api/src/main.rs' o 'src/main.rs'.
2. Pureza del Dominio: crates/domain o src/domain sin frameworks web (axum, hyper),
   persistencia (sqlx, diesel), I/O de red ni acoplamiento a otras capas.
3. Aislamiento de Application: crates/application o src/application sin referencias
   a infrastructure, api o axum.
4. Infrastructure limpia: sin acoplamiento a axum/transporte HTTP.
5. Tests deterministas: sin llamadas a thread::sleep o tokio::time::sleep en pruebas.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FORBIDDEN_DOMAIN_CRATES = [
    "axum",
    "sqlx",
    "tokio::net",
    "tokio::fs",
    "hyper",
    "diesel",
    "reqwest",
    "tower",
    "tower_http",
]

FORBIDDEN_DOMAIN_DEPS = [
    "axum",
    "sqlx",
    "hyper",
    "diesel",
    "reqwest",
    "tower",
    "tower-http",
    "tower_http",
]

FORBIDDEN_APPLICATION_CRATES = [
    "axum",
    "hyper",
]

USE_RE = re.compile(r'^\s*use\s+([^;]+);', re.MULTILINE)
SLEEP_RE = re.compile(r'\b(?:std::)?thread::sleep\s*\(|\btokio::time::sleep\s*\(')
TOML_DEP_SECTION_RE = re.compile(r'\[(?:workspace\.)?dependencies(?:\.([a-zA-Z0-9_-]+))?\]')


def extract_uses(rust_source: str) -> list[str]:
    uses = []
    for match in USE_RE.finditer(rust_source):
        raw = match.group(1).strip()
        # Eliminar comentarios inline
        raw = raw.split("//")[0].strip()
        uses.append(raw)
    return uses


def extract_toml_dependencies(toml_text: str) -> list[str]:
    deps = []
    in_deps = False
    for line in toml_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            sec = line.strip("[]").strip()
            in_deps = sec in ("dependencies", "dev-dependencies", "build-dependencies")
            if "." in sec:
                parts = sec.split(".")
                if parts[0] in ("dependencies", "dev-dependencies", "build-dependencies"):
                    deps.append(parts[1])
            continue
        if in_deps and "=" in line:
            dep_name = line.split("=")[0].strip()
            deps.append(dep_name)
    return deps


def check_rust_architecture(root_dir: Path) -> tuple[list[str], list[str]]:
    """Devuelve (errores, advertencias)."""
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Composition Root (main.rs)
    main_files = [
        p for p in root_dir.glob("**/main.rs")
        if "target" not in p.parts and ".git" not in p.parts
    ]
    if not main_files:
        errors.append("Composition Root ausente: se esperaba 'crates/api/src/main.rs' o 'src/main.rs'")
    else:
        has_canonical = any(
            p.parts[-3:] == ("crates", "api", "src") or
            p.parts[-2:] == ("src", "main.rs") or
            ("api" in [part.lower() for part in p.parts] and p.name == "main.rs")
            for p in main_files
        )
        if not has_canonical:
            warnings.append(f"Composition Root no canónico: encontrado en {[str(p.relative_to(root_dir)) for p in main_files]}, se recomienda 'crates/api/src/main.rs' o 'src/main.rs'")

    # 2. Verificar Cargo.toml de crates
    toml_files = [
        f for f in root_dir.glob("**/Cargo.toml")
        if "target" not in f.parts and ".git" not in f.parts
    ]

    for toml in toml_files:
        rel = toml.relative_to(root_dir)
        text = toml.read_text(encoding="utf-8", errors="ignore")
        deps = extract_toml_dependencies(text)
        parts_lower = [p.lower() for p in rel.parts]

        # Crate Domain
        if "domain" in parts_lower and "test" not in parts_lower:
            for dep in deps:
                dep_norm = dep.lower().replace("_", "-")
                for forbidden in FORBIDDEN_DOMAIN_DEPS:
                    if dep_norm == forbidden or dep_norm.startswith(forbidden + "-"):
                        errors.append(f"{rel}: el crate Domain no debe incluir la dependencia externa '{dep}'")
                if any(k in dep_norm for k in ["application", "infrastructure", "api"]):
                    errors.append(f"{rel}: el crate Domain no debe referenciar otros crates internos ('{dep}')")

        # Crate Application
        elif "application" in parts_lower and "test" not in parts_lower:
            for dep in deps:
                dep_norm = dep.lower().replace("_", "-")
                if any(k in dep_norm for k in ["infrastructure", "api"]):
                    errors.append(f"{rel}: el crate Application no debe referenciar capas externas ('{dep}')")
                if dep_norm in ("axum", "hyper"):
                    errors.append(f"{rel}: el crate Application no debe incluir transporte HTTP '{dep}'")

    # 3. Verificar archivos de código Rust (.rs)
    rs_files = [
        f for f in root_dir.glob("**/*.rs")
        if "target" not in f.parts and ".git" not in f.parts
    ]

    for rs in rs_files:
        rel = rs.relative_to(root_dir)
        parts = rel.parts
        parts_lower = [p.lower() for p in parts]
        dir_parts_lower = parts_lower[:-1]

        is_test = any("test" in p for p in parts_lower) or rs.name.endswith("_test.rs") or rs.name == "tests.rs"

        try:
            content = rs.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            warnings.append(f"No se pudo leer {rel}: {exc}")
            continue

        uses = extract_uses(content)

        # Regla: Dominio puro
        is_domain = any("domain" in p for p in dir_parts_lower) and not any(k in dir_parts_lower for k in ["infrastructure", "application", "api"]) and not is_test
        if is_domain:
            for u in uses:
                for forbidden in FORBIDDEN_DOMAIN_CRATES:
                    if forbidden in u:
                        errors.append(f"{rel}: Domain no permite dependencia externa '{forbidden}' en '{u}'")
                if any(k in u.lower() for k in ["::infrastructure", "infrastructure::", "::application", "application::", "::api", "api::"]):
                    errors.append(f"{rel}: Domain no debe acoplarse a capas externas ('{u}')")

        # Regla: Application aislado
        is_application = any("application" in p for p in dir_parts_lower) and not any(k in dir_parts_lower for k in ["infrastructure", "api"]) and not is_test
        if is_application:
            for u in uses:
                for forbidden in FORBIDDEN_APPLICATION_CRATES:
                    if forbidden in u:
                        errors.append(f"{rel}: Application no debe importar transporte '{forbidden}' en '{u}'")
                if any(k in u.lower() for k in ["::infrastructure", "infrastructure::", "::api", "api::"]):
                    errors.append(f"{rel}: Application no debe importar adaptadores concretos ('{u}')")

        # Regla: Infrastructure no debe acoplar transporte Axum
        is_infrastructure = any("infrastructure" in p for p in dir_parts_lower) and not any("api" in p for p in dir_parts_lower) and not is_test
        if is_infrastructure:
            for u in uses:
                if "axum" in u:
                    errors.append(f"{rel}: Infrastructure no debe acoplarse a transporte HTTP axum ('{u}')")

        # Regla: Tests deterministas
        if is_test:
            # Ignorar comentarios con sleep
            lines_with_sleep = [
                line.strip() for line in content.splitlines()
                if SLEEP_RE.search(line) and not line.strip().startswith("//") and not line.strip().startswith("/*")
            ]
            if lines_with_sleep:
                errors.append(f"{rel}: uso de sleep prohibido en pruebas deterministas; usar mocks, FakeClock o sincronización determinista")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificador de arquitectura Rust Hexagonal (CALPIL)")
    parser.add_argument("--repo", default=".", help="Ruta de la raíz del repositorio a verificar")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    errors, warnings = check_rust_architecture(repo)

    if warnings:
        print("[!] Advertencias de arquitectura:")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"[X] Fallo normativo: {len(errors)} infracción(es) de límites hexagonales Rust:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("[OK] Arquitectura hexagonal Rust validada: Pureza de Dominio, Aislamiento de Application y Tests Deterministas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
