#!/usr/bin/env python3
"""Validador normativo de arquitectura Angular Feature-Layered (CALPIL).

Verifica:
1. Pureza del Dominio: src/app/features/*/domain/** sin @angular/, rxjs, @core/, @shared/, @env/, @calpil-ds/.
2. Límites de capas:
   - application/** sin data-access/** ni ui/**
   - ui/** sin data-access/** directo
   - data-access/** sin ui/**
   - sin acceso directo entre features distintas
3. Composition Root: existencia de src/app/app.routes.ts.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FORBIDDEN_DOMAIN_PREFIXES = [
    "@angular/",
    "rxjs",
    "@core/",
    "@shared/",
    "@env/",
    "@calpil-ds/",
]

IMPORT_RE = re.compile(r"""(?:from|import|export\s*\*\s*from)\s*['"]([^'"]+)['"]""")


def check_angular_architecture(root_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    routes_file = root_dir / "src" / "app" / "app.routes.ts"
    if not routes_file.exists():
        errors.append("Composition Root ausente: se esperaba 'src/app/app.routes.ts'")

    features_dir = root_dir / "src" / "app" / "features"
    if not features_dir.exists():
        errors.append("Directorio de features ausente: se esperaba 'src/app/features/'")
        return errors, warnings

    for ts_file in features_dir.rglob("*.ts"):
        if ts_file.name.endswith(".spec.ts"):
            continue

        rel = ts_file.relative_to(features_dir)
        parts = rel.parts
        if len(parts) < 2:
            continue

        feature = parts[0]
        layer = parts[1]

        if layer not in ("domain", "application", "data-access", "ui"):
            continue

        try:
            content = ts_file.read_text(encoding="utf-8")
        except Exception as exc:
            warnings.append(f"No se pudo leer {ts_file.relative_to(root_dir)}: {exc}")
            continue

        imports = IMPORT_RE.findall(content)
        for spec in imports:
            # 1. Regla: Dominio puro
            if layer == "domain":
                for forbidden in FORBIDDEN_DOMAIN_PREFIXES:
                    if spec == forbidden or spec.startswith(forbidden):
                        errors.append(f"{ts_file.relative_to(root_dir)}: domain no permite dependencia '{spec}'")

            # 2. Regla: Cross-feature directa
            if spec.startswith("@") and "/" in spec:
                pass  # alias de tsconfig
            elif spec.startswith(f"../") or spec.startswith("./"):
                # resolver ruta relativa
                target_path = (ts_file.parent / spec).resolve()
                try:
                    rel_target = target_path.relative_to(features_dir.resolve())
                    target_parts = rel_target.parts
                    if len(target_parts) >= 2:
                        target_feature = target_parts[0]
                        target_layer = target_parts[1]
                        if target_feature != feature:
                            errors.append(f"{ts_file.relative_to(root_dir)}: acceso directo a otra feature '{target_feature}' ({spec})")
                        else:
                            # Mismas reglas dentro de la misma feature
                            if layer == "domain" and target_layer != "domain":
                                errors.append(f"{ts_file.relative_to(root_dir)}: domain -> {target_layer}")
                            elif layer == "application" and target_layer in ("ui", "data-access"):
                                errors.append(f"{ts_file.relative_to(root_dir)}: application -> {target_layer}")
                            elif layer == "ui" and target_layer == "data-access":
                                errors.append(f"{ts_file.relative_to(root_dir)}: ui -> data-access")
                            elif layer == "data-access" and target_layer == "ui":
                                errors.append(f"{ts_file.relative_to(root_dir)}: data-access -> ui")
                except ValueError:
                    pass

    return errors, warnings


def main() -> None:
    ap = argparse.ArgumentParser(description="Valida arquitectura Angular feature-oriented layered")
    ap.add_argument("--repo", default=".", help="Ruta del repositorio a inspeccionar")
    args = ap.parse_args()

    repo_path = Path(args.repo).resolve()
    errors, warnings = check_angular_architecture(repo_path)

    for w in warnings:
        print(f"[WARN] {w}", file=sys.stderr)

    if errors:
        print(f"[ARCH-ERROR] Se encontraron {len(errors)} violaciones de arquitectura Angular:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[ARCH-OK] Arquitectura Angular feature-oriented layered verificada correctamente en {repo_path.name}.")
    sys.exit(0)


if __name__ == "__main__":
    main()
