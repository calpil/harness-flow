#!/usr/bin/env python3
"""Sincroniza documentos de producto/diseno desde features cerradas.

No intenta escribir prosa de producto por el usuario. Mantiene un bloque generado
por harness-flow y preserva cualquier contenido manual fuera de ese bloque.
Funciona igual desde Hermes y Claude Code porque solo depende del arbol del
proyecto con harness/feature_list.json.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (bitacora, impl_path, load_backlog, paths, review_path,  # noqa: E402
                   save_backlog, spec_path)

INICIO = "<!-- harness-flow:features:start -->"
FIN = "<!-- harness-flow:features:end -->"


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _leer(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _acs_desde_spec(path: Path) -> list[str]:
    if not path.exists():
        return []
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*[-*]?\s*(AC-\d+\s*:\s*.+?)\s*$", line)
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out


def _features_done(data: dict) -> list[dict]:
    return sorted(
        [f for f in data.get("features", []) if f.get("status") == "done"],
        key=lambda x: int(x.get("id", 0)),
    )


def _bloque_prd(p: dict, data: dict) -> str:
    root = p["root"]
    lines = [
        INICIO,
        "## Features implementadas",
        "",
        "Fuente: harness/feature_list.json",
        "",
    ]
    feats = _features_done(data)
    if not feats:
        lines += ["No hay features cerradas todavia.", "", FIN, ""]
        return "\n".join(lines)

    for f in feats:
        sp = spec_path(p, f)
        lines += [
            f"### Feature #{f['id']} - {f.get('name', '')}",
            "",
            f"- Tipo: {f.get('kind', 'feature')}",
            f"- Cerrada: {f.get('closed_at', 'sin fecha')}",
            f"- Spec: `{_rel(root, sp)}`" if sp.exists() else "- Spec: sin archivo",
        ]
        if f.get("prd"):
            lines.append(f"- PRD fuente: `{f['prd']}`")
        acs = _acs_desde_spec(sp)
        if acs:
            lines.append("- Criterios de aceptacion:")
            lines.extend(f"  - {ac}" for ac in acs)
        else:
            lines.append("- Criterios de aceptacion: sin AC en spec")
        lines.append("")
    lines += [FIN, ""]
    return "\n".join(lines)


def _bloque_sdd(p: dict, data: dict) -> str:
    root = p["root"]
    lines = [
        INICIO,
        "## Diseno implementado por feature",
        "",
        "Fuente: harness/feature_list.json",
        "",
    ]
    feats = _features_done(data)
    if not feats:
        lines += ["No hay features cerradas todavia.", "", FIN, ""]
        return "\n".join(lines)

    for f in feats:
        sp = spec_path(p, f)
        ip = impl_path(p, f)
        rp = review_path(p, f)
        micros = f.get("microservicios") or []
        lines += [
            f"### Feature #{f['id']} - {f.get('name', '')}",
            "",
            f"- Microservicios: {', '.join(micros) if micros else 'no declarado'}",
            f"- Rama: {f.get('branch', 'no declarada')}",
            f"- Integrado en: {f.get('integrado_en', 'no declarado')}",
            f"- Merge commit: {f.get('merge_commit', 'no declarado')}",
            f"- Spec: `{_rel(root, sp)}`" if sp.exists() else "- Spec: sin archivo",
            f"- Evidencia: `{_rel(root, ip)}`" if ip.exists() else "- Evidencia: sin archivo",
            f"- Review: `{_rel(root, rp)}`" if rp.exists() else "- Review: sin archivo",
        ]
        if f.get("progress_archive"):
            lines.append(f"- Progreso archivado: `{f['progress_archive']}`")
        if f.get("jira_key"):
            lines.append(f"- Jira: {f['jira_key']}")
        if f.get("confluence_page_id"):
            lines.append(f"- Confluence page id: {f['confluence_page_id']}")
        lines.append("")
    lines += [FIN, ""]
    return "\n".join(lines)


def _actualizar_bloque(path: Path, titulo: str, bloque: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        previo = _leer(path)
    else:
        previo = f"# {titulo}\n\nContenido manual arriba; harness-flow mantiene solo el bloque generado.\n\n"

    if INICIO in previo and FIN in previo:
        antes, resto = previo.split(INICIO, 1)
        _, despues = resto.split(FIN, 1)
        nuevo = antes.rstrip() + "\n\n" + bloque.rstrip() + "\n" + despues.lstrip("\n")
    else:
        nuevo = previo.rstrip() + "\n\n" + bloque.rstrip() + "\n"
    if nuevo != previo:
        path.write_text(nuevo, encoding="utf-8")
        return True
    return False


def sync(p: dict | None = None, data: dict | None = None) -> list[Path]:
    p = p or paths()
    data = data or load_backlog(p)
    prd = p["docs"] / "prd" / "PRD-master.md"
    sdd = p["docs"] / "sdd.md"
    cambiados: list[Path] = []
    if _actualizar_bloque(prd, "PRD maestro", _bloque_prd(p, data)):
        cambiados.append(prd)
    if _actualizar_bloque(sdd, "SDD", _bloque_sdd(p, data)):
        cambiados.append(sdd)
    return cambiados


def cmd_sync(args) -> None:
    p = paths()
    data = load_backlog(p)
    cambiados = sync(p, data)
    for path in cambiados:
        print(f"[ok] documentacion sincronizada: {_rel(p['root'], path)}")
    if not cambiados:
        print("[ok] documentacion ya estaba sincronizada")
    bitacora(p, "documentacion PRD/SDD sincronizada")
    save_backlog(p, data)


def main() -> None:
    ap = argparse.ArgumentParser(description="Sincroniza PRD/SDD generados desde el backlog")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync")
    s.set_defaults(fn=cmd_sync)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
