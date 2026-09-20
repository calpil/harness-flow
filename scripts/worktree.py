#!/usr/bin/env python3
"""Aislamiento por feature con git worktree.

  worktree.py start  --feature <id> [--repo <microservicio>] [--sin-worktree]
  worktree.py list
  worktree.py drop   --feature <id>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (bitacora, get_feature, git, load_backlog, now_iso, paths,  # noqa: E402
                   save_backlog, slugify)

ABIERTOS = ("in_progress", "blocked", "review")


def rama_base(data: dict, args) -> str:
    """Rama de la que sale la feature: --base > rules.rama_base > develop."""
    return (getattr(args, "base", None)
            or data.get("rules", {}).get("rama_base")
            or "develop")


def resolver_base(repo, base: str) -> str:
    """SHA de la base. No cae al HEAD del repo: un HEAD ajeno es trabajo ajeno."""
    code, sha = git(["rev-parse", "--verify", f"refs/heads/{base}"], repo)
    if code != 0:
        code, sha = git(["rev-parse", "--verify", f"refs/remotes/origin/{base}"], repo)
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


def cmd_start(args) -> None:
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, args.feature)
    fid, slug = f["id"], slugify(f.get("name", ""))
    rama = ("bugfix/" if f.get("kind") == "bug" else "feature/") + f"{fid}-{slug}"

    if args.sin_worktree:
        otras = [x for x in data["features"]
                 if x.get("status") in ABIERTOS and str(x["id"]) != str(fid)]
        no_aisladas = [x for x in otras if not x.get("worktree")]
        if no_aisladas:
            ids = ", ".join(f"#{x['id']}" for x in no_aisladas)
            sys.exit(f"[!!] no puedes arrancar sin worktree: {ids} ya esta(n) sin aislar.\n"
                     "     Una sola feature no aislada a la vez.")
        f.update(status="in_progress", started_at=now_iso(), aislada=False,
                 branch=rama, base_branch=rama_base(data, args))
        save_backlog(p, data)
        bitacora(p, f"start #{fid} SIN worktree (no aislada)")
        print(f"[!] feature #{fid} arrancada SIN aislamiento. Trabaja en {p['root']}")
        _contexto(p, fid, args)
        return

    repo = p["root"] / args.repo if args.repo else p["root"]
    if not (repo / ".git").exists():
        sys.exit(f"[!!] {repo} no es un repo git.\n"
                 "     Proyecto multi-repo: pasa --repo <microservicio>, o prepara el\n"
                 "     arbol a mano y declaralo con --worktree <ruta>.")

    base = rama_base(data, args)
    base_sha = resolver_base(repo, base)

    destino = repo.parent / f"{repo.name}-wt" / f"{fid}-{slug}"
    code, out = git(["worktree", "add", "-b", rama, str(destino), base_sha], repo)
    if code != 0 and "already exists" in out:
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

    f.update(status="in_progress", started_at=now_iso(), aislada=True,
             branch=rama, base_branch=base, base_sha=base_sha,
             worktree=str(destino))
    save_backlog(p, data)
    bitacora(p, f"start #{fid} rama={rama} worktree={destino}")
    print(f"[ok] feature #{fid} arrancada\n     rama:     {rama}\n     worktree: {destino}")
    print("[i]  TRABAJA DENTRO de ese worktree.")
    _contexto(p, fid, args)


def cmd_register(args) -> None:
    """Registra worktrees existentes; nunca crea ramas ni integra."""
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, args.feature)
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
    save_backlog(p, data)
    bitacora(p, f"register #{f['id']} multi-repo")


def cmd_list(args) -> None:
    p = paths()
    data = load_backlog(p)
    for f in data["features"]:
        if f.get("status") in ABIERTOS:
            wt = f.get("worktree") or "(sin worktree)"
            print(f"#{f['id']:>3} [{f['status']:<11}] {f.get('branch','-'):<40} {wt}")


def cmd_drop(args) -> None:
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, args.feature)
    if "multi_repo" in f:
        sys.exit("[!!] multi-repo: drop no elimina worktrees existentes registrados")
    wt = f.get("worktree")
    if not wt:
        sys.exit(f"[!!] la feature #{f['id']} no tiene worktree registrado.")
    # rsplit y no replace: un repo llamado 'front-wt-app' daba 'front-app'
    # y el remove se intentaba sobre una ruta que no existe.
    contenedor = Path(wt).parent
    repo = contenedor.parent / contenedor.name.rsplit("-wt", 1)[0]
    code, out = git(["worktree", "remove", wt, "--force"], repo if repo.exists() else p["root"])
    print(out or f"[ok] worktree {wt} eliminado")
    f.pop("worktree", None)
    save_backlog(p, data)


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
    s.set_defaults(fn=cmd_start)
    s = sub.add_parser("register"); s.add_argument("--feature", required=True)
    s.add_argument("--manifest", required=True); s.set_defaults(fn=cmd_register)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    s = sub.add_parser("drop"); s.add_argument("--feature", required=True)
    s.set_defaults(fn=cmd_drop)
    a = ap.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
