#!/usr/bin/env python3
"""Validador normativo de arquitectura hexagonal en Golang (CALPIL).

Verifica:
1. Pureza del Dominio: internal/*/domain/** sin frameworks, transporte (net/http, chi),
   JWT ni SQL/pgx, ni directos ni transitivos.
2. Aislamiento de Application: internal/*/application/** sin imports de adapter y sin
   transporte, JWT ni persistencia, ni directos ni transitivos (un paquete de
   internal/platform que trae net/http tambien cuenta).
3. Tests deterministas: sin time.Sleep ni una pausa `<-time.After(d)` suelta en ningun
   test del repo (internal/**, platform incluido, y cmd/**) ni en los paquetes de apoyo
   a tests (testsupport, testutil, testhelpers). Un `case <-time.After(...)` dentro de
   un select es un timeout, no una pausa, y se permite.
4. Composition Root: existencia de cmd/server/main.go o cmd/*/main.go.

Los imports se leen en bloque y de una linea, con alias, `_` o `.`. Las dependencias
transitivas se miden con `go list`; sin toolchain Go (o si `go list` falla) sale un
aviso y el verde dice que esa parte NO se midio.

Adopcion progresiva: un servicio sin `internal/` no es un error. Lo existente no
se mueve y los modulos nuevos nacen en internal/<modulo>/{domain,application,adapter}.
Sin `internal/` las reglas 1 a 3 no se miden: sale un aviso y el verde dice que
esos limites NO se midieron. Con `internal/`, siguen siendo error.
La composition root se exige siempre.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
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
    "github.com/golang-jwt/jwt",
    "github.com/MicahParks/keyfunc",
]
# application tiene los mismos limites que domain (ademas de no importar adapters).
FORBIDDEN_APPLICATION_IMPORTS = FORBIDDEN_DOMAIN_IMPORTS
CAPAS_MEDIDAS = ("domain", "application")
MODULOS_TRANSVERSALES = ("platform", "config", "shared")
DIRS_APOYO_TESTS = {"testsupport", "testutil", "testhelpers"}
DIRS_IGNORADOS = {"vendor", ".git", "node_modules"}
_NO_MEDIDO = "__transitivo_no_medido__"

IMPORT_BLOCK_RE = re.compile(r'^\s*import\s*\((.*?)\)', re.DOTALL | re.MULTILINE)
# import "x" | import alias "x" | import _ "x" | import . "x"
SINGLE_IMPORT_RE = re.compile(r'^\s*import\s+(?:[A-Za-z_]\w*\s+|[_.]\s+)?"([^"]+)"', re.MULTILINE)
SLEEP_RE = re.compile(r'\btime\.Sleep\s*\(')
PAUSA_AFTER_RE = re.compile(r'^\s*<-\s*time\.After\s*\(')


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


def es_prohibido(imp: str, prohibidos: list[str]) -> bool:
    return any(imp == f or imp.startswith(f + "/") for f in prohibidos)


def es_prohibido_transitivo(dep: str, prohibidos: list[str]) -> bool:
    """Como es_prohibido, pero `database/sql/driver` (y sus internos) no cuentan.

    Son solo interfaces (Scanner/Valuer) que traen tipos de valor legitimos, como
    github.com/google/uuid. El motor `database/sql` y los drivers si cuentan.
    """
    if dep.startswith("database/sql/"):
        return False
    return es_prohibido(dep, prohibidos)


def modulo_go(root_dir: Path) -> str | None:
    gomod = root_dir / "go.mod"
    if not gomod.is_file():
        return None
    m = re.search(r'^module\s+(\S+)', gomod.read_text(encoding="utf-8", errors="replace"), re.MULTILINE)
    return m.group(1) if m else None


def capa_de(rel_parts: tuple[str, ...]) -> tuple[str, str] | None:
    """('internal', mod, capa, ...) -> (mod, capa) si es una capa medida de un modulo."""
    if len(rel_parts) < 3 or rel_parts[0] != "internal":
        return None
    mod, capa = rel_parts[1], rel_parts[2]
    if mod in MODULOS_TRANSVERSALES or capa not in CAPAS_MEDIDAS:
        return None
    return mod, capa


def grafo_go_list(root_dir: Path) -> tuple[dict[str, tuple[list[str], set[str]]] | None, str]:
    """ImportPath -> (Imports directos, Deps transitivas) de ./internal/... y sus deps."""
    go = shutil.which("go")
    if not go:
        return None, "sin toolchain Go en el PATH"
    try:
        r = subprocess.run(
            [go, "list", "-e", "-deps", "-f",
             '{{.ImportPath}}\t{{join .Imports " "}}\t{{join .Deps " "}}', "./internal/..."],
            cwd=root_dir, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"go list no corrio: {exc}"
    if r.returncode != 0 or not r.stdout.strip():
        detalle = (r.stderr.strip().splitlines() or ["sin salida"])[0]
        return None, f"go list fallo: {detalle}"
    grafo: dict[str, tuple[list[str], set[str]]] = {}
    for linea in r.stdout.splitlines():
        partes = linea.split("\t")
        if len(partes) != 3:
            continue
        ruta, imps, deps = partes
        grafo[ruta] = (imps.split(), set(deps.split()))
    return grafo, ""


def check_transitivo(root_dir: Path, errors: list[str], warnings: list[str]) -> bool:
    """Agrega un error por cada dependencia prohibida que llega por un import permitido.

    Devuelve True si midio y False si no pudo (deja el aviso con el motivo).
    """
    modulo = modulo_go(root_dir)
    if not modulo:
        warnings.append("Sin go.mod con 'module': dependencias transitivas de domain/application NO medidas")
        return False
    grafo, motivo = grafo_go_list(root_dir)
    if grafo is None:
        warnings.append(f"Dependencias transitivas de domain/application NO medidas ({motivo})")
        return False
    for ruta in sorted(grafo):
        if not ruta.startswith(modulo + "/"):
            continue
        rel = tuple(ruta[len(modulo) + 1:].split("/"))
        cl = capa_de(rel)
        if not cl:
            continue
        prohibidos = FORBIDDEN_DOMAIN_IMPORTS if cl[1] == "domain" else FORBIDDEN_APPLICATION_IMPORTS
        directos, _ = grafo[ruta]
        vistos: set[str] = set()
        for imp in directos:
            if es_prohibido(imp, prohibidos):
                continue  # el directo ya lo reporta la lectura por archivo, con su ruta
            _, deps_imp = grafo.get(imp, ([], set()))
            for dep in sorted(d for d in deps_imp if es_prohibido_transitivo(d, prohibidos)):
                if dep in vistos:
                    continue
                vistos.add(dep)
                errors.append(f"{'/'.join(rel)}: {cl[1]} trae '{dep}' de forma transitiva (por '{imp}')")
    return True


def check_esperas(root_dir: Path, errors: list[str]) -> None:
    for go_file in sorted(root_dir.rglob("*.go")):
        rel = go_file.relative_to(root_dir)
        if any(p in DIRS_IGNORADOS or p.startswith(".") for p in rel.parts[:-1]):
            continue
        es_test = go_file.name.endswith("_test.go")
        es_apoyo = any(p in DIRS_APOYO_TESTS for p in rel.parts[:-1])
        if not (es_test or es_apoyo):
            continue
        try:
            lineas = go_file.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for idx, line in enumerate(lineas, start=1):
            if line.strip().startswith("//"):
                continue
            if SLEEP_RE.search(line):
                errors.append(f"{rel}:{idx}: uso de time.Sleep prohibido en tests deterministas "
                              "(usa sincronización, channels, un sondeo acotado con time.Ticker o fake clock)")
            elif PAUSA_AFTER_RE.search(line):
                errors.append(f"{rel}:{idx}: '<-time.After(...)' suelto es una pausa fija, igual que time.Sleep "
                              "(usa sincronización, channels o un sondeo acotado con time.Ticker)")


def check_golang_architecture(root_dir: Path) -> tuple[list[str], list[str]]:
    """Devuelve (errores, advertencias)."""
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Composition Root
    main_files = list(root_dir.glob("cmd/**/main.go"))
    if not main_files:
        errors.append("Composition Root ausente: se esperaba 'cmd/server/main.go' o 'cmd/*/main.go'")
    elif not (root_dir / "cmd" / "server" / "main.go").exists():
        warnings.append(f"Composition Root no canónico: encontrado en {[str(m.relative_to(root_dir)) for m in main_files]}, se recomienda 'cmd/server/main.go'")

    # 2. Internal layers
    internal_dir = root_dir / "internal"
    if not internal_dir.is_dir():
        warnings.append("Directorio 'internal/' ausente (adopción progresiva): pureza de dominio, "
                        "aislamiento de application y tests deterministas NO se midieron. "
                        "Los módulos nuevos nacen en 'internal/<modulo>/{domain,application,adapter}'")
        return errors, warnings

    # 3. Tests deterministas: con internal/ se miden en todo el repo (platform y cmd incluidos)
    check_esperas(root_dir, errors)

    for go_file in sorted(root_dir.glob("internal/**/*.go")):
        rel = go_file.relative_to(root_dir)
        cl = capa_de(rel.parts)
        if not cl or go_file.name.endswith("_test.go"):
            continue
        layer = cl[1]
        try:
            content = go_file.read_text(encoding="utf-8")
        except Exception as exc:
            warnings.append(f"No se pudo leer {rel}: {exc}")
            continue
        imports = extract_imports(content)

        # Regla: Dominio puro
        if layer == "domain":
            for imp in imports:
                if es_prohibido(imp, FORBIDDEN_DOMAIN_IMPORTS):
                    errors.append(f"{rel}: domain no permite dependencia externa '{imp}'")

        # Regla: Application aislado de adaptadores, transporte y persistencia
        if layer == "application":
            for imp in imports:
                if "/adapter" in imp:
                    errors.append(f"{rel}: application no debe importar adapters ('{imp}')")
                elif es_prohibido(imp, FORBIDDEN_APPLICATION_IMPORTS):
                    errors.append(f"{rel}: application no permite dependencia externa '{imp}'")

    if not check_transitivo(root_dir, errors, warnings):
        warnings.append(_NO_MEDIDO)
    return errors, warnings


def main() -> None:
    ap = argparse.ArgumentParser(description="Valida arquitectura hexagonal en Golang")
    ap.add_argument("--repo", default=".", help="Ruta del repositorio a inspeccionar")
    args = ap.parse_args()

    repo_path = Path(args.repo).resolve()
    errors, warnings = check_golang_architecture(repo_path)
    sin_transitivo = _NO_MEDIDO in warnings
    warnings = [w for w in warnings if w != _NO_MEDIDO]

    for w in warnings:
        print(f"[WARN] {w}", file=sys.stderr)

    if errors:
        print(f"[ARCH-ERROR] Se encontraron {len(errors)} violaciones de arquitectura hexagonal:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    if not (repo_path / "internal").is_dir():
        # Un conteo parcial nunca se reporta como total: sin internal/ solo se midio la composition root.
        print(f"[ARCH-OK] Composition root verificada en {repo_path.name}. "
              "Sin 'internal/': límites hexagonales NO medidos.")
        sys.exit(0)

    if sin_transitivo:
        print(f"[ARCH-OK] Arquitectura hexagonal en Go verificada en {repo_path.name}, salvo las dependencias "
              "transitivas de domain/application, que NO se midieron (ver aviso).")
        sys.exit(0)

    print(f"[ARCH-OK] Arquitectura hexagonal en Go verificada correctamente en {repo_path.name}.")
    sys.exit(0)


if __name__ == "__main__":
    main()
