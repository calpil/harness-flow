#!/usr/bin/env python3
"""Gates del harness-flow. TODOS devuelven exit != 0 cuando algo falta.

Este archivo es lo que hace que el proceso sea un gate y no una intencion:
un agente puede olvidarse de una regla, pero no puede hacer que un exit 1
sea un exit 0.

  gate.py check
  gate.py check-spec   --feature <id>
  gate.py approve-spec --feature <id> --yes
  gate.py enmienda     --feature <id> --propuesta docs/<propuesta>.md --yes
  gate.py revision     --feature <id> --veredicto approved|changes_requested|blocked
  gate.py verify       --feature <id>
  gate.py close        --feature <id> --status done|blocked --to <rama> [--leccion <clase>]
"""
from __future__ import annotations

import argparse
import fnmatch
import getpass
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (  # noqa: E402
    ENMIENDAS_RE, Reporte, acs_faltantes, acs_no_reconocidos, bitacora, comparar_huellas, cubre_acs,
    enmiendas_posteriores, get_feature, git, impl_path, load_backlog, n_enmiendas,
    now_iso, paths, review_path, ac_comandos, save_backlog, sello_revision,
    sig_fresh, sign, spec_acs, spec_estado, spec_huella, spec_path,
)

ABIERTOS = ("in_progress", "blocked", "review")


# --- check maestro ---------------------------------------------------------

def cmd_check(args) -> None:
    p = paths()
    data = load_backlog(p)
    rules = data["rules"]
    r = Reporte()
    print(f"== Harness check: {data.get('project','(sin nombre)')} ==")
    print(f"   raiz: {p['root']}\n")

    abiertas = [f for f in data["features"] if f.get("status") in ABIERTOS]
    if not abiertas:
        r.info("no hay features abiertas")
    for f in abiertas:
        _check_feature(p, f, rules, r)

    _check_rutas_protegidas(p, rules, r, data)
    _check_aislamiento(abiertas, r, p, rules)
    r.salir()


def _check_feature(p, f, rules, r) -> None:
    fid = f["id"]
    print(f"-- feature #{fid}: {f.get('name')} [{f.get('status')}]")
    sp = spec_path(p, f)
    if not sp.exists():
        r.fallo(f"#{fid} sin spec ({sp.name})", "escribe el spec y hazlo aprobar")
        return
    text = sp.read_text(encoding="utf-8")
    acs = spec_acs(text)
    if not acs:
        r.fallo(f"#{fid} el spec no declara ningun AC-n",
                "agrega AC-1: Given/When/Then")
    ignorados = acs_no_reconocidos(text, acs)
    if ignorados:
        r.fallo(f"#{fid} hay lineas que declaran {', '.join(ignorados)} y el parser "
                "NO los reconoce como AC",
                "nadie los va a verificar y este check saldria en verde: escribelos "
                "como '- AC-n: Given/When/Then' (el titulo entre parentesis vale)")
    huecos = [x for x in acs_faltantes(acs) if x not in ignorados]
    if huecos:
        r.aviso(f"#{fid} la numeracion de AC salta: falta(n) {', '.join(huecos)}",
                "si lo borraste a proposito, renumera")
    estado = spec_estado(text)

    if rules.get("require_spec_approved"):
        if estado != "approved":
            r.fallo(f"#{fid} spec en '{estado}', se requiere approved",
                    f"gate.py approve-spec --feature {fid} --yes (tras el SI del usuario)")
        elif not sig_fresh(sp, f.get("last_spec_sig")):
            r.fallo(f"#{fid} el spec cambio despues de aprobarse (sello invalido)",
                    "vuelve a mostrarlo al usuario y re-aprueba")
        else:
            r.ok(f"#{fid} spec approved y fresco ({len(acs)} AC)")

    ip = impl_path(p, f)
    if ip.exists():
        _, faltan = cubre_acs(ip.read_text(encoding="utf-8"), acs)
        if faltan:
            r.fallo(f"#{fid} evidencia sin cubrir: {', '.join(faltan)}",
                    f"agrega en {ip.name} una fila por AC citando archivo:linea")
        else:
            r.ok(f"#{fid} evidencia cubre los {len(acs)} AC")
    elif f.get("status") != "in_progress":
        r.fallo(f"#{fid} sin evidencia ({ip.name})", "escribe la evidencia por AC")

    if rules.get("require_review"):
        rp = review_path(p, f)
        if not rp.exists():
            r.aviso(f"#{fid} sin review todavia ({rp.name})")
        else:
            rtext = rp.read_text(encoding="utf-8")
            sello = sello_revision(rtext)
            _, faltan = cubre_acs(rtext, acs)
            if faltan:
                r.fallo(f"#{fid} el review no responde por: {', '.join(faltan)}",
                        "una fila por AC-n citando archivo:linea")
            tarde = enmiendas_posteriores(f, f.get("last_review_enmiendas"))
            if sello is None:
                r.aviso(f"#{fid} review sin sello (un 'Veredicto:' a mano no cuenta)",
                        f"gate.py revision --feature {fid} --veredicto approved")
            elif tarde:
                r.aviso(f"#{fid} el review ({sello}) se sello antes de la enmienda "
                        f"{', '.join(tarde)}",
                        "close no lo acepta: lanza un review nuevo sobre el spec enmendado")
            elif sello != "approved":
                r.aviso(f"#{fid} review sellado como '{sello}'")
            else:
                r.ok(f"#{fid} review approved y sellado")

    for e in f.get("enmiendas") or []:
        if not isinstance(e, dict):
            continue
        pp = p["root"] / str(e.get("propuesta") or "")
        if not e.get("propuesta") or not pp.is_file() or not sig_fresh(pp, e.get("propuesta_sig")):
            r.aviso(f"#{fid} la propuesta de la {e.get('id')} falta o cambio despues de "
                    f"sellarse ({e.get('propuesta')})",
                    "es el registro de lo que aprobo el usuario: restaurala")


def _porcelain_path(line: str) -> str:
    """Extrae path de una linea porcelain aun si git() recorto espacios."""
    if len(line) >= 4 and line[2] == " ":
        return line[3:].strip().strip('"')
    if len(line) >= 3 and line[1] == " ":
        return line[2:].strip().strip('"')
    if len(line) >= 3:
        return line[3:].strip().strip('"')
    return ""


def _prd_master_seguro(p: dict, rel: str, data: dict | None = None) -> bool:
    """Misma excepcion en snapshot y Git: solo bloque, bytes manuales exactos.

    Segunda via, la unica en que el cuerpo manual puede diferir de HEAD: el
    sello de `producto.py aprobar --yes` (`documentos.prd` en el backlog). El
    usuario aprobo ESE cuerpo en el chat; vale para bytes identicos a los
    sellados (o su primera insercion del bloque generado) y hasta que lo
    commitea. No autoriza otros archivos bajo docs/prd/ ni ediciones posteriores.
    """
    from bloques import allowed, compatible, fingerprint
    if rel != "docs/prd/PRD-master.md":
        return False
    actual = p["root"] / rel
    if not actual.is_file() or actual.is_symlink():
        return False
    contenido = actual.read_bytes()
    base = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=p["root"], capture_output=True)
    if allowed(base.stdout if base.returncode == 0 else None, contenido):
        return True
    sello = ((data or {}).get("documentos") or {}).get("prd") or {}
    if not isinstance(sello.get("fingerprint"), dict):
        return False
    try:
        return compatible(sello["fingerprint"], fingerprint(contenido))
    except ValueError:
        return False


def _rutas_prd_tocadas(p: dict, rel: str) -> list[str]:
    if rel.rstrip("/") == "docs/prd":
        raiz = p["root"] / "docs" / "prd"
        return [x.relative_to(p["root"]).as_posix() for x in raiz.rglob("*") if x.is_file()]
    return [rel]


def _ruta_protegida_permitida(p: dict, rel: str, data: dict | None = None) -> bool:
    prd_tocadas = _rutas_prd_tocadas(p, rel) if rel.startswith("docs/prd") else []
    if not prd_tocadas:
        return False
    return all(_prd_master_seguro(p, x, data) for x in prd_tocadas)


def _check_rutas_protegidas(p, rules, r, data: dict | None = None) -> None:
    pats = rules.get("rutas_protegidas") or []
    if data is None:
        data = load_backlog(p)
    # -uall: sin el, un docs/ entero sin trackear sale como `?? docs/`, que no
    # matchea docs/prd/** y escondia un PRD-master.md nuevo bajo ese directorio.
    code, out = git(["status", "--porcelain", "-uall"], p["root"])
    if code != 0:
        r.info("sin repo git en la raiz: no se puede auditar rutas protegidas")
        return
    tocadas = []
    for line in out.splitlines():
        f = _porcelain_path(line)
        for pat in pats:
            # pat[:-3] sin el separador marcaba docs/prdX/ como si fuera docs/prd/.
            if fnmatch.fnmatch(f, pat) or (pat.endswith("/**") and f.startswith(pat[:-2])):
                if not _ruta_protegida_permitida(p, f, data):
                    tocadas.append(f)
    if tocadas:
        r.fallo("rutas protegidas modificadas: " + ", ".join(sorted(set(tocadas))),
                "son del USUARIO; revierte esos cambios")
    else:
        r.ok(f"{len(pats)} ruta(s) protegida(s) intactas")


def _check_aislamiento(abiertas, r, p, rules) -> None:
    from multirepo import Invalid, check_registered, _path, git as repo_git
    sin_wt, usados = [], {}
    for f in abiertas:
        worktrees = []
        try:
            if "multi_repo" in f:
                manifest = check_registered(p, f, rules)
                worktrees = [x["worktree"] for x in manifest["repos"]]
                aislada = all(x["worktree"] != x["repo"] for x in manifest["repos"])
            elif f.get("worktree"):
                wt = _path(f["worktree"])
                common = Path(repo_git(wt, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
                aislada = (wt / ".git").is_file() and common != wt / ".git"
                worktrees = [str(wt)]
            else:
                aislada = False
        except Invalid as exc:
            aislada = False
            r.fallo(f"aislamiento #{f['id']} no verificable: {exc}")
        if not aislada:
            sin_wt.append(f)
        for wt in worktrees:
            if wt in usados:
                r.fallo(f"worktree compartido entre #{usados[wt]} y #{f['id']}: {wt}")
            usados[wt] = f["id"]
    if len(sin_wt) > 1:
        ids = ", ".join(f"#{f['id']}" for f in sin_wt)
        r.fallo(f"aislamiento: {len(sin_wt)} features abiertas sin worktree ({ids})",
                "solo una feature puede trabajar sin aislamiento")


# --- check-spec ------------------------------------------------------------

def cmd_check_spec(args) -> None:
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, args.feature)
    sp = spec_path(p, f)
    if not sp.exists():
        sys.exit(f"[!!] no existe {sp}")
    text = sp.read_text(encoding="utf-8")
    estado, acs = spec_estado(text), spec_acs(text)
    if not acs:
        sys.exit("[!!] el spec no declara ningun AC-n")
    if data["rules"].get("require_spec_approved"):
        if estado != "approved":
            sys.exit(f"[!!] spec en '{estado}'. No implementes hasta que el usuario lo apruebe.")
        if not sig_fresh(sp, f.get("last_spec_sig")):
            sys.exit("[!!] el spec cambio despues de aprobarse: el sello ya no vale.")
    print(f"[ok] spec #{f['id']} approved y fresco. AC: {', '.join(acs)}")
    cmds = ac_comandos(text)
    if cmds:
        print(f"[i]  {len(cmds)} AC con comando declarado (gate.py verify los corre)")


# --- approve-spec ----------------------------------------------------------

def cmd_approve_spec(args) -> None:
    if not args.yes:
        sys.exit("[!!] approve-spec requiere --yes.\n"
                 "     Ningun agente aprueba por su cuenta: MUESTRALE el spec al\n"
                 "     usuario, PREGUNTALE si lo aprueba, y solo con su SI corre\n"
                 "     este comando con --yes.")
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, args.feature)
    sp = spec_path(p, f)
    if not sp.exists():
        sys.exit(f"[!!] no existe {sp}")
    trabajo = _trabajo_hecho(p, f)
    if f.get("last_spec_sig") and not sig_fresh(sp, f["last_spec_sig"]) and trabajo:
        # Re-aprobar aqui borraba el rastro: el backlog solo guardaba la firma
        # nueva, y el review y el verify del spec anterior seguian valiendo
        # para close mientras el numero de AC no cambiara.
        sys.exit(f"[!!] el spec de #{f['id']} ya estaba aprobado y hay trabajo hecho sobre el "
                 f"({', '.join(trabajo)}):\n"
                 "     cambiarlo ahora es una ENMIENDA, no una re-aprobacion. Escribe la\n"
                 "     propuesta (templates/enmienda.md), muestrasela al usuario junto al\n"
                 "     spec cambiado y, solo con su SI:\n"
                 f"     gate.py enmienda --feature {f['id']} --propuesta docs/<propuesta>.md --yes")
    text = sp.read_text(encoding="utf-8")
    acs = _acs_sellables(text)

    quien = _firmante(args.por)
    cuando = now_iso()
    text = _sellar_spec(text, f"Aprobado: {quien} · {cuando} · sellado por gate.py approve-spec --yes")
    sp.write_text(text, encoding="utf-8")

    _registrar_sello(f, sp, text, quien, cuando)
    save_backlog(p, data)
    bitacora(p, f"spec #{f['id']} approved por {quien} ({len(acs)} AC)")
    print(f"[ok] spec #{f['id']} aprobado y sellado. AC: {', '.join(acs)}")


def _trabajo_hecho(p, f) -> list[str]:
    """Lo que ya se construyo sobre el spec aprobado."""
    hechos = [x.name for x in (impl_path(p, f), review_path(p, f)) if x.exists()]
    if f.get("last_verify"):
        hechos.append("verify")
    return hechos


def _acs_sellables(text: str) -> list[str]:
    """Los AC del spec, o exit si sellarlo dejaria criterios sin verificar."""
    acs = spec_acs(text)
    if not acs:
        sys.exit("[!!] el spec no declara ningun AC-n: no se puede aprobar.")
    ignorados = acs_no_reconocidos(text, acs)
    if ignorados:
        # Aprobar aqui sella un spec al que le falta un criterio: nadie lo
        # verifica y todo el flujo sale en verde. El arreglo es reescribir una
        # linea, y el usuario esta justo aqui.
        sys.exit(f"[!!] estas lineas declaran {', '.join(ignorados)} y el parser NO\n"
                 "     los reconoce como AC: se sellaria un spec sin esos criterios\n"
                 "     y NADIE los verificaria (el check saldria en verde igual).\n"
                 "     Escribelos como '- AC-n: Given/When/Then' -- el titulo entre\n"
                 "     parentesis o corchetes vale -- y vuelve a aprobar.")
    huecos = [x for x in acs_faltantes(acs) if x not in ignorados]
    if huecos:
        print(f"[!] OJO: la numeracion salta, falta(n) {', '.join(huecos)}.")
    return acs


def _sellar_spec(text: str, sello: str) -> str:
    # Reemplazo con lambda: un '\' en --por no se lee como escape de re.sub.
    if "Estado:" in text:
        text = re.sub(r"^Estado:.*$", "Estado: approved", text, count=1, flags=re.M)
    else:
        text = text.replace("\n", "\n\nEstado: approved\n", 1)
    if "Aprobado:" in text:
        return re.sub(r"^Aprobado:.*$", lambda _: sello, text, count=1, flags=re.M)
    return re.sub(r"^(Estado: approved)$", lambda m: m.group(1) + "\n" + sello,
                  text, count=1, flags=re.M)


def _registrar_sello(f: dict, sp: Path, text: str, quien: str, cuando: str) -> None:
    f["last_spec_sig"] = sign(sp)   # se firma DESPUES de escribir el sello
    f["aprobado_por"] = quien
    f["aprobado_at"] = cuando
    # La huella por AC es la linea base de la proxima enmienda: sin ella no hay
    # forma de saber que AC toco.
    f["spec_huella"] = spec_huella(text)


# --- enmienda --------------------------------------------------------------
#
# Cambiar un spec que ya tiene evidencia, review o verify encima. Antes se
# hacia a mano con approve-spec: el backlog quedaba solo con la firma nueva,
# probar que AC habia cambiado exigia reconstruir el spec anterior, y el review
# y el verify viejos seguian valiendo para close.

COMENTARIO_RE = re.compile(r"<!--.*?-->", re.S)
# (nombre en el mensaje, prefijo del encabezado ya normalizado)
SECCIONES_PROPUESTA = (("Por que", "por que"), ("Cambios al spec", "cambio"),
                       ("Lo que NO cambia", "lo que no cambia"))


def _normal(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.strip().lower()


def _propuesta(p: dict, f: dict, valor: str) -> tuple[Path, str]:
    """La propuesta aprobada: un archivo real dentro de docs/. Devuelve (ruta, rel)."""
    crudo = Path(valor).expanduser()
    if not crudo.is_absolute():
        crudo = crudo if (Path.cwd() / crudo).exists() else p["root"] / crudo
    if crudo.is_symlink():
        sys.exit(f"[!!] la propuesta es un enlace: {valor}. Sella el archivo real.")
    real, docs = crudo.resolve(), p["docs"].resolve()
    if docs not in real.parents:
        sys.exit(f"[!!] la propuesta tiene que vivir en docs/ del proyecto: {valor}")
    if not real.is_file():
        sys.exit(f"[!!] no existe la propuesta {valor}")
    propios = {x.resolve() for x in (spec_path(p, f), impl_path(p, f), review_path(p, f))}
    if real in propios:
        sys.exit(f"[!!] {real.name} es un documento de la feature, no una propuesta.")
    return real, (Path("docs") / real.relative_to(docs)).as_posix()


def _problemas_propuesta(texto: str) -> list[str]:
    """Que le falta a la propuesta para sellarse. Mide estructura, no calidad."""
    problemas = []
    if not texto.lstrip().startswith("# "):
        problemas.append("falta el titulo '# ...' en la primera linea")
    secs: dict[str, str] = {}
    actual = None
    for linea in COMENTARIO_RE.sub("", texto).splitlines():
        m = re.match(r"^##[^\S\n]+(.+?)[^\S\n]*$", linea)
        if m:
            actual = _normal(m.group(1))
            secs.setdefault(actual, "")
        elif actual is not None:
            secs[actual] += linea + "\n"
    for nombre, prefijo in SECCIONES_PROPUESTA:
        cuerpos = [c for k, c in secs.items() if k.startswith(prefijo)]
        if not cuerpos:
            problemas.append(f"falta la seccion '## {nombre}'")
        elif not any(c.strip() for c in cuerpos):
            problemas.append(f"la seccion '## {nombre}' esta vacia (solo guia)")
    return problemas


def _nombra(texto: str, ac: str) -> bool:
    return bool(re.search(rf"\b{re.escape(ac)}(?!\d)", texto))


def _titulo_propuesta(texto: str) -> str:
    titulo = texto.lstrip().splitlines()[0][2:].strip()
    # 'Propuesta E-3 (#13): los smokes...' -> 'los smokes...': el numero lo pone el gate.
    corto = re.sub(r"^(?:Propuesta|Enmienda)\b[^:]*:[^\S\n]*", "", titulo, flags=re.I)
    return corto or titulo


def _siguiente_enmienda(text: str, f: dict) -> int:
    """El proximo E-n libre, contando tambien las enmiendas escritas a mano."""
    usados = [int(n) for n in re.findall(r"^#{2,4}[^\S\n]+E-(\d+)\b", text, re.M)]
    for e in f.get("enmiendas") or []:
        m = re.fullmatch(r"E-(\d+)", str(e.get("id", ""))) if isinstance(e, dict) else None
        if m:
            usados.append(int(m.group(1)))
    return max(usados, default=0) + 1


def _describir_alcance(alcance: dict | None) -> str:
    if alcance is None:
        return "no medidos (el sello anterior no guardo huella por AC)"
    partes = ([f"{a} cambiado" for a in alcance["cambiados"]]
              + [f"{a} nuevo" for a in alcance["nuevos"]]
              + [f"{a} retirado" for a in alcance["retirados"]])
    texto = ", ".join(partes) or "ninguno"
    return texto + ("; cambio texto fuera de los AC" if alcance["resto"] else "")


def _anotar_enmienda(text: str, eid: str, titulo: str, firma: str,
                     propuesta: str, detalle: str) -> str:
    """Agrega la entrada al final de 'Enmiendas posteriores a la aprobacion'."""
    entrada = (f"### {eid}: {titulo}\n\n"
               f"Enmienda: {eid} · {firma} · sellada por gate.py enmienda --yes\n"
               f"Propuesta: `{propuesta}`\n"
               f"AC tocados: {detalle}\n")
    m = ENMIENDAS_RE.search(text)
    if m is None:
        return (text.rstrip("\n") + "\n\n## Enmiendas posteriores a la aprobacion\n\n"
                + entrada)
    fin = re.compile(r"^#{1,2}[^\S\n#]", re.M).search(text, m.end())
    if fin is None:
        return text.rstrip("\n") + "\n\n" + entrada
    return text[:fin.start()].rstrip("\n") + "\n\n" + entrada + "\n" + text[fin.start():]


def _sellar_propuesta(texto: str, sello: str) -> str:
    if re.search(r"^Estado:", texto, re.M):
        texto = re.sub(r"^Estado:.*$", "Estado: aprobada", texto, count=1, flags=re.M)
    else:
        texto = texto.replace("\n", "\n\nEstado: aprobada\n", 1)
    if re.search(r"^Aprobada:", texto, re.M):
        return re.sub(r"^Aprobada:.*$", lambda _: sello, texto, count=1, flags=re.M)
    return re.sub(r"^(Estado: aprobada)$", lambda m: m.group(1) + "\n" + sello,
                  texto, count=1, flags=re.M)


def cmd_enmienda(args) -> None:
    if not args.yes:
        sys.exit("[!!] enmienda requiere --yes.\n"
                 "     Ningun agente enmienda por su cuenta: MUESTRALE al usuario la\n"
                 "     propuesta y el spec cambiado, PREGUNTALE si los aprueba, y solo\n"
                 "     con su SI corre este comando con --yes.")
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, args.feature)
    fid = f["id"]
    sp = spec_path(p, f)
    if not sp.exists():
        sys.exit(f"[!!] no existe {sp}")
    anterior = f.get("last_spec_sig")
    if not anterior:
        sys.exit(f"[!!] el spec de #{fid} nunca se aprobo: no hay nada que enmendar.\n"
                 f"     Apruebalo con gate.py approve-spec --feature {fid} --yes (tras el SI del usuario).")
    if sig_fresh(sp, anterior):
        sys.exit("[!!] el spec no cambio desde su ultimo sello: aplica en el los cambios de\n"
                 "     la propuesta y vuelve a correr la enmienda.")
    prop, rel = _propuesta(p, f, args.propuesta)
    for otra in data["features"]:
        for e in otra.get("enmiendas") or []:
            if isinstance(e, dict) and e.get("propuesta") == rel:
                sys.exit(f"[!!] {rel} ya sello la {e.get('id')} de la #{otra.get('id')}: "
                         "cada enmienda lleva su propia propuesta.")
    ptext = prop.read_text(encoding="utf-8")
    problemas = _problemas_propuesta(ptext)
    if problemas:
        sys.exit("[!!] la propuesta no esta lista para sellarse:\n"
                 + "\n".join(f"     - {x}" for x in problemas)
                 + "\n     Plantilla: templates/enmienda.md")

    text = sp.read_text(encoding="utf-8")
    acs = _acs_sellables(text)
    base = f.get("spec_huella")
    alcance = None
    if isinstance(base, dict) and isinstance(base.get("acs"), dict):
        alcance = comparar_huellas(base, spec_huella(text))
        tocados = alcance["cambiados"] + alcance["nuevos"] + alcance["retirados"]
        if not tocados and not alcance["resto"]:
            sys.exit("[!!] fuera de Estado/Aprobado y de la seccion de enmiendas, el spec es\n"
                     "     el mismo que se sello: no hay cambio que enmendar.")
        limpio = COMENTARIO_RE.sub("", ptext)
        sin_nombrar = [a for a in tocados if not _nombra(limpio, a)]
        if sin_nombrar:
            # El usuario aprueba la propuesta, no el diff: un AC que cambio sin
            # que la propuesta lo nombre se sellaria sin que nadie lo aprobara.
            sys.exit(f"[!!] el spec cambio {', '.join(sin_nombrar)} y la propuesta no lo nombra.\n"
                     "     O ese cambio se colo sin aprobacion (reviertelo en el spec), o\n"
                     "     falta en la propuesta (agregalo y vuelve a mostrarsela al usuario).")
    else:
        print("[!] el sello anterior no guardo huella por AC: no puedo acotar que AC toca\n"
              "    esta enmienda. Queda registrada como 'no medidos'; revisa el diff a mano.")

    quien = _firmante(args.por)
    cuando = now_iso()
    eid = f"E-{_siguiente_enmienda(text, f)}"
    detalle = _describir_alcance(alcance)
    text = _anotar_enmienda(text, eid, _titulo_propuesta(ptext), f"{quien} · {cuando}",
                            rel, detalle)
    text = _sellar_spec(text, f"Aprobado: {quien} · {cuando} · sellado por gate.py enmienda --yes ({eid})")
    prop.write_text(_sellar_propuesta(
        ptext, f"Aprobada: {quien} · {cuando} · {eid} de la #{fid} · sellada por gate.py enmienda --yes"),
        encoding="utf-8")
    sp.write_text(text, encoding="utf-8")

    f.setdefault("enmiendas", []).append({
        "id": eid, "at": cuando, "por": quien, "propuesta": rel,
        "propuesta_sig": sign(prop), "acs": alcance,
        "spec_sig_anterior": {k: anterior.get(k) for k in ("size", "hash")},
    })
    _registrar_sello(f, sp, text, quien, cuando)
    save_backlog(p, data)
    bitacora(p, f"spec #{fid} enmienda {eid} aprobada por {quien} ({rel}; AC tocados: {detalle})")
    print(f"[ok] enmienda {eid} de #{fid} sellada. AC tocados: {detalle}")
    print(f"     spec re-sellado ({len(acs)} AC) y propuesta sellada: {rel}")
    rp = review_path(p, f)
    if rp.exists():
        print(f"[!] {rp.name} se sello sobre el spec anterior: close ya no lo acepta.\n"
              "    Lanza un review nuevo sobre el spec enmendado.")
    if f.get("last_verify"):
        print(f"[!] el verify anterior no midio el spec enmendado: vuelve a correr "
              f"gate.py verify --feature {fid}.")


# --- revision --------------------------------------------------------------

# U+0085 (NEXT LINE), U+2028 (LINE SEPARATOR) y U+2029 (PARAGRAPH SEPARATOR) no
# son "c < ' '" (su valor de codigo es mayor a 0x20): un chequeo solo de control
# ASCII los deja pasar aunque casi todo visor que no sea una terminal cruda los
# rendericen como salto de linea. Mismo hueco en _firmante y en --motivo de
# --historico; un solo helper evita que se corrija uno y no el otro.
_SEPARADORES_UNICODE = "\u0085\u2028\u2029"


def _sin_saltos(valor: str) -> bool:
    """True si `valor` no tiene saltos de linea/control ASCII NI separadores
    Unicode de linea/parrafo (ver _SEPARADORES_UNICODE)."""
    return not any(c < " " or c == "\x7f" or c in _SEPARADORES_UNICODE for c in valor)


def _firmante(valor: str | None) -> str:
    """Quien firma va DENTRO del sello que estampa el gate.

    Un salto de linea ahi inyecta en el documento texto que nadie escribio, y
    cualquier lector del sellado (la cita de --retirados, entre otros) lo leeria
    como del revisor. No cambia el formato del sello: solo saca la inyeccion.
    """
    if valor is None:
        return getpass.getuser()
    if not valor.strip() or not _sin_saltos(valor):
        sys.exit("[!!] --por no admite saltos de linea ni caracteres de control "
                 "(incluidos U+0085/U+2028/U+2029):\n"
                 "     ese texto va DENTRO del sello que estampa el gate.")
    return valor.strip()


def cmd_revision(args) -> None:
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, args.feature)
    sp, rp = spec_path(p, f), review_path(p, f)
    if not sp.exists():
        sys.exit(f"[!!] no existe {sp}")
    if not rp.exists():
        sys.exit(f"[!!] no existe {rp}: escribe el review antes de sellarlo.")
    acs = spec_acs(sp.read_text(encoding="utf-8"))
    if not acs:
        # Sin AC, cubre_acs no tiene nada que exigir y el sello diria
        # "cubre 0 AC": un veredicto sobre nada, con forma de veredicto.
        sys.exit(f"[!!] el spec de #{f['id']} no declara ningun AC-n: no hay nada "
                 "que revisar.\n     Arregla el spec (revisa la forma de cada "
                 "linea AC-n) antes de sellar.")
    tarde = enmiendas_posteriores(f, f.get("last_review_enmiendas"))
    if tarde and sig_fresh(rp, f.get("last_review_sig")):
        # Re-sellar el mismo archivo le pondria fecha nueva a un veredicto
        # sobre el spec anterior.
        sys.exit(f"[!!] {rp.name} no cambio desde que se sello, y despues llego la enmienda "
                 f"{', '.join(tarde)}.\n"
                 "     Ese veredicto habla del spec anterior: lanza un review nuevo sobre\n"
                 "     el spec enmendado.")
    contexto = _multi_context(p, f, data["rules"]) if "multi_repo" in f else None
    rtext = rp.read_text(encoding="utf-8")
    _, faltan = cubre_acs(rtext, acs)
    if faltan:
        sys.exit(f"[!!] el review no responde por: {', '.join(faltan)}\n"
                 "     Cada AC-n necesita una fila que lo nombre y cite archivo:linea.")

    quien = _firmante(args.por)
    sello = (f"Revisado: {args.veredicto} · {now_iso()} · {quien} · "
             "estampado por gate.py revision")
    import re as _re
    if _re.search(r"^Revisado:.*$", rtext, _re.M):
        rtext = _re.sub(r"^Revisado:.*$", sello, rtext, count=1, flags=_re.M)
    else:
        rtext = rtext.rstrip() + "\n\n" + sello + "\n"
    rp.write_text(rtext, encoding="utf-8")

    f["last_review_sig"] = sign(rp)
    f["last_review_enmiendas"] = n_enmiendas(f)
    if contexto:
        f["last_review_context"] = contexto
    f["veredicto"] = args.veredicto
    save_backlog(p, data)
    bitacora(p, f"review #{f['id']} sellado: {args.veredicto} por {quien}")
    print(f"[ok] review #{f['id']} sellado como {args.veredicto} "
          f"(cubre {len(acs)} AC)")


# --- verify ----------------------------------------------------------------

def _multi_context(p, f, rules):
    from multirepo import Invalid, context
    try:
        return context(p, f, rules)
    except Invalid as exc:
        sys.exit(f"[!!] multi-repo: {exc}")

def cmd_verify(args) -> None:
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, args.feature)
    sp = spec_path(p, f)
    if not sp.exists():
        sys.exit(f"[!!] la feature #{f['id']} todavia no tiene spec: {sp.name}\n"
                 "     Escribe el spec y hazlo aprobar antes de verificar.")
    text = sp.read_text(encoding="utf-8")
    if spec_estado(text) != "approved":
        sys.exit(f"[!!] el spec de #{f['id']} esta '{spec_estado(text)}', no 'approved'.\n"
                 "     Verify corre sobre un spec aprobado por el usuario.")
    cmds = ac_comandos(text)
    acs = spec_acs(text)
    sin_comando = [a for a in acs if a not in cmds]
    contexto = _multi_context(p, f, data["rules"]) if "multi_repo" in f else None
    if contexto and not sig_fresh(sp, f.get("last_spec_sig")):
        sys.exit("[!!] spec stale: no verificar multi-repo sin aprobacion fresca")
    if not cmds:
        print("[i]  ningun AC declara comando: los verifica el reviewer a mano.")
        return
    timeout = int(data["rules"].get("verify_timeout_segundos", 900))
    # Los AC miden el arbol de la FEATURE. Correrlos desde la raiz mide develop:
    # verde falso si el comando no engancha nada, rojo falso si la rama vecina
    # tiene otro codigo. Se corre en el worktree cuando existe.
    cwd = p["root"]
    wt = f.get("worktree")
    if "multi_repo" not in f:
        if wt and Path(wt).is_dir():
            cwd = Path(wt)
            print(f"[i]  verify corre en el worktree de #{f['id']}: {cwd}")
        elif wt:
            sys.exit(f"[!!] el worktree declarado de #{f['id']} no existe: {wt}\n"
                     "     No corro los AC contra la raiz: mediria otra rama.")
        else:
            print(f"[!] #{f['id']} sin worktree: los AC se miden sobre la raiz "
                  f"({p['root']}), que esta en la rama de integracion.")
    out = [f"# Verify - Feature #{f['id']}", "", f"Corrido: {now_iso()}",
           f"Arbol: {cwd}", ""]
    fallos = 0
    for ac, cmd in cmds.items():
        print(f"-- {ac}: {cmd}")
        try:
            r = subprocess.run(cmd, shell=True, cwd=str(cwd),
                               capture_output=True, text=True, timeout=timeout)
            code, salida = r.returncode, (r.stdout + r.stderr)[-4000:]
        except subprocess.TimeoutExpired:
            code, salida = 124, f"TIMEOUT tras {timeout}s"
        estado = "PASS" if code == 0 else "FAIL"
        if code != 0:
            fallos += 1
        print(f"   {estado} (exit {code})")
        out += [f"## {ac} — {estado} (exit {code})", "", f"Comando: `{cmd}`", "",
                "```", salida.strip() or "(sin salida)", "```", ""]
    vp = p["docs"] / f"verify-{f['id']}.md"
    vp.parent.mkdir(parents=True, exist_ok=True)
    vp.write_text("\n".join(out), encoding="utf-8")
    f["last_verify"] = {"at": now_iso(), "fallos": fallos, "total": len(cmds),
                        "acs_declarados": len(acs),
                        "sin_comando": sin_comando,
                        "enmiendas": n_enmiendas(f)}
    if contexto:
        from multirepo import Invalid, context
        try:
            vigente = context(p, f, data["rules"]) == contexto
        except Invalid:
            vigente = False
        if not vigente:
            fallos += 1
            f["last_verify"]["fallos"] = fallos
            print("[!!] contexto multi-repo cambio durante verify")
        f["last_verify"].update(context=contexto, report_sig=sign(vp))
    save_backlog(p, data)
    print(f"\n[{'ok' if not fallos else '!!'}] {len(cmds)-fallos}/{len(cmds)} AC en verde -> {vp.name}")
    if sin_comando:
        print(f"[!] {len(sin_comando)}/{len(acs)} AC NO se midieron (sin comando "
              f"declarado): {', '.join(sin_comando)}\n"
              "    Ese verde NO cubre esos AC: los verifica el reviewer a mano.")
    if fallos:
        sys.exit(1)


# --- close -----------------------------------------------------------------

def git_merge(p: dict, f: dict, destino: str) -> str:
    """Integra la rama de la feature en <destino>. Devuelve el sha del merge.

    Existe porque close SOLO escribia 'integrado_en' en el backlog e imprimia
    'integra en <rama>': afirmaba una integracion que nunca ocurria, y la
    feature quedaba 'done' con su rama sin mergear. Un arnes que combate los
    falsos verdes no puede permitirse uno propio.

    Cualquier problema aborta con exit 1 ANTES de que el backlog se toque: es
    preferible una feature que no cierra a un 'done' que miente.
    """
    repo = p["root"]
    rama = f.get("branch")
    if not rama:
        sys.exit(f"[!!] la feature #{f['id']} no tiene rama registrada: "
                 "no se puede integrar sola.\n"
                 f"     Mergeala a mano y volve a cerrar, o arranca con worktree.py start.")

    code, _ = git(["rev-parse", "--verify", rama], repo)
    if code != 0:
        sys.exit(f"[!!] la rama '{rama}' de la feature #{f['id']} no existe en {repo}.")

    code, out = git(["status", "--porcelain"], repo)
    if code != 0 or out.strip():
        sys.exit(f"[!!] el repo tiene cambios sin commitear: no mergeo sobre un arbol sucio.\n"
                 f"     Commitealos o guardalos antes de cerrar.\n{out}")

    code, actual = git(["rev-parse", "--abbrev-ref", "HEAD"], repo)
    if code != 0:
        sys.exit(f"[!!] no pude leer la rama actual de {repo}:\n{actual}")
    if actual.strip() != destino:
        code, out = git(["checkout", destino], repo)
        if code != 0:
            sys.exit(f"[!!] no pude pararme en '{destino}':\n{out}")

    code, out = git(["merge", "--no-ff", rama,
                     "-m", f"merge: {rama} -> {destino} (cierre de feature del arnes)"], repo)
    if code != 0:
        git(["merge", "--abort"], repo)
        sys.exit(f"[!!] el merge de '{rama}' en '{destino}' fallo (abortado, nada quedo a medias):\n{out}\n"
                 "     Resolvelo a mano y volve a cerrar.")

    code, sha = git(["rev-parse", "--short", "HEAD"], repo)
    return sha.strip() if code == 0 else "?"


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def archivar_progress_actual(p: dict, f: dict) -> Path | None:
    """Mueve progress/current-<id>.md a progress/archive/ al cerrar."""
    origen = p["progress"] / f"current-{f['id']}.md"
    if not origen.exists():
        return None
    destino = p["progress"] / "archive" / origen.name
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        destino = destino.with_name(f"current-{f['id']}-{now_iso().replace(':', '').replace('-', '')}.md")
    origen.rename(destino)
    f["progress_archive"] = _rel(p["root"], destino)
    return destino


def cmd_close(args) -> None:
    p = paths()
    data = load_backlog(p)
    rules = data["rules"]
    f = get_feature(data, args.feature)
    fid = f["id"]
    multi = "multi_repo" in f or args.integrated
    if multi and args.status == "done":
        rules = dict(rules, require_spec_approved=True, require_review=True,
                     require_verify_green=True, require_leccion=True)
        if not args.integrated:
            sys.exit("[!!] multi-repo requiere close --status done --integrated --to <rama>")
    if args.integrated and args.status != "done":
        sys.exit("[!!] --integrated solo aplica a --status done")
    if args.historico and args.postmerge:
        sys.exit("[!!] --historico y --postmerge son mutuamente excluyentes: todo el mapa se "
                 "cierra en un solo modo (docs/diseno-arnes-cierre-historico.md)")
    if args.historico and not (args.integrated and args.status == "done"):
        sys.exit("[!!] --historico solo aplica a close --status done --integrated")
    if args.integrated and args.status == "done" and not args.postmerge and not args.historico:
        sys.exit("[!!] postmerge obligatorio: declara bases por repo con --postmerge <mapa.json>, "
                 "o usa --historico si la base preintegracion no se puede medir con el contrato vigente")
    motivo_historico = None
    if args.historico:
        if not args.yes:
            sys.exit("[!!] --historico requiere --yes.\n"
                     "     Es un cierre SIN base medible: MUESTRALE al usuario por que (contrato\n"
                     "     roto, tests renombrados por otra feature, etc.) y PREGUNTALE si lo\n"
                     "     autoriza. Solo con su SI corre este comando con --yes y --motivo.\n"
                     "     Aviso: --yes/--motivo son una barrera de PROCESO (igual que --yes de\n"
                     "     approve-spec), no una restriccion TECNICA de antiguedad ni de intento\n"
                     "     previo de medir una base: nada en este gate impide invocar --historico\n"
                     "     sobre una feature nueva con base perfectamente medible. Quien autoriza\n"
                     "     responde por esa decision; el camino normal (--postmerge) sigue siendo\n"
                     "     el UNICO recomendado para features nuevas por compromiso de proceso,\n"
                     "     no porque este gate lo bloquee automaticamente.")
        motivo_historico = args.motivo
        if not motivo_historico or not motivo_historico.strip() or not _sin_saltos(motivo_historico):
            sys.exit("[!!] --historico requiere --motivo '<texto>' no vacio, sin saltos de linea\n"
                     "     ni caracteres de control (incluidos U+0085/U+2028/U+2029): queda\n"
                     "     escrito dentro del backlog.")
        motivo_historico = motivo_historico.strip()
    if args.retirados and not args.integrated:
        sys.exit("[!!] --retirados solo aplica a close --integrated: lo verifica la medicion postmerge")

    if args.status == "done" and not args.to:
        sys.exit("[!!] close --status done requiere --to <rama>.\n"
                 "     PREGUNTALE AL USUARIO a que rama se integra: no lo adivines.")
    if args.publicar_atlassian and not p["atlassian"].exists():
        sys.exit("[!!] --publicar-atlassian exige harness/atlassian.json")

    fallos: list[str] = []
    avisos_cierre: list[str] = []
    stext = ""
    sp = spec_path(p, f)
    if not sp.exists():
        fallos.append(f"no existe {sp.name}")
        acs: list[str] = []
    else:
        stext = sp.read_text(encoding="utf-8")
        acs = spec_acs(stext)
        if not acs:
            fallos.append("spec sin AC-n")
        if rules.get("require_spec_approved"):
            if spec_estado(stext) != "approved":
                fallos.append(f"spec en '{spec_estado(stext)}', se requiere approved")
            elif not sig_fresh(sp, f.get("last_spec_sig")):
                fallos.append("el spec cambio despues de aprobarse (sello invalido)")

    if args.status == "done":
        ip = impl_path(p, f)
        if not ip.exists():
            fallos.append(f"sin evidencia ({ip.name})")
        else:
            _, faltan = cubre_acs(ip.read_text(encoding="utf-8"), acs)
            if faltan:
                fallos.append(f"evidencia sin cubrir: {', '.join(faltan)}")

        if rules.get("require_review"):
            rp = review_path(p, f)
            if not rp.exists():
                fallos.append(f"sin review ({rp.name})")
            else:
                rtext = rp.read_text(encoding="utf-8")
                sello = sello_revision(rtext)
                if sello != "approved":
                    fallos.append(f"review sin sello approved (actual: {sello or 'ninguno'})")
                if not sig_fresh(rp, f.get("last_review_sig")):
                    fallos.append("el review cambio despues de sellarse")
                tarde = enmiendas_posteriores(f, f.get("last_review_enmiendas"))
                if tarde:
                    fallos.append(f"el review se sello antes de la enmienda {', '.join(tarde)}: "
                                  "re-revisa sobre el spec enmendado")
                _, faltan = cubre_acs(rtext, acs)
                if faltan:
                    fallos.append(f"el review no responde por: {', '.join(faltan)}")

        if rules.get("require_verify_green"):
            lv = f.get("last_verify")
            if (not isinstance(lv, dict) or type(lv.get("total")) is not int or lv["total"] <= 0
                    or type(lv.get("fallos")) is not int or not lv.get("at")):
                fallos.append("verify ausente, vacio o no registrado")
            elif lv["fallos"] != 0:
                fallos.append(f"verify con {lv['fallos']} AC en rojo")
            else:
                # Un verify viejo, corrido cuando el spec tenia otros AC, no es
                # un veredicto sobre el spec actual: 'N/N verde' puede venir de
                # medir un subconjunto que ya no existe.
                declarados = lv.get("acs_declarados")
                if type(declarados) is int and declarados != len(acs):
                    fallos.append(
                        f"verify obsoleto: midio un spec de {declarados} AC y "
                        f"el actual tiene {len(acs)}; vuelve a correr verify")
                tarde = enmiendas_posteriores(f, lv.get("enmiendas"))
                if tarde:
                    fallos.append(f"verify anterior a la enmienda {', '.join(tarde)}: "
                                  "vuelve a correr verify")
                sin_cmd = lv.get("sin_comando") or []
                if sin_cmd:
                    avisos_cierre.append(
                        f"{len(sin_cmd)}/{len(acs)} AC no los midio ninguna suite "
                        f"(sin comando declarado): {', '.join(sin_cmd)}. "
                        "El verde de verify NO habla de ellos; responde el review.")

        if multi:
            from multirepo import Invalid, context
            try:
                contexto = context(p, f, data["rules"])
                if f.get("last_review_context") != contexto:
                    fallos.append("review no corresponde al contexto multi-repo actual")
                lv = f.get("last_verify") or {}
                vp = p["docs"] / f"verify-{fid}.md"
                if (not isinstance(lv, dict) or lv.get("context") != contexto
                        or not sig_fresh(vp, lv.get("report_sig"))
                        or lv.get("total") != len(ac_comandos(stext))):
                    fallos.append("verify no corresponde al contexto/reporte actual")
            except Invalid as exc:
                fallos.append(f"multi-repo: {exc}")
            check = Reporte()
            abiertas = [x for x in data["features"] if x.get("status") in ABIERTOS]
            for other in abiertas:
                _check_feature(p, other, rules, check)
            _check_rutas_protegidas(p, rules, check, data)
            _check_aislamiento(abiertas, check, p, data["rules"])
            fallos.extend(check.fallos)

        if rules.get("require_leccion") and not args.leccion:
            fallos.append("falta --leccion <clase> (o --leccion ninguna --leccion-motivo '<por que>')")
        if args.leccion == "ninguna" and not args.leccion_motivo:
            fallos.append("--leccion ninguna exige --leccion-motivo")
        if multi and args.leccion == "ninguna":
            fallos.append("multi-repo exige leccion real, no 'ninguna'")
        # la leccion vive como SKILL del agente: exigimos que exista de verdad
        if args.leccion and args.leccion != "ninguna":
            sys.path.insert(0, str(Path(__file__).parent))
            from leccion import buscar as buscar_leccion
            if not buscar_leccion(args.leccion):
                fallos.append(
                    f"la leccion '{args.leccion}' no existe como skill "
                    "(creala antes de cerrar: skill_manage en Hermes; SKILL.md en Claude Code, GPT o Grok)")

    if fallos:
        print(f"[!!] close #{fid} BLOQUEADO por {len(fallos)} regla(s):")
        for x in fallos:
            print(f"     - {x}")
        sys.exit(1)

    for x in avisos_cierre:
        print(f"[!] {x}")

    from cierre_local import preflight, transaction
    try:
        preflight(p, fid)
    except (OSError, ValueError) as exc:
        sys.exit(f"[!!] cierre local bloqueado: {exc}")

    merged = None
    manifest = None
    if args.status == "done" and args.integrated:
        from multirepo import Invalid, check_registered
        try:
            manifest = check_registered(p, f, rules, integrated=True, target=args.to)
            if args.historico:
                from medicion_destino import measure_historico
                f["mediciones_destino"] = measure_historico(p, f, data["rules"], manifest, args.retirados)
            else:
                from medicion_destino import measure
                f["mediciones_destino"] = measure(p, f, data["rules"], manifest, args.postmerge, args.retirados)
            # Las suites pueden tener efectos laterales: revalidar todos los tips.
            check_registered(p, f, rules, integrated=True, target=args.to)
        except Invalid as exc:
            sys.exit(f"[!!] multi-repo: {exc}")
        f["integraciones"] = manifest["repos"]
        f.pop("merge_commit", None)
        if args.historico:
            f["cierre_historico"] = {"motivo": motivo_historico, "autorizado_por": getpass.getuser(),
                                     "at": now_iso()}
    elif args.status == "done" and args.to:
        merged = git_merge(p, f, args.to)

    try:
        with transaction(p, fid):
            f["status"] = args.status
            f["closed_at"] = now_iso()
            if args.to:
                f["integrado_en"] = args.to
            if merged:
                f["merge_commit"] = merged
            if args.leccion:
                f["leccion"] = args.leccion
            if args.leccion_motivo:
                f["leccion_motivo"] = args.leccion_motivo
            if args.nota:
                f["note"] = args.nota
            progress_archivado = archivar_progress_actual(p, f) if args.status == "done" else None
            save_backlog(p, data)
            docs_sincronizados = []
            if args.status == "done":
                import documentacion
                docs_sincronizados = documentacion.sync(p, data)
                if args.integrated:
                    assert manifest is not None  # Validado antes de medir destinos.
                    from multirepo import protected_snapshot, snapshot_matches
                    current_protected = protected_snapshot(p, manifest, rules)
                    if not snapshot_matches(f['multi_repo_protected'], current_protected):
                        raise ValueError('generacion modifico bytes protegidos fuera del contrato')
                    f['multi_repo_protected'] = current_protected
                    save_backlog(p, data)
            atlassian_sync = False
            if args.publicar_atlassian:
                import atlassian
                atlassian.cmd_push(argparse.Namespace(feature=str(fid)))
                atlassian_sync = True
            if progress_archivado:
                bitacora(p, f"progress #{fid} archivado en {f['progress_archive']}")
            if docs_sincronizados:
                bitacora(p, f"documentacion PRD/SDD sincronizada para #{fid}")
            bitacora(p, f"close #{fid} status={args.status}" +
                     (f" -> {args.to}" if args.to else "") +
                     (f" merge={merged}" if merged else "") +
                     (f" leccion={args.leccion}" if args.leccion else ""))
    except (Exception, SystemExit, KeyboardInterrupt) as exc:
        if merged:
            print(f"[!] merge local conservado: {merged}; no resetear ni repetir a ciegas.")
        if args.publicar_atlassian:
            print("[!] publicacion remota puede ser parcial; reconciliar antes de reintentar.")
        sys.exit(f"[!!] cierre local fallo; rollback intentado: {exc}")
    print(f"[ok] feature #{fid} cerrada como {args.status}")
    if merged:
        print(f"[ok] rama integrada en {args.to} (merge {merged})")
    if progress_archivado:
        print(f"[ok] progreso archivado en {f['progress_archive']}")
    if docs_sincronizados:
        print("[ok] documentacion PRD/SDD sincronizada")
    if args.leccion:
        # La leccion escrita desde Claude Code se mueve a Hermes con un enlace de
        # vuelta: ambos hosts la cargan. Fuera de la transaccion: nunca bloquea.
        try:
            from leccion import espejo_al_cerrar
            aviso = espejo_al_cerrar(args.leccion)
        except Exception as exc:
            aviso = f"[!] no se pudo espejar la leccion en Hermes: {exc}"
        if aviso:
            print(aviso)
    print("[i]  la integracion es LOCAL: publicar es una decision aparte.")
    if args.status == "done" and not getattr(args, "sin_contexto", False):
        # El cierre cambio el arbol: el grafo, el hub y el vault que quedaron
        # describen el codigo de antes. Se refresca DESPUES del cierre para no
        # mezclarlo con la transaccion de rollback.
        try:
            import contexto
            if contexto._desactivado():
                print("[i]  HARNESS_SIN_CONTEXTO: no se refresca el contexto.")
                parte = None
            else:
                print("[i]  refrescando contexto (grafo/hub/vault) tras el cierre...")
                parte = contexto.refrescar(p, con_vault=True, con_hub=True)
            if parte and parte["fallos"]:
                print("[!] contexto NO quedo refrescado; corre contexto.py refrescar:")
                for x in parte["fallos"]:
                    print(f"     - {x}")
            else:
                if parte:
                    print("[ok] contexto refrescado")
        except Exception as exc:
            print(f"[!] no se pudo refrescar el contexto: {exc}")
    if atlassian_sync:
        print(f"[ok] Atlassian sincronizado para feature #{fid}")
    elif (p["atlassian"]).exists():
        print("[i]  hay atlassian.json: corre atlassian.py push --feature "
              f"{fid} para reflejarlo en Jira y Confluence, o usa close --publicar-atlassian.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Gates del harness-flow (exit!=0 si falta algo)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check").set_defaults(fn=cmd_check)

    s = sub.add_parser("check-spec"); s.add_argument("--feature", required=True)
    s.set_defaults(fn=cmd_check_spec)

    s = sub.add_parser("approve-spec"); s.add_argument("--feature", required=True)
    s.add_argument("--yes", action="store_true"); s.add_argument("--por")
    s.set_defaults(fn=cmd_approve_spec)

    s = sub.add_parser("enmienda"); s.add_argument("--feature", required=True)
    s.add_argument("--propuesta", required=True,
                   help="docs/<propuesta>.md que el usuario aprobo (templates/enmienda.md)")
    s.add_argument("--yes", action="store_true"); s.add_argument("--por")
    s.set_defaults(fn=cmd_enmienda)

    s = sub.add_parser("revision"); s.add_argument("--feature", required=True)
    s.add_argument("--veredicto", required=True,
                   choices=["approved", "changes_requested", "blocked"])
    s.add_argument("--por"); s.set_defaults(fn=cmd_revision)

    s = sub.add_parser("verify"); s.add_argument("--feature", required=True)
    s.set_defaults(fn=cmd_verify)

    s = sub.add_parser("close"); s.add_argument("--feature", required=True)
    s.add_argument("--status", required=True, choices=["done", "blocked"])
    s.add_argument("--to"); s.add_argument("--leccion")
    s.add_argument("--integrated", action="store_true",
                   help="verifica integracion manual multi-repo registrada, sin merge")
    s.add_argument("--postmerge", help="mapa de bases preintegracion; close ejecuta suites reales en TODOS los destinos")
    s.add_argument("--historico", action="store_true",
                   help="cierre YA integrado cuya base preintegracion no se puede medir con el contrato "
                        "vigente; mide el destino sin base (exige --yes y --motivo)")
    s.add_argument("--yes", action="store_true",
                   help="autorizacion explicita del usuario para --historico (nunca la pasa el agente solo)")
    s.add_argument("--motivo", help="por que no hay base medible; se persiste en cierre_historico")
    s.add_argument("--retirados", help="tests de la base que la feature BORRO (verificados en su delta y citados en el review)")
    s.add_argument("--leccion-motivo", dest="leccion_motivo"); s.add_argument("--nota")
    s.add_argument("--sin-contexto", action="store_true", dest="sin_contexto",
                   help="no refrescar grafo/hub/vault despues del cierre")
    s.add_argument("--publicar-atlassian", action="store_true", dest="publicar_atlassian",
                   help="despues del cierre, sincroniza Jira y Confluence con atlassian.py push")
    s.set_defaults(fn=cmd_close)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
