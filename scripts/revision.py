#!/usr/bin/env python3
"""Paquete de revision. NO sella nada: el sello lo pone
gate.py revision --veredicto.

  revision.py --feature <id>              resumen legible
  revision.py --feature <id> --briefing   contexto para delegar a un subagente

El review lo hace un SUBAGENTE en contexto aislado (delegate_task en Hermes,
la tool Task con subagente general-purpose en Claude Code), que no vio
como se implemento. Un revisor que recuerda haber escrito el codigo se aprueba
solo; uno que solo ve spec + diff, no.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (cubre_acs, get_feature, git, impl_path, load_backlog,  # noqa: E402
                   paths, review_path, sello_revision, sig_fresh, spec_acs,
                   spec_estado, spec_path)


def datos(a):
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, a.feature)
    sp = spec_path(p, f)
    if not sp.exists():
        sys.exit(f"[!!] no existe {sp}")
    return p, f, sp, sp.read_text(encoding="utf-8")


def cmd_resumen(a) -> None:
    p, f, sp, stext = datos(a)
    acs = spec_acs(stext)

    print(f"== Paquete de revision - Feature #{f['id']}: {f.get('name')} ==\n")
    print(f"Spec:  {sp.name}  [Estado: {spec_estado(stext)}]"
          f"{'' if sig_fresh(sp, f.get('last_spec_sig')) else '  <- SELLO INVALIDO'}")
    print(f"AC declarados ({len(acs)}): {', '.join(acs) or 'NINGUNO'}\n")

    for ac in acs:
        for ln in stext.splitlines():
            if ac in ln and ln.strip().startswith(("- " + ac, ac, "* " + ac)):
                print(f"   {ln.strip()[:160]}")
                break

    ip = impl_path(p, f)
    print(f"\nEvidencia: {ip.name if ip.exists() else 'AUSENTE'}")
    if ip.exists():
        cub, faltan = cubre_acs(ip.read_text(encoding="utf-8"), acs)
        print(f"   cubre: {', '.join(cub) or 'ninguno'}")
        if faltan:
            print(f"   FALTAN: {', '.join(faltan)}")

    rp = review_path(p, f)
    print(f"\nReview: {rp.name if rp.exists() else 'AUSENTE'}")
    if rp.exists():
        print(f"   sello actual: {sello_revision(rp.read_text(encoding='utf-8')) or 'sin sellar'}")

    wt = f.get("worktree") or str(p["root"])
    code, out = git(["diff", "--stat", "HEAD~1"], Path(wt))
    print(f"\nArchivos tocados (en {Path(wt).name}):")
    print("   " + ("\n   ".join(out.splitlines()[:25]) if code == 0 and out
                   else "(sin diff disponible)"))

    print("\n[i]  Esto es SOLO LECTURA. Delega el review a un subagente:")
    print(f"     revision.py --feature {f['id']} --briefing")
    print("     y sella su veredicto con:")
    print(f"     gate.py revision --feature {f['id']} --veredicto approved")


def cmd_briefing(a) -> None:
    """Contexto autocontenido para delegate_task: el subagente no sabe nada."""
    p, f, sp, stext = datos(a)
    acs = spec_acs(stext)
    wt = Path(f.get("worktree") or p["root"])
    ip = impl_path(p, f)
    rp = review_path(p, f)

    if "multi_repo" in f:
        from multirepo import Invalid, check_registered, git as repo_git
        import json
        try:
            manifest = check_registered(p, f, load_backlog(p)["rules"])
            parts = ["MAPA MULTI-REPO VALIDADO (fuente y tip destino):", json.dumps(manifest, indent=2),
                     "Revisa TODOS los repos y ambos SHAs; el recibo no prueba los AC."]
            for row in manifest["repos"]:
                parts.append(f"\n{row['microservicio']} — inventario base..fuente:")
                parts.append(repo_git(row["repo"], "diff", "--stat", "--no-ext-diff", "--no-textconv",
                                      row["base_sha"], row["source_sha"], "--"))
            diff = "\n".join(parts)
        except Invalid as exc:
            sys.exit(f"[!!] multi-repo: {exc}")
    else:
        code, diff = git(["diff", "HEAD~1"], wt)
        if code != 0 or not diff:
            code, diff = git(["diff", "HEAD"], wt)
        diff = diff[:60000]

    print("=" * 72)
    print("CONTEXTO PARA EL SUBAGENTE REVISOR (delegate_task.context | prompt de Task)")
    print("=" * 72)
    try:
        import contexto
        est = contexto.estado_contexto(p)
        if not est["fresco"]:
            print(f"[!] CONTEXTO VENCIDO ({', '.join(est['vencidas'])}): el brief de "
                  "abajo puede no reflejar el arbol actual. Refresca con "
                  "contexto.py refrescar antes de delegar.\n")
        contexto.cmd_brief(argparse.Namespace(
            feature=str(f["id"]), max_lineas=a.max_lineas_brief,
            max_archivos=10, max_lecciones=10))
        print()
    except Exception as exc:
        print(f"[!] sin brief de contexto ({exc}); el revisor arranca solo con spec + diff.\n")
    print(f"""
Eres el REVISOR de la feature #{f['id']} '{f.get('name')}' del proyecto
{load_backlog(p).get('project')}. No implementaste esto y no debes asumir que
esta bien. Responde SIEMPRE en espanol.

Tu trabajo: decidir si CADA criterio de aceptacion esta realmente cumplido en el
codigo, citando `archivo:linea`. No aceptes la palabra del implementer.

Raiz del proyecto: {p['root']}
Worktree de la feature: {'ver mapa multi-repo completo abajo' if 'multi_repo' in f else wt}

Criterios de aceptacion a verificar ({len(acs)}):""")
    for ac in acs:
        for ln in stext.splitlines():
            if ac in ln and ln.strip().startswith(("- " + ac, ac, "* " + ac)):
                print(f"  {ln.strip()}")
                break
        else:
            print(f"  {ac}")

    print(f"""
Archivos que debes leer tu mismo (no confies en este resumen):
  spec:      {sp}
  evidencia: {ip if ip.exists() else '(no existe: es un hallazgo)'}

Entregable: escribe {rp} con este formato exacto, una fila por CADA AC:

| AC | Veredicto | Cita |
|----|-----------|------|
| AC-1 | ok | ruta/archivo.ts:42 |

Veredictos validos por fila: ok / falla / no verificable.
Debajo de la tabla, una seccion '## Observaciones' con deuda o riesgos.

NO selles el archivo ni escribas una linea 'Revisado:'. El sello lo pone el
gate. Termina informando: veredicto global (approved / changes_requested /
blocked) y el motivo en una frase.

Reglas:
- Un AC sin cita `archivo:linea` NO es 'ok'.
- Si la evidencia cita una linea que no existe o no hace lo que dice, es 'falla'.
- No modifiques codigo. Solo lees y escribes {rp.name}.
""")
    print("-" * 72)
    print("DIFF DE LA FEATURE")
    print("-" * 72)
    print(diff if diff else "(sin diff disponible; el revisor debe leer los archivos)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feature", required=True)
    ap.add_argument("--briefing", action="store_true",
                    help="imprime el contexto para el subagente revisor")
    ap.add_argument("--max-lineas-brief", type=int, default=70,
                    dest="max_lineas_brief",
                    help="tope de lineas del brief de contexto dentro del briefing")
    a = ap.parse_args()
    (cmd_briefing if a.briefing else cmd_resumen)(a)


if __name__ == "__main__":
    main()
