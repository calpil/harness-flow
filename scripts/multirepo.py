"""Contrato de integracion manual multi-repo. Solo lectura Git; stdlib."""
from __future__ import annotations

import json
import fnmatch
import hashlib
import os
from pathlib import Path
import re
import subprocess


class Invalid(ValueError):
    """Declaracion o evidencia multi-repo no verificable."""


def require(ok, message):
    if not ok:
        raise Invalid(message)


def git(repo, *args, binary=False, ok=(0,)):
    # No permitir GIT_DIR/WORK_TREE/INDEX_FILE ni replaces heredados: se mide la
    # ruta declarada, no el repo que el proceso padre pudiera redirigir.
    # ok admite otros exits legitimos (grep sin coincidencias sale 1).
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_OPTIONAL_LOCKS="0", GIT_NO_REPLACE_OBJECTS="1")
    try:
        r = subprocess.run(["git", "-c", "core.fsmonitor=false", "-C", str(repo), *args],
                           env=env, capture_output=True, text=not binary, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Invalid(f"no pude medir Git en {repo}: {exc}") from exc
    require(r.returncode in ok, f"Git no verificable en {repo}: {args[0]}")
    return r.stdout if binary else r.stdout.rstrip("\n")


def read_manifest(path):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, f"clave duplicada: {key}")
            out[key] = value
        return out
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique)
    except (OSError, ValueError) as exc:
        raise Invalid(f"manifiesto invalido: {exc}") from exc


def _path(value):
    require(isinstance(value, str) and value and Path(value).is_absolute(),
            "paths deben ser absolutos y no vacios")
    path = Path(value).resolve()
    require(path.is_dir(), f"no existe directorio: {path}")
    require(Path(git(path, "rev-parse", "--show-toplevel")).resolve() == path,
            f"no es raiz de worktree Git: {path}")
    return path


def protected_paths(p, rules):
    """Foto local: no leer/imprimir contenidos protegidos en evidencia."""
    snapshot = {}
    root = p["root"]
    # El recibo no concede permisos nuevos al generador ni a los roles. Un
    # symlink vacio tambien puede redirigir su futura escritura fuera de raiz.
    outputs = [p["backlog"], p["progress"] / "archive", p["progress"] / "history.md",
               p["docs"] / "prd" / "PRD-master.md", p["docs"] / "sdd.md"]
    outputs += list(p["docs"].glob("*.md")) + list(p["progress"].glob("current-*.md"))
    for path in outputs:
        require(not any(x.is_symlink() for x in (path, *path.parents) if x != root and root in x.parents),
                "escritura fuera de contrato: symlink en documentos/progreso")
    for pat in rules.get("rutas_protegidas", []):
        require(isinstance(pat, str) and not Path(pat).is_absolute() and ".." not in Path(pat).parts,
                "patron protegido fuera de raiz")
        # pathlib 'dir/**' enumera directorios, por eso se usa /**/*.
        pattern = pat + "/*" if pat.endswith("/**") else pat
        for path in root.glob(pattern):
            require(not any(x.is_symlink() for x in (path, *path.parents) if x != root and root in x.parents),
                    "rutas protegidas con symlink no auditables")
            if path.is_file():
                snapshot[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    rel = "docs/prd/PRD-master.md"
    if any(fnmatch.fnmatchcase(rel, pat) for pat in rules.get("rutas_protegidas", [])):
        from bloques import fingerprint
        path = root / rel
        try:
            snapshot[rel] = fingerprint(path.read_bytes() if path.exists() else None)
        except (OSError, ValueError) as exc:
            raise Invalid(f"rutas protegidas: {exc}") from exc
    return snapshot


def _clean(path):
    flags = git(path, "ls-files", "-v", "-z").split("\0")
    require(not any(x and (x[0].islower() or x[0] == "S") for x in flags),
            f"indice oculta trabajo (assume-unchanged/skip-worktree): {path}")
    require(not git(path, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignore-submodules=none"),
            f"arbol sucio (tracked/untracked): {path}")


def validate(p, f, manifest, rules=None, integrated=False, target=None):
    require(isinstance(manifest, dict) and set(manifest) == {"version", "feature", "repos"},
            "esquema de manifiesto invalido")
    require(type(manifest["version"]) is int and manifest["version"] == 1
            and manifest["feature"] == str(f["id"]), "version/feature no coincide")
    micros = f.get("microservicios")
    require(isinstance(micros, list) and bool(micros)
            and all(isinstance(x, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", x) for x in micros)
            and len(set(micros)) == len(micros), "microservicios debe ser lista explicita completa y unica")
    rows = manifest["repos"]
    require(isinstance(rows, list) and len(rows) == len(micros), "falta repo en mapa completo de microservicios")
    names, identities, result = set(), set(), []
    fields = {"microservicio", "repo", "worktree", "base_sha", "source_sha", "target_branch", "target_sha"}
    for row in rows:
        require(isinstance(row, dict) and set(row) == fields and all(isinstance(v, str) and v for v in row.values()),
                "campos de repo incompletos o desconocidos")
        name = row["microservicio"]
        require(name in micros and name not in names, "microservicio ausente, ajeno o duplicado")
        names.add(name)
        repo, wt = _path(row["repo"]), _path(row["worktree"])
        require(repo == (p["root"] / name).resolve(), f"repo fuera del path declarado para {name}")
        common = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
        require(common not in identities, "repo duplicado (path canonico/Git common-dir)")
        identities.add(common)
        require(Path(git(wt, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve() == common,
                f"worktree ajeno para {name}")
        worktrees = {Path(x[len("worktree "):]).resolve()
                     for x in git(repo, "worktree", "list", "--porcelain", "-z").split("\0")
                     if x.startswith("worktree ")}
        require(repo in worktrees and wt in worktrees, f"worktree no registrado en Git: {name}")
        branch = row["target_branch"]
        require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", branch) and not branch.startswith("refs/"),
                "rama destino invalida (no opciones ni refs arbitrarias)")
        git(repo, "check-ref-format", f"refs/heads/{branch}")
        require(target is None or target == branch, "--to no coincide con rama destino declarada")
        for key in ("base_sha", "source_sha", "target_sha"):
            sha = row[key]
            require(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sha), f"{key} requiere SHA completo literal")
            require(git(repo, "cat-file", "-t", sha) == "commit", f"{key} no es commit")
        require(git(repo, "symbolic-ref", "HEAD") == f"refs/heads/{branch}", "rama destino ajena/no activa")
        require(git(repo, "rev-parse", f"refs/heads/{branch}") == row["target_sha"]
                and git(repo, "rev-parse", "HEAD") == row["target_sha"], "tip destino cambio (stale target)")
        if wt == repo:
            git(repo, "merge-base", "--is-ancestor", row["source_sha"], row["target_sha"])
        else:
            require(git(wt, "rev-parse", "HEAD") == row["source_sha"], "HEAD fuente no coincide con source_sha")
        git(repo, "merge-base", "--is-ancestor", row["base_sha"], row["source_sha"])
        require(bool(git(repo, "diff", "--name-only", row["base_sha"], row["source_sha"], "--")),
                "source_sha no contiene delta de feature respecto a base_sha")
        for path in {repo, wt}:
            _clean(path)
        for end in ("source_sha", "target_sha"):
            # Rev-list conserva ambos lados de merges y cambios restaurados.
            commits = git(repo, "rev-list", "--parents", f"{row['base_sha']}..{row[end]}").splitlines()
            for line in commits:
                commit, *parents = line.split()
                for parent in parents:
                    changed = git(repo, "diff", "--name-only", "--no-renames", "-z", parent, commit, "--").split("\0")
                    for path in changed:
                        if path and any(fnmatch.fnmatchcase(path, pat) for pat in (rules or {}).get("rutas_protegidas", [])):
                            safe = False
                            if path == "docs/prd/PRD-master.md":
                                from bloques import allowed
                                # Unica excepcion; nunca leer blobs .env/secretos.
                                before = (git(repo, "show", f"{parent}:{path}", binary=True)
                                          if git(repo, "ls-tree", parent, "--", path) else None)
                                after = (git(repo, "show", f"{commit}:{path}", binary=True)
                                         if git(repo, "ls-tree", commit, "--", path) else b"")
                                safe = allowed(before, after)
                            require(safe, f"rutas protegidas modificadas en commits de {name}: {commit} {path}")
        if integrated:
            try:
                git(repo, "merge-base", "--is-ancestor", row["source_sha"], row["target_sha"])
            except Invalid as exc:
                raise Invalid(f"fuente no integrada en {name}") from exc
        result.append(dict(row, repo=str(repo), worktree=str(wt)))
    require(names == set(micros), "mapa no cubre todos los microservicios")
    return dict(manifest, repos=result)


def protected_snapshot(p, manifest, rules):
    from comun import paths
    roots = {p["root"]}
    for row in manifest["repos"]:
        roots.update((Path(row["repo"]), Path(row["worktree"])))
    return {str(root): protected_paths(paths(root), rules) for root in sorted(roots)}


def check_registered(p, f, rules, integrated=False, target=None):
    manifest = validate(p, f, f.get("multi_repo"), rules, integrated, target)
    require(snapshot_matches(f.get("multi_repo_protected"), protected_snapshot(p, manifest, rules)),
            "rutas protegidas de raiz/repos cambiaron desde registro")
    return manifest


def snapshot_matches(before, after):
    from bloques import compatible
    if not isinstance(before, dict) or not isinstance(after, dict) or before.keys() != after.keys():
        return False
    for root, values in after.items():
        old = before[root]
        if not isinstance(old, dict) or not isinstance(values, dict) or old.keys() != values.keys():
            return False
        for path, value in values.items():
            if path == 'docs/prd/PRD-master.md':
                if not compatible(old[path], value):
                    return False
            elif old[path] != value:
                return False
    return True


def protected_context(snapshot):
    from bloques import context_fingerprint
    return {root: {path: context_fingerprint(value) if path == 'docs/prd/PRD-master.md' else value
                   for path, value in values.items()} for root, values in snapshot.items()}


def context(p, f, rules):
    """Vincula review/verify a TODOS los SHAs, spec y evidencia actuales."""
    from comun import spec_path, impl_path
    payload = {"map": check_registered(p, f, rules), "protected": protected_context(f["multi_repo_protected"]), "rules": rules}
    for name, path in (("spec", spec_path(p, f)), ("impl", impl_path(p, f))):
        require(path.is_file(), f"sin {name} para contexto multi-repo")
        payload[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
