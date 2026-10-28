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
import unicodedata
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
TIPOS_EXIGIDOS = ("feature",)  # kind: bug y task no nacen de un PRD

# `- F-1: nombre: resultado` -> (1, "nombre"). Todo en UNA linea, como los AC.
CANDIDATA_RE = re.compile(r"^[^\S\n]*[-*][^\S\n]*F-(\d+)[^\S\n]*:[^\S\n]*([^:\n]+?)[^\S\n]*(?::|$)", re.M)
COMENTARIO_RE = re.compile(r"<!--.*?-->", re.S)
ESTADO_RE = re.compile(r"^Estado:[^\S\n]*(\S+)", re.M)
ALCANCE_RE = re.compile(r"^Alcance:[^\S\n]*(\S.*)?$", re.M)
# `- O1: ...` / `- NO1: ...` (tambien O-1 / NO-1): objetivos con nombre, para citarlos.
OBJETIVO_RE = re.compile(r"^[^\S\n]*[-*][^\S\n]*(O-?\d+)[^\S\n]*:", re.M)
NO_OBJETIVO_RE = re.compile(r"^[^\S\n]*[-*][^\S\n]*(NO-?\d+)[^\S\n]*:", re.M)
# `- D1: ...` en las Decisiones del SDD: con nombre, para que el spec las cite.
DECISION_RE = re.compile(r"^[^\S\n]*[-*][^\S\n]*(D-?\d+)[^\S\n]*:", re.M)
# Una cita en el spec: `O1` suelto, no `NO1`, `IO1` ni `AC-O1`.
CITA_OBJETIVO_RE = re.compile(r"(?<![\w-])(O-?\d+)(?![\w-])")
CITA_DECISION_RE = re.compile(r"(?<![\w-])(D-?\d+)(?![\w-])")
SIN_CITA_RE = re.compile(r"(cumple|decisiones que aplica)[^\S\n]*:[^\S\n]*ningun", re.I)
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


def plegar(texto: str) -> str:
    """Sin tildes y en minusculas: 'Pseudo-código' y 'PSEUDO-CODIGO' son el mismo titulo."""
    nfd = unicodedata.normalize("NFD", texto)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").casefold()


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


def seccion(text: str, nombre: str) -> str | None:
    """Cuerpo de `## nombre`, aunque el titulo traiga tildes o mayusculas. None si no esta."""
    clave = plegar(nombre)
    for titulo, cuerpo in secciones(text).items():
        if plegar(titulo) == clave:
            return cuerpo
    return None


def candidatas(text: str) -> list[tuple[str, str]]:
    return [(n, nombre.strip()) for n, nombre in CANDIDATA_RE.findall(COMENTARIO_RE.sub("", text))]


REQUIERE_CANDIDATA_RE = re.compile(
    r"(?:requiere|requires|bloquead[ao]\s+por)\s*:\s*([Ff]-\d+(?:\s*[,;y]\s*[Ff]-\d+)*)",
    re.I,
)
_CAPA_HORIZONTAL_RE = re.compile(
    r"\b(?:crear\s+tabla\w*|esquema\s+(?:sql|db|base\s+de\s+datos)|migraci[oó]n(?:es)?\s+(?:sql|db|inicial\w*)"
    r"|configurar\s+(?:orm|base\s+de\s+datos|db)|capa\s+de\s+(?:repositorio|datos|persistencia)"
    r"|solo\s+(?:backend|frontend|base\s+de\s+datos|api|ui)|como\s+(?:desarrollador|sistema))\b",
    re.I,
)


def candidatas_dependencias(text: str) -> dict[str, list[str]]:
    """Mapa F-n -> [F-m, ...] declaradas con 'requiere: F-m' en las lineas de Features candidatas."""
    out: dict[str, list[str]] = {}
    for linea in COMENTARIO_RE.sub("", text).splitlines():
        m = CANDIDATA_RE.match(linea)
        if not m:
            continue
        fid = f"F-{m.group(1)}"
        deps: list[str] = []
        for rm in REQUIERE_CANDIDATA_RE.finditer(linea):
            for tok in re.findall(r"[Ff]-\d+", rm.group(1)):
                norm = f"F-{tok.split('-', 1)[1]}"
                if norm not in deps:
                    deps.append(norm)
        if deps:
            out[fid] = deps
    return out


def _problemas_dependencias_candidatas(feats_txt: str) -> list[str]:
    declaradas = {f"F-{n}" for n, _ in candidatas(feats_txt)}
    deps = candidatas_dependencias(feats_txt)
    problemas: list[str] = []
    for fid, reqs in deps.items():
        for r in reqs:
            if r == fid:
                problemas.append(f"'## Features candidatas': {fid} no puede depender de si misma (requiere: {r})")
            elif r not in declaradas:
                problemas.append(f"'## Features candidatas': {fid} requiere {r}, que no existe en la lista")
    # Deteccion de ciclos simples
    visitados: dict[str, int] = {}  # 0=visiting, 1=done

    def dfs(nodo: str, camino: list[str]) -> None:
        estado = visitados.get(nodo)
        if estado == 0:
            ciclo = " -> ".join(camino[camino.index(nodo):] + [nodo])
            msg = f"'## Features candidatas' tiene un ciclo de dependencias: {ciclo}"
            if msg not in problemas:
                problemas.append(msg)
            return
        if estado == 1:
            return
        visitados[nodo] = 0
        for sig in deps.get(nodo, []):
            if sig in declaradas and sig != nodo:
                dfs(sig, camino + [sig])
        visitados[nodo] = 1

    for fid in declaradas:
        if fid not in visitados:
            dfs(fid, [fid])
    return problemas


def avisos_vertical_prd(text: str, max_candidatas: int = 15) -> list[str]:
    """Avisos (no bloqueantes) cuando una candidata parece capa horizontal, historia tecnica o excede el tope."""
    sec = COMENTARIO_RE.sub("", seccion(text, "Features candidatas") or "")
    avisos: list[str] = []
    cands = candidatas(sec)
    if max_candidatas > 0 and len(cands) > max_candidatas:
        avisos.append(
            f"vertical-slice: el PRD declara {len(cands)} candidatas (recomendado <= {max_candidatas}); "
            "prefiere empezar con 10-15 historias verticales e ir agregando despues"
        )
    for linea in sec.splitlines():
        m = CANDIDATA_RE.match(linea)
        if not m:
            continue
        fid = f"F-{m.group(1)}"
        if _CAPA_HORIZONTAL_RE.search(linea):
            avisos.append(
                f"vertical-slice: {fid} ('{m.group(2).strip()}') parece cortada por capa tecnica "
                "o actor de sistema; cada F-n debe atravesar las capas y dar valor observable al usuario"
            )
    return avisos


def _etiqueta_con_contenido(seccion: str, etiqueta: str) -> bool:
    """`Hoy: texto` en la linea, o `Hoy:` y el parrafo debajo (hasta el blanco o la otra etiqueta)."""
    pat = re.compile(rf"^[^\S\n]*[*_]{{0,2}}{etiqueta}[*_]{{0,2}}[^\S\n]*:[^\S\n]*(.*)$", re.M | re.I)
    plano = plegar(seccion)
    m = pat.search(plano)
    if not m:
        return False
    if m.group(1).strip():
        return True
    resto = plano[m.end():].splitlines()
    for linea in resto:
        if not linea.strip():
            return False
        if re.match(r"^[^\S\n]*[*_]{0,2}[A-Za-z]+[*_]{0,2}[^\S\n]*:", linea):
            return False
        return True
    return False


def _decisiones_sin_alternativa(seccion_txt: str) -> list[str]:
    """Ids D-n cuyo bloque no nombra una opcion descartada. Estructura, no calidad."""
    bloques: list[tuple[str, list[str]]] = []
    actual = None
    lineas: list[str] = []
    for linea in seccion_txt.splitlines():
        m = DECISION_RE.match(linea)
        if m:
            if actual:
                bloques.append((actual, lineas))
            actual = m.group(1).replace("-", "")
            lineas = [linea]
        elif actual:
            lineas.append(linea)
    if actual:
        bloques.append((actual, lineas))
    marca = re.compile(r"descartad\w*[^\S\n]*:[^\S\n]*\S")
    return [did for did, ls in bloques if not marca.search(plegar("\n".join(ls)))]


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
    for nombre in DOCS[doc]["secciones"]:
        cuerpo = seccion(text, nombre)
        if cuerpo is None:
            problemas.append(f"falta la seccion '## {nombre}'")
        elif not cuerpo.strip():
            problemas.append(f"la seccion '## {nombre}' esta vacia (solo guia)")
    if doc == "prd":
        m = ALCANCE_RE.search(limpio)
        if not m or not (m.group(1) or "").strip():
            problemas.append("falta 'Alcance:' en el encabezado (una linea: que toca y que NO toca)")
        for nombre, etiquetas in ETIQUETAS.items():
            cuerpo = seccion(text, nombre)
            if cuerpo and cuerpo.strip():
                faltan = [e for e in etiquetas if not _etiqueta_con_contenido(cuerpo, e)]
                if faltan:
                    problemas.append(f"'## {nombre}' necesita {' y '.join(repr(e + ':') for e in etiquetas)} "
                                     f"con contenido (falta {', '.join(faltan)})")
        obj = seccion(text, "Objetivos y no-objetivos") or ""
        if obj.strip():
            if not OBJETIVO_RE.search(obj):
                problemas.append("'## Objetivos y no-objetivos' no declara ningun '- O1: ...' (con nombre, para citarlo)")
            if not NO_OBJETIVO_RE.search(obj):
                problemas.append("'## Objetivos y no-objetivos' no declara ningun '- NO1: ...' (frenan el 'ya que estamos')")
        feats = seccion(text, "Features candidatas")
        if feats is not None and not candidatas(feats):
            problemas.append("'## Features candidatas' no declara ninguna '- F-n: nombre: resultado'")
        elif feats is not None:
            problemas.extend(_problemas_dependencias_candidatas(feats))
        lenguajes = sorted({m.group(1).lower() for m in FENCE_RE.finditer(limpio)} - PSEUDO)
        if lenguajes:
            problemas.append("trae codigo final (bloque " + ", ".join(f"```{x}" for x in lenguajes)
                             + "): el PRD lleva pseudo-codigo; el codigo se escribe despues, en otra parte")
    if doc == "sdd":
        dec = seccion(text, "Decisiones") or ""
        if dec.strip() and not DECISION_RE.search(dec):
            problemas.append("'## Decisiones' no declara ninguna '- D1: ...' (con nombre, para que el spec la cite)")
        sin_alt = _decisiones_sin_alternativa(dec)
        if sin_alt:
            problemas.append("'## Decisiones' declara " + ", ".join(sin_alt)
                             + " sin alternativa descartada: escribe 'Descartada: <opcion>, porque <motivo>'")
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


# --- el PRD/SDD a lo largo del flujo ------------------------------------------
#
# El rol producto los escribe y el cierre les agrega el bloque generado; lo de
# abajo es lo que usan los roles del medio: approve-spec (la regla
# require_docs_al_dia y la huella con que se aprobo cada spec), el brief del
# leader y estado.py.

def requeridos(rules: dict) -> list[str]:
    """Documentos que exige `require_docs_al_dia`. ValueError si el valor no se entiende:
    una regla mal escrita que se apaga sola es un verde falso."""
    valor = rules.get("require_docs_al_dia")
    if valor is True:
        return ["prd"]
    if valor is False or valor is None:
        return []
    if isinstance(valor, list) and all(isinstance(x, str) and x in DOCS for x in valor):
        return [doc for doc in DOCS if doc in valor]
    raise ValueError(f"rules.require_docs_al_dia invalido ({valor!r}): usa true (solo prd), "
                     f"false o una lista de {sorted(DOCS)}")


def texto_manual(path: Path) -> str | None:
    """Cuerpo manual de un documento, arriba y abajo del bloque generado; None si no
    hay uno del usuario. Con marcadores malformados tampoco: no se adivina."""
    from bloques import GENERADOS, parts
    try:
        previo = path.read_bytes()
        partes = parts(previo)
    except (OSError, ValueError):
        return None
    if partes is None:
        partes = (previo, b"")
    if partes[0] in GENERADOS.values():  # el encabezado que inventa documentacion.py
        partes = (b"", partes[1])
    manual = partes[0] + partes[1]
    return manual.decode("utf-8", "replace") if manual.strip() else None


def falta(p: dict, data: dict, doc: str) -> str | None:
    """Por que `doc` no tiene cuerpo para approve-spec; None si lo tiene.

    Vale el cuerpo sellado por `aprobar --yes` y el que el usuario escribio a
    mano. Que nadie mas lo haya tocado lo decide gate.py con las rutas protegidas.
    """
    from bloques import parts
    destino = destino_path(p, doc)
    if texto_manual(destino) is not None:
        return None
    try:
        if destino.is_file():
            parts(destino.read_bytes())
    except ValueError as exc:
        return f"{_rel(p['root'], destino)}: {exc}"
    return estado_documentos(p, data)[doc]


def huella(p: dict, doc: str) -> str | None:
    """Firma del cuerpo manual con que se aprueba un spec; None sin cuerpo.

    Ignora el bloque generado (cambia en cada cierre) y las lineas Estado/Aprobado
    (re-aprobar el mismo texto no es un cambio de producto).
    """
    texto = texto_manual(destino_path(p, doc))
    if texto is None:
        return None
    texto = re.sub(r"^(?:Estado|Aprobado):.*(?:\n|$)", "", texto, flags=re.M)
    return hashlib.sha256(texto.strip().encode("utf-8")).hexdigest()


def huellas(p: dict) -> dict[str, str]:
    return {doc: h for doc in DOCS if (h := huella(p, doc)) is not None}


def cambiados(p: dict, f: dict) -> list[str]:
    """Documentos que cambiaron desde que se aprobo el spec de `f`."""
    base = f.get("docs_base") or {}
    return [doc for doc in DOCS if doc in base and base[doc] != huella(p, doc)]


def _ids(regex: re.Pattern, texto: str) -> list[str]:
    vistos: dict[str, None] = {}
    for m in regex.finditer(COMENTARIO_RE.sub("", texto)):
        vistos.setdefault(m.group(1).replace("-", ""), None)
    return list(vistos)


def objetivos(prd: str) -> tuple[list[str], list[str]]:
    sec = seccion(prd, "Objetivos y no-objetivos") or ""
    return _ids(OBJETIVO_RE, sec), _ids(NO_OBJETIVO_RE, sec)


def decisiones(sdd: str) -> list[str]:
    return _ids(DECISION_RE, seccion(sdd, "Decisiones") or "")


def candidata(prd: str, fid: str) -> str | None:
    """La linea `- F-n: ...` de las Features candidatas, o None si no esta."""
    sec = COMENTARIO_RE.sub("", seccion(prd, "Features candidatas") or "")
    for linea in sec.splitlines():
        m = CANDIDATA_RE.match(linea)
        if m and f"F-{m.group(1)}" == fid:
            return linea.strip().lstrip("-* ").strip()
    return None


def prd_de(p: dict, f: dict) -> Path:
    return p["root"] / (f.get("prd") or "docs/prd/PRD-master.md")


def avisos_citas(p: dict, f: dict, spec: str) -> list[str]:
    """Lo que el spec no cita del PRD/SDD que lo origina. Avisos, no rechazos:
    el validador mide estructura; si la cita es la correcta lo decide el usuario."""
    if f.get("kind", "feature") not in TIPOS_EXIGIDOS:
        return []
    spec = COMENTARIO_RE.sub("", spec)
    sin_cita = {m.group(1).lower() for m in SIN_CITA_RE.finditer(spec)}
    out = []
    prd = texto_manual(prd_de(p, f))
    if prd is not None:
        declarados = objetivos(prd)[0]
        citados = _ids(CITA_OBJETIVO_RE, spec)
        if declarados and not citados and "cumple" not in sin_cita:
            out.append(f"el spec no cita ningun objetivo del PRD ({', '.join(declarados)}): "
                       "escribe 'cumple: O1' en el Contexto, o 'cumple: ninguno'")
        ajenos = [x for x in citados if x not in declarados]
        if ajenos:
            out.append(f"el spec cita {', '.join(ajenos)}, que el PRD no declara")
        fid = f.get("prd_candidata")
        if fid and candidata(prd, fid) is None:
            out.append(f"la candidata {fid} de esta feature ya no esta en el PRD")
    sdd = texto_manual(destino_path(p, "sdd"))
    if sdd is not None:
        declaradas = decisiones(sdd)
        citadas = _ids(CITA_DECISION_RE, spec)
        if declaradas and not citadas and "decisiones que aplica" not in sin_cita:
            out.append(f"el spec no cita ninguna decision del SDD ({', '.join(declaradas)}): escribe "
                       "'decisiones que aplica: D1' en el Contexto, o 'decisiones que aplica: ninguna'")
        ajenas = [x for x in citadas if x not in declaradas]
        if ajenas:
            out.append(f"el spec cita {', '.join(ajenas)}, que el SDD no declara")
    return out


def cobertura(p: dict, data: dict) -> str | None:
    """Que candidatas del PRD ya tienen feature y en que estado."""
    prd = texto_manual(destino_path(p, "prd"))
    if prd is None:
        return None
    sec_feats = seccion(prd, "Features candidatas") or ""
    deps = candidatas_dependencias(sec_feats)
    filas = []
    for n, _ in candidatas(sec_feats):
        fid = f"F-{n}"
        feats = [f for f in data["features"]
                 if f.get("prd_candidata") == fid and f.get("status") != "superseded"]
        req_txt = f" (requiere {', '.join(deps[fid])})" if fid in deps and not feats else ""
        filas.append(f"{fid} " + (", ".join(f"#{f['id']} {f.get('status')}" for f in feats)
                                  if feats else f"sin feature{req_txt}"))
    return " · ".join(filas) or None


def lineas_brief(p: dict, data: dict, f: dict) -> list[str]:
    """Seccion del brief del leader: que dice el PRD/SDD de esta feature."""
    estados = estado_documentos(p, data)
    L = ["", "producto (leelo antes de disenar; el spec cita sus O-n y D-n):"]
    prd_path = prd_de(p, f)
    prd = texto_manual(prd_path)
    L.append(f"  prd: {_rel(p['root'], prd_path)} · "
             + (estados["prd"] if prd_path == destino_path(p, "prd") else
                ("con cuerpo" if prd is not None else "sin cuerpo")))
    if prd is not None:
        fid = f.get("prd_candidata")
        linea = candidata(prd, fid) if fid else None
        if linea:
            L.append(f"       {linea[:200]}")
        elif fid:
            L.append(f"       [!] la candidata {fid} ya no esta en el PRD")
        elif f.get("kind", "feature") in TIPOS_EXIGIDOS and candidatas(prd):
            L.append("       (sin candidata F-n declarada: add.py --candidata la registra)")
        obj, no_obj = objetivos(prd)
        if obj or no_obj:
            L.append(f"       objetivos: {', '.join(obj) or '-'} · no-objetivos: {', '.join(no_obj) or '-'}")
    sdd = texto_manual(destino_path(p, "sdd"))
    L.append(f"  sdd: {_rel(p['root'], destino_path(p, 'sdd'))} · {estados['sdd']}")
    if sdd is not None and decisiones(sdd):
        L.append(f"       decisiones: {', '.join(decisiones(sdd))}")
    for doc in cambiados(p, f):
        L.append(f"  [!] el {DOCS[doc]['titulo']} cambio desde que se aprobo este spec: si un AC "
                 "deja de valer es una enmienda; si sigue valiendo, re-aprueba el spec")
    return L


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
    # El registro multi-repo fijo los bytes manuales del documento si era ruta
    # protegida, y su contrato dice que nada los reautoriza (ni re-registrar).
    # Aprobar aqui dejaria esas features sin cierre posible: mejor negarse antes.
    rel_destino = _rel(p["root"], destino)
    registradas = [f for f in data["features"]
                   if f.get("status") in ABIERTOS and isinstance(f.get("multi_repo_protected"), dict)
                   and any(isinstance(v, dict) and rel_destino in v
                           for v in f["multi_repo_protected"].values())]
    if registradas:
        ids = ", ".join(f"#{f['id']}" for f in registradas)
        sys.exit(f"[!!] hay features multi-repo registradas abiertas ({ids}): su registro fijo\n"
                 f"     los bytes manuales de {rel_destino} y el sello NO lo reautoriza. Cierralas\n"
                 f"     antes, o aprueba el {cfg['titulo']} antes de registrar.")

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
        max_cands = int(data.get("rules", {}).get("max_candidatas_prd", 15) or 15)
        for aviso in avisos_vertical_prd(sellado, max_candidatas=max_cands):
            print(f"[!]  {aviso}")
        sec_feats = seccion(sellado, "Features candidatas") or ""
        cands = candidatas(sec_feats)
        deps_cands = candidatas_dependencias(sec_feats)
        if cands:
            print("[i]  features candidatas para el backlog:")
            for n, nombre in cands:
                fid = f"F-{n}"
                flags_req = "".join(f" --requiere {r}" for r in deps_cands.get(fid, []))
                print(f'     add.py --name "{nombre}" --prd docs/prd/PRD-master.md --candidata {fid}{flags_req}')
    else:
        print("[i]  documentacion.py sync seguira agregando el bloque por feature debajo del cuerpo.")
    viejas = [f for f in data["features"] if f.get("status") in ABIERTOS and doc in cambiados(p, f)]
    if viejas:
        print(f"[!]  specs aprobados contra la version anterior del {cfg['titulo']}: "
              + ", ".join(f"#{f['id']}" for f in viejas) + ".")
        print("     El leader los revisa: si un AC deja de valer es una enmienda; si sigue")
        print("     valiendo, se re-aprueba el spec (approve-spec --yes, con el SI del usuario).")


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
