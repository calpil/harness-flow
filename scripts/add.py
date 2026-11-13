#!/usr/bin/env python3
"""Alta de feature en el backlog y creacion del spec en draft.

  add.py --name "cobro idempotente" [--kind bug|task|normalizacion] [--microservicio a --microservicio b]
         [--prd docs/prd/PRD-master.md] [--candidata F-1] [--requiere F-1]
         [--yes --peso "<por que es ficha y no enmienda>"]

Una ficha nueva es decision del usuario. Entra sin --yes solo lo que el ya
decidio: la primera ficha de una candidata F-n del PRD aprobado y una
normalizacion con el trinquete adoptado. Todo lo demas exige --yes y --peso, y
un hallazgo no abre ficha: va a una feature abierta (hallazgo.py, enmienda).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (bitacora, load_backlog, now_iso, paths, requiere_declarados,  # noqa: E402
                   save_backlog, slugify, spec_path)

TEMPLATE = Path(__file__).parent.parent / "templates" / "spec.md"


def plantilla() -> str:
    """El bloque ```markdown de templates/spec.md; el resto del archivo es la guia del formato."""
    m = re.search(r"^```markdown\n(.*?)^```[^\S\n]*$", TEMPLATE.read_text(encoding="utf-8"), re.M | re.S)
    if m is None:
        sys.exit(f"[!!] {TEMPLATE} no trae el bloque ```markdown del spec")
    return m.group(1)


def _ya_decidida(p: dict, a, candidata_cubierta: bool) -> bool:
    """El usuario ya decidio esta ficha: aprobo la candidata en el PRD o adopto el trinquete."""
    if a.candidata and not candidata_cubierta:
        return True
    if a.kind == "normalizacion":
        import arquitectura
        return bool(arquitectura.modo_trinquete(p))
    return False


def _negar_sin_si(data: dict, a) -> None:
    """Sin el SI del usuario no hay ficha: dice a donde va un hallazgo y donde cabe."""
    import hallazgo
    import normas
    L = ["[!!] add.py requiere --yes: una ficha nueva la decide el usuario.",
         "     Cada ficha paga spec, lista de tests, review, verify y cierre. Un hallazgo del",
         "     codigo NO abre ficha. Va, en este orden:",
         "     1. A la feature en curso que toca ese codigo: arreglalo en su rama. Si cambia un AC",
         "        es una enmienda (templates/enmienda.md, gate.py enmienda); si no, citalo en la evidencia.",
         "     2. A otra feature abierta que lo cubre:",
         "        " + normas.comando("hallazgo.py", "anotar", "--feature", "<id>", "--texto", "<hallazgo>"),
         "     3. Al proyecto, si ninguna lo cubre (mismo comando sin --feature).",
         "     Ficha nueva solo si tiene peso propio: un comportamiento nuevo que ve el usuario, o",
         "     un riesgo de plata, datos o seguridad que no espera a otra feature.",
         "     Si le preguntas al usuario, la primera opcion es el destino sin ficha (enmienda o",
         "     anotar); la ficha es otra opcion y no la recomendada si cabe en una feature abierta.",
         "     Solo con su SI repite con --yes --peso '<por que es ficha y no enmienda>'."]
    donde = hallazgo.features_donde_cabe(data, a.microservicio,
                                         requiere_declarados({"requiere": a.requiere}))
    if donde:
        L.append("     Features abiertas donde puede caber:")
        L += [f"       #{f['id']} [{f.get('status')}] {f.get('name')}" for f in donde]
    sys.exit("\n".join(L))


def _peso(valor: str | None) -> str:
    """Por que esta ficha no cabe como enmienda. Queda escrito en el backlog."""
    limpio = (valor or "").strip()
    if len(limpio) < 15 or any(c in limpio for c in "\n\r\x85\u2028\u2029"):
        sys.exit("[!!] --yes va con --peso '<por que es ficha y no enmienda>': una linea que diga el\n"
                 "     comportamiento nuevo o el riesgo que la justifica, o que el usuario la pidio.\n"
                 "     Queda escrito en el backlog. Si no sabes que poner, no es una ficha:\n"
                 "     hallazgo.py anotar.")
    return limpio


def main() -> None:
    import producto
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--kind", choices=["feature", "bug", "task", "normalizacion"], default="feature")
    ap.add_argument("--microservicio", action="append", default=[])
    ap.add_argument("--prd")
    ap.add_argument("--candidata", help="la F-n de '## Features candidatas' del PRD que origina la feature")
    ap.add_argument("--requiere", action="append", default=[],
                    help="vertical slice del que depende (p.ej. F-1 o #1; repetible)")
    ap.add_argument("--acceptance", action="append", default=[])
    ap.add_argument("--yes", action="store_true",
                    help="el usuario pidio o aprobo esta ficha (no hace falta para la primera ficha "
                         "de una candidata F-n ni para una normalizacion con el trinquete adoptado)")
    ap.add_argument("--peso", help="con --yes: por que es una ficha y no una enmienda de una feature abierta")
    a = ap.parse_args()

    p = paths()
    data = load_backlog(p)
    slug = slugify(a.name)
    for f in data["features"]:
        if slugify(f.get("name", "")) == slug and f.get("status") not in ("done", "superseded"):
            sys.exit(f"[!!] ya existe la feature #{f['id']} '{f['name']}' abierta con el mismo nombre.")

    prd = a.prd or "docs/prd/PRD-master.md"
    if a.prd and a.prd.replace("\\", "/").removeprefix("./") != "docs/prd/PRD-master.md":
        sys.exit("[!!] --prd solo puede ser docs/prd/PRD-master.md: es el unico cuerpo que sella "
                 "producto.py aprobar. Una candidata F-n no es otro archivo; su historia la cuenta el spec.")
    linea = None
    deps_prd: list[str] = []
    candidata_cubierta = False
    if a.candidata:
        if not re.fullmatch(r"F-\d+", a.candidata):
            sys.exit(f"[!!] --candidata {a.candidata!r}: usa el id del PRD, por ejemplo F-1")
        texto = producto.texto_manual(p["root"] / prd)
        if texto is None:
            sys.exit(f"[!!] --candidata {a.candidata} sin PRD con cuerpo en {prd}: el rol producto va antes")
        linea = producto.candidata(texto, a.candidata)
        if linea is None:
            sys.exit(f"[!!] {a.candidata} no esta en '## Features candidatas' de {prd}")
        deps_prd = producto.candidatas_dependencias(
            producto.seccion(texto, "Features candidatas") or ""
        ).get(a.candidata, [])
        otras = [x for x in data["features"]
                 if x.get("prd_candidata") == a.candidata and x.get("status") != "superseded"]
        candidata_cubierta = bool(otras)
        if otras:
            print(f"[i]  {a.candidata} ya la cubre " + ", ".join(f"#{x['id']}" for x in otras)
                  + ": esta feature sera otra parte de la misma candidata")

    decidida = _ya_decidida(p, a, candidata_cubierta)
    if not a.yes and not decidida:
        _negar_sin_si(data, a)
    peso = None if decidida and not a.peso else _peso(a.peso)

    fid = max([int(f["id"]) for f in data["features"]] or [0]) + 1
    reqs = requiere_declarados({"requiere": [*deps_prd, *a.requiere]})
    for r in reqs:
        if not re.fullmatch(r"(?:#\d+|F-\d+)", r):
            sys.exit(f"[!!] --requiere {r!r} invalido: usa F-n (candidata del PRD) o #<id> (feature del backlog)")
        if r == f"#{fid}" or (a.candidata and r == a.candidata):
            sys.exit(f"[!!] la feature #{fid} ({a.candidata or a.name}) no puede depender de si misma ({r})")
    f = {"id": fid, "name": a.name, "kind": a.kind,
         "microservicios": a.microservicio, "acceptance": a.acceptance,
         "status": "todo", "created_at": now_iso()}
    if a.prd or a.candidata:
        f["prd"] = prd
    if a.candidata:
        f["prd_candidata"] = a.candidata
    if reqs:
        f["requiere"] = reqs
    if peso:
        f["peso"] = peso
    data["features"].append(f)
    save_backlog(p, data)

    sp = spec_path(p, f)
    if not sp.exists():
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(plantilla().replace("{{ID}}", str(fid)).replace("{{NAME}}", a.name)
                      .replace("{{PRD}}", prd)
                      .replace("{{CANDIDATA}}", linea or "ninguna declarada"),
                      encoding="utf-8")
    bitacora(p, f"add #{fid} '{a.name}' ({a.kind})"
             + (f" candidata {a.candidata}" if a.candidata else ""))
    print(f"[ok] feature #{fid} agregada")
    if reqs:
        print(f"[i]  requiere: {', '.join(reqs)}")
    print(f"[ok] spec en draft: {sp}")
    try:
        import gate
        pendientes = [] if a.kind not in producto.TIPOS_EXIGIDOS else [
            f"{doc}: {m}" for doc in producto.requeridos(data["rules"])
            if (m := gate.motivo_doc(p, data, doc))]
    except ValueError as exc:
        pendientes = [str(exc)]
    if pendientes:
        print("[!]  approve-spec se va a negar (require_docs_al_dia): " + "; ".join(pendientes))
        print("     el rol producto va antes: producto.py borrador --doc prd|sdd")
    print("[i]  completa la historia y los AC-n, cita los O-n del PRD y las D-n del SDD,")
    print(f"     MUESTRASELO al usuario y solo con su SI corre: gate.py approve-spec --feature {fid} --yes")


if __name__ == "__main__":
    main()
