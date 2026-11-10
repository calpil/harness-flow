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

Workspaces con varios proyectos: si `angular.json` declara `projects`, se
verifica cada proyecto de tipo `application` en su propia raiz (`sourceRoot`,
o `<root>/src`). En la raiz de un workspace asi no hay `src/app`, y medirla
daba violaciones falsas. Las librerias no se verifican y el verde las nombra.
Sin `angular.json`, o sin aplicaciones declaradas, se verifica la raiz.
"""
from __future__ import annotations

import argparse
import json
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

CAPAS = ("domain", "application", "data-access", "ui")


def _feature_y_capa(parts: tuple[str, ...]) -> tuple[str | None, str | None]:
    """(feature, capa) de una ruta bajo features/: la capa es el PRIMER segmento
    que sea una capa y la feature, todo lo anterior. Asi se mide una feature
    nueva anidada en una heredada (`condominios/camaras/ui/...`); antes se
    tomaba `parts[1]` como capa y esos archivos se saltaban sin medir.
    Sin capa en la ruta (codigo heredado) devuelve (None, None)."""
    for i, segmento in enumerate(parts[:-1]):
        if segmento in CAPAS and i > 0:
            return "/".join(parts[:i]), segmento
    return None, None


def _aplicaciones(root_dir: Path) -> tuple[list[tuple[str, Path]], list[str], list[str], list[str]]:
    """(aplicaciones [(nombre, src)], librerias, errores, avisos) segun angular.json.

    Sin aplicaciones declaradas devuelve la raiz como unica aplicacion sin nombre:
    es lo que este verificador media antes de entender workspaces.
    """
    raiz = [("", root_dir / "src")]
    conf = root_dir / "angular.json"
    if not conf.is_file():
        return raiz, [], [], []
    try:
        proyectos = json.loads(conf.read_text(encoding="utf-8")).get("projects")
    except (OSError, ValueError, AttributeError) as exc:
        return raiz, [], [], [f"angular.json ilegible ({exc}): se verifica la raiz"]
    if not isinstance(proyectos, dict):
        return raiz, [], [], []

    apps: list[tuple[str, Path]] = []
    libs: list[str] = []
    errores: list[str] = []
    for nombre, cfg in proyectos.items():
        if not isinstance(cfg, dict):
            continue
        if cfg.get("projectType", "application") != "application":
            libs.append(nombre)
            continue
        base = str(cfg.get("root") or "")
        src = (root_dir / str(cfg.get("sourceRoot") or Path(base) / "src")).resolve()
        if src != root_dir and root_dir not in src.parents:
            # Un proyecto que apunta afuera no se mide en silencio ni se da por bueno.
            errores.append(f"proyecto '{nombre}': su raiz queda fuera del workspace ({src})")
            continue
        apps.append((nombre, src))
    if not apps and not errores:
        return raiz, libs, [], []
    return apps, libs, errores, []


def _verificar_aplicacion(root_dir: Path, src_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    rel_src = src_dir.relative_to(root_dir).as_posix()

    routes_file = src_dir / "app" / "app.routes.ts"
    if not routes_file.exists():
        errors.append(f"Composition Root ausente: se esperaba '{rel_src}/app/app.routes.ts'")

    features_dir = src_dir / "app" / "features"
    if not features_dir.exists():
        errors.append(f"Directorio de features ausente: se esperaba '{rel_src}/app/features/'")
        return errors, warnings

    for ts_file in features_dir.rglob("*.ts"):
        if ts_file.name.endswith(".spec.ts"):
            continue

        rel = ts_file.relative_to(features_dir)
        parts = rel.parts
        if len(parts) < 2:
            continue

        feature, layer = _feature_y_capa(parts)
        if layer is None:
            continue

        archivo = ts_file.relative_to(root_dir).as_posix()
        try:
            content = ts_file.read_text(encoding="utf-8")
        except Exception as exc:
            warnings.append(f"No se pudo leer {archivo}: {exc}")
            continue

        imports = IMPORT_RE.findall(content)
        for spec in imports:
            # 1. Regla: Dominio puro
            if layer == "domain":
                for forbidden in FORBIDDEN_DOMAIN_PREFIXES:
                    if spec == forbidden or spec.startswith(forbidden):
                        errors.append(f"{archivo}: domain no permite dependencia '{spec}'")

            # 2. Regla: Cross-feature directa
            if spec.startswith("@") and "/" in spec:
                pass  # alias de tsconfig
            elif spec.startswith("../") or spec.startswith("./"):
                # resolver ruta relativa
                target_path = (ts_file.parent / spec).resolve()
                try:
                    rel_target = target_path.relative_to(features_dir.resolve())
                    target_parts = rel_target.parts
                    if len(target_parts) >= 2:
                        target_feature, target_layer = _feature_y_capa(target_parts + ("_",))
                        if target_parts[0] != parts[0]:
                            # Otra feature de primer nivel, con o sin capas (la regla de siempre).
                            errors.append(f"{archivo}: acceso directo a otra feature '{target_parts[0]}' ({spec})")
                        elif target_layer is None:
                            pass  # codigo heredado sin capas de la misma raiz: no se mide
                        elif target_feature != feature:
                            errors.append(f"{archivo}: acceso directo a otra feature '{target_feature}' ({spec})")
                        else:
                            # Mismas reglas dentro de la misma feature
                            if layer == "domain" and target_layer != "domain":
                                errors.append(f"{archivo}: domain -> {target_layer}")
                            elif layer == "application" and target_layer in ("ui", "data-access"):
                                errors.append(f"{archivo}: application -> {target_layer}")
                            elif layer == "ui" and target_layer == "data-access":
                                errors.append(f"{archivo}: ui -> data-access")
                            elif layer == "data-access" and target_layer == "ui":
                                errors.append(f"{archivo}: data-access -> ui")
                except ValueError:
                    pass

    return errors, warnings


def verificar_workspace(root_dir: Path) -> tuple[list[str], list[str], list[str], list[str]]:
    """(errores, avisos, aplicaciones verificadas, librerias no verificadas)."""
    root_dir = root_dir.resolve()
    apps, libs, errors, warnings = _aplicaciones(root_dir)
    for _, src_dir in apps:
        e, w = _verificar_aplicacion(root_dir, src_dir)
        errors.extend(e)
        warnings.extend(w)
    return errors, warnings, [nombre for nombre, _ in apps if nombre], libs


def check_angular_architecture(root_dir: Path) -> tuple[list[str], list[str]]:
    errors, warnings, _, _ = verificar_workspace(root_dir)
    return errors, warnings


def main() -> None:
    ap = argparse.ArgumentParser(description="Valida arquitectura Angular feature-oriented layered")
    ap.add_argument("--repo", default=".", help="Ruta del repositorio a inspeccionar")
    args = ap.parse_args()

    repo_path = Path(args.repo).resolve()
    errors, warnings, apps, libs = verificar_workspace(repo_path)

    for w in warnings:
        print(f"[WARN] {w}", file=sys.stderr)

    if errors:
        print(f"[ARCH-ERROR] Se encontraron {len(errors)} violaciones de arquitectura Angular:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    # Un conteo parcial nunca se reporta como total: el verde dice que midio y que no.
    alcance = ""
    if apps:
        alcance += f" Aplicaciones verificadas ({len(apps)}): {', '.join(apps)}."
    if libs:
        alcance += f" Librerias NO verificadas ({len(libs)}): {', '.join(libs)}."
    print(f"[ARCH-OK] Arquitectura Angular feature-oriented layered verificada correctamente en {repo_path.name}.{alcance}")
    sys.exit(0)


if __name__ == "__main__":
    main()
