#!/usr/bin/env python3
"""Utilidades de seguridad OWASP para harness-flow (versiones, ZAP DAST, diff).

Concentra tres piezas que usan stack.py, gate.py y revision.py:
  1. Comparacion semantica de versiones minimas (sin comparacion lexicografica).
  2. Reescritura de URL local para Docker Desktop y parseo de alertas OWASP ZAP
     (JSON `-J` con respaldo sobre stdout; alertas High => status='failed').
  3. Escaneo ligero de secretos hardcodeados y deteccion de manifiestos de
     dependencias tocados sobre el diff de la feature (monorepo y multi-repo).
     Nunca imprime el valor del secreto encontrado: solo archivo, linea y regla.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse


# --- 1. Comparacion semantica de versiones ----------------------------------

def parse_version(ver: str) -> tuple[int, ...]:
    """Extrae tupla numerica de una cadena de version ('^19.2.1' -> (19, 2, 1))."""
    return tuple(int(x) for x in re.findall(r"\d+", str(ver or "")))


def version_menor(actual: str, minima: str) -> bool:
    """True si `actual` es estrictamente menor que `minima`.

    Si `actual` declara menos segmentos que `minima` (ej. '8.0' contra '8.0.0',
    o '1.23' contra '1.23.0'), compara contra el prefijo de igual largo para no
    reportar la version minima misma como inferior.
    """
    det = parse_version(actual)
    req = parse_version(minima)
    if not det or not req:
        return False
    return det < req[:len(det)]


# --- 2. OWASP ZAP DAST (URL Docker + parseo de alertas) ---------------------

_ZAP_RISK_MAP = {
    "3": "High",
    "2": "Medium",
    "1": "Low",
    "0": "Informational",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "informational": "Informational",
    "info": "Informational",
}

_LOCALHOST_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1"})


def es_url_localhost(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return host in _LOCALHOST_HOSTS


def reescribir_url_docker(url: str, plataforma: str | None = None) -> str:
    """En macOS/Windows (Docker Desktop), localhost dentro del contenedor es el
    propio contenedor ZAP, no el host: reescribe a host.docker.internal.
    """
    plat = plataforma if plataforma is not None else sys.platform
    if plat not in ("darwin", "win32"):
        return url
    try:
        parsed = urlparse(url)
    except ValueError:
        return url
    host = (parsed.hostname or "").lower()
    if host not in _LOCALHOST_HOSTS:
        return url
    netloc = "host.docker.internal"
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"
    if parsed.username:
        auth = parsed.username + (f":{parsed.password}" if parsed.password else "")
        netloc = f"{auth}@{netloc}"
    return urlunparse(parsed._replace(netloc=netloc))


def parsear_reporte_zap_json(data: dict[str, Any]) -> dict[str, Any]:
    """Parsea el JSON generado por `zap-api-scan.py -J` / `zap-baseline.py -J`."""
    counts = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
    high_alerts: list[dict[str, Any]] = []
    vistas_high: set[str] = set()

    sites = data.get("site") or []
    if isinstance(sites, dict):
        sites = [sites]
    for site in sites:
        if not isinstance(site, dict):
            continue
        for alert in site.get("alerts") or []:
            if not isinstance(alert, dict):
                continue
            raw_risk = str(alert.get("riskcode", "")).strip()
            level = _ZAP_RISK_MAP.get(raw_risk)
            if not level:
                riskdesc = str(alert.get("riskdesc", "")).strip().split(" ", 1)[0].lower()
                level = _ZAP_RISK_MAP.get(riskdesc, "Informational")
            counts[level] += 1
            if level == "High":
                nombre = str(alert.get("name") or alert.get("alert") or "Alerta High sin nombre").strip()
                if nombre not in vistas_high:
                    vistas_high.add(nombre)
                    high_alerts.append({
                        "name": nombre,
                        "cweid": str(alert.get("cweid") or ""),
                        "count": str(alert.get("count") or "1"),
                    })
    return {"counts": counts, "high_alerts": high_alerts, "source": "json"}


_ZAP_FAIL_NEW_RE = re.compile(r"FAIL-NEW:\s*(\d+)", re.IGNORECASE)
_ZAP_FAIL_INPROG_RE = re.compile(r"FAIL-INPROG:\s*(\d+)", re.IGNORECASE)
_ZAP_WARN_NEW_RE = re.compile(r"WARN-NEW:\s*(\d+)", re.IGNORECASE)
_ZAP_WARN_INPROG_RE = re.compile(r"WARN-INPROG:\s*(\d+)", re.IGNORECASE)
_ZAP_INFO_RE = re.compile(r"\bINFO:\s*(\d+)", re.IGNORECASE)
_ZAP_HIGH_LINE_RE = re.compile(
    r"^\s*(?:FAIL-NEW|FAIL-INPROG):\s+(.+?)(?:\s+\[\d+\])?\s*$"
    r"|^\s*(?:WARN-NEW|FAIL-NEW).*?\bHigh\b.*?:\s*(.+?)\s*$",
    re.IGNORECASE,
)


def parsear_salida_zap_texto(output: str) -> dict[str, Any]:
    """Respaldo sobre stdout de ZAP cuando el reporte JSON no existe."""
    counts = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
    high_alerts: list[dict[str, Any]] = []
    txt = output or ""

    m_fn = _ZAP_FAIL_NEW_RE.search(txt)
    m_fi = _ZAP_FAIL_INPROG_RE.search(txt)
    m_wn = _ZAP_WARN_NEW_RE.search(txt)
    m_wi = _ZAP_WARN_INPROG_RE.search(txt)
    m_in = _ZAP_INFO_RE.search(txt)

    fail_total = (int(m_fn.group(1)) if m_fn else 0) + (int(m_fi.group(1)) if m_fi else 0)
    warn_total = (int(m_wn.group(1)) if m_wn else 0) + (int(m_wi.group(1)) if m_wi else 0)
    info_total = int(m_in.group(1)) if m_in else 0

    counts["High"] = fail_total
    counts["Medium"] = warn_total
    counts["Informational"] = info_total

    vistas: set[str] = set()
    for ln in txt.splitlines():
        m = _ZAP_HIGH_LINE_RE.match(ln)
        if not m:
            continue
        nombre = (m.group(1) or m.group(2) or "").strip()
        if nombre and not nombre.isdigit() and nombre not in vistas:
            vistas.add(nombre)
            high_alerts.append({"name": nombre, "cweid": "", "count": "1"})
    if high_alerts and counts["High"] < len(high_alerts):
        counts["High"] = len(high_alerts)

    parsed_summary = any(x is not None for x in (m_fn, m_fi, m_wn, m_wi, m_in)) or bool(high_alerts)
    return {
        "counts": counts,
        "high_alerts": high_alerts,
        "source": "stdout" if parsed_summary else "none",
    }


def evaluar_dast_zap(
    exit_code: int,
    output: str,
    report_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Determina veredicto DAST ('passed' | 'warnings' | 'failed' | 'error').

    Regla acordada (references/seguridad-owasp-y-zap.md):
      - Alertas High > 0 => 'failed' (bloquea `stack.py auditar` con exit 1).
      - Alertas Medium/Low > 0 sin High => 'warnings' (no cambia exit de SCA).
      - exit_code != 0 sin resumen ni JSON parseable => 'error' (Docker/target caido).
      - exit_code == 0 y sin alertas => 'passed'.
    """
    parsed = parsear_reporte_zap_json(report_json) if isinstance(report_json, dict) else parsear_salida_zap_texto(output)
    counts = parsed["counts"]
    high_alerts = parsed["high_alerts"]

    if counts["High"] > 0:
        status = "failed"
    elif counts["Medium"] > 0 or counts["Low"] > 0:
        status = "warnings"
    elif exit_code == 0:
        status = "passed"
    elif parsed["source"] == "none":
        status = "error"
    else:
        status = "warnings"

    return {
        "status": status,
        "alerts": counts,
        "high_alerts": high_alerts,
        "source": parsed["source"],
    }


# --- 3. Escaneo ligero de secretos y manifiestos de dependencias en diff ----

_IGNORE_MARKER = "harness-ignore-secret"

# Patrones de alta precision (prefijos reales de proveedor / claves privadas).
_SECRET_PATTERNS_STRICT: tuple[tuple[str, re.Pattern], ...] = (
    ("clave privada PEM/OpenSSH", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----")),
    ("AWS Access Key ID", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub Token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("GitLab PAT", re.compile(r"\bglpat-[A-Za-z0-9\-_]{20,}\b")),
    ("Stripe Live Key", re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{20,}\b")),
    ("Slack Token", re.compile(r"\bxox[baprs]-[0-9]{10,}-[A-Za-z0-9-]{10,}\b")),
    ("Google API Key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("LLM Provider Key (Anthropic/OpenAI/xAI)", re.compile(r"\b(?:sk-ant-[A-Za-z0-9\-_]{20,}|sk-proj-[A-Za-z0-9\-_]{20,}|xai-[A-Za-z0-9]{30,})\b")),
)

# Patrones contextuales (solo en archivos de codigo/config, excluyendo tests/docs/examples).
_SECRET_CONNSTR_RE = re.compile(
    r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqps?|mssql)://[^:\s/@\"']+:([^@\s$%{}\"'`]{8,})@([^\s/\"'`]+)",
    re.IGNORECASE,
)
_SECRET_ASSIGN_RE = re.compile(
    r"""(?i)\b(?:api[_-]?key|secret[_-]?key|client[_-]?secret|jwt[_-]?secret|signing[_-]?key|access[_-]?token|auth[_-]?token|private[_-]?key|db[_-]?password|database[_-]?password)\b\s*[:=]\s*["']([^"'\s]{12,})["']"""
)

_PLACEHOLDER_RE = re.compile(
    r"(?:example|dummy|fake|test|sample|changeme|placeholder|your[_-]|replace[_-]?me|redacted|"
    r"secret[_-]?here|token[_-]?here|password|postgres|localhost|127\.0\.0\.1|\$\{|\{\{|xxxx|0000|123456)",
    re.IGNORECASE,
)
_LOCAL_DB_HOSTS = frozenset({"localhost", "127.0.0.1", "postgres", "db", "mysql", "mongo", "redis", "sqlserver", "host.docker.internal"})

_NON_PROD_FILE_RE = re.compile(
    r"(?:^|/)(?:tests?|__tests__|spec|fixtures?|mocks?|docs?|examples?)/"
    r"|(?:_test\.go|\.test\.[jt]sx?|\.spec\.[jt]sx?|Tests?\.cs|Test\.java|Test\.kt|Tests?\.swift)$"
    r"|\.(?:md|txt|rst|example|sample|template)$"
    r"|(?:^|/)\.env\.example$",
    re.IGNORECASE,
)

# Manifiestos y lockfiles de dependencias de los 12 stacks.
_DEP_EXACT_NAMES = frozenset({
    "go.mod", "go.sum",
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "cargo.toml", "cargo.lock",
    "directory.packages.props", "packages.lock.json", "nuget.config",
    "pom.xml", "build.gradle", "build.gradle.kts", "libs.versions.toml",
    "pyproject.toml", "poetry.lock", "uv.lock", "pipfile", "pipfile.lock",
    "package.swift", "package.resolved",
})


def es_archivo_dependencias(ruta_rel: str) -> bool:
    """True si `ruta_rel` corresponde a un manifiesto o lockfile de dependencias."""
    nombre = Path(ruta_rel).name.lower()
    if nombre in _DEP_EXACT_NAMES:
        return True
    if nombre.endswith(".csproj") or nombre.endswith(".fsproj"):
        return True
    if re.fullmatch(r"requirements(?:[-_.\w]*)?\.txt", nombre):
        return True
    return False


def _es_placeholder(valor: str) -> bool:
    if not valor or _PLACEHOLDER_RE.search(valor):
        return True
    if len(set(valor)) <= 3:  # ej. 'aaaaaaaaaaaa'
        return True
    return False


def escanear_diff_seguridad(diff_text: str, prefijo_repo: str = "") -> dict[str, Any]:
    """Analiza un unified diff buscando secretos en lineas agregadas y cambios en dependencias.

    Devuelve:
      {
        "secrets": [{"file": str, "line": int, "rule": str}],
        "dep_files": [str, ...],
      }
    Nunca incluye el valor del secreto en el resultado.
    """
    secrets: list[dict[str, Any]] = []
    dep_files: list[str] = []
    dep_vistos: set[str] = set()

    archivo_actual: str | None = None
    linea_actual = 0

    for raw in (diff_text or "").splitlines():
        if raw.startswith("+++ b/"):
            archivo_actual = raw[6:].strip()
            linea_actual = 0
            if es_archivo_dependencias(archivo_actual) and archivo_actual not in dep_vistos:
                dep_vistos.add(archivo_actual)
                dep_files.append(archivo_actual)
            continue
        if raw.startswith("+++ /dev/null"):
            archivo_actual = None
            continue
        if raw.startswith("@@ "):
            m = re.search(r"\+(\d+)", raw)
            linea_actual = int(m.group(1)) if m else 0
            continue
        if archivo_actual is None:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            linea = raw[1:]
            num = linea_actual
            linea_actual += 1
            if _IGNORE_MARKER in linea:
                continue
            etiqueta = f"{prefijo_repo}/{archivo_actual}" if prefijo_repo else archivo_actual
            encontrado = False
            for nombre_regla, patron in _SECRET_PATTERNS_STRICT:
                m = patron.search(linea)
                if m and not _es_placeholder(m.group(0)):
                    secrets.append({"file": etiqueta, "line": num, "rule": nombre_regla})
                    encontrado = True
                    break
            if encontrado:
                continue
            if _NON_PROD_FILE_RE.search(archivo_actual):
                continue
            m_cs = _SECRET_CONNSTR_RE.search(linea)
            if m_cs:
                pwd, host = m_cs.group(1), m_cs.group(2).split(":", 1)[0].lower()
                if host not in _LOCAL_DB_HOSTS and not _es_placeholder(pwd):
                    secrets.append({"file": etiqueta, "line": num, "rule": "credencial en cadena de conexion"})
                    continue
            m_as = _SECRET_ASSIGN_RE.search(linea)
            if m_as and not _es_placeholder(m_as.group(1)):
                secrets.append({"file": etiqueta, "line": num, "rule": "secreto/token hardcodeado"})
        elif not raw.startswith("-"):
            linea_actual += 1

    return {"secrets": secrets, "dep_files": dep_files}


def _git_diff_repo(repo: Path, base: str, head: str = "HEAD") -> str:
    """Diff base..head de un repo git; cadena vacia si no se puede resolver."""
    import subprocess
    try:
        r_mb = subprocess.run(
            ["git", "merge-base", base, head],
            cwd=str(repo), capture_output=True, text=True, timeout=30,
        )
        ref = r_mb.stdout.strip() if r_mb.returncode == 0 and r_mb.stdout.strip() else base
        r = subprocess.run(
            ["git", "diff", "--no-ext-diff", "--no-textconv", "-U0", ref, head, "--"],
            cwd=str(repo), capture_output=True, text=True, timeout=60,
        )
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def auditar_diff_feature(p: dict, data: dict, f: dict) -> dict[str, Any]:
    """Audita el diff real de la feature (monorepo o multi-repo).

    Devuelve:
      {
        "secrets": [{"file", "line", "rule"}],
        "deps_por_repo": [{"repo_name", "repo_path", "files": [...]}],
      }
    """
    secrets: list[dict[str, Any]] = []
    deps_por_repo: list[dict[str, Any]] = []

    if "multi_repo" in f:
        try:
            from multirepo import Invalid, check_registered
            manifest = check_registered(p, f, data.get("rules") or {})
        except Exception:
            return {"secrets": [], "deps_por_repo": []}
        for row in manifest.get("repos") or []:
            ruta = Path(row["repo"])
            nombre = row.get("microservicio") or ruta.name
            diff = _git_diff_repo(ruta, row["base_sha"], row["source_sha"])
            if not diff:
                continue
            res = escanear_diff_seguridad(diff, prefijo_repo=nombre)
            secrets.extend(res["secrets"])
            if res["dep_files"]:
                deps_por_repo.append({"repo_name": nombre, "repo_path": str(ruta), "files": res["dep_files"]})
        return {"secrets": secrets, "deps_por_repo": deps_por_repo}

    wt = f.get("worktree")
    arbol = Path(wt) if wt and Path(wt).is_dir() else Path(p["root"])
    base = (
        f.get("base_sha")
        or f.get("base_branch")
        or (data.get("rules") or {}).get("rama_base")
        or "develop"
    )
    diff = _git_diff_repo(arbol, base, "HEAD")
    if not diff:
        return {"secrets": [], "deps_por_repo": []}
    res = escanear_diff_seguridad(diff)
    secrets.extend(res["secrets"])
    if res["dep_files"]:
        deps_por_repo.append({"repo_name": arbol.name, "repo_path": str(arbol), "files": res["dep_files"]})
    return {"secrets": secrets, "deps_por_repo": deps_por_repo}
