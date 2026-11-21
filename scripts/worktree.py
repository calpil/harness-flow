#!/usr/bin/env python3
"""Aislamiento por feature con git worktree y sincronizacion multi-dev.

  worktree.py start   --feature <id> [--repo <microservicio>] [--sin-worktree] [--por <dev>] [--offline]
  worktree.py sync    [--feature <id>] [--base <rama>] [--por <dev>] [--offline]
  worktree.py liberar --feature <id> [--forzar --yes] [--mantener-worktree] [--por <dev>] [--offline]
  worktree.py list
  worktree.py drop    --feature <id> [--forzar --yes]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (bitacora, bloqueos_feature, enlazar_dependencias, enlazar_normativa, get_feature, git,  # noqa: E402
                   load_backlog, now_iso, paths, save_backlog, slugify)
import sync_remoto  # noqa: E402

ABIERTOS = ("in_progress", "blocked", "review")


def rama_base(data: dict, args) -> str:
    """Rama de la que sale la feature: --base > rules.rama_base > develop."""
    return (getattr(args, "base", None)
            or data.get("rules", {}).get("rama_base")
            or "develop")


def resolver_base(repo, base: str, *, remoto: str = "origin", preferir_remoto: bool = False) -> str:
    """SHA de la base. No cae al HEAD del repo: un HEAD ajeno es trabajo ajeno."""
    if preferir_remoto:
        rem_sha = sync_remoto.base_mas_reciente(repo, base, remoto)
        if rem_sha:
            return rem_sha
    code, sha = git(["rev-parse", "--verify", f"refs/heads/{base}"], repo)
    if code != 0:
        code, sha = git(["rev-parse", "--verify", f"refs/remotes/{remoto}/{base}"], repo)
    if code != 0:
        sys.exit(f"[!!] la rama base '{base}' no existe en {repo}.\n"
                 f"     Declara la correcta en harness/feature_list.json -> "
                 f"rules.rama_base, o pasa --base <rama>.\n"
                 f"     NO arranco desde el HEAD actual: seria la rama de quien\n"
                 f"     hizo checkout ultimo.")
    return sha.strip()


def _contexto(p, fid, args) -> None:
    """Refresca grafo/hub/vault si estan vencidos e imprime el brief.

    Arrancar una feature con el grafo de ayer es como arrancarla a ciegas: es
    justo el momento en que el implementer va a preguntarle al grafo.
    """
    if getattr(args, "sin_contexto", False):
        print("[i]  --sin-contexto: no se refresco el grafo ni se imprimio el brief.")
        return
    try:
        import contexto
        if contexto._desactivado():
            print("[i]  HARNESS_SIN_CONTEXTO: sin refresco ni brief.")
            return
        contexto.refrescar_si_vencido(p, etiqueta=f"arrancar #{fid}")
        print()
        contexto.cmd_brief(argparse.Namespace(
            feature=str(fid), max_lineas=90, max_archivos=12, max_lecciones=12))
    except SystemExit:
        raise
    except Exception as exc:  # el contexto es ayuda, no un gate: nunca tumba el start
        print(f"[!] no se pudo preparar el contexto: {exc}")


def _fijar_modo(p: dict, f: dict, args) -> str:
    """Modo de implementacion de la feature: pair salvo que el usuario pida delegar.

    Se registra aqui, no en el texto de un comando: antes el modo pair dependia
    de que el brief detectara un stack y de que el agente lo siguiera, y nada
    quedaba escrito. Con el modo en el backlog, close puede exigir su rastro
    (la lista de tests sellada, gate.py sellar-tests).
    """
    previo = f.get("modo")
    if getattr(args, "delegado", False):
        f["modo"] = "delegado"
    elif getattr(args, "pair", False) or not previo:
        f["modo"] = "pair"
    if previo and previo != f["modo"]:
        por = " con el SI del usuario" if f["modo"] == "delegado" else ""
        bitacora(p, f"modo de #{f['id']}: {f['modo']} (antes {previo}){por}")
    return f["modo"]


def _exigir_si_para_delegar(f: dict, args) -> None:
    """Pasar a delegado exige --yes: el SI del usuario, o de quien lanzo una sesion sin usuario.

    El texto decia "delegar es decision del usuario" y el script aceptaba
    --delegado de cualquiera: en un proyecto real nueve features pasaron de pair a
    delegado entre 1 y 13 segundos despues de aprobarse. Una feature que ya esta
    en delegado no vuelve a preguntar (arrancar otro de sus repos).
    """
    if getattr(args, "delegado", False) and f.get("modo") != "delegado" and not getattr(args, "yes", False):
        sys.exit(f"[!!] delegar #{f['id']} es decision del usuario: preguntaselo en un formulario y,\n"
                 "     solo con su SI, repite con --delegado --yes. Sin eso la feature sigue en pair.")


def _decir_modo(f: dict) -> None:
    if f["modo"] == "pair":
        print(f"[i]  modo pair automatico (por defecto): la lista de tests va en docs/tests-{f['id']}.md y la\n"
              f"     sella quien implementa (gate.py sellar-tests --feature {f['id']}); close la exige.\n"
              "     Avanza sin pausar tras cada ciclo; formulario solo en las paradas que preguntan (ver el brief).\n"
              "     Para delegar al subagente: worktree.py modo --feature <id> --delegado --yes (solo con el SI del usuario).")
    else:
        print("[i]  modo delegado: lo decidio el usuario (--yes).")


def cmd_modo(args) -> None:
    """Fija o cambia el modo de una feature. Delegar es decision del usuario."""
    if args.pair == args.delegado:
        sys.exit("[!!] indica --pair o --delegado (uno de los dos)")
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, args.feature)
    _exigir_si_para_delegar(f, args)
    _fijar_modo(p, f, args)
    save_backlog(p, data)
    print(f"[ok] feature #{f['id']}: modo {f['modo']}")
    _decir_modo(f)


def _reportar_sync_publicado(pub: dict, fid) -> None:
    if pub.get("publicado_git"):
        suf = " (rama base local sincronizada)" if pub.get("ff_local") else (
            " (cambios locales sin commitear: corre git pull --rebase luego)"
        )
        print(f"[ok] estado 'desarrollando' publicado en {pub['remoto']}/{pub['base']} "
              f"({pub['commit'][:7]}){suf}")
    elif pub.get("offline"):
        print(f"[!]  --offline: estado 'desarrollando' guardado SOLO en local.\n"
              f"     Publica al recuperar conexion: worktree.py sync --feature {fid}")
    elif pub.get("omitido_entorno"):
        print("[i]  HARNESS_SIN_SYNC_REMOTO: estado guardado solo en local.")
    if pub.get("hub_ok"):
        print("[ok] espejo actualizado en Memory Hub Postgres")
    elif pub.get("hub_aviso"):
        print(f"[!]  espejo Memory Hub Postgres no actualizado: {pub['hub_aviso']}")


def cmd_start(args) -> None:
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, args.feature)
    _exigir_si_para_delegar(f, args)
    fid, slug = f["id"], slugify(f.get("name", ""))
    base = rama_base(data, args)
    offline = getattr(args, "offline", False)
    por = getattr(args, "por", None)

    # Primero siempre validar el estado remoto + Memory Hub Postgres antes de tocar nada local.
    try:
        remoto_est = sync_remoto.validar_feature_libre(
            p, data, f, accion="iniciar el desarrollo", base=base, offline=offline, por=por,
        )
    except (sync_remoto.ErrorSyncRemoto, sync_remoto.ErrorConflictoDesarrollo) as exc:
        sys.exit(f"[!!] {exc}")
    yo = remoto_est["yo"]
    data_vista, _ = sync_remoto.aplicar_vista_remota(data, remoto_est)

    f0 = next((x for x in data_vista.get("features", []) if str(x.get("id")) == "0"), None)
    # Con el trinquete adoptado (arquitectura.py) la #0 ya no es un muro.
    if (f0 and f0.get("status") != "done" and str(fid) != "0"
            and not (p["harness"] / "arquitectura-base.json").is_file()):
        sys.exit(f"[!!] require_stack_normativo: la Feature #0 ({f0.get('name')}) esta en estado '{f0.get('status')}'.\n"
                 f"     No puedes arrancar features de negocio antes de normalizar el codigo existente.\n"
                 f"     Ejecuta primero: worktree.py start --feature 0")

    bloq = bloqueos_feature(data_vista, f)
    if bloq:
        sys.exit(f"[!!] la feature #{fid} tiene dependencias sin cerrar:\n"
                 + "".join(f"     - {b}\n" for b in bloq) +
                 "     Cierra primero sus dependencias antes de arrancar.")

    rama = ("bugfix/" if f.get("kind") == "bug" else "feature/") + f"{fid}-{slug}"
    ahora = now_iso()
    desarrollo = sync_remoto.construir_desarrollo(yo, branch=rama, desde=ahora, offline=offline)

    if args.sin_worktree:
        otras = [x for x in data["features"]
                 if x.get("status") in ABIERTOS and str(x["id"]) != str(fid)
                 and not sync_remoto.es_de_otro_dev(x, yo)]
        no_aisladas = [x for x in otras if not x.get("worktree")]
        if no_aisladas:
            ids = ", ".join(f"#{x['id']}" for x in no_aisladas)
            sys.exit(f"[!!] no puedes arrancar sin worktree: {ids} ya esta(n) sin aislar.\n"
                     "     Una sola feature no aislada a la vez.")
        f.update(status="in_progress", started_at=ahora, aislada=False,
                 branch=rama, base_branch=base, desarrollo=desarrollo)
        _fijar_modo(p, f, args)
        try:
            pub = sync_remoto.publicar_reclamo(
                p, data, f, desarrollo, base=base, offline=offline, por=por,
            )
        except (sync_remoto.ErrorSyncRemoto, sync_remoto.ErrorConflictoDesarrollo) as exc:
            sys.exit(f"[!!] {exc}")
        if not pub["ff_local"]:
            save_backlog(p, pub["data_actualizada"])
        bitacora(p, f"start #{fid} SIN worktree (no aislada) modo={f['modo']} por={yo['por']}"
                    + (" (offline)" if offline else ""))
        print(f"[!] feature #{fid} arrancada SIN aislamiento. Trabaja en {p['root']}")
        print(f"     desarrollando: {sync_remoto.formato_dueno(desarrollo)}")
        _reportar_sync_publicado(pub, fid)
        _decir_modo(f)
        _contexto(p, fid, args)
        return

    repo = p["root"] / args.repo if args.repo else p["root"]
    if not (repo / ".git").exists():
        sys.exit(f"[!!] {repo} no es un repo git.\n"
                 "     Proyecto multi-repo: pasa --repo <microservicio>, o prepara el\n"
                 "     arbol a mano y declaralo con --worktree <ruta>.")

    base_sha = resolver_base(
        repo, base, remoto=remoto_est["remoto"], preferir_remoto=remoto_est["activo"],
    )

    destino = repo.parent / f"{repo.name}-wt" / f"{fid}-{slug}"
    rama_creada = False
    code, out = git(["worktree", "add", "-b", rama, str(destino), base_sha], repo)
    if code == 0:
        rama_creada = True
    elif "already exists" in out:
        # La rama ya existe: se reusa, pero se exige que salga de la base.
        code, out = git(["worktree", "add", str(destino), rama], repo)
        if code == 0:
            cod2, _ = git(["merge-base", "--is-ancestor", base_sha, rama], repo)
            if cod2 != 0:
                # El worktree YA esta creado: dejarlo puesto al abortar convertia
                # el error en un callejon sin salida (drop no lo conoce porque el
                # backlog nunca se escribio, y el proximo start choca con
                # 'already exists' sobre la ruta). Se deshace antes de salir.
                limpieza, salida = git(["worktree", "remove", "--force", str(destino)], repo)
                resto = ("" if limpieza == 0 else
                         f"\n     [!] no pude quitar el worktree {destino}: {salida}\n"
                         f"     Quitalo a mano: git -C {repo} worktree remove --force {destino}")
                sys.exit(f"[!!] la rama '{rama}' ya existe y NO desciende de '{base}'.\n"
                         f"     Rebasea o borrala antes de arrancar: el diff de la\n"
                         f"     feature mediria trabajo ajeno." + resto)
    if code != 0:
        sys.exit(f"[!!] no se pudo crear el worktree, la feature NO arranca:\n{out}")

    f.update(status="in_progress", started_at=ahora, aislada=True,
             branch=rama, base_branch=base, base_sha=base_sha,
             worktree=str(destino), desarrollo=desarrollo)
    _fijar_modo(p, f, args)
    try:
        pub = sync_remoto.publicar_reclamo(
            p, data, f, desarrollo, base=base, offline=offline, por=por,
        )
    except (sync_remoto.ErrorSyncRemoto, sync_remoto.ErrorConflictoDesarrollo) as exc:
        # Si fallo el push o hubo carrera OCC con otro dev, deshacemos el worktree local.
        git(["worktree", "remove", "--force", str(destino)], repo)
        if rama_creada:
            git(["branch", "-D", rama], repo)
        sys.exit(f"[!!] {exc}")

    if not pub["ff_local"]:
        save_backlog(p, pub["data_actualizada"])
    bitacora(p, f"start #{fid} rama={rama} worktree={destino} modo={f['modo']} por={yo['por']}"
                + (f" commit={pub['commit'][:7]}" if pub.get("commit") else "")
                + (" (offline)" if offline else ""))
    print(f"[ok] feature #{fid} arrancada\n     rama:          {rama}\n     worktree:      {destino}\n"
          f"     desarrollando: {sync_remoto.formato_dueno(desarrollo)}")
    _reportar_sync_publicado(pub, fid)
    _decir_modo(f)
    enlazados = enlazar_dependencias(data, repo, destino) + enlazar_normativa(repo, destino)
    if enlazados:
        print(f"     enlazado desde la raiz: {', '.join(enlazados)}")
    print("[i]  TRABAJA DENTRO de ese worktree.")
    _contexto(p, fid, args)


def cmd_register(args) -> None:
    """Registra worktrees existentes; nunca crea ramas ni integra."""
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, args.feature)
    try:
        sync_remoto.validar_feature_libre(
            p, data, f, accion="registrar worktrees",
            offline=getattr(args, "offline", False), por=getattr(args, "por", None),
        )
    except (sync_remoto.ErrorSyncRemoto, sync_remoto.ErrorConflictoDesarrollo) as exc:
        sys.exit(f"[!!] {exc}")
    from multirepo import Invalid, read_manifest, validate, protected_snapshot, snapshot_matches, require
    try:
        manifest = validate(p, f, read_manifest(args.manifest), data["rules"])
        protected = protected_snapshot(p, manifest, data["rules"])
        require("multi_repo_protected" not in f or snapshot_matches(f["multi_repo_protected"], protected),
                "rutas protegidas cambiaron: registrar no reautoriza ediciones")
    except Invalid as exc:
        sys.exit(f"[!!] multi-repo: {exc}")
    f["multi_repo"] = manifest
    f["multi_repo_protected"] = protected
    # register NO fija el modo: registra worktrees que ya existen, con el trabajo
    # hecho, para validar una integracion. Ponerla en pair aqui exigiria una
    # lista de tests "sellada antes de implementar" despues de haber implementado.
    # El modo lo fija gate.py approve-spec (primera aprobacion), start o `worktree.py modo`.
    save_backlog(p, data)
    bitacora(p, f"register #{f['id']} multi-repo")
    for fila in manifest.get("repos", []):
        if fila.get("repo") and fila.get("worktree"):
            enlazadas = enlazar_normativa(Path(str(fila["repo"])), Path(str(fila["worktree"])))
            if enlazadas:
                print(f"[i]  {Path(str(fila['worktree'])).name}: normativa del stack enlazada desde el "
                      f"checkout principal ({', '.join(enlazadas)})")
    if f.get("modo"):
        _decir_modo(f)
    else:
        # Solo le pasa a un spec sellado antes de que el modo se registrara al aprobar.
        print(f"[!]  #{f['id']} no tiene modo registrado: close NO exigira la lista de tests.\n"
              f"     Si aun no hay codigo, fijalo: worktree.py modo --feature {f['id']} --pair\n"
              f"     (o --delegado --yes, si el usuario decide delegar).")


def cmd_list(args) -> None:
    p = paths()
    data = load_backlog(p)
    for f in data["features"]:
        if f.get("status") in ABIERTOS:
            wt = f.get("worktree") or "(sin worktree)"
            d = sync_remoto.dueno_activo(f)
            quien = f"  [{sync_remoto.formato_dueno(d)}]" if d else ""
            print(f"#{f['id']:>3} [{f['status']:<11}] {f.get('branch','-'):<40} {wt}{quien}")


def _eliminar_worktree_local(p: dict, f: dict) -> bool:
    wt = f.get("worktree")
    if not wt or not Path(wt).exists():
        return False
    # rsplit y no replace: un repo llamado 'front-wt-app' daba 'front-app'
    # y el remove se intentaba sobre una ruta que no existe.
    contenedor = Path(wt).parent
    repo = contenedor.parent / contenedor.name.rsplit("-wt", 1)[0]
    code, out = git(["worktree", "remove", wt, "--force"], repo if repo.exists() else p["root"])
    print(out or f"[ok] worktree {wt} eliminado")
    return code == 0


def cmd_drop(args) -> None:
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, args.feature)
    if "multi_repo" in f:
        sys.exit("[!!] multi-repo: drop no elimina worktrees existentes registrados")
    yo = sync_remoto.identidad_actual(sync_remoto.repo_harness(p)[0], por=getattr(args, "por", None))
    if sync_remoto.es_de_otro_dev(f, yo) and not (getattr(args, "forzar", False) and getattr(args, "yes", False)):
        d = sync_remoto.dueno_activo(f)
        sys.exit(f"[!!] la feature #{f['id']} pertenece a {sync_remoto.formato_dueno(d)}.\n"
                 "     No puedes eliminar su worktree sin acuerdo del equipo (--forzar --yes).")
    wt = f.get("worktree")
    if not wt:
        sys.exit(f"[!!] la feature #{f['id']} no tiene worktree registrado.")
    _eliminar_worktree_local(p, f)
    f.pop("worktree", None)
    save_backlog(p, data)


def cmd_liberar(args) -> None:
    """Libera una feature en desarrollo (vuelve a `todo` en local, remoto y Memory Hub)."""
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, args.feature)
    fid = str(f["id"])
    base = rama_base(data, args)
    offline = getattr(args, "offline", False)
    por = getattr(args, "por", None)

    try:
        est = sync_remoto.leer_remoto(p, data, base=base, offline=offline, por=por)
    except sync_remoto.ErrorSyncRemoto as exc:
        sys.exit(f"[!!] {exc}")
    yo = est["yo"]
    dueno = est["en_desarrollo"].get(fid) or sync_remoto.dueno_activo(f)
    if dueno and not sync_remoto.mismo_desarrollador(dueno, yo):
        if not (args.forzar and args.yes):
            sys.exit(
                f"[!!] la feature #{fid} esta tomada por {sync_remoto.formato_dueno(dueno)}.\n"
                "     Liberar una feature ajena exige confirmacion explicita tras acordarlo en equipo:\n"
                f"       worktree.py liberar --feature {fid} --forzar --yes"
            )

    if not args.mantener_worktree and "multi_repo" not in f and f.get("worktree"):
        if Path(str(f["worktree"])).exists():
            _eliminar_worktree_local(p, f)

    f["status"] = "todo"
    f.pop("desarrollo", None)
    f.pop("worktree", None)
    try:
        res = sync_remoto.publicar_liberacion(
            p, data, f, nuevo_estado="todo", base=base, offline=offline, por=por,
        )
    except sync_remoto.ErrorSyncRemoto as exc:
        sys.exit(f"[!!] {exc}")
    if not res["ff_local"]:
        save_backlog(p, res["data_actualizada"])
    bitacora(p, f"liberar #{fid} -> todo por={yo['por']}"
                + (" (forzado)" if args.forzar else "")
                + (" (offline)" if offline else ""))
    print(f"[ok] feature #{fid} liberada (status=todo)")
    if res["publicado_git"]:
        print(f"[ok] liberacion publicada en {res['remoto']}/{res['base']} ({res['commit'][:7]})")
    elif offline:
        print("[!]  --offline: liberacion guardada solo en local.")
    if res["hub_ok"]:
        print("[ok] reclamo liberado en Memory Hub Postgres")
    elif res["hub_aviso"]:
        print(f"[!]  espejo Memory Hub Postgres: {res['hub_aviso']}")


def cmd_sync(args) -> None:
    """Sincroniza estado de desarrollos activos con `origin/<base>` y Memory Hub Postgres."""
    if args.feature:
        sync_remoto.cmd_publicar(args)
        return
    p = paths()
    data = load_backlog(p)
    base = rama_base(data, args)
    sync_remoto.cmd_estado(argparse.Namespace(base=base, offline=args.offline, por=args.por))
    if args.offline:
        return
    try:
        est = sync_remoto.leer_remoto(p, data, base=base, offline=False, por=args.por)
    except sync_remoto.ErrorSyncRemoto:
        return
    if est["activo"] and est["atras_local"] and est["repo"] and est["rel_backlog"]:
        ff = sync_remoto._avanzar_base_local(
            est["repo"], est["base"], est["remote_sha"], est["remote_sha"], est["rel_backlog"],
        )
        if ff:
            print(f"[ok] rama local '{est['base']}' actualizada (fast-forward a {est['remote_sha'][:7]})")
        else:
            print(f"[i]  no se hizo fast-forward automatico en '{est['base']}' "
                  "(tienes cambios locales o estas en otra rama); corre git pull --rebase cuando corresponda.")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start"); s.add_argument("--feature", required=True)
    s.add_argument("--repo"); s.add_argument("--sin-worktree", action="store_true",
                                             dest="sin_worktree")
    s.add_argument("--base", help="rama de la que sale la feature "
                                  "(por defecto rules.rama_base, o develop)")
    s.add_argument("--sin-contexto", action="store_true", dest="sin_contexto",
                   help="no refrescar grafo/hub/vault ni imprimir el brief")
    s.add_argument("--delegado", action="store_true",
                   help="implementa el subagente, no en pair: solo con el SI del usuario (--yes)")
    s.add_argument("--pair", action="store_true", help="modo pair (es el modo por defecto)")
    s.add_argument("--yes", action="store_true", help="el usuario decidio delegar (requerido con --delegado)")
    s.add_argument("--por", help="identidad del desarrollador (por defecto git config user.name/email)")
    s.add_argument("--offline", action="store_true",
                   help="emergencia sin red: arranca solo en local sin validar ni publicar en remoto")
    s.set_defaults(fn=cmd_start)
    s = sub.add_parser("register"); s.add_argument("--feature", required=True)
    s.add_argument("--manifest", required=True)
    s.add_argument("--por"); s.add_argument("--offline", action="store_true")
    s.set_defaults(fn=cmd_register)
    s = sub.add_parser("modo"); s.add_argument("--feature", required=True)
    s.add_argument("--pair", action="store_true"); s.add_argument("--delegado", action="store_true")
    s.add_argument("--yes", action="store_true", help="el usuario decidio delegar (requerido con --delegado)")
    s.set_defaults(fn=cmd_modo)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    s = sub.add_parser("drop"); s.add_argument("--feature", required=True)
    s.add_argument("--por"); s.add_argument("--forzar", action="store_true")
    s.add_argument("--yes", action="store_true")
    s.set_defaults(fn=cmd_drop)
    s = sub.add_parser("liberar", help="libera una feature en desarrollo y lo publica en remoto y Hub")
    s.add_argument("--feature", required=True)
    s.add_argument("--base"); s.add_argument("--por")
    s.add_argument("--mantener-worktree", action="store_true", dest="mantener_worktree")
    s.add_argument("--forzar", action="store_true", help="liberar una feature de otro dev (exige --yes)")
    s.add_argument("--yes", action="store_true", help="confirmacion explicita para --forzar")
    s.add_argument("--offline", action="store_true")
    s.set_defaults(fn=cmd_liberar)
    s = sub.add_parser("sync", help="sincroniza el estado de desarrollo con remoto y Hub (o publica --feature)")
    s.add_argument("--feature", help="publica una feature ya in_progress (ej. arrancada --offline)")
    s.add_argument("--base"); s.add_argument("--por")
    s.add_argument("--offline", action="store_true")
    s.set_defaults(fn=cmd_sync)
    a = ap.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
