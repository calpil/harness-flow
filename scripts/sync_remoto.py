#!/usr/bin/env python3
"""Sincronizacion multi-desarrollador del estado de desarrollo local.

Evita que dos desarrolladores tomen la misma feature en local y se pisen:
  1. Antes de arrancar, aprobar spec o consultar estado, valida contra
     `origin/<rama_base>` y contra el espejo en Memory Hub Postgres.
  2. Al iniciar una feature (`worktree.py start`), marca `status = "in_progress"`
     con metadatos `desarrollo` (`estado = "desarrollando"`, desarrollador,
     email, host, rama, timestamp), hace commit+push atomico (OCC con reintento)
     en `origin/<rama_base>` sin ensuciar el arbol local ni cambiar la rama
     actual, y refleja el estado en Memory Hub Postgres.
  3. Al liberar (`worktree.py liberar`) o cerrar (`gate.py close`), limpia el
     reclamo activo en remoto y en el Hub.

Regla en `harness/feature_list.json -> rules`:
  - `require_sync_remoto`: `"auto"` (por defecto: activo si el repo tiene remoto
    `origin`), `true` (obligatorio incluso sin remoto), o `false` (apagado).
  - `remoto_sync`: nombre del remoto Git (por defecto `"origin"`).
  - `require_hub_sync`: `true` si un fallo del espejo Postgres tambien debe
    bloquear (por defecto `false`: Git bloquea y el Hub es espejo con aviso).
"""
from __future__ import annotations

import argparse
import copy
import getpass
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (  # noqa: E402
    bitacora, get_feature, git, load_backlog, now_iso, paths, save_backlog, slugify,
)

REMOTO_DEFECTO = "origin"
MAX_REINTENTOS_OCC = 3
_SEPARADORES_CONTROL = "\u0085\u2028\u2029"
_CAMPOS_SPEC_COMPARTIDOS = (
    "name", "kind", "microservicios", "acceptance", "prd", "prd_candidata",
    "requiere", "peso", "created_at", "modo", "last_spec_sig", "aprobado_por",
    "aprobado_at", "spec_huella", "docs_base",
)
_CAMPOS_DESARROLLO_COMPARTIDOS = (
    "status", "started_at", "aislada", "branch", "base_branch", "base_sha",
    "worktree", "modo", "desarrollo",
)


class ErrorSyncRemoto(Exception):
    """Fallo de conectividad, configuracion o push con el remoto/Hub."""


class ErrorConflictoDesarrollo(Exception):
    """Otra persona ya tiene la feature en desarrollo o cerrada en remoto."""


# --- entorno y configuracion -----------------------------------------------

def desactivado_por_entorno() -> bool:
    """HARNESS_SIN_SYNC_REMOTO=1 apaga el sync remoto (CI / pruebas aisladas)."""
    return os.environ.get("HARNESS_SIN_SYNC_REMOTO", "").strip().lower() not in (
        "", "0", "false", "no",
    )


def regla_sync_remoto(rules: dict | None) -> str | bool:
    """Valida `rules.require_sync_remoto`: 'auto', true o false."""
    val = (rules or {}).get("require_sync_remoto", "auto")
    if val is None or val == "auto":
        return "auto"
    if isinstance(val, bool):
        return val
    raise ValueError(
        f"rules.require_sync_remoto invalido ({val!r}): usa 'auto', true o false"
    )


def remoto_nombre(rules: dict | None) -> str:
    val = (rules or {}).get("remoto_sync")
    return str(val).strip() if val else REMOTO_DEFECTO


def _git_cmd(
    args: list[str],
    cwd: Path,
    *,
    env_extra: dict[str, str] | None = None,
    input_bytes: bytes | None = None,
    timeout: int = 45,
) -> tuple[int, str]:
    """Ejecuta Git sin prompts interactivos y con mensajes en ingles estable."""
    env = dict(os.environ, LC_ALL="C", LANGUAGE="", GIT_TERMINAL_PROMPT="0")
    if env_extra:
        env.update(env_extra)
    try:
        r = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            input=input_bytes,
            capture_output=True,
            timeout=timeout,
            env=env,
        )
        stdout = r.stdout.decode("utf-8", errors="replace")
        stderr = r.stderr.decode("utf-8", errors="replace")
        if r.returncode != 0:
            return r.returncode, (stdout + "\n" + stderr).strip()
        return 0, stdout
    except subprocess.TimeoutExpired:
        return 124, f"timeout ejecutando git {' '.join(args[:3])}"
    except Exception as exc:
        return 1, str(exc)


def repo_harness(p: dict) -> tuple[Path | None, str | None]:
    """Devuelve (raiz_git, ruta_relativa_backlog) para harness/feature_list.json."""
    code, top = _git_cmd(["rev-parse", "--show-toplevel"], p["root"])
    if code != 0 or not top.strip():
        return None, None
    raiz_git = Path(top.strip()).resolve()
    try:
        rel = p["backlog"].resolve().relative_to(raiz_git).as_posix()
    except ValueError:
        return None, None
    return raiz_git, rel


def tiene_remoto(repo: Path | None, remoto: str = REMOTO_DEFECTO) -> bool:
    if repo is None:
        return False
    code, out = _git_cmd(["remote", "get-url", remoto], repo)
    return code == 0 and bool(out.strip())


def evaluar_modo(
    p: dict,
    data: dict,
    *,
    base: str | None = None,
    offline: bool = False,
) -> dict:
    """Resuelve si el sync remoto aplica a este proyecto y con que parametros."""
    rules = data.get("rules") or {}
    remoto = remoto_nombre(rules)
    rama_base = base or rules.get("rama_base") or "develop"
    repo, rel_backlog = repo_harness(p)
    hay_remoto = tiene_remoto(repo, remoto)

    try:
        regla = regla_sync_remoto(rules)
    except ValueError as exc:
        return {
            "regla": None, "activo": True, "obligatorio": True, "offline": offline,
            "omitido_entorno": False, "repo": repo, "rel_backlog": rel_backlog,
            "remoto": remoto, "tiene_remoto": hay_remoto, "base": rama_base,
            "error_config": str(exc),
        }

    if regla is False:
        return {
            "regla": False, "activo": False, "obligatorio": False, "offline": offline,
            "omitido_entorno": False, "repo": repo, "rel_backlog": rel_backlog,
            "remoto": remoto, "tiene_remoto": hay_remoto, "base": rama_base,
            "error_config": None,
        }

    if desactivado_por_entorno():
        return {
            "regla": regla, "activo": False, "obligatorio": regla is True, "offline": offline,
            "omitido_entorno": True, "repo": repo, "rel_backlog": rel_backlog,
            "remoto": remoto, "tiene_remoto": hay_remoto, "base": rama_base,
            "error_config": None,
        }

    if offline:
        return {
            "regla": regla, "activo": False, "obligatorio": regla is True, "offline": True,
            "omitido_entorno": False, "repo": repo, "rel_backlog": rel_backlog,
            "remoto": remoto, "tiene_remoto": hay_remoto, "base": rama_base,
            "error_config": None,
        }

    if regla is True:
        err = None
        if repo is None:
            err = (
                f"require_sync_remoto esta activo, pero {p['root']} no es un repo git "
                "con remoto configurado (usa --offline en emergencias o apaga la regla "
                "en harness/feature_list.json)."
            )
        elif not hay_remoto:
            err = (
                f"require_sync_remoto esta activo, pero no existe el remoto '{remoto}' "
                f"en {repo} (agrega el remoto o usa --offline en emergencias)."
            )
        return {
            "regla": True, "activo": True, "obligatorio": True, "offline": False,
            "omitido_entorno": False, "repo": repo, "rel_backlog": rel_backlog,
            "remoto": remoto, "tiene_remoto": hay_remoto, "base": rama_base,
            "error_config": err,
        }

    # Modo "auto": activo automaticamente cuando existe repo git con remoto `origin`.
    activo = repo is not None and hay_remoto
    return {
        "regla": "auto", "activo": activo, "obligatorio": False, "offline": False,
        "omitido_entorno": False, "repo": repo, "rel_backlog": rel_backlog,
        "remoto": remoto, "tiene_remoto": hay_remoto, "base": rama_base,
        "error_config": None,
    }


# --- identidad y propiedad -------------------------------------------------

def _limpiar_texto(valor: str, campo: str) -> str:
    limpio = valor.strip()
    if not limpio or any(c < " " or c == "\x7f" or c in _SEPARADORES_CONTROL for c in limpio):
        raise ValueError(f"{campo} no admite saltos de linea ni caracteres de control")
    return limpio


def identidad_actual(repo: Path | None = None, por: str | None = None) -> dict:
    """Identidad del desarrollador actual para reclamar/validar features."""
    host = (os.environ.get("HARNESS_HOST_NAME") or "").strip() or socket.gethostname()
    explicito = (por or os.environ.get("HARNESS_DEV") or "").strip()
    if explicito:
        val = _limpiar_texto(explicito, "--por / HARNESS_DEV")
        if "@" in val:
            return {"por": val, "email": val.lower(), "id": val.lower(), "host": host}
        return {"por": val, "email": "", "id": val.lower(), "host": host}

    cwd = repo if (repo and repo.is_dir()) else Path.cwd()
    c_name, g_name = _git_cmd(["config", "--get", "user.name"], cwd)
    c_mail, g_mail = _git_cmd(["config", "--get", "user.email"], cwd)
    nombre = g_name.strip() if c_name == 0 else ""
    email = g_mail.strip().lower() if c_mail == 0 else ""
    por_display = nombre or email or getpass.getuser()
    dev_id = email or por_display.lower()
    return {"por": por_display, "email": email, "id": dev_id, "host": host}


def construir_desarrollo(
    dev: dict,
    *,
    branch: str,
    desde: str | None = None,
    offline: bool = False,
) -> dict:
    """Estructura canonica persistida en `f['desarrollo']`."""
    d = {
        "estado": "desarrollando",
        "por": dev["por"],
        "email": dev.get("email", ""),
        "id": dev["id"],
        "host": dev.get("host", ""),
        "branch": branch,
        "desde": desde or now_iso(),
    }
    if offline:
        d["offline"] = True
    return d


def dueno_activo(f: dict) -> dict | None:
    """Devuelve el reclamo activo de desarrollo de una feature, o None."""
    if f.get("status") in ("done", "superseded"):
        return None
    d = f.get("desarrollo")
    if not isinstance(d, dict):
        return None
    if d.get("estado") == "desarrollando" or (
        f.get("status") == "in_progress" and (d.get("id") or d.get("por") or d.get("email"))
    ):
        por = str(d.get("por") or d.get("email") or d.get("id") or "").strip()
        email = str(d.get("email") or "").strip().lower()
        dev_id = str(d.get("id") or email or por.lower()).strip().lower()
        return {
            "estado": "desarrollando",
            "por": por,
            "email": email,
            "id": dev_id,
            "host": str(d.get("host") or "").strip(),
            "branch": str(d.get("branch") or f.get("branch") or "").strip(),
            "desde": str(d.get("desde") or f.get("started_at") or "").strip(),
            "offline": bool(d.get("offline")),
            "fuente": str(d.get("fuente") or "local"),
        }
    return None


def mismo_desarrollador(dueno: dict | None, yo: dict) -> bool:
    """True si `dueno` corresponde a la misma persona que `yo`."""
    if not dueno or dueno.get("sin_dueno"):
        return False
    d_email = str(dueno.get("email") or "").strip().lower()
    y_email = str(yo.get("email") or "").strip().lower()
    if d_email and y_email:
        return d_email == y_email
    d_id = str(dueno.get("id") or "").strip().lower()
    y_id = str(yo.get("id") or "").strip().lower()
    if d_id and y_id and d_id == y_id:
        return True
    d_por = str(dueno.get("por") or "").strip().lower()
    y_por = str(yo.get("por") or "").strip().lower()
    if (not d_email or not y_email) and d_por and y_por and d_por == y_por:
        return True
    return False


def es_de_otro_dev(f: dict, yo: dict | None = None, repo: Path | None = None) -> bool:
    """True si la feature esta en desarrollo activo y pertenece a otra persona."""
    d = dueno_activo(f)
    if not d:
        return False
    return not mismo_desarrollador(d, yo or identidad_actual(repo))


def formato_dueno(d: dict) -> str:
    por = d.get("por") or d.get("id") or "(sin nombre)"
    host = d.get("host") or ""
    return f"{por} ({host})" if host else por


# --- espejo Memory Hub Postgres --------------------------------------------

def hub_configurado() -> bool:
    """True si el hub esta habilitado (sin HARNESS_SIN_HUB) y tiene credenciales."""
    import hub
    if hub.hub_desactivado():
        return False
    from comun import hub_env
    e = hub_env()
    return bool(e.get("DB_HOST") and e.get("DB_USER") and e.get("DB_PASSWORD"))


def _hub_proyecto(p: dict, data: dict) -> str:
    return str(data.get("project") or p["root"].name)


def hub_consultar_desarrollos(project: str) -> tuple[dict[str, dict], str | None]:
    """Lee desarrollos activos desde Memory Hub Postgres sin ejecutar DDL.

    Devuelve ({fid_str: claim}, aviso_o_error). Si el Hub no esta configurado
    o HARNESS_SIN_HUB=1, devuelve ({}, None).
    """
    if not hub_configurado():
        return {}, None
    import hub
    try:
        conn = hub.conectar(crear_tablas=False)
    except SystemExit as exc:
        return {}, str(exc).replace("[!!] ", "").strip()
    except Exception as exc:
        return {}, str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__

    claims: dict[str, dict] = {}
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, props FROM graph_nodes "
                "WHERE label = 'Feature' AND props->>'proyecto' = %s "
                "AND props->>'desarrollo_estado' = 'desarrollando'",
                (project,),
            )
            for nid, props in cur.fetchall():
                props = props or {}
                fid = str(props.get("feature_id") or str(nid).rsplit("/", 1)[-1])
                por = str(props.get("desarrollador") or props.get("desarrollador_id") or "").strip()
                email = str(props.get("email") or "").strip().lower()
                dev_id = str(props.get("desarrollador_id") or email or por.lower()).strip().lower()
                claims[fid] = {
                    "estado": "desarrollando",
                    "por": por or "(sin nombre)",
                    "email": email,
                    "id": dev_id,
                    "host": str(props.get("host") or "").strip(),
                    "branch": str(props.get("branch") or "").strip(),
                    "desde": str(props.get("desde") or "").strip(),
                    "fuente": "hub",
                }
        return claims, None
    except Exception as exc:
        linea = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
        return {}, linea
    finally:
        try:
            conn.close()
        except Exception:
            pass


def hub_publicar_desarrollo(project: str, f: dict, desarrollo: dict) -> tuple[bool, str | None]:
    """Refleja el estado `desarrollando` en Memory Hub Postgres."""
    if not hub_configurado():
        return False, None
    import hub
    try:
        conn = hub.conectar(crear_tablas=True)
    except SystemExit as exc:
        return False, str(exc).replace("[!!] ", "").strip()
    except Exception as exc:
        return False, str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__

    fid = str(f["id"])
    ahora = now_iso()
    dev_nid = f"dev/{desarrollo['id']}"
    feat_nid = f"{project}/feature/{fid}"
    try:
        with conn.cursor() as cur:
            hub.upsert_node(cur, project, "Proyecto", {"actualizado_at": ahora})
            hub.upsert_node(cur, dev_nid, "Desarrollador", {
                "nombre": desarrollo["por"],
                "email": desarrollo.get("email", ""),
                "host": desarrollo.get("host", ""),
                "actualizado_at": ahora,
            })
            hub.upsert_node(cur, feat_nid, "Feature", {
                "proyecto": project,
                "feature_id": fid,
                "nombre": f.get("name", ""),
                "estado": f.get("status", "in_progress"),
                "desarrollo_estado": "desarrollando",
                "desarrollador": desarrollo["por"],
                "desarrollador_id": desarrollo["id"],
                "email": desarrollo.get("email", ""),
                "host": desarrollo.get("host", ""),
                "branch": desarrollo.get("branch", f.get("branch", "")),
                "desde": desarrollo.get("desde", ahora),
                "actualizado_at": ahora,
            })
            cur.execute(
                "DELETE FROM graph_edges WHERE target = %s AND type = 'DESARROLLANDO' AND source <> %s",
                (feat_nid, dev_nid),
            )
            hub.upsert_edge(cur, "DESARROLLANDO", dev_nid, feat_nid, {
                "proyecto": project,
                "feature_id": fid,
                "branch": desarrollo.get("branch", f.get("branch", "")),
                "host": desarrollo.get("host", ""),
                "desde": desarrollo.get("desde", ahora),
                "activo": True,
                "actualizado_at": ahora,
            })
        conn.commit()
        return True, None
    except Exception as exc:
        linea = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
        return False, linea
    finally:
        try:
            conn.close()
        except Exception:
            pass


def hub_liberar_desarrollo(project: str, f: dict, nuevo_estado: str = "todo") -> tuple[bool, str | None]:
    """Limpia el reclamo activo en Memory Hub Postgres al liberar o cerrar."""
    if not hub_configurado():
        return False, None
    import hub
    try:
        conn = hub.conectar(crear_tablas=True)
    except SystemExit as exc:
        return False, str(exc).replace("[!!] ", "").strip()
    except Exception as exc:
        return False, str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__

    fid = str(f["id"])
    ahora = now_iso()
    feat_nid = f"{project}/feature/{fid}"
    estado_des = (
        "cerrada" if nuevo_estado == "done"
        else "bloqueada" if nuevo_estado == "blocked"
        else "libre"
    )
    try:
        with conn.cursor() as cur:
            hub.upsert_node(cur, feat_nid, "Feature", {
                "proyecto": project,
                "feature_id": fid,
                "nombre": f.get("name", ""),
                "estado": nuevo_estado,
                "desarrollo_estado": estado_des,
                "actualizado_at": ahora,
            })
            cur.execute(
                "DELETE FROM graph_edges WHERE target = %s AND type = 'DESARROLLANDO'",
                (feat_nid,),
            )
        conn.commit()
        return True, None
    except Exception as exc:
        linea = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
        return False, linea
    finally:
        try:
            conn.close()
        except Exception:
            pass


# --- lectura remota (Git + Hub) --------------------------------------------

def _leer_backlog_en_ref(repo: Path, ref: str, rel_backlog: str) -> dict | None:
    code, out = _git_cmd(["show", f"{ref}:{rel_backlog}"], repo)
    if code != 0:
        return None
    try:
        datos = json.loads(out)
    except ValueError as exc:
        raise ErrorSyncRemoto(f"{ref}:{rel_backlog} no es JSON valido: {exc}") from exc
    if not isinstance(datos, dict):
        raise ErrorSyncRemoto(f"{ref}:{rel_backlog} debe ser un objeto JSON")
    datos.setdefault("features", [])
    return datos


def _distancia_ramas(repo: Path, base: str, remote_sha: str) -> tuple[int, int]:
    """(adelante_local, atras_local) de refs/heads/<base> respecto a remote_sha."""
    code, _ = _git_cmd(["rev-parse", "--verify", f"refs/heads/{base}"], repo)
    if code != 0:
        return 0, 0
    code, out = _git_cmd(["rev-list", "--left-right", "--count", f"refs/heads/{base}...{remote_sha}"], repo)
    if code != 0:
        return 0, 0
    partes = out.strip().split()
    if len(partes) != 2:
        return 0, 0
    return int(partes[0]), int(partes[1])


def _combinar_reclamos(
    local_data: dict,
    remote_data: dict | None,
    hub_claims: dict[str, dict],
) -> tuple[dict[str, dict], dict[str, dict]]:
    """Construye (remoto_features_por_id, en_desarrollo_por_id)."""
    local_por_id = {str(f.get("id")): f for f in local_data.get("features") or []}
    remoto_por_id = {
        str(f.get("id")): f for f in ((remote_data or {}).get("features") or [])
    }
    en_desarrollo: dict[str, dict] = {}

    for fid, rf in remoto_por_id.items():
        if rf.get("status") in ("done", "superseded"):
            continue
        dueno = dueno_activo(rf)
        if dueno:
            fuente = "git+hub" if fid in hub_claims else "git"
            dueno["fuente"] = fuente
            en_desarrollo[fid] = dueno
        elif rf.get("status") == "in_progress":
            lf = local_por_id.get(fid)
            wt_local = lf.get("worktree") if lf else None
            if wt_local and Path(str(wt_local)).is_dir():
                continue  # trabajo local previo a este esquema, en esta maquina
            en_desarrollo[fid] = {
                "estado": "desarrollando",
                "por": "(sin dueno registrado)",
                "email": "",
                "id": "",
                "host": "",
                "branch": str(rf.get("branch") or ""),
                "desde": str(rf.get("started_at") or ""),
                "fuente": "git+hub" if fid in hub_claims else "git",
                "sin_dueno": True,
            }

    for fid, hclaim in hub_claims.items():
        rf = remoto_por_id.get(fid)
        if rf and rf.get("status") in ("done", "superseded"):
            continue  # Git ya cerro esta feature: no revivir un reclamo viejo del Hub
        if fid not in en_desarrollo:
            en_desarrollo[fid] = dict(hclaim)
        elif en_desarrollo[fid].get("sin_dueno"):
            # El Hub si trae quien la tomo: enriquece el reclamo anonimo de Git.
            mejorado = dict(hclaim)
            mejorado["fuente"] = "git+hub"
            en_desarrollo[fid] = mejorado

    return remoto_por_id, en_desarrollo


def leer_remoto(
    p: dict,
    data: dict,
    *,
    base: str | None = None,
    offline: bool = False,
    por: str | None = None,
) -> dict:
    """Consulta `origin/<base>` y el espejo Memory Hub Postgres.

    Lanza `ErrorSyncRemoto` si el sync esta activo y falla la consulta Git
    (o la de Hub cuando `rules.require_hub_sync` esta en true).
    """
    modo = evaluar_modo(p, data, base=base, offline=offline)
    yo = identidad_actual(modo["repo"], por=por)
    resultado = {
        **modo,
        "yo": yo,
        "remote_sha": None,
        "remote_data": None,
        "remoto_features": {},
        "hub_claims": {},
        "hub_estado": "omitido",
        "hub_aviso": None,
        "en_desarrollo": {},
        "adelante_local": 0,
        "atras_local": 0,
    }
    if modo["error_config"]:
        raise ErrorSyncRemoto(modo["error_config"])
    if not modo["activo"]:
        return resultado

    repo = modo["repo"]
    remoto = modo["remoto"]
    rama_base = modo["base"]
    rel_backlog = modo["rel_backlog"]
    assert repo is not None and rel_backlog is not None

    code, out = _git_cmd(["fetch", remoto, rama_base], repo)
    if code != 0:
        primera = out.splitlines()[0] if out else "error desconocido"
        raise ErrorSyncRemoto(
            f"no se pudo sincronizar con {remoto}/{rama_base}: {primera}\n"
            "     Comprueba tu conexion/permisos Git o usa --offline para emergencias."
        )

    ref = f"refs/remotes/{remoto}/{rama_base}"
    code, sha = _git_cmd(["rev-parse", "--verify", ref], repo)
    if code != 0 or not sha.strip():
        raise ErrorSyncRemoto(
            f"la rama base '{rama_base}' no existe en '{remoto}'.\n"
            f"     Publica '{rama_base}' en {remoto}, ajusta rules.rama_base o usa --offline."
        )
    remote_sha = sha.strip()
    remote_data = _leer_backlog_en_ref(repo, remote_sha, rel_backlog)
    adelante, atras = _distancia_ramas(repo, rama_base, remote_sha)

    proyecto = _hub_proyecto(p, data)
    hub_claims, hub_err = hub_consultar_desarrollos(proyecto)
    if hub_err:
        resultado["hub_estado"] = "error"
        resultado["hub_aviso"] = hub_err
        if (data.get("rules") or {}).get("require_hub_sync"):
            raise ErrorSyncRemoto(
                f"espejo Memory Hub Postgres fallo (require_hub_sync=true): {hub_err}"
            )
    elif hub_configurado():
        resultado["hub_estado"] = "ok"
    else:
        resultado["hub_estado"] = "no_configurado"

    remoto_por_id, en_desarrollo = _combinar_reclamos(data, remote_data, hub_claims)
    resultado.update(
        remote_sha=remote_sha,
        remote_data=remote_data,
        remoto_features=remoto_por_id,
        hub_claims=hub_claims,
        en_desarrollo=en_desarrollo,
        adelante_local=adelante,
        atras_local=atras,
    )
    return resultado


# --- validacion de conflictos ----------------------------------------------

def _mensaje_conflicto(fid, nombre: str, claim: dict, remoto: str, base: str, accion: str) -> str:
    fuente = claim.get("fuente") or "remoto"
    fuente_txt = {
        "git": f"{remoto}/{base}",
        "hub": "Memory Hub Postgres",
        "git+hub": f"{remoto}/{base} + Memory Hub Postgres",
        "local": "backlog local",
    }.get(fuente, fuente)
    detalles = []
    if claim.get("email") and claim.get("email") != (claim.get("por") or "").lower():
        detalles.append(claim["email"])
    if claim.get("host"):
        detalles.append(claim["host"])
    extra = f" ({' · '.join(detalles)})" if detalles else ""
    rama = claim.get("branch") or "-"
    desde = claim.get("desde") or "-"
    return (
        f"la feature #{fid} ({nombre}) ya esta siendo desarrollada por "
        f"{claim.get('por') or '(desconocido)'}{extra}.\n"
        f"     rama: {rama} · desde: {desde} · fuente: {fuente_txt}\n"
        f"     No se permite {accion} mientras otro desarrollador la tiene tomada.\n"
        "     Coordina con esa persona; si el desarrollo fue abandonado, liberala con:\n"
        f"       worktree.py liberar --feature {fid} --forzar --yes"
    )


def validar_feature_libre(
    p: dict,
    data: dict,
    f: dict,
    *,
    accion: str = "iniciar",
    base: str | None = None,
    offline: bool = False,
    por: str | None = None,
) -> dict:
    """Valida primero en local y luego en remoto + Hub que otro dev no tomo `#fid`."""
    fid = str(f["id"])
    nombre = str(f.get("name") or "")
    remoto_est = leer_remoto(p, data, base=base, offline=offline, por=por)
    yo = remoto_est["yo"]
    remoto = remoto_est["remoto"]
    rama_base = remoto_est["base"]

    # Incluso en --offline o sin remoto, nunca pisar un reclamo ajeno ya visible en local.
    local_dueno = dueno_activo(f)
    if local_dueno and not mismo_desarrollador(local_dueno, yo):
        local_dueno = dict(local_dueno, fuente="local")
        raise ErrorConflictoDesarrollo(
            _mensaje_conflicto(fid, nombre, local_dueno, remoto, rama_base, accion)
        )

    if not remoto_est["activo"]:
        return remoto_est

    rf = remoto_est["remoto_features"].get(fid)
    if rf:
        if rf.get("status") in ("done", "superseded"):
            raise ErrorConflictoDesarrollo(
                f"la feature #{fid} ({nombre}) ya esta cerrada ('{rf.get('status')}') "
                f"en {remoto}/{rama_base}.\n"
                f"     Actualiza tu rama local (git pull) antes de continuar."
            )
        if rf.get("name") and nombre and slugify(rf["name"]) != slugify(nombre):
            raise ErrorConflictoDesarrollo(
                f"colision de ID #{fid}: en {remoto}/{rama_base} esa ficha es "
                f"'{rf['name']}', no '{nombre}'.\n"
                "     Sincroniza tu backlog antes de continuar para no pisar la ficha ajena."
            )

    claim = remoto_est["en_desarrollo"].get(fid)
    if claim and not mismo_desarrollador(claim, yo):
        raise ErrorConflictoDesarrollo(
            _mensaje_conflicto(fid, nombre, claim, remoto, rama_base, accion)
        )

    return remoto_est


# --- publicacion atomica (OCC) en Git + espejo Hub -------------------------

def _crear_commit_backlog(
    repo: Path,
    parent_sha: str,
    rel_backlog: str,
    contenido: bytes,
    mensaje: str,
    dev: dict,
) -> str:
    """Crea un commit hijo de `parent_sha` tocando SOLO `rel_backlog` sin tocar el arbol."""
    fd, idx_path = tempfile.mkstemp(prefix="harness-idx-", suffix=".idx")
    os.close(fd)
    os.unlink(idx_path)  # git read-tree crea el archivo de indice desde cero
    env_idx = {"GIT_INDEX_FILE": idx_path}
    try:
        code, out = _git_cmd(["read-tree", parent_sha], repo, env_extra=env_idx)
        if code != 0:
            raise ErrorSyncRemoto(f"git read-tree fallo: {out}")

        code, blob = _git_cmd(["hash-object", "-w", "--stdin"], repo, input_bytes=contenido)
        if code != 0 or not blob.strip():
            raise ErrorSyncRemoto(f"git hash-object fallo: {blob}")
        blob_sha = blob.strip()

        code, out = _git_cmd(
            ["update-index", "--add", "--cacheinfo", f"100644,{blob_sha},{rel_backlog}"],
            repo,
            env_extra=env_idx,
        )
        if code != 0:
            raise ErrorSyncRemoto(f"git update-index fallo: {out}")

        code, tree = _git_cmd(["write-tree"], repo, env_extra=env_idx)
        if code != 0 or not tree.strip():
            raise ErrorSyncRemoto(f"git write-tree fallo: {tree}")

        env_autor: dict[str, str] = {}
        c_n, g_n = _git_cmd(["config", "--get", "user.name"], repo)
        c_e, g_e = _git_cmd(["config", "--get", "user.email"], repo)
        if c_n != 0 or not g_n.strip():
            env_autor["GIT_AUTHOR_NAME"] = dev["por"]
            env_autor["GIT_COMMITTER_NAME"] = dev["por"]
        if c_e != 0 or not g_e.strip():
            correo = dev.get("email") or f"{slugify(dev['por'])}@harness.local"
            env_autor["GIT_AUTHOR_EMAIL"] = correo
            env_autor["GIT_COMMITTER_EMAIL"] = correo

        code, commit = _git_cmd(
            ["commit-tree", tree.strip(), "-p", parent_sha, "-m", mensaje],
            repo,
            env_extra=env_autor or None,
        )
        if code != 0 or not commit.strip():
            raise ErrorSyncRemoto(f"git commit-tree fallo: {commit}")
        return commit.strip()
    finally:
        try:
            Path(idx_path).unlink(missing_ok=True)
        except OSError:
            pass


def _es_non_fast_forward(salida: str) -> bool:
    bajo = (salida or "").lower()
    return any(
        marca in bajo
        for marca in ("non-fast-forward", "fetch first", "failed to push some refs", "stale info")
    )


def _avanzar_base_local(
    repo: Path,
    base: str,
    old_remote_sha: str,
    new_sha: str,
    rel_backlog: str,
) -> bool:
    """Avanza la rama base local via fast-forward si esta limpia. True si el archivo quedo actualizado."""
    code, local_base = _git_cmd(["rev-parse", "--verify", f"refs/heads/{base}"], repo)
    if code != 0:
        return False
    local_sha = local_base.strip()
    if local_sha == new_sha:
        return False
    code, _ = _git_cmd(["merge-base", "--is-ancestor", local_sha, new_sha], repo)
    if code != 0:
        return False  # la rama base local tiene commits propios: no se toca

    code, actual = _git_cmd(["rev-parse", "--abbrev-ref", "HEAD"], repo)
    en_base = (code == 0 and actual.strip() == base)
    if not en_base:
        code, _ = _git_cmd(["update-ref", f"refs/heads/{base}", new_sha, local_sha], repo)
        return False  # el archivo del working tree actual no corresponde a <base>

    # Estamos parados en <base>: solo hacemos ff-only si el backlog no tiene cambios sucios.
    code, dirty = _git_cmd(["status", "--porcelain", "--", rel_backlog], repo)
    if code != 0 or dirty.strip():
        return False
    code, _ = _git_cmd(["merge", "--ff-only", new_sha], repo)
    return code == 0


def _mezclar_en_remoto(remote_data: dict | None, local_data: dict, f_local: dict, fid_str: str) -> dict:
    """Actualiza solo la ficha `fid_str` sobre `remote_data`, preservando el resto del equipo."""
    if remote_data is None:
        base_doc = copy.deepcopy(local_data)
    else:
        base_doc = copy.deepcopy(remote_data)
    base_doc.setdefault("project", local_data.get("project", ""))
    base_doc.setdefault("rules", copy.deepcopy(local_data.get("rules") or {}))
    base_doc.setdefault("features", [])

    destino = next((x for x in base_doc["features"] if str(x.get("id")) == fid_str), None)
    if destino is None:
        base_doc["features"].append(copy.deepcopy(f_local))
    else:
        for campo in _CAMPOS_SPEC_COMPARTIDOS:
            if campo in f_local and f_local[campo] not in (None, ""):
                destino[campo] = copy.deepcopy(f_local[campo])
        for campo in _CAMPOS_DESARROLLO_COMPARTIDOS:
            if campo in f_local:
                destino[campo] = copy.deepcopy(f_local[campo])
            elif campo == "desarrollo":
                destino.pop("desarrollo", None)
    return base_doc


def _mezclar_remoto_en_local(local_data: dict, remote_data: dict, fid_actual: str) -> dict:
    """Incorpora al backlog local los estados remotos de otras features sin perder fichas locales."""
    out = copy.deepcopy(local_data)
    locales = {str(x.get("id")): x for x in out.get("features") or []}
    for rf in remote_data.get("features") or []:
        rfid = str(rf.get("id"))
        if rfid == fid_actual:
            continue
        if rfid not in locales:
            out["features"].append(copy.deepcopy(rf))
        else:
            lf = locales[rfid]
            # Si otro dev tomo o cerro esa feature en remoto, se refleja en local.
            if rf.get("status") in ("done", "superseded") or dueno_activo(rf):
                lf["status"] = rf.get("status", lf.get("status"))
                for campo in ("desarrollo", "branch", "started_at", "closed_at"):
                    if campo in rf:
                        lf[campo] = copy.deepcopy(rf[campo])
    return out


def publicar_reclamo(
    p: dict,
    data: dict,
    f: dict,
    desarrollo: dict,
    *,
    base: str | None = None,
    offline: bool = False,
    por: str | None = None,
) -> dict:
    """Publica el estado `desarrollando` en `origin/<base>` (OCC) y en Memory Hub Postgres.

    Devuelve un resumen con `publicado_git`, `commit`, `ff_local`, `hub_ok`,
    `hub_aviso` y `data_actualizada` (para guardar localmente si no hubo ff).
    """
    modo = evaluar_modo(p, data, base=base, offline=offline)
    yo = identidad_actual(modo["repo"], por=por)
    fid = str(f["id"])
    nombre = str(f.get("name") or "")
    resumen = {
        "activo": modo["activo"],
        "offline": modo["offline"],
        "omitido_entorno": modo["omitido_entorno"],
        "remoto": modo["remoto"],
        "base": modo["base"],
        "publicado_git": False,
        "commit": None,
        "ff_local": False,
        "hub_ok": False,
        "hub_aviso": None,
        "data_actualizada": data,
    }
    if modo["error_config"]:
        raise ErrorSyncRemoto(modo["error_config"])
    if not modo["activo"]:
        return resumen

    repo = modo["repo"]
    remoto = modo["remoto"]
    rama_base = modo["base"]
    rel_backlog = modo["rel_backlog"]
    assert repo is not None and rel_backlog is not None

    mensaje = f"harness: #{fid} desarrollando ({desarrollo['por']})"
    for intento in range(MAX_REINTENTOS_OCC):
        code, out = _git_cmd(["fetch", remoto, rama_base], repo)
        if code != 0:
            raise ErrorSyncRemoto(f"no se pudo hacer fetch de {remoto}/{rama_base}: {out}")
        code, sha = _git_cmd(["rev-parse", "--verify", f"refs/remotes/{remoto}/{rama_base}"], repo)
        if code != 0 or not sha.strip():
            raise ErrorSyncRemoto(f"no existe {remoto}/{rama_base} tras fetch")
        remote_sha = sha.strip()
        remote_data = _leer_backlog_en_ref(repo, remote_sha, rel_backlog)

        # Revalidacion justo antes del push (cierra la ventana de carrera entre devs).
        remoto_por_id, en_desarrollo = _combinar_reclamos(data, remote_data, {})
        rf = remoto_por_id.get(fid)
        if rf and rf.get("status") in ("done", "superseded"):
            raise ErrorConflictoDesarrollo(
                f"la feature #{fid} ya se cerro ('{rf['status']}') en {remoto}/{rama_base}."
            )
        if rf and rf.get("name") and nombre and slugify(rf["name"]) != slugify(nombre):
            raise ErrorConflictoDesarrollo(
                f"colision de ID #{fid}: en {remoto}/{rama_base} es '{rf['name']}', no '{nombre}'."
            )
        claim = en_desarrollo.get(fid)
        if claim and not mismo_desarrollador(claim, yo):
            raise ErrorConflictoDesarrollo(
                _mensaje_conflicto(fid, nombre, claim, remoto, rama_base, "iniciar")
            )

        nuevo_remoto = _mezclar_en_remoto(remote_data, data, f, fid)
        payload = (json.dumps(nuevo_remoto, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        commit_sha = _crear_commit_backlog(repo, remote_sha, rel_backlog, payload, mensaje, yo)

        code, out = _git_cmd(["push", remoto, f"{commit_sha}:refs/heads/{rama_base}"], repo)
        if code == 0:
            _git_cmd(["fetch", remoto, rama_base], repo)
            ff = _avanzar_base_local(repo, rama_base, remote_sha, commit_sha, rel_backlog)
            resumen["publicado_git"] = True
            resumen["commit"] = commit_sha
            resumen["ff_local"] = ff
            resumen["data_actualizada"] = _mezclar_remoto_en_local(data, nuevo_remoto, fid)
            break
        if _es_non_fast_forward(out) and intento < MAX_REINTENTOS_OCC - 1:
            continue
        primera = out.splitlines()[0] if out else "push rechazado"
        raise ErrorSyncRemoto(
            f"no se pudo subir el estado 'desarrollando' a {remoto}/{rama_base}: {primera}\n"
            "     Revisa permisos/branch protection o usa --offline para emergencias."
        )

    hub_ok, hub_err = hub_publicar_desarrollo(_hub_proyecto(p, data), f, desarrollo)
    resumen["hub_ok"] = hub_ok
    resumen["hub_aviso"] = hub_err
    if hub_err and (data.get("rules") or {}).get("require_hub_sync"):
        raise ErrorSyncRemoto(
            f"espejo Memory Hub Postgres fallo (require_hub_sync=true): {hub_err}"
        )
    return resumen


def publicar_liberacion(
    p: dict,
    data: dict,
    f: dict,
    *,
    nuevo_estado: str = "todo",
    base: str | None = None,
    offline: bool = False,
    por: str | None = None,
) -> dict:
    """Publica la liberacion de una feature en `origin/<base>` y Memory Hub Postgres."""
    modo = evaluar_modo(p, data, base=base, offline=offline)
    yo = identidad_actual(modo["repo"], por=por)
    fid = str(f["id"])
    resumen = {
        "activo": modo["activo"],
        "offline": modo["offline"],
        "remoto": modo["remoto"],
        "base": modo["base"],
        "publicado_git": False,
        "commit": None,
        "ff_local": False,
        "hub_ok": False,
        "hub_aviso": None,
        "data_actualizada": data,
    }
    if modo["error_config"]:
        raise ErrorSyncRemoto(modo["error_config"])
    if not modo["activo"]:
        return resumen

    repo = modo["repo"]
    remoto = modo["remoto"]
    rama_base = modo["base"]
    rel_backlog = modo["rel_backlog"]
    assert repo is not None and rel_backlog is not None

    mensaje = f"harness: #{fid} liberada ({yo['por']})"
    for intento in range(MAX_REINTENTOS_OCC):
        code, out = _git_cmd(["fetch", remoto, rama_base], repo)
        if code != 0:
            raise ErrorSyncRemoto(f"no se pudo hacer fetch de {remoto}/{rama_base}: {out}")
        code, sha = _git_cmd(["rev-parse", "--verify", f"refs/remotes/{remoto}/{rama_base}"], repo)
        if code != 0 or not sha.strip():
            raise ErrorSyncRemoto(f"no existe {remoto}/{rama_base} tras fetch")
        remote_sha = sha.strip()
        remote_data = _leer_backlog_en_ref(repo, remote_sha, rel_backlog)
        nuevo_remoto = _mezclar_en_remoto(remote_data, data, f, fid)
        # Asegura que el reclamo y el worktree local desaparezcan del remoto.
        for rf in nuevo_remoto.get("features") or []:
            if str(rf.get("id")) == fid:
                rf["status"] = nuevo_estado
                rf.pop("desarrollo", None)
                rf.pop("worktree", None)
        payload = (json.dumps(nuevo_remoto, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        commit_sha = _crear_commit_backlog(repo, remote_sha, rel_backlog, payload, mensaje, yo)

        code, out = _git_cmd(["push", remoto, f"{commit_sha}:refs/heads/{rama_base}"], repo)
        if code == 0:
            _git_cmd(["fetch", remoto, rama_base], repo)
            ff = _avanzar_base_local(repo, rama_base, remote_sha, commit_sha, rel_backlog)
            resumen["publicado_git"] = True
            resumen["commit"] = commit_sha
            resumen["ff_local"] = ff
            resumen["data_actualizada"] = _mezclar_remoto_en_local(data, nuevo_remoto, fid)
            break
        if _es_non_fast_forward(out) and intento < MAX_REINTENTOS_OCC - 1:
            continue
        primera = out.splitlines()[0] if out else "push rechazado"
        raise ErrorSyncRemoto(
            f"no se pudo subir la liberacion a {remoto}/{rama_base}: {primera}"
        )

    hub_ok, hub_err = hub_liberar_desarrollo(_hub_proyecto(p, data), f, nuevo_estado=nuevo_estado)
    resumen["hub_ok"] = hub_ok
    resumen["hub_aviso"] = hub_err
    return resumen


# --- utilidades de vista combinada (para estado.py / gate.py) --------------

def aplicar_vista_remota(data: dict, remoto_est: dict) -> tuple[dict, list[dict]]:
    """Superpone el estado remoto en memoria sin tocar disco.

    Devuelve (data_vista, conflictos) donde cada conflicto indica una feature
    abierta localmente que otro desarrollador tiene tomada en remoto/Hub.
    """
    vista = copy.deepcopy(data)
    if not remoto_est.get("activo"):
        return vista, []

    yo = remoto_est["yo"]
    en_des = remoto_est.get("en_desarrollo") or {}
    rem_feats = remoto_est.get("remoto_features") or {}
    locales = {str(f.get("id")): f for f in vista.get("features") or []}
    conflictos: list[dict] = []

    for fid, f in locales.items():
        rf = rem_feats.get(fid)
        claim = en_des.get(fid)
        local_activo = (f.get("status") == "in_progress" and not es_de_otro_dev(f, yo))
        if claim and not mismo_desarrollador(claim, yo):
            if local_activo and (f.get("worktree") or dueno_activo(f)):
                conflictos.append({
                    "id": fid, "name": f.get("name", ""), "claim": claim,
                })
            # Marca el estado remoto en la vista para que estado.py no la sugiera libre.
            f["status"] = "in_progress"
            f["desarrollo"] = dict(claim)
            f["_remoto_actualizado"] = True
            if claim.get("branch"):
                f["branch"] = claim["branch"]
        elif rf and rf.get("status") in ("done", "superseded") and f.get("status") != rf.get("status"):
            f["status"] = rf["status"]
            f["_remoto_actualizado"] = True
        elif local_activo and fid not in en_des:
            # Iniciada en local (--offline o sin subir): avisar que falta publicar.
            f["_sin_publicar_remoto"] = True

    # Features que existen en remoto (en desarrollo) y aun no entraron al backlog local.
    for fid, rf in rem_feats.items():
        if fid not in locales:
            nuevo = copy.deepcopy(rf)
            if fid in en_des:
                nuevo["desarrollo"] = dict(en_des[fid])
                nuevo["status"] = "in_progress"
            nuevo["_solo_remoto"] = True
            vista["features"].append(nuevo)

    return vista, conflictos


def base_mas_reciente(repo: Path, base: str, remoto: str = REMOTO_DEFECTO) -> str | None:
    """Devuelve `refs/remotes/<remoto>/<base>` si es estrictamente mas nueva que la local."""
    c_loc, sha_loc = _git_cmd(["rev-parse", "--verify", f"refs/heads/{base}"], repo)
    c_rem, sha_rem = _git_cmd(["rev-parse", "--verify", f"refs/remotes/{remoto}/{base}"], repo)
    if c_rem != 0 or not sha_rem.strip():
        return None
    sha_rem = sha_rem.strip()
    if c_loc != 0:
        return sha_rem
    sha_loc = sha_loc.strip()
    if sha_loc == sha_rem:
        return sha_rem
    c_anc, _ = _git_cmd(["merge-base", "--is-ancestor", sha_loc, sha_rem], repo)
    return sha_rem if c_anc == 0 else None


# --- CLI directo -----------------------------------------------------------

def cmd_estado(args) -> None:
    p = paths()
    data = load_backlog(p)
    try:
        est = leer_remoto(p, data, base=args.base, offline=args.offline, por=args.por)
    except ErrorSyncRemoto as exc:
        sys.exit(f"[!!] {exc}")
    if not est["activo"]:
        motivo = ("--offline" if est["offline"] else
                  "HARNESS_SIN_SYNC_REMOTO" if est["omitido_entorno"] else
                  "sin remoto origin (o regla apagada)")
        print(f"[i]  sync remoto inactivo ({motivo}).")
        return
    print(f"== Sync remoto ({est['remoto']}/{est['base']} @ {est['remote_sha'][:7]}) ==")
    print(f"   desarrollador actual: {est['yo']['por']} ({est['yo']['id']} · {est['yo']['host']})")
    print(f"   Memory Hub Postgres:  {est['hub_estado']}"
          + (f" ({est['hub_aviso']})" if est["hub_aviso"] else ""))
    if est["atras_local"]:
        print(f"   [!] rama local '{est['base']}' atrasada {est['atras_local']} commit(s) "
              f"respecto a {est['remoto']}/{est['base']}")
    if not est["en_desarrollo"]:
        print("   ninguna feature en desarrollo activo.")
        return
    print("   features desarrollando:")
    for fid, c in sorted(est["en_desarrollo"].items(), key=lambda kv: (len(kv[0]), kv[0])):
        quien = "tu" if mismo_desarrollador(c, est["yo"]) else formato_dueno(c)
        print(f"     - #{fid} · {quien} · rama {c.get('branch') or '-'} · "
              f"desde {c.get('desde') or '-'} [{c.get('fuente')}]")


def cmd_publicar(args) -> None:
    p = paths()
    data = load_backlog(p)
    f = get_feature(data, args.feature)
    dev = identidad_actual(repo_harness(p)[0], por=args.por)
    if f.get("status") != "in_progress":
        sys.exit(f"[!!] la feature #{f['id']} esta en '{f.get('status')}', no en 'in_progress'.\n"
                 f"     Arrancala primero con: worktree.py start --feature {f['id']}")
    desarrollo = construir_desarrollo(
        dev,
        branch=f.get("branch") or "",
        desde=f.get("started_at"),
        offline=False,
    )
    f["desarrollo"] = desarrollo
    try:
        validar_feature_libre(p, data, f, accion="publicar", base=args.base,
                              offline=args.offline, por=args.por)
        res = publicar_reclamo(p, data, f, desarrollo, base=args.base,
                               offline=args.offline, por=args.por)
    except (ErrorSyncRemoto, ErrorConflictoDesarrollo) as exc:
        sys.exit(f"[!!] {exc}")
    if not res["ff_local"]:
        save_backlog(p, res["data_actualizada"])
    bitacora(p, f"sync remoto #{f['id']} desarrollando ({dev['por']})"
                + (f" commit={res['commit'][:7]}" if res["commit"] else ""))
    if res["publicado_git"]:
        print(f"[ok] feature #{f['id']} publicada como desarrollando en "
              f"{res['remoto']}/{res['base']} ({res['commit'][:7]})")
    else:
        print(f"[i]  sync remoto no activo para #{f['id']}.")
    if res["hub_ok"]:
        print("[ok] espejo actualizado en Memory Hub Postgres")
    elif res["hub_aviso"]:
        print(f"[!]  espejo Memory Hub Postgres: {res['hub_aviso']}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Sincronizacion multi-dev de features en desarrollo")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("estado", help="consulta el estado remoto y del Hub Postgres")
    s.add_argument("--base"); s.add_argument("--por")
    s.add_argument("--offline", action="store_true")
    s.set_defaults(fn=cmd_estado)
    s = sub.add_parser("publicar", help="publica una feature ya in_progress (p.ej. arrancada --offline)")
    s.add_argument("--feature", required=True)
    s.add_argument("--base"); s.add_argument("--por")
    s.add_argument("--offline", action="store_true")
    s.set_defaults(fn=cmd_publicar)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
