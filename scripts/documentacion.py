#!/usr/bin/env python3
"""Sincroniza documentos de producto/diseno desde features cerradas.

No intenta escribir prosa de producto por el usuario. Mantiene un bloque generado
por harness-flow y preserva cualquier contenido manual fuera de ese bloque.
Funciona igual desde Hermes y Claude Code porque solo depende del arbol del
proyecto con harness/feature_list.json.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (bitacora, impl_path, load_backlog, paths, review_path,  # noqa: E402
                   save_backlog, spec_ac_lineas, spec_path)

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
    """Los AC del spec, con el MISMO parser que usan los gates.

    Tenia un regex propio que exigia `AC-n:` pegado, asi que perdia en silencio
    los AC con titulo entre parentesis ("- AC-1 (cola por estado): ...") que
    spec_acs si reconoce: el PRD listaba menos AC que el spec, o directamente
    "sin AC en spec" para una feature que los tenia todos.
    """
    if not path.exists():
        return []
    return list(spec_ac_lineas(path.read_text(encoding="utf-8")).values())


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
            *([] if f.get("integraciones") else [f"- Merge commit: {f.get('merge_commit', 'no declarado')}"]),
            f"- Spec: `{_rel(root, sp)}`" if sp.exists() else "- Spec: sin archivo",
            f"- Evidencia: `{_rel(root, ip)}`" if ip.exists() else "- Evidencia: sin archivo",
            f"- Review: `{_rel(root, rp)}`" if rp.exists() else "- Review: sin archivo",
        ]
        for repo in f.get("integraciones", []):
            lines.append(f"- Integracion manual `{repo['microservicio']}`: "
                         f"fuente `{repo['source_sha']}` -> `{repo['target_branch']}` "
                         f"tip validado `{repo['target_sha']}` (sin merge creado por close)")
        if f.get("cierre_historico"):
            ch = f["cierre_historico"]
            lines.append(f"- Cierre historico (sin base preintegracion medible): motivo "
                         f"«{ch.get('motivo', '')}», autorizado por {ch.get('autorizado_por', 'no declarado')} "
                         f"el {ch.get('at', 'sin fecha')}")
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
    from bloques import parts, START, END
    previo = path.read_bytes() if path.exists() else (
        f"# {titulo}\n\nContenido manual arriba; harness-flow mantiene solo el bloque generado.\n\n".encode())
    manual = parts(previo)  # rechaza marcador parcial/duplicado antes de escribir
    generated = bloque.encode().split(START, 1)[1].split(END, 1)[0]
    if manual is not None:
        nuevo = manual[0] + START + generated + END + manual[1]
    else:
        nuevo = previo + START + generated + END + b"\n"
    if not path.exists() or nuevo != previo:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(nuevo)
        return True
    return False


def sync(p: dict | None = None, data: dict | None = None) -> list[Path]:
    p = p or paths()
    data = data or load_backlog(p)
    prd = p["docs"] / "prd" / "PRD-master.md"
    sdd = p["docs"] / "sdd.md"
    cambiados: list[Path] = []
    from cierre_local import transaction
    with transaction(p, "documentacion"):
        if _actualizar_bloque(prd, "PRD maestro", _bloque_prd(p, data)):
            cambiados.append(prd)
        if _actualizar_bloque(sdd, "SDD", _bloque_sdd(p, data)):
            cambiados.append(sdd)
    return cambiados


def cmd_sync(args) -> None:
    p = paths()
    data = load_backlog(p)
    from cierre_local import transaction
    with transaction(p, "documentacion"):
        cambiados = sync(p, data)
        bitacora(p, "documentacion PRD/SDD sincronizada")
        save_backlog(p, data)
    for path in cambiados:
        print(f"[ok] documentacion sincronizada: {_rel(p['root'], path)}")
    if not cambiados:
        print("[ok] documentacion ya estaba sincronizada")


def main() -> None:
    ap = argparse.ArgumentParser(description="Sincroniza PRD/SDD generados desde el backlog")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync")
    s.set_defaults(fn=cmd_sync)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
