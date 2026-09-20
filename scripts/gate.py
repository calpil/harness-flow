#!/usr/bin/env python3
"""Gates del harness-flow. TODOS devuelven exit != 0 cuando algo falta.

Este archivo es lo que hace que el proceso sea un gate y no una intencion:
un agente puede olvidarse de una regla, pero no puede hacer que un exit 1
sea un exit 0.

  gate.py check
  gate.py check-spec   --feature <id>
  gate.py approve-spec --feature <id> --yes
  gate.py revision     --feature <id> --veredicto approved|changes_requested|blocked
  gate.py verify       --feature <id>
  gate.py close        --feature <id> --status done|blocked --to <rama> [--leccion <clase>]
"""
from __future__ import annotations

import argparse
import fnmatch
import getpass
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (  # noqa: E402
    Reporte, acs_faltantes, acs_no_reconocidos, bitacora, cubre_acs, get_feature, git, impl_path, load_backlog,
    now_iso, paths, review_path, ac_comandos, save_backlog, sello_revision,
    sig_fresh, sign, spec_acs, spec_estado, spec_path,
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
            if sello is None:
                r.aviso(f"#{fid} review sin sello (un 'Veredicto:' a mano no cuenta)",
                        f"gate.py revision --feature {fid} --veredicto approved")
            elif sello != "approved":
                r.aviso(f"#{fid} review sellado como '{sello}'")
            else:
                r.ok(f"#{fid} review approved y sellado")


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
    text = sp.read_text(encoding="utf-8")
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

    quien = args.por or getpass.getuser()
    cuando = now_iso()
    if "Estado:" in text:
        import re as _re
        text = _re.sub(r"^Estado:.*$", "Estado: approved", text, count=1, flags=_re.M)
    else:
        text = text.replace("\n", f"\n\nEstado: approved\n", 1)
    sello = f"Aprobado: {quien} · {cuando} · sellado por gate.py approve-spec --yes"
    if "Aprobado:" in text:
        import re as _re
        text = _re.sub(r"^Aprobado:.*$", sello, text, count=1, flags=_re.M)
    else:
        import re as _re
        text = _re.sub(r"^(Estado: approved)$", r"\1\n" + sello, text, count=1, flags=_re.M)
    sp.write_text(text, encoding="utf-8")

    f["last_spec_sig"] = sign(sp)   # se firma DESPUES de escribir el sello
    f["aprobado_por"] = quien
    f["aprobado_at"] = cuando
    save_backlog(p, data)
    bitacora(p, f"spec #{f['id']} approved por {quien} ({len(acs)} AC)")
    print(f"[ok] spec #{f['id']} aprobado y sellado. AC: {', '.join(acs)}")


# --- revision --------------------------------------------------------------

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
    contexto = _multi_context(p, f, data["rules"]) if "multi_repo" in f else None
    rtext = rp.read_text(encoding="utf-8")
    _, faltan = cubre_acs(rtext, acs)
    if faltan:
        sys.exit(f"[!!] el review no responde por: {', '.join(faltan)}\n"
                 "     Cada AC-n necesita una fila que lo nombre y cite archivo:linea.")

    quien = args.por or getpass.getuser()
    sello = (f"Revisado: {args.veredicto} · {now_iso()} · {quien} · "
             "estampado por gate.py revision")
    import re as _re
    if _re.search(r"^Revisado:.*$", rtext, _re.M):
        rtext = _re.sub(r"^Revisado:.*$", sello, rtext, count=1, flags=_re.M)
    else:
        rtext = rtext.rstrip() + "\n\n" + sello + "\n"
    rp.write_text(rtext, encoding="utf-8")

    f["last_review_sig"] = sign(rp)
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
                        "sin_comando": sin_comando}
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
    if args.integrated and not args.postmerge:
        sys.exit("[!!] postmerge obligatorio: declara bases por repo con --postmerge <mapa.json>")

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
                    "(creala antes de cerrar: skill_manage en Hermes, SKILL.md en Claude Code/GPT)")

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
            from medicion_destino import measure
            f["mediciones_destino"] = measure(p, f, data["rules"], manifest, args.postmerge)
            # Las suites pueden tener efectos laterales: revalidar todos los tips.
            check_registered(p, f, rules, integrated=True, target=args.to)
        except Invalid as exc:
            sys.exit(f"[!!] multi-repo: {exc}")
        f["integraciones"] = manifest["repos"]
        f.pop("merge_commit", None)
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
