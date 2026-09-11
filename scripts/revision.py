#!/usr/bin/env python3
"""Paquete de revision. NO sella nada: el sello lo pone
gate.py revision --veredicto.

  revision.py --feature <id>              resumen legible
  revision.py --feature <id> --briefing   contexto para delegar a un subagente

El review lo hace un SUBAGENTE en contexto aislado (delegate_task), que no vio
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

    code, diff = git(["diff", "HEAD~1"], wt)
    if code != 0 or not diff:
        code, diff = git(["diff", "HEAD"], wt)
    diff = diff[:60000]

    print("=" * 72)
    print("CONTEXTO PARA EL SUBAGENTE REVISOR (pegalo en delegate_task.context)")
    print("=" * 72)
    print(f"""
Eres el REVISOR de la feature #{f['id']} '{f.get('name')}' del proyecto
{load_backlog(p).get('project')}. No implementaste esto y no debes asumir que
esta bien. Responde SIEMPRE en espanol.

Tu trabajo: decidir si CADA criterio de aceptacion esta realmente cumplido en el
codigo, citando `archivo:linea`. No aceptes la palabra del implementer.

Raiz del proyecto: {p['root']}
Worktree de la feature: {wt}

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
                    help="imprime el contexto para delegate_task")
    a = ap.parse_args()
    (cmd_briefing if a.briefing else cmd_resumen)(a)


if __name__ == "__main__":
    main()
