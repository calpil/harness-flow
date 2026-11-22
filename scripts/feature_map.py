#!/usr/bin/env python3
"""Mecanismo 1 (Feedback Loop): Feature Map del proyecto y verificacion autonoma.

Ensena a los agentes DONDE vive cada funcionalidad, COMO acceder a ella y COMO
comprobar su propio trabajo interactuando con la aplicacion, evitando que el
humano sea el cuello de botella y permitiendo reproducir bugs de forma autonoma.

  feature_map.py init [--start-cmd <cmd>] [--base-url <url>] [--verificador <tool>]
  feature_map.py registrar --id <slug> --nombre "<nombre>" [--feature <id>]
                           [--repo <r> ...] [--ruta-ui <ruta> ...]
                           [--endpoint <ep> ...] [--paso "<paso>" ...]
                           [--como-verificar "<cmd>"] [--archivo <path> ...]
  feature_map.py buscar <termino>
  feature_map.py list [--json]
  feature_map.py verificar [--feature <id>]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from comun import (  # noqa: E402
    ac_costuras, bitacora, get_feature, impl_path, load_backlog, now_iso,
    paths, slugify, spec_path,
)

# Costuras expuestas o interactivas que exigen entrada vigente en el Feature Map.
COSTURAS_MAPA = frozenset({
    "ui", "componente", "pantalla", "vista",
    "endpoint", "api", "http", "rest", "grpc", "graphql", "bff", "webhook", "cli",
})

_REPRO_ENCABEZADO_RE = re.compile(
    r"(?im)^\s*(?:#{1,4}\s+reproducci[oó]n\b.*|[-*]?\s*\*\*?reproducci[oó]n\*\*?\s*:.*)$"
)
_EVIDENCIA_REPRO_RE = re.compile(
    r"`[^`\n]{3,}`"
    r"|\b[\w./-]+\.[A-Za-z0-9]{1,8}:\d+\b"
    r"|https?://\S+"
    r"|\b(?:playwright|cypress|devtools|curl|pytest|go\s+test|npm\s+test|vitest|exit\s+\d+|HTTP\s+\d{3})\b"
    r"|\b[\w./-]+\.(?:png|jpe?g|webp|mp4|webm|log|har|trace\.zip)\b",
    re.IGNORECASE,
)
_PLACEHOLDER_RE = re.compile(r"<[^>\n]{2,}>")


def ruta_mapa(p: dict) -> Path:
    return p["harness"] / "feature-map.json"


def crear_esqueleto(
    start_command: str = "",
    base_url: str = "",
    verificador: str = "playwright",
) -> dict[str, Any]:
    return {
        "version": 1,
        "app": {
            "start_command": start_command.strip(),
            "base_url": base_url.strip(),
            "verificador": (verificador or "playwright").strip(),
        },
        "features": {},
    }


def cargar_mapa(p: dict) -> dict[str, Any] | None:
    """Carga harness/feature-map.json. None si no existe; ValueError si esta corrupto."""
    ruta = ruta_mapa(p)
    if not ruta.exists():
        return None
    if not ruta.is_file():
        raise ValueError(f"{ruta.name} no es un archivo regular")
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"{ruta.name} ilegible o JSON invalido: {exc}")
    if not isinstance(datos, dict) or not isinstance(datos.get("features"), dict):
        raise ValueError(f"{ruta.name} invalido: debe ser un objeto JSON con clave 'features' (dict)")
    datos.setdefault("version", 1)
    if not isinstance(datos.get("app"), dict):
        datos["app"] = {}
    return datos


def guardar_mapa(p: dict, mapa: dict[str, Any]) -> Path:
    destino = ruta_mapa(p)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(f".{destino.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(mapa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, destino)
    return destino


def costuras_interactivas(stext: str) -> dict[str, str]:
    """Subconjunto de AC del spec cuyas costuras exponen UI, endpoint o CLI."""
    out: dict[str, str] = {}
    for ac, costura in ac_costuras(stext).items():
        if costura.strip().lower() in COSTURAS_MAPA:
            out[ac] = costura.strip().lower()
    return out


def validar_entrada(entry_id: str, entry: Any) -> list[str]:
    """Verifica que una entrada del Feature Map sea util para un agente (sin vacios ni huecos)."""
    if not isinstance(entry, dict):
        return [f"entrada '{entry_id}' debe ser un objeto JSON"]
    fallos: list[str] = []
    nombre = str(entry.get("nombre") or "").strip()
    if not nombre or _PLACEHOLDER_RE.search(nombre):
        fallos.append(f"entrada '{entry_id}': falta 'nombre' valido")

    accesos = []
    for clave in ("rutas_ui", "endpoints", "pasos_acceso"):
        vals = entry.get(clave) or []
        if not isinstance(vals, list):
            fallos.append(f"entrada '{entry_id}': '{clave}' debe ser una lista")
            continue
        accesos.extend(str(x).strip() for x in vals if str(x).strip() and not _PLACEHOLDER_RE.search(str(x)))
    if not accesos:
        fallos.append(
            f"entrada '{entry_id}': declara al menos un acceso (rutas_ui, endpoints o pasos_acceso)"
        )

    verificar = str(entry.get("como_verificar") or "").strip()
    if not verificar or _PLACEHOLDER_RE.search(verificar):
        fallos.append(f"entrada '{entry_id}': falta 'como_verificar' (comando o flujo concreto de comprobacion)")
    return fallos


def entradas_de_feature(mapa: dict[str, Any] | None, f: dict) -> list[tuple[str, dict[str, Any]]]:
    """Entradas del Feature Map asociadas a la feature `f`."""
    if not mapa:
        return []
    fid_str = str(f.get("id"))
    map_id = str(f.get("feature_map_id") or "").strip()
    slug_f = slugify(str(f.get("name") or ""))
    hits: list[tuple[str, dict[str, Any]]] = []
    for eid, entry in sorted((mapa.get("features") or {}).items()):
        if not isinstance(entry, dict):
            continue
        fids = [str(x).lstrip("#") for x in (entry.get("feature_ids") or [])]
        if (map_id and eid == map_id) or (fid_str in fids) or (slug_f and eid == slug_f):
            hits.append((eid, entry))
    return hits


def entradas_relacionadas(
    mapa: dict[str, Any] | None,
    f: dict,
    micros: list[str] | None = None,
    tope: int = 6,
) -> list[tuple[str, dict[str, Any]]]:
    """Entradas propias primero; luego las que comparten repo/microservicio."""
    if not mapa:
        return []
    propias = entradas_de_feature(mapa, f)
    vistas = {eid for eid, _ in propias}
    out = list(propias)
    mset = {m.lower() for m in (micros or [])}
    if mset:
        for eid, entry in sorted((mapa.get("features") or {}).items()):
            if eid in vistas or not isinstance(entry, dict):
                continue
            repos = {str(r).lower() for r in (entry.get("repos") or [])}
            if repos & mset:
                out.append((eid, entry))
                vistas.add(eid)
                if len(out) >= tope:
                    break
    return out[:tope]


def tiene_evidencia_reproduccion(impl_text: str) -> tuple[bool, str]:
    """Comprueba que docs/impl-<id>.md documenta la reproduccion autonoma de un bug.

    Regla anti-falso-verde: no basta mencionar 'reproducido'. Exige una seccion
    `## Reproduccion` (o linea `Reproduccion:`) con evidencia verificable
    (comando en backticks, archivo:linea, HTTP/exit, URL o captura/log).
    """
    limpio = re.sub(r"<!--.*?-->", "", impl_text or "", flags=re.S)
    lineas = limpio.splitlines()
    bloques: list[str] = []
    i = 0
    while i < len(lineas):
        ln = lineas[i]
        if _REPRO_ENCABEZADO_RE.match(ln):
            # Si es linea 'Reproduccion: texto', conservar texto despues de ':'
            if not ln.lstrip().startswith("#"):
                despues = ln.split(":", 1)[1].strip() if ":" in ln else ""
                cuerpo = [despues] if despues else []
            else:
                cuerpo = []
            i += 1
            while i < len(lineas) and not re.match(r"^\s*#{1,4}\s+", lineas[i]):
                cuerpo.append(lineas[i])
                i += 1
            bloques.append("\n".join(cuerpo).strip())
            continue
        i += 1
    if not bloques:
        return False, "falta seccion `## Reproduccion` (o `Reproduccion:`) en la evidencia del bug"
    texto = "\n".join(b for b in bloques if b).strip()
    if len(texto) < 15:
        return False, "la seccion de reproduccion esta vacia o es demasiado corta"
    if not _EVIDENCIA_REPRO_RE.search(texto):
        return False, (
            "la seccion de reproduccion no incluye evidencia verificable "
            "(comando en backticks, archivo:linea, salida HTTP/exit o ruta de captura/log)"
        )
    return True, ""


def regla_activa(rules: dict | None) -> bool:
    """Evalua rules.require_feature_map (True por defecto). Valida el tipo."""
    val = (rules or {}).get("require_feature_map", True)
    if not isinstance(val, bool):
        raise ValueError(
            f"rules.require_feature_map invalido ({val!r}): debe ser true o false"
        )
    return val


def validar_feature(
    p: dict,
    data: dict,
    f: dict,
    stext: str,
    *,
    modo_check: bool = False,
) -> tuple[list[str], list[str]]:
    """Valida Feature Map y evidencia de reproduccion para `f`.

    Devuelve `(fallos, avisos)`.
    - JSON corrupto en `harness/feature-map.json` es SIEMPRE un fallo.
    - Con `require_feature_map=True` (default):
      - Feature con costuras UI/endpoint/CLI exige entrada valida en el mapa.
      - Feature `kind == 'bug'` exige evidencia de reproduccion previa al fix en `docs/impl-<id>.md`.
    - En `modo_check` sobre una feature `in_progress`, los faltantes son avisos
      para no bloquear trabajo en curso; en `close` son fallos bloqueantes.
    """
    fallos: list[str] = []
    avisos: list[str] = []
    try:
        requerido = regla_activa(data.get("rules"))
    except ValueError as exc:
        return [str(exc)], []

    try:
        mapa = cargar_mapa(p)
    except ValueError as exc:
        return [f"feature-map: {exc}"], []

    destino_lista = avisos if (not requerido or (modo_check and f.get("status") == "in_progress")) else fallos
    fid = f["id"]
    slug_sug = slugify(str(f.get("name") or f"feature-{fid}"))

    inter = costuras_interactivas(stext)
    if inter:
        costuras_txt = ", ".join(f"{ac}({c})" for ac, c in sorted(inter.items()))
        if mapa is None:
            destino_lista.append(
                f"feature-map: #{fid} expone {costuras_txt} pero falta harness/feature-map.json "
                f"(registra la funcionalidad con: feature_map.py registrar --id {slug_sug} "
                f"--nombre '{f.get('name', slug_sug)}' --feature {fid} --ruta-ui /... --como-verificar '...')"
            )
        else:
            propias = entradas_de_feature(mapa, f)
            if not propias:
                destino_lista.append(
                    f"feature-map: #{fid} expone {costuras_txt} sin entrada en harness/feature-map.json "
                    f"(registra con: feature_map.py registrar --id {slug_sug} "
                    f"--nombre '{f.get('name', slug_sug)}' --feature {fid} --ruta-ui /... --como-verificar '...')"
                )
            else:
                for eid, entry in propias:
                    for err in validar_entrada(eid, entry):
                        destino_lista.append(f"feature-map: {err}")

    if f.get("kind") == "bug":
        ip = impl_path(p, f)
        if not ip.exists():
            if not modo_check or f.get("status") != "in_progress":
                destino_lista.append(
                    f"feedback-loop: #{fid} (bug) sin evidencia de reproduccion ({ip.name} ausente)"
                )
        else:
            ok_repro, motivo = tiene_evidencia_reproduccion(ip.read_text(encoding="utf-8"))
            if not ok_repro:
                destino_lista.append(
                    f"feedback-loop: #{fid} (bug) {motivo}; reproduce el bug antes del fix "
                    "(usando harness/feature-map.json) y registra comando + evidencia en `## Reproduccion`"
                )

    return fallos, avisos


def lineas_brief(p: dict, data: dict, f: dict, micros: list[str], stext: str) -> list[str]:
    """Bloque FEATURE MAP Y FEEDBACK LOOP para `contexto.py brief`."""
    import normas
    L: list[str] = ["", "FEATURE MAP Y FEEDBACK LOOP (comprobacion autonoma sobre la app):"]
    try:
        mapa = cargar_mapa(p)
    except ValueError as exc:
        L.append(f"  [!!] {exc}")
        return L

    inter = costuras_interactivas(stext)
    if mapa is None:
        L.append("  mapa: ausente (harness/feature-map.json). Inicializalo: "
                 + normas.comando("feature_map.py", "init"))
    else:
        app = mapa.get("app") or {}
        detalles_app = []
        if app.get("start_command"):
            detalles_app.append(f"arranque=`{app['start_command']}`")
        if app.get("base_url"):
            detalles_app.append(f"url={app['base_url']}")
        if app.get("verificador"):
            detalles_app.append(f"verificador={app['verificador']}")
        total = len(mapa.get("features") or {})
        L.append(f"  mapa: {total} funcionalidad(es) en harness/feature-map.json"
                 + (f" ({', '.join(detalles_app)})" if detalles_app else ""))
        rel = entradas_relacionadas(mapa, f, micros)
        if rel:
            for eid, entry in rel:
                rutas = ", ".join(entry.get("rutas_ui") or [])
                eps = ", ".join(entry.get("endpoints") or [])
                acceso = " | ".join(x for x in (f"UI: {rutas}" if rutas else "", f"API: {eps}" if eps else "") if x)
                L.append(f"  - [{eid}] {entry.get('nombre', eid)}" + (f" ({acceso})" if acceso else ""))
                for paso in (entry.get("pasos_acceso") or [])[:3]:
                    L.append(f"      acceso: {paso}")
                if entry.get("como_verificar"):
                    L.append(f"      verificar: {entry['como_verificar']}")
        else:
            L.append("  (sin entradas asociadas todavia; busca otras con: "
                     + normas.comando("feature_map.py", "buscar", "<termino>") + ")")

    if inter and (mapa is None or not entradas_de_feature(mapa, f)):
        slug_sug = slugify(str(f.get("name") or f"feature-{f['id']}"))
        L.append("  [!] esta feature expone UI/endpoints: antes de cerrar actualiza el Feature Map:")
        L.append("      " + normas.comando(
            "feature_map.py", "registrar", "--id", slug_sug,
            "--nombre", str(f.get("name") or slug_sug),
            "--feature", str(f["id"]),
            "--como-verificar", "<comando-o-flujo>",
        ))

    if f.get("kind") == "bug":
        L.append("  [!] FLUJO DE BUG (reproduccion autonoma obligatoria):")
        L.append("      1. Localiza la funcionalidad en el Feature Map (`feature_map.py buscar <termino>`).")
        L.append("      2. Reproduce el bug en ROJO interactuando con la app/costura ANTES de editar codigo.")
        L.append("      3. Aplica el fix, re-verifica en VERDE (tope 2 intentos antes de parada 4) y documenta "
                 "el comando/evidencia en `## Reproduccion` de docs/impl-<id>.md.")
    else:
        L.append("  feedback loop: tras pasar unit tests, comprueba el flujo real en la app/costura "
                 "(Playwright, Chrome DevTools MCP, HTTP o CLI); si falla, usa el error para corregir y "
                 "reintentar (max 2 intentos antes de parada 4).")
    return L


def resumen_estado(p: dict, data: dict) -> str:
    try:
        req = regla_activa(data.get("rules"))
    except ValueError as exc:
        return f"[!!] {exc}"
    try:
        mapa = cargar_mapa(p)
    except ValueError as exc:
        return f"[!!] {exc}"
    tag = "obligatorio" if req else "opcional"
    if mapa is None:
        return f"ausente ({tag}; crea con feature_map.py init)"
    n = len(mapa.get("features") or {})
    invalidas = sum(1 for eid, e in (mapa.get("features") or {}).items() if validar_entrada(eid, e))
    if invalidas:
        return f"[!] {n} entrada(s), {invalidas} incompleta(s) ({tag}; corre feature_map.py verificar)"
    return f"{n} entrada(s) en harness/feature-map.json ({tag})"


# --- CLI -------------------------------------------------------------------

def cmd_init(args) -> None:
    p = paths()
    ruta = ruta_mapa(p)
    if ruta.exists() and not args.forzar:
        print(f"[i]  {ruta} ya existe; no se sobreescribe (usa --forzar para reiniciar)")
        return
    mapa = crear_esqueleto(args.start_cmd or "", args.base_url or "", args.verificador or "playwright")
    guardar_mapa(p, mapa)
    bitacora(p, "feature-map inicializado en harness/feature-map.json")
    print(f"[ok] feature-map inicializado: {ruta}")


def cmd_registrar(args) -> None:
    p = paths()
    data = load_backlog(p)
    try:
        mapa = cargar_mapa(p) or crear_esqueleto()
    except ValueError as exc:
        sys.exit(f"[!!] {exc}")

    eid = slugify(args.id)
    if not eid or eid == "sin-nombre":
        sys.exit("[!!] --id invalido: usa un slug descriptivo (ej. registro-usuarios)")

    previa = dict(mapa["features"].get(eid) or {})
    fids = [str(x).lstrip("#") for x in (previa.get("feature_ids") or [])]
    for fid in args.feature or []:
        f_obj = get_feature(data, fid)
        fid_clean = str(f_obj["id"])
        if fid_clean not in fids:
            fids.append(fid_clean)

    def _merge(clave: str, nuevos: list[str]) -> list[str]:
        base = list(previa.get(clave) or [])
        for x in nuevos:
            limpio = x.strip()
            if limpio and limpio not in base:
                base.append(limpio)
        return base

    entry = {
        "id": eid,
        "nombre": (args.nombre or previa.get("nombre") or "").strip(),
        "feature_ids": fids,
        "repos": _merge("repos", args.repo or []),
        "rutas_ui": _merge("rutas_ui", args.ruta_ui or []),
        "endpoints": _merge("endpoints", args.endpoint or []),
        "pasos_acceso": _merge("pasos_acceso", args.paso or []),
        "como_verificar": (args.como_verificar or previa.get("como_verificar") or "").strip(),
        "archivos_clave": _merge("archivos_clave", args.archivo or []),
        "updated_at": now_iso(),
    }
    errores = validar_entrada(eid, entry)
    if errores:
        sys.exit("[!!] entrada de Feature Map incompleta:\n" + "\n".join(f"     - {e}" for e in errores))

    if args.start_cmd:
        mapa.setdefault("app", {})["start_command"] = args.start_cmd.strip()
    if args.base_url:
        mapa.setdefault("app", {})["base_url"] = args.base_url.strip()
    if args.verificador:
        mapa.setdefault("app", {})["verificador"] = args.verificador.strip()

    mapa["features"][eid] = entry
    guardar_mapa(p, mapa)
    bitacora(p, f"feature-map actualizado: {eid}" + (f" (features: {', '.join('#' + x for x in fids)})" if fids else ""))
    print(f"[ok] feature-map registrado: {eid} -> {ruta_mapa(p)}")


def cmd_buscar(args) -> None:
    p = paths()
    try:
        mapa = cargar_mapa(p)
    except ValueError as exc:
        sys.exit(f"[!!] {exc}")
    if not mapa or not mapa.get("features"):
        sys.exit("[!!] harness/feature-map.json no existe o no tiene entradas.")
    q = args.termino.strip().lower()
    hits = []
    for eid, entry in sorted(mapa["features"].items()):
        blob = json.dumps(entry, ensure_ascii=False).lower()
        if q in eid.lower() or q in blob:
            hits.append((eid, entry))
    if not hits:
        print(f"[i]  sin coincidencias en feature-map para '{args.termino}'")
        sys.exit(1)
    for eid, entry in hits:
        print(f"- {eid}: {entry.get('nombre')}")
        if entry.get("rutas_ui"):
            print(f"    rutas UI:   {', '.join(entry['rutas_ui'])}")
        if entry.get("endpoints"):
            print(f"    endpoints:  {', '.join(entry['endpoints'])}")
        for paso in entry.get("pasos_acceso") or []:
            print(f"    paso:       {paso}")
        if entry.get("como_verificar"):
            print(f"    verificar:  {entry['como_verificar']}")
        if entry.get("archivos_clave"):
            print(f"    archivos:   {', '.join(entry['archivos_clave'])}")


def cmd_list(args) -> None:
    p = paths()
    try:
        mapa = cargar_mapa(p)
    except ValueError as exc:
        sys.exit(f"[!!] {exc}")
    if mapa is None:
        print("[i]  sin harness/feature-map.json (crea con: feature_map.py init)")
        return
    if args.json:
        print(json.dumps(mapa, ensure_ascii=False, indent=2))
        return
    app = mapa.get("app") or {}
    print(f"== Feature Map ({len(mapa.get('features') or {})} entradas) ==")
    if any(app.values()):
        print(f"   app: start=`{app.get('start_command') or '-'}` · url={app.get('base_url') or '-'} "
              f"· verificador={app.get('verificador') or '-'}")
    for eid, entry in sorted((mapa.get("features") or {}).items()):
        fids = ", ".join(f"#{x}" for x in (entry.get("feature_ids") or []))
        errs = validar_entrada(eid, entry)
        marca = "  <- INCOMPLETA" if errs else ""
        print(f"   - {eid}: {entry.get('nombre', '')}" + (f" [{fids}]" if fids else "") + marca)
        if entry.get("rutas_ui"):
            print(f"       UI: {', '.join(entry['rutas_ui'])}")
        if entry.get("endpoints"):
            print(f"       API: {', '.join(entry['endpoints'])}")
        if entry.get("como_verificar"):
            print(f"       verificar: {entry['como_verificar']}")


def cmd_verificar(args) -> None:
    p = paths()
    data = load_backlog(p)
    fallos: list[str] = []
    avisos: list[str] = []

    if args.feature:
        f = get_feature(data, args.feature)
        sp = spec_path(p, f)
        stext = sp.read_text(encoding="utf-8") if sp.exists() else ""
        fallos, avisos = validar_feature(p, data, f, stext, modo_check=False)
    else:
        try:
            mapa = cargar_mapa(p)
        except ValueError as exc:
            sys.exit(f"[!!] feature-map: {exc}")
        if mapa is None:
            sys.exit("[!!] harness/feature-map.json no existe (crea con: feature_map.py init)")
        for eid, entry in sorted((mapa.get("features") or {}).items()):
            fallos.extend(validar_entrada(eid, entry))

    for a in avisos:
        print(f"[!]  {a}")
    if fallos:
        print(f"[!!] feature-map: {len(fallos)} fallo(s):")
        for x in fallos:
            print(f"     - {x}")
        sys.exit(1)
    print("[ok] feature-map valido" + (f" para feature #{args.feature}" if args.feature else ""))


def main() -> None:
    ap = argparse.ArgumentParser(description="Feature Map y Feedback Loop autonomo de harness-flow")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="crea harness/feature-map.json")
    s.add_argument("--start-cmd", dest="start_cmd", help="comando para levantar la app localmente")
    s.add_argument("--base-url", dest="base_url", help="URL base local (ej. http://localhost:3000)")
    s.add_argument("--verificador", default="playwright", help="herramienta principal (playwright, chrome-devtools, curl, cli)")
    s.add_argument("--forzar", action="store_true")
    s.set_defaults(fn=cmd_init)

    s = sub.add_parser("registrar", help="registra o actualiza una funcionalidad en harness/feature-map.json")
    s.add_argument("--id", required=True, help="slug de la funcionalidad (ej. registro-usuarios)")
    s.add_argument("--nombre", help="nombre legible de la funcionalidad")
    s.add_argument("--feature", action="append", default=[], help="id de feature del backlog asociada (repetible)")
    s.add_argument("--repo", action="append", default=[], help="repo/microservicio donde vive (repetible)")
    s.add_argument("--ruta-ui", action="append", default=[], dest="ruta_ui", help="ruta UI (ej. /registro; repetible)")
    s.add_argument("--endpoint", action="append", default=[], help="endpoint (ej. 'POST /api/v1/users'; repetible)")
    s.add_argument("--paso", action="append", default=[], help="paso concreto de navegacion/acceso (repetible)")
    s.add_argument("--como-verificar", dest="como_verificar", help="comando E2E o flujo verificable sobre la app")
    s.add_argument("--archivo", action="append", default=[], help="archivo clave de entrada (repetible)")
    s.add_argument("--start-cmd", dest="start_cmd")
    s.add_argument("--base-url", dest="base_url")
    s.add_argument("--verificador")
    s.set_defaults(fn=cmd_registrar)

    s = sub.add_parser("buscar", help="busca funcionalidades por nombre, ruta UI, endpoint o repo")
    s.add_argument("termino")
    s.set_defaults(fn=cmd_buscar)

    s = sub.add_parser("list", help="lista el Feature Map")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_list)

    s = sub.add_parser("verificar", help="valida el Feature Map completo o para una feature (exit!=0 si falla)")
    s.add_argument("--feature")
    s.set_defaults(fn=cmd_verificar)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
