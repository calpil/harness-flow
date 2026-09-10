#!/usr/bin/env python3
"""Paquete de revision (SOLO LECTURA). No sella nada: el sello lo pone
gate.py revision --veredicto.

  revision.py --feature <id>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (cubre_acs, get_feature, git, impl_path, load_backlog,  # noqa: E402
                   paths, review_path, sello_revision, sig_fresh, spec_acs,
                   spec_estado, spec_path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feature", required=True)
    a = ap.parse_args()
    p = paths(); data = load_backlog(p); f = get_feature(data, a.feature)
    sp = spec_path(p, f)
    if not sp.exists():
        sys.exit(f"[!!] no existe {sp}")
    stext = sp.read_text(encoding="utf-8")
    acs = spec_acs(stext)

    print(f"== Paquete de revision - Feature #{f['id']}: {f.get('name')} ==\n")
    print(f"Spec:  {sp.name}  [Estado: {spec_estado(stext)}]"
          f"{'' if sig_fresh(sp, f.get('last_spec_sig')) else '  <- SELLO INVALIDO'}")
    print(f"AC declarados ({len(acs)}): {', '.join(acs) or 'NINGUNO'}\n")

    for ac in acs:
        for ln in stext.splitlines():
            if ln.strip().startswith(("- " + ac, ac)) and ac in ln:
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
    print("   " + ("\n   ".join(out.splitlines()[:25]) if code == 0 and out else "(sin diff disponible)"))

    print("\n[i]  Esto es SOLO LECTURA. Escribe docs/review-<id>.md con una fila por")
    print("     cada AC-n citando archivo:linea, y despues sella con:")
    print(f"     gate.py revision --feature {f['id']} --veredicto approved")


if __name__ == "__main__":
    main()
