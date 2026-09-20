#!/usr/bin/env python3
"""Rol producto: PRD inicial y SDD de arquitectura ANTES de las features.

  producto.py borrador --doc prd|sdd
  producto.py aprobar  --doc prd|sdd --yes [--por <quien>]
  producto.py estado

`docs/prd/**` es del USUARIO y ningun agente la escribe a mano. Por eso el rol
redacta en `docs/borrador-<doc>.md` (ruta sin proteger) y solo `aprobar --yes`,
tras el SI explicito del usuario en el chat, copia ese cuerpo a su destino
(`docs/prd/PRD-master.md` o `docs/sdd.md`), conserva el bloque generado que
mantiene documentacion.py y deja el sello en `documentos.<doc>` del backlog.
`gate.py check` reconoce ese sello hasta que el usuario commitea el PRD.

No escribe prosa de producto por el usuario: valida que el borrador este
completo y ejecuta el ritual. Funciona igual en Hermes, Claude Code y Codex
porque solo depende del arbol del proyecto.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import bitacora, load_backlog, now_iso, paths, save_backlog  # noqa: E402

TEMPLATES = Path(__file__).parent.parent / "templates"
ABIERTOS = ("todo", "pending", "in_progress", "blocked", "review")

DOCS = {
    "prd": {
        "titulo": "PRD maestro",
        "borrador": "borrador-prd.md",
        "destino": ("prd", "PRD-master.md"),
        "plantilla": "prd.md",
        # El orden de "Escribe tu maldito PRD": historia, objetivos con nombre,
        # flujo hoy/despues, datos, pseudo-codigo. Nunca codigo final.
        "secciones": ("Resumen", "La historia", "Objetivos y no-objetivos",
                      "Como funciona hoy y como va a funcionar", "Los datos",
                      "Pseudo-codigo: el acuerdo", "Features candidatas"),
    },
    "sdd": {
        "titulo": "SDD",
        "borrador": "borrador-sdd.md",
        "destino": ("sdd.md",),
        "plantilla": "sdd.md",
        "secciones": ("Contexto", "Componentes", "Datos e integraciones", "Decisiones", "Riesgos"),
    },
}

# `- F-1: nombre: resultado` -> (1, "nombre"). Todo en UNA linea, como los AC.
CANDIDATA_RE = re.compile(r"^[^\S\n]*[-*][^\S\n]*F-(\d+)[^\S\n]*:[^\S\n]*([^:\n]+?)[^\S\n]*(?::|$)", re.M)
COMENTARIO_RE = re.compile(r"<!--.*?-->", re.S)
ESTADO_RE = re.compile(r"^Estado:[^\S\n]*(\S+)", re.M)
ALCANCE_RE = re.compile(r"^Alcance:[^\S\n]*(\S.*)?$", re.M)
# `- O1: ...` / `- NO1: ...` (tambien O-1 / NO-1): objetivos con nombre, para citarlos.
OBJETIVO_RE = re.compile(r"^[^\S\n]*[-*][^\S\n]*O-?\d+[^\S\n]*:", re.M)
NO_OBJETIVO_RE = re.compile(r"^[^\S\n]*[-*][^\S\n]*NO-?\d+[^\S\n]*:", re.M)
# Un bloque ```<lenguaje> es codigo final: el PRD lleva pseudo-codigo.
FENCE_RE = re.compile(r"^[^\S\n]*```[^\S\n]*([A-Za-z][A-Za-z0-9_+#.-]*)", re.M)
PSEUDO = frozenset({"text", "txt", "pseudo", "pseudocodigo", "pseudocode", "md", "markdown", "plain"})
# Secciones que se cuentan en dos tiempos: cada etiqueta con contenido propio.
ETIQUETAS = {"Resumen": ("Hoy", "Despues"), "La historia": ("Antes", "Despues")}


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def borrador_path(p: dict, doc: str) -> Path:
    return p["docs"] / DOCS[doc]["borrador"]


def destino_path(p: dict, doc: str) -> Path:
    return p["docs"].joinpath(*DOCS[doc]["destino"])


def _prefijo_generador(titulo: str) -> bytes:
    # El mismo encabezado que documentacion.py inventa cuando no hay cuerpo manual.
    return f"# {titulo}\n\nContenido manual arriba; harness-flow mantiene solo el bloque generado.\n\n".encode()


def cuerpo_manual(destino: Path, titulo: str) -> bytes | None:
    """Cuerpo manual del destino (todo menos el bloque generado); None si no hay uno del usuario.

    Sube ValueError si los marcadores estan malformados: no se adivina.
    """
    from bloques import parts
    if not destino.is_file():
        return None
    previo = destino.read_bytes()
    partes = parts(previo)
    manual = previo if partes is None else partes[0]
    if not manual.strip() or manual == _prefijo_generador(titulo):
        return None
    return manual


def secciones(text: str) -> dict[str, str]:
    """Cuerpo de cada seccion `## X`, ya sin las guias `<!-- -->`."""
    out: dict[str, str] = {}
    actual = None
    for linea in COMENTARIO_RE.sub("", text).splitlines():
        m = re.match(r"^##[^\S\n]+(.+?)[^\S\n]*$", linea)
        if m:
            actual = m.group(1)
            out[actual] = ""
        elif actual is not None:
            out[actual] += linea + "\n"
    return out


def candidatas(text: str) -> list[tuple[str, str]]:
    return [(n, nombre.strip()) for n, nombre in CANDIDATA_RE.findall(COMENTARIO_RE.sub("", text))]


def _etiqueta_con_contenido(seccion: str, etiqueta: str) -> bool:
    """`Hoy: texto` en la linea, o `Hoy:` y el parrafo debajo (hasta el blanco o la otra etiqueta)."""
    pat = re.compile(rf"^[^\S\n]*[*_]{{0,2}}{etiqueta}[*_]{{0,2}}[^\S\n]*:[^\S\n]*(.*)$", re.M | re.I)
    m = pat.search(seccion.replace("é", "e"))
    if not m:
        return False
    if m.group(1).strip():
        return True
    resto = seccion.replace("é", "e")[m.end():].splitlines()
    for linea in resto:
        if not linea.strip():
            return False
        if re.match(r"^[^\S\n]*[*_]{0,2}[A-Za-z]+[*_]{0,2}[^\S\n]*:", linea):
            return False
        return True
    return False


def validar(text: str, doc: str) -> list[str]:
    """Que le falta al borrador para poder aprobarse. Vacio = aprobable.

    Mide estructura, no calidad: que cada parte del PRD exista con contenido
    propio y que no traiga codigo final. Si la historia convence es del usuario
    decidirlo en el ritual; aqui solo se garantiza que haya una.
    """
    problemas = []
    if "harness-flow:features" in text:
        problemas.append("trae el bloque generado harness-flow:features: quitalo, lo mantiene documentacion.py sync")
    if not text.lstrip().startswith("# "):
        problemas.append("falta el titulo '# ...' en la primera linea")
    if not ESTADO_RE.search(text):
        problemas.append("falta la linea 'Estado: draft'")
    limpio = COMENTARIO_RE.sub("", text)
    secs = secciones(text)
    for nombre in DOCS[doc]["secciones"]:
        if nombre not in secs:
            problemas.append(f"falta la seccion '## {nombre}'")
        elif not secs[nombre].strip():
            problemas.append(f"la seccion '## {nombre}' esta vacia (solo guia)")
    if doc == "prd":
        m = ALCANCE_RE.search(limpio)
        if not m or not (m.group(1) or "").strip():
            problemas.append("falta 'Alcance:' en el encabezado (una linea: que toca y que NO toca)")
        for nombre, etiquetas in ETIQUETAS.items():
            if nombre in secs and secs[nombre].strip():
                faltan = [e for e in etiquetas if not _etiqueta_con_contenido(secs[nombre], e)]
                if faltan:
                    problemas.append(f"'## {nombre}' necesita {' y '.join(repr(e + ':') for e in etiquetas)} "
                                     f"con contenido (falta {', '.join(faltan)})")
        obj = secs.get("Objetivos y no-objetivos", "")
        if obj.strip():
            if not OBJETIVO_RE.search(obj):
                problemas.append("'## Objetivos y no-objetivos' no declara ningun '- O1: ...' (con nombre, para citarlo)")
            if not NO_OBJETIVO_RE.search(obj):
                problemas.append("'## Objetivos y no-objetivos' no declara ningun '- NO1: ...' (frenan el 'ya que estamos')")
        if "Features candidatas" in secs and not candidatas(secs["Features candidatas"]):
            problemas.append("'## Features candidatas' no declara ninguna '- F-n: nombre: resultado'")
        lenguajes = sorted({m.group(1).lower() for m in FENCE_RE.finditer(limpio)} - PSEUDO)
        if lenguajes:
            problemas.append("trae codigo final (bloque " + ", ".join(f"```{x}" for x in lenguajes)
                             + "): el PRD lleva pseudo-codigo; el codigo se escribe despues, en otra parte")
    return problemas


def sellar(text: str, quien: str, cuando: str) -> str:
    sello = f"Aprobado: {quien} · {cuando} · sellado por producto.py aprobar --yes"
    if ESTADO_RE.search(text):
        text = re.sub(r"^Estado:.*$", "Estado: approved", text, count=1, flags=re.M)
    else:
        text = text.replace("\n", "\n\nEstado: approved\n", 1)
    if re.search(r"^Aprobado:.*$", text, re.M):
        text = re.sub(r"^Aprobado:.*$", lambda _: sello, text, count=1, flags=re.M)
    else:
        text = re.sub(r"^(Estado: approved)$", lambda m: m.group(1) + "\n" + sello, text, count=1, flags=re.M)
    return text


def _en_draft(text: str) -> str:
    """Un cuerpo ya aprobado vuelve a draft al reabrirlo como borrador."""
    text = re.sub(r"^Aprobado:.*\n?", "", text, count=1, flags=re.M)
    if ESTADO_RE.search(text):
        return re.sub(r"^Estado:.*$", "Estado: draft", text, count=1, flags=re.M)
    return text.replace("\n", "\n\nEstado: draft\n", 1)


def componer(destino: Path, cuerpo: str) -> bytes:
    """Cuerpo aprobado + el bloque generado que ya tuviera el destino (bytes exactos)."""
    from bloques import END, START, parts
    manual = cuerpo.encode("utf-8")
    if not manual.endswith(b"\n"):
        manual += b"\n"
    if not destino.is_file():
        return manual
    previo = destino.read_bytes()
    partes = parts(previo)  # ValueError con marcadores malformados: no se pisa a ciegas
    if partes is None:
        return manual
    generado = previo.split(START, 1)[1].split(END, 1)[0]
    return manual + b"\n" + START + generado + END + partes[1]


def estado_documentos(p: dict, data: dict) -> dict[str, str]:
    """Una linea por documento para estado.py; nunca escribe nada."""
    from bloques import compatible, fingerprint
    out = {}
    for doc, cfg in DOCS.items():
        borrador, destino = borrador_path(p, doc), destino_path(p, doc)
        sello = (data.get("documentos") or {}).get(doc) or {}
        if sello:
            try:
                vigente = destino.is_file() and compatible(sello.get("fingerprint"), fingerprint(destino.read_bytes()))
            except ValueError:
                vigente = False
            quien = f"aprobado por {sello.get('aprobado_por')} · {sello.get('aprobado_at')}"
            if not vigente:
                out[doc] = f"{quien}; {_rel(p['root'], destino)} cambio despues del sello"
            elif borrador.is_file() and hashlib.sha256(borrador.read_bytes()).hexdigest() != sello.get("borrador_sha256"):
                out[doc] = f"{quien}; borrador cambiado despues (re-aprobar)"
            else:
                out[doc] = quien
        elif borrador.is_file():
            out[doc] = f"borrador sin aprobar ({_rel(p['root'], borrador)})"
        else:
            try:
                manual = cuerpo_manual(destino, cfg["titulo"])
            except ValueError:
                manual = b"marcadores malformados"
            out[doc] = (f"manual del usuario sin sello ({_rel(p['root'], destino)})" if manual
                        else f"sin documento (producto.py borrador --doc {doc})")
    return out


# --- comandos --------------------------------------------------------------

def cmd_borrador(args) -> None:
    p = paths()
    data = load_backlog(p)
    doc, cfg = args.doc, DOCS[args.doc]
    borrador, destino = borrador_path(p, doc), destino_path(p, doc)
    if borrador.exists():
        print(f"[i]  {_rel(p['root'], borrador)} ya existe, no se toca")
    else:
        try:
            manual = cuerpo_manual(destino, cfg["titulo"])
        except ValueError as exc:
            sys.exit(f"[!!] {_rel(p['root'], destino)}: {exc}")
        if manual is not None:
            try:
                cuerpo = _en_draft(manual.decode("utf-8"))
            except UnicodeDecodeError:
                sys.exit(f"[!!] {_rel(p['root'], destino)} no es UTF-8: reabrilo a mano como borrador")
            origen = f"cuerpo manual de {_rel(p['root'], destino)}"
        else:
            proyecto = data.get("project") or p["root"].name
            cuerpo = ((TEMPLATES / cfg["plantilla"]).read_text(encoding="utf-8")
                      .replace("{{PROYECTO}}", proyecto)
                      .replace("{{DUENO}}", getpass.getuser())
                      .replace("{{FECHA}}", now_iso()[:10]))
            origen = f"templates/{cfg['plantilla']}"
        borrador.parent.mkdir(parents=True, exist_ok=True)
        borrador.write_text(cuerpo, encoding="utf-8")
        bitacora(p, f"borrador de {cfg['titulo']} creado desde {origen}")
        print(f"[ok] borrador de {cfg['titulo']}: {_rel(p['root'], borrador)} (desde {origen})")
    print("[i]  rellena cada seccion (las guias <!-- --> se reemplazan o se borran),")
    print("     MUESTRASELO al usuario y solo con su SI corre:")
    print(f"     producto.py aprobar --doc {doc} --yes")


def cmd_aprobar(args) -> None:
    if not args.yes:
        sys.exit("[!!] aprobar requiere --yes.\n"
                 "     Ningun agente aprueba por su cuenta: MUESTRALE el borrador al\n"
                 "     usuario, PREGUNTALE si lo aprueba, y solo con su SI corre\n"
                 "     este comando con --yes.")
    p = paths()
    data = load_backlog(p)
    doc, cfg = args.doc, DOCS[args.doc]
    borrador, destino = borrador_path(p, doc), destino_path(p, doc)
    if not borrador.is_file():
        sys.exit(f"[!!] no existe {_rel(p['root'], borrador)}: producto.py borrador --doc {doc} lo crea.")
    text = borrador.read_text(encoding="utf-8")
    problemas = validar(text, doc)
    if problemas:
        sys.exit(f"[!!] el borrador de {cfg['titulo']} no se puede aprobar:\n     - " + "\n     - ".join(problemas))
    if doc == "prd":
        # El registro multi-repo fijo los bytes manuales del PRD y su contrato
        # dice que nada los reautoriza (ni re-registrar). Aprobar aqui dejaria
        # esas features sin cierre posible: mejor negarse antes de escribir.
        registradas = [f for f in data["features"]
                       if f.get("status") in ABIERTOS and f.get("multi_repo_protected")]
        if registradas:
            ids = ", ".join(f"#{f['id']}" for f in registradas)
            sys.exit(f"[!!] hay features multi-repo registradas abiertas ({ids}): su registro fijo\n"
                     "     los bytes manuales del PRD y el sello NO lo reautoriza. Cierralas antes,\n"
                     "     o aprueba el PRD antes de registrar.")

    quien = args.por or getpass.getuser()
    cuando = now_iso()
    sellado = sellar(text, quien, cuando)
    try:
        nuevo = componer(destino, sellado)
    except ValueError as exc:
        sys.exit(f"[!!] {_rel(p['root'], destino)}: {exc}; no se sobreescribe a ciegas.")

    from bloques import fingerprint
    from cierre_local import transaction
    with transaction(p, f"producto-{doc}"):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(nuevo)
        data.setdefault("documentos", {})[doc] = {
            "aprobado_por": quien,
            "aprobado_at": cuando,
            "origen": _rel(p["root"], borrador),
            "destino": _rel(p["root"], destino),
            "fingerprint": fingerprint(nuevo),
            "borrador_sha256": hashlib.sha256(sellado.encode("utf-8")).hexdigest(),
        }
        save_backlog(p, data)
        bitacora(p, f"{cfg['titulo']} aprobado por {quien} -> {_rel(p['root'], destino)}")
        # Ultimo: si esto falla, el rollback deja el resto como estaba y el
        # borrador sigue en draft, que es el estado coherente con "no aprobado".
        borrador.write_text(sellado, encoding="utf-8")

    print(f"[ok] {cfg['titulo']} aprobado y sellado por {quien}: {_rel(p['root'], destino)}")
    if doc == "prd":
        print("[i]  gate.py check acepta ese cuerpo por el sello; commitea docs/prd/PRD-master.md")
        print("     cuando corresponda (es del usuario, el agente no lo commitea).")
        cands = candidatas(secciones(sellado).get("Features candidatas", ""))
        if cands:
            print("[i]  features candidatas para el backlog:")
            for _, nombre in cands:
                print(f'     add.py --name "{nombre}" --prd docs/prd/PRD-master.md')
    else:
        print("[i]  documentacion.py sync seguira agregando el bloque por feature debajo del cuerpo.")


def cmd_estado(args) -> None:
    p = paths()
    data = load_backlog(p)
    for doc, texto in estado_documentos(p, data).items():
        print(f"   {doc}:   {texto}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Rol producto: PRD inicial y SDD de arquitectura")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("borrador"); s.add_argument("--doc", required=True, choices=sorted(DOCS))
    s.set_defaults(fn=cmd_borrador)
    s = sub.add_parser("aprobar"); s.add_argument("--doc", required=True, choices=sorted(DOCS))
    s.add_argument("--yes", action="store_true"); s.add_argument("--por")
    s.set_defaults(fn=cmd_aprobar)
    sub.add_parser("estado").set_defaults(fn=cmd_estado)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
