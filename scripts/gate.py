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
    Reporte, bitacora, cubre_acs, get_feature, git, impl_path, load_backlog,
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

    _check_rutas_protegidas(p, rules, r)
    _check_aislamiento(abiertas, r)
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


def _check_rutas_protegidas(p, rules, r) -> None:
    pats = rules.get("rutas_protegidas") or []
    code, out = git(["status", "--porcelain"], p["root"])
    if code != 0:
        r.info("sin repo git en la raiz: no se puede auditar rutas protegidas")
        return
    tocadas = []
    for line in out.splitlines():
        f = line[3:].strip().strip('"')
        for pat in pats:
            if fnmatch.fnmatch(f, pat) or (pat.endswith("/**") and f.startswith(pat[:-3])):
                tocadas.append(f)
    if tocadas:
        r.fallo("rutas protegidas modificadas: " + ", ".join(sorted(set(tocadas))),
                "son del USUARIO; revierte esos cambios")
    else:
        r.ok(f"{len(pats)} ruta(s) protegida(s) intactas")


def _check_aislamiento(abiertas, r) -> None:
    sin_wt = [f for f in abiertas if not f.get("worktree")]
    if len(sin_wt) > 1:
        ids = ", ".join(f"#{f['id']}" for f in sin_wt)
        r.fallo(f"{len(sin_wt)} features abiertas sin worktree ({ids})",
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
    f["veredicto"] = args.veredicto
    save_backlog(p, data)
    bitacora(p, f"review #{f['id']} sellado: {args.veredicto} por {quien}")
    print(f"[ok] review #{f['id']} sellado como {args.veredicto} "
          f"(cubre {len(acs)} AC)")


# --- verify ----------------------------------------------------------------

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
    if not cmds:
        print("[i]  ningun AC declara comando: los verifica el reviewer a mano.")
        return
    timeout = int(data["rules"].get("verify_timeout_segundos", 900))
    out = [f"# Verify - Feature #{f['id']}", "", f"Corrido: {now_iso()}", ""]
    fallos = 0
    for ac, cmd in cmds.items():
        print(f"-- {ac}: {cmd}")
        try:
            r = subprocess.run(cmd, shell=True, cwd=str(p["root"]),
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
    f["last_verify"] = {"at": now_iso(), "fallos": fallos, "total": len(cmds)}
    save_backlog(p, data)
    print(f"\n[{'ok' if not fallos else '!!'}] {len(cmds)-fallos}/{len(cmds)} AC en verde -> {vp.name}")
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


def cmd_close(args) -> None:
    p = paths()
    data = load_backlog(p)
    rules = data["rules"]
    f = get_feature(data, args.feature)
    fid = f["id"]

    if args.status == "done" and not args.to:
        sys.exit("[!!] close --status done requiere --to <rama>.\n"
                 "     PREGUNTALE AL USUARIO a que rama se integra: no lo adivines.")

    fallos: list[str] = []
    sp = spec_path(p, f)
    if not sp.exists():
        fallos.append(f"no existe {sp.name}")
        acs: list[str] = []
    else:
        stext = sp.read_text(encoding="utf-8")
        acs = spec_acs(stext)
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
            if lv and lv.get("fallos"):
                fallos.append(f"verify con {lv['fallos']} AC en rojo")

        if rules.get("require_leccion") and not args.leccion:
            fallos.append("falta --leccion <clase> (o --leccion ninguna --leccion-motivo '<por que>')")
        if args.leccion == "ninguna" and not args.leccion_motivo:
            fallos.append("--leccion ninguna exige --leccion-motivo")
        # la leccion vive como SKILL del agente: exigimos que exista de verdad
        if args.leccion and args.leccion != "ninguna":
            sys.path.insert(0, str(Path(__file__).parent))
            from leccion import buscar as buscar_leccion
            if not buscar_leccion(args.leccion):
                fallos.append(
                    f"la leccion '{args.leccion}' no existe como skill "
                    "(creala antes de cerrar: skill_manage en Hermes, SKILL.md en Claude Code)")

    if fallos:
        print(f"[!!] close #{fid} BLOQUEADO por {len(fallos)} regla(s):")
        for x in fallos:
            print(f"     - {x}")
        sys.exit(1)

    # La integracion se hace ANTES de tocar el backlog: si el merge falla, la
    # feature NO queda marcada como cerrada. Al reves quedaria un 'done' sobre
    # una rama que nunca entro, que es el falso verde que este arnes combate.
    merged = None
    if args.status == "done" and args.to:
        merged = git_merge(p, f, args.to)

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
    save_backlog(p, data)
    bitacora(p, f"close #{fid} status={args.status}" +
             (f" -> {args.to}" if args.to else "") +
             (f" merge={merged}" if merged else "") +
             (f" leccion={args.leccion}" if args.leccion else ""))
    print(f"[ok] feature #{fid} cerrada como {args.status}")
    if merged:
        print(f"[ok] rama integrada en {args.to} (merge {merged})")
    print("[i]  la integracion es LOCAL: publicar es una decision aparte.")
    if (p["atlassian"]).exists():
        print("[i]  hay atlassian.json: corre atlassian.py push --feature "
              f"{fid} para reflejarlo en Jira.")


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
    s.add_argument("--leccion-motivo", dest="leccion_motivo"); s.add_argument("--nota")
    s.set_defaults(fn=cmd_close)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
