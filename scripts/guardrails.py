#!/usr/bin/env python3
"""Mecanismo 3 (Guardrails): barreras deterministas que los agentes no pueden saltarse.

Las skills dicen como DEBERIA hacerse algo; los guardrails BLOQUEAN directamente
patrones prohibidos, ruido de comentarios de IA y cruces entre modulos separados
para que el camino mas corto sea tambien el correcto.

  guardrails.py init [--perfil estandar|spacex] [--forzar]
  guardrails.py check [--feature <id>] [--repo <ruta>] [--json]
  guardrails.py agregar --id <id> --patron "<regex>" --mensaje "<msg>"
                        [--glob <g> ...] [--excluir <e> ...]
                        [--severidad block|warn] [--stack <sid> ...] --yes --por <usuario>
  guardrails.py promover --desde-skill <clase> --id <id> --patron "<regex>"
                         --mensaje "<msg>" [--glob <g> ...] [--stack <sid> ...] --yes --por <usuario>
  guardrails.py instalar-hook [--repo <ruta>] --yes
  guardrails.py quitar-hook [--repo <ruta>]

Agregar o promover un guardrail lo PROPONE el agente y lo decide el usuario: sin
`--yes --por` el comando muestra la propuesta y no registra nada. El hook
`pre-push` bloquea la subida de lineas que infringen un guardrail; lo instala el
usuario, no se versiona y no reemplaza un hook ajeno.
  guardrails.py desactivar --id <id> --motivo "<por que>" --yes
  guardrails.py list [--repo <ruta>]
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from comun import (  # noqa: E402
    bitacora, get_feature, git, load_backlog, now_iso, paths,
)
import seguridad  # noqa: E402

# Extensiones de codigo fuente sobre las que aplica la politica de comentarios.
EXT_CODIGO_SLASH = frozenset({
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".go", ".rs", ".cs", ".java", ".kt", ".swift", ".php",
})
EXT_CODIGO_HASH = frozenset({".py", ".rb"})
EXT_CODIGO = EXT_CODIGO_SLASH | EXT_CODIGO_HASH

_NON_PROD_FILE_RE = re.compile(
    r"(?:^|/)(?:tests?|__tests__|spec|fixtures?|mocks?|docs?|examples?)/"
    r"|(?:_test\.go|\.test\.[jt]sx?|\.spec\.[jt]sx?|Tests?\.cs|Test\.java|Test\.kt|Tests?\.swift)$"
    r"|\.(?:md|txt|rst|example|sample|template|json|ya?ml|toml|lock)$"
    r"|(?:^|/)(?:go\.mod|go\.sum)$",
    re.IGNORECASE,
)

# Exencion en linea: exige id exacto de la regla + motivo >= 10 caracteres.
_INLINE_EXEMPT_RE = re.compile(
    r"harness-ignore-guardrail:\s*([a-z0-9][a-z0-9_-]*)\s+(.+)$",
    re.IGNORECASE,
)

# Directivas tecnicas de compilador/linters que NUNCA se bloquean como comentario.
_DIRECTIVA_TECNICA_RE = re.compile(
    r"^(?:#!|#\s*-\*-|#\s*(?:noqa|type:\s*ignore|pragma:|pylint:|pyright:|ruff:|nosec|fmt:|isort:)"
    r"|//\s*(?:go:|nolint|@ts-|eslint-|prettier-ignore|biome-ignore|stylelint-|istanbul|c8|v8)"
    r"|///|/\*\*|//\s*@(?:param|returns?|deprecated|see)\b)",
    re.IGNORECASE,
)

# Comentarios narrativos / diario de agente / relleno de IA (modo 'anti-ruido').
_COMENTARIO_RUIDO_IA_RE = re.compile(
    r"^(?://|#)\s*(?:"
    r"(?:changed|updated|added|fixed|removed|modified|replaced|refactored|implemented|created|deleted)\b"
    r"|(?:cambiado|actualizado|agregado|a[nñ]adido|corregido|eliminado|modificado|reemplazado|refactorizado|implementado)\b"
    r"|(?:step|paso)\s+\d+\s*[:.-]"
    r"|(?:now\s+we|here\s+we|this\s+(?:function|method|class|block|line)\s+(?:does|handles|returns|creates|checks))"
    r"|(?:aqu[ií]\s+(?:se|hacemos|creamos|validamos|guardamos|llamamos)|esta\s+(?:funci[oó]n|clase)\s+(?:hace|devuelve))"
    r"|(?:\.\.\.\s*(?:rest|existing|previous|remaining)\b|(?:existing|previous)\s+(?:code|implementation)\b)"
    r"|(?:todo\s*:\s*(?:implement|implementar|add|agregar)\b|fixme\s*:\s*placeholder\b)"
    r")",
    re.IGNORECASE,
)

# Defaults seguros: patrones inequivocos de alto riesgo / cero falsos positivos.
REGLAS_DEFAULT: tuple[dict[str, Any], ...] = (
    {
        "id": "no-eval-dinamico",
        "descripcion": "Prohibido ejecutar codigo dinamico con eval() o new Function()",
        "severidad": "block",
        "globs": ["**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx", "**/*.mjs", "**/*.cjs"],
        "excluir_no_prod": True,
        "patron": r"(?<![.\w])(?:eval\s*\(|new\s+Function\s*\()",
        "mensaje": "eval() / new Function() prohibido por riesgo de inyeccion (OWASP A03)",
    },
    {
        "id": "no-html-crudo",
        "descripcion": "Prohibido inyectar HTML crudo sin sanitizar",
        "severidad": "block",
        "globs": ["**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx", "**/*.cs", "**/*.cshtml"],
        "excluir_no_prod": True,
        "patron": r"\b(?:dangerouslySetInnerHTML|bypassSecurityTrustHtml)\b|\bHtml\.Raw\s*\(",
        "mensaje": "HTML crudo sin sanitizar prohibido (XSS / OWASP A03)",
    },
    {
        "id": "no-pickle-inseguro",
        "descripcion": "Prohibido deserializar entrada no confiable con pickle.load/loads",
        "severidad": "block",
        "globs": ["**/*.py"],
        "excluir_no_prod": True,
        "patron": r"\bpickle\.loads?\s*\(",
        "mensaje": "pickle.load(s) prohibido por deserializacion insegura (OWASP A08)",
    },
    {
        "id": "no-debugger",
        "descripcion": "Prohibido commitear puntos de ruptura de depuracion en produccion",
        "severidad": "block",
        "globs": ["**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx", "**/*.py"],
        "excluir_no_prod": True,
        "patron": r"^\s*debugger\s*;?\s*$|\b(?:pdb\.set_trace|breakpoint)\s*\(\s*\)",
        "mensaje": "retira debugger / breakpoint() antes de cerrar",
    },
    {
        "id": "no-jwt-alg-none",
        "descripcion": "Prohibido desactivar firma JWT con algoritmo 'none'",
        "severidad": "block",
        "globs": ["**/*.js", "**/*.ts", "**/*.py", "**/*.go", "**/*.cs", "**/*.java", "**/*.kt", "**/*.rs"],
        "excluir_no_prod": True,
        "patron": r"""["']alg["']\s*[:=]\s*["']none["']""",
        "mensaje": "JWT con alg:'none' prohibido (OWASP A07)",
    },
    {
        "id": "py-no-bare-except",
        "descripcion": "Prohibido `except:` desnudo que traga cualquier excepcion",
        "severidad": "block",
        "globs": ["**/*.py"],
        "excluir_no_prod": True,
        "patron": r"^\s*except\s*:\s*(?:#.*)?$",
        "mensaje": "captura una excepcion especifica en vez de `except:` desnudo (McConnell)",
    },
    {
        "id": "go-no-sleep-en-tests",
        "descripcion": "Prohibido time.Sleep en tests Go (causa flakiness)",
        "severidad": "block",
        "globs": ["**/*_test.go"],
        "excluir_no_prod": False,
        "stacks": ["golang-hexagonal"],
        "patron": r"\btime\.Sleep\s*\(",
        "mensaje": "time.Sleep prohibido en tests Go; usa canales, contextos o relojes inyectables",
    },
    {
        "id": "angular-no-ngif-ngfor-legacy",
        "descripcion": "Preferir control flow nativo @if/@for en Angular 19+",
        "severidad": "warn",
        "globs": ["**/*.html"],
        "excluir_no_prod": True,
        "stacks": ["angular-product"],
        "patron": r"\*ng(?:If|For)\s*=",
        "mensaje": "usa control flow nativo @if / @for en lugar de *ngIf / *ngFor",
    },
)

# Frontera por defecto: evita el atajo mas corto de mezclar internos entre features.
FRONTERAS_DEFAULT: tuple[dict[str, Any], ...] = (
    {
        "id": "aislamiento-entre-features",
        "descripcion": "Una feature no puede importar capas internas de otra feature",
        "severidad": "block",
        "origen": "**/features/<modulo>/**",
        "import_prohibido": (
            r"""(?:from\s+["']|import\s*\(?["']|require\s*\(["'])[^"']*"""
            r"""features/(?!<modulo>/)[^/"']+/(?:domain|application|infrastructure|data-access|ui)(?:/|["'])"""
        ),
        "mensaje": "prohibido importar capas internas de otra feature; usa su punto de entrada publico",
    },
)

# Reglas adicionales del perfil estricto SpaceX (activables con `guardrails.py init --perfil spacex`).
REGLAS_PERFIL_SPACEX: tuple[dict[str, Any], ...] = (
    {
        "id": "no-use-effect",
        "descripcion": "Prohibido useEffect en React/Next.js (patron SpaceX/Lauren Tan)",
        "severidad": "block",
        "globs": ["**/*.tsx", "**/*.jsx", "**/*.ts", "**/*.js"],
        "excluir": ["**/*.test.*", "**/*.spec.*", "**/__tests__/**"],
        "stacks": ["nextjs-product"],
        "patron": r"\b(?:React\.)?useEffect\s*\(",
        "mensaje": "useEffect esta prohibido en este proyecto; deriva estado o usa Server Components/handlers",
    },
)

PERFILES_COMENTARIOS = ("anti-ruido", "sin-comentarios", "off")


def ruta_config(p: dict) -> Path:
    return p["harness"] / "guardrails.json"


def config_default(perfil: str = "estandar") -> dict[str, Any]:
    if perfil == "spacex":
        return {
            "version": 1,
            "perfil": "spacex",
            "comentarios": "sin-comentarios",
            "usar_defaults_stack": True,
            "reglas": [dict(r) for r in REGLAS_PERFIL_SPACEX],
            "fronteras": [dict(f) for f in FRONTERAS_DEFAULT],
            "comandos": [],
            "reglas_desactivadas": {},
        }
    return {
        "version": 1,
        "perfil": "estandar",
        "comentarios": "anti-ruido",
        "usar_defaults_stack": True,
        "reglas": [],
        "fronteras": [],
        "comandos": [],
        "reglas_desactivadas": {},
    }


def cargar_config(p: dict) -> dict[str, Any]:
    """Carga harness/guardrails.json; si no existe devuelve el perfil estandar."""
    ruta = ruta_config(p)
    if not ruta.exists():
        return config_default("estandar")
    if not ruta.is_file():
        raise ValueError(f"{ruta.name} no es un archivo regular")
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"{ruta.name} ilegible o JSON invalido: {exc}")
    if not isinstance(datos, dict):
        raise ValueError(f"{ruta.name} debe ser un objeto JSON")
    comentarios = datos.get("comentarios", "anti-ruido")
    if comentarios not in PERFILES_COMENTARIOS:
        raise ValueError(
            f"{ruta.name}: 'comentarios' invalido ({comentarios!r}); usa {', '.join(PERFILES_COMENTARIOS)}"
        )
    datos.setdefault("version", 1)
    datos.setdefault("usar_defaults_stack", True)
    datos.setdefault("reglas", [])
    datos.setdefault("fronteras", [])
    datos.setdefault("comandos", [])
    datos.setdefault("reglas_desactivadas", {})
    return datos


def guardar_config(p: dict, cfg: dict[str, Any]) -> Path:
    destino = ruta_config(p)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(f".{destino.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, destino)
    return destino


def _match_glob(ruta: str, patrones: list[str] | None) -> bool:
    if not patrones:
        return True
    norm = ruta.replace("\\", "/")
    for pat in patrones:
        p = pat.replace("\\", "/")
        if fnmatch.fnmatch(norm, p):
            return True
        if p.startswith("**/") and fnmatch.fnmatch(norm, p[3:]):
            return True
    return False


def _exencion_valida(linea: str, rule_id: str) -> bool:
    m = _INLINE_EXEMPT_RE.search(linea)
    if not m:
        return False
    rid, motivo = m.group(1).strip().lower(), m.group(2).strip()
    return rid == rule_id.lower() and len(motivo) >= 10


def _reglas_activas(cfg: dict[str, Any], stack_id: str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Combina defaults seguros + reglas/fronteras del proyecto, filtrando desactivadas y stack."""
    desact = {str(k).lower() for k in (cfg.get("reglas_desactivadas") or {}).keys()}
    reglas_raw: list[dict[str, Any]] = []
    if cfg.get("usar_defaults_stack", True):
        reglas_raw.extend(dict(r) for r in REGLAS_DEFAULT)
    reglas_raw.extend(dict(r) for r in (cfg.get("reglas") or []) if isinstance(r, dict))

    # Si el proyecto redeclara una regla con el mismo id, la suya gana.
    por_id: dict[str, dict[str, Any]] = {}
    for r in reglas_raw:
        rid = str(r.get("id") or "").strip()
        if not rid or rid.lower() in desact:
            continue
        stacks_req = r.get("stacks")
        if stacks_req and stack_id not in stacks_req:
            continue
        por_id[rid] = r

    fronteras_raw: list[dict[str, Any]] = []
    if cfg.get("usar_defaults_stack", True):
        fronteras_raw.extend(dict(f) for f in FRONTERAS_DEFAULT)
    fronteras_raw.extend(dict(f) for f in (cfg.get("fronteras") or []) if isinstance(f, dict))
    fronteras_id: dict[str, dict[str, Any]] = {}
    for fr in fronteras_raw:
        fid = str(fr.get("id") or "").strip()
        if not fid or fid.lower() in desact:
            continue
        stacks_req = fr.get("stacks")
        if stacks_req and stack_id not in stacks_req:
            continue
        fronteras_id[fid] = fr

    return list(por_id.values()), list(fronteras_id.values())


def _capturar_modulo(ruta: str, patron_origen: str) -> str | None:
    """Extrae `<modulo>` desde un patron tipo `**/features/<modulo>/**`."""
    norm = ruta.replace("\\", "/")
    pat = patron_origen.replace("\\", "/")
    if "<modulo>" not in pat:
        return "" if _match_glob(norm, [pat]) else None
    partes = pat.split("<modulo>", 1)
    def _glob_to_re(s: str) -> str:
        s = re.escape(s).replace(r"\*\*/", "(?:.*/)?").replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
        return s
    rx = "^" + _glob_to_re(partes[0]) + r"(?P<modulo>[^/]+)" + _glob_to_re(partes[1]) + "$"
    m = re.match(rx, norm)
    return m.group("modulo") if m else None


def _es_comentario_standalone(archivo: str, linea: str) -> tuple[bool, str]:
    ext = Path(archivo).suffix.lower()
    if ext not in EXT_CODIGO:
        return False, ""
    s = linea.lstrip()
    if not s:
        return False, ""
    if _DIRECTIVA_TECNICA_RE.match(s):
        return False, ""
    if ext in EXT_CODIGO_SLASH and (s.startswith("//") or (s.startswith("/*") and not s.startswith("/**"))):
        return True, s
    if ext in EXT_CODIGO_HASH and s.startswith("#"):
        return True, s
    return False, ""


def escanear_diff_guardrails(
    diff_text: str,
    cfg: dict[str, Any],
    *,
    stack_id: str | None = None,
    prefijo_repo: str = "",
) -> dict[str, list[dict[str, Any]]]:
    """Audita lineas agregadas de un unified diff contra reglas, comentarios y fronteras.

    Devuelve `{"bloqueos": [...], "avisos": [...]}`.
    """
    bloqueos: list[dict[str, Any]] = []
    avisos: list[dict[str, Any]] = []
    reglas, fronteras = _reglas_activas(cfg, stack_id)
    modo_com = cfg.get("comentarios", "anti-ruido")
    desact = {str(k).lower() for k in (cfg.get("reglas_desactivadas") or {}).keys()}

    reglas_comp: list[tuple[dict[str, Any], re.Pattern]] = []
    for r in reglas:
        try:
            reglas_comp.append((r, re.compile(str(r["patron"]))))
        except (KeyError, re.error) as exc:
            raise ValueError(f"guardrail '{r.get('id', '?')}' tiene regex invalido: {exc}")

    archivo_actual: str | None = None
    linea_actual = 0

    for raw in (diff_text or "").splitlines():
        if raw.startswith("+++ b/"):
            archivo_actual = raw[6:].strip()
            linea_actual = 0
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
            etiqueta = f"{prefijo_repo}/{archivo_actual}" if prefijo_repo else archivo_actual
            es_no_prod = bool(_NON_PROD_FILE_RE.search(archivo_actual))

            # 1. Reglas de patron
            for r, pat in reglas_comp:
                if r.get("excluir_no_prod", True) and es_no_prod:
                    continue
                if not _match_glob(archivo_actual, r.get("globs")):
                    continue
                if r.get("excluir") and _match_glob(archivo_actual, r.get("excluir")):
                    continue
                if not pat.search(linea):
                    continue
                if _exencion_valida(linea, r["id"]):
                    continue
                hit = {
                    "id": r["id"],
                    "file": etiqueta,
                    "line": num,
                    "severidad": r.get("severidad", "block"),
                    "mensaje": r.get("mensaje") or r.get("descripcion") or r["id"],
                }
                (bloqueos if hit["severidad"] == "block" else avisos).append(hit)

            # 2. Politica de comentarios (solo codigo fuente de produccion)
            if modo_com != "off" and not es_no_prod:
                es_com, limpio = _es_comentario_standalone(archivo_actual, linea)
                if es_com:
                    rid_com = "comentarios-sin-comentarios" if modo_com == "sin-comentarios" else "comentarios-anti-ruido"
                    if rid_com not in desact and not _exencion_valida(linea, rid_com):
                        if modo_com == "sin-comentarios":
                            bloqueos.append({
                                "id": rid_com,
                                "file": etiqueta,
                                "line": num,
                                "severidad": "block",
                                "mensaje": (
                                    "perfil 'sin-comentarios' activo: elimina comentarios en codigo de produccion "
                                    "(o usa exencion auditada `harness-ignore-guardrail: comentarios-sin-comentarios <motivo>`)"
                                ),
                            })
                        elif _COMENTARIO_RUIDO_IA_RE.match(limpio):
                            bloqueos.append({
                                "id": rid_com,
                                "file": etiqueta,
                                "line": num,
                                "severidad": "block",
                                "mensaje": (
                                    "comentario narrativo/ruido de IA detectado; elimina comentarios de diario "
                                    "y conserva solo invariantes o contratos reales"
                                ),
                            })

            # 3. Fronteras entre modulos / features
            if not es_no_prod:
                for fr in fronteras:
                    mod = _capturar_modulo(archivo_actual, str(fr.get("origen") or ""))
                    if mod is None:
                        continue
                    pat_txt = str(fr.get("import_prohibido") or "").replace("<modulo>", re.escape(mod))
                    if not pat_txt:
                        continue
                    try:
                        pat_fr = re.compile(pat_txt)
                    except re.error as exc:
                        raise ValueError(f"frontera '{fr.get('id', '?')}' tiene regex invalido: {exc}")
                    if pat_fr.search(linea) and not _exencion_valida(linea, fr["id"]):
                        hit = {
                            "id": fr["id"],
                            "file": etiqueta,
                            "line": num,
                            "severidad": fr.get("severidad", "block"),
                            "mensaje": fr.get("mensaje") or fr.get("descripcion") or fr["id"],
                        }
                        (bloqueos if hit["severidad"] == "block" else avisos).append(hit)
        elif not raw.startswith("-"):
            linea_actual += 1

    return {"bloqueos": bloqueos, "avisos": avisos}


def _ejecutar_comandos_guardrail(cfg: dict[str, Any], cwd: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Ejecuta los comandos deterministas declarados en harness/guardrails.json."""
    bloqueos: list[dict[str, Any]] = []
    avisos: list[dict[str, Any]] = []
    errores_medicion: list[str] = []
    for c in cfg.get("comandos") or []:
        if not isinstance(c, dict) or not c.get("comando"):
            continue
        cid = str(c.get("id") or "cmd-guardrail")
        sev = str(c.get("severidad") or "block")
        timeout = int(c.get("timeout") or 120)
        cmd = str(c["comando"])
        try:
            r = subprocess.run(cmd, shell=True, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
            code = r.returncode
            salida = (r.stdout + r.stderr).strip()[-600:]
        except subprocess.TimeoutExpired:
            errores_medicion.append(f"comando guardrail '{cid}' expiro tras {timeout}s (`{cmd}`)")
            continue
        except OSError as exc:
            errores_medicion.append(f"comando guardrail '{cid}' no se pudo ejecutar ({exc})")
            continue
        if code == 0:
            continue
        if code == 127:
            errores_medicion.append(f"comando guardrail '{cid}' no encontrado (exit 127): `{cmd}`")
            continue
        hit = {
            "id": cid,
            "file": str(cwd.name),
            "line": 0,
            "severidad": sev,
            "mensaje": f"comando `{cmd}` fallo (exit {code})" + (f": {salida.splitlines()[-1][:140]}" if salida else ""),
        }
        (bloqueos if sev == "block" else avisos).append(hit)
    return bloqueos, avisos, errores_medicion


def _detectar_stack_seguro(ruta: Path) -> str | None:
    try:
        import stack
        det = stack.detectar_stack_directorio(ruta)
        return None if det.get("stack") == "generico" else det.get("stack")
    except Exception:
        return None


def _diff_repo_pendiente(repo: Path) -> str:
    """Diff de cambios no commiteados + staged, o contra HEAD~1 si el arbol esta limpio."""
    try:
        r = subprocess.run(
            ["git", "diff", "--no-ext-diff", "--no-textconv", "-U0", "HEAD", "--"],
            cwd=str(repo), capture_output=True, text=True, timeout=60,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
        r2 = subprocess.run(
            ["git", "diff", "--no-ext-diff", "--no-textconv", "-U0", "HEAD~1", "HEAD", "--"],
            cwd=str(repo), capture_output=True, text=True, timeout=60,
        )
        return r2.stdout if r2.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def auditar_feature(p: dict, data: dict, f: dict) -> dict[str, Any]:
    """Audita el diff real de la feature (monorepo o multi-repo) + comandos guardrail."""
    cfg = cargar_config(p)
    bloqueos: list[dict[str, Any]] = []
    avisos: list[dict[str, Any]] = []
    errores_medicion: list[str] = []

    if "multi_repo" in f:
        try:
            from multirepo import check_registered
            manifest = check_registered(p, f, data.get("rules") or {})
        except Exception:
            return {"bloqueos": [], "avisos": [], "errores_medicion": [], "perfil": cfg.get("comentarios", "anti-ruido")}
        for row in manifest.get("repos") or []:
            ruta = Path(row["repo"])
            wt = Path(row["worktree"]) if row.get("worktree") and Path(row["worktree"]).is_dir() else ruta
            nombre = row.get("microservicio") or ruta.name
            diff = seguridad._git_diff_repo(ruta, row["base_sha"], row["source_sha"])
            if diff:
                sid = _detectar_stack_seguro(wt)
                res = escanear_diff_guardrails(diff, cfg, stack_id=sid, prefijo_repo=nombre)
                bloqueos.extend(res["bloqueos"])
                avisos.extend(res["avisos"])
            cb, ca, ce = _ejecutar_comandos_guardrail(cfg, wt)
            bloqueos.extend(cb); avisos.extend(ca); errores_medicion.extend(ce)
        return {
            "bloqueos": bloqueos,
            "avisos": avisos,
            "errores_medicion": errores_medicion,
            "perfil": cfg.get("comentarios", "anti-ruido"),
        }

    wt = f.get("worktree")
    arbol = Path(wt) if wt and Path(wt).is_dir() else Path(p["root"])
    base = (
        f.get("base_sha")
        or f.get("base_branch")
        or (data.get("rules") or {}).get("rama_base")
        or "develop"
    )
    diff = seguridad._git_diff_repo(arbol, base, "HEAD")
    if diff:
        sid = _detectar_stack_seguro(arbol)
        res = escanear_diff_guardrails(diff, cfg, stack_id=sid)
        bloqueos.extend(res["bloqueos"])
        avisos.extend(res["avisos"])
    cb, ca, ce = _ejecutar_comandos_guardrail(cfg, arbol)
    bloqueos.extend(cb); avisos.extend(ca); errores_medicion.extend(ce)
    return {
        "bloqueos": bloqueos,
        "avisos": avisos,
        "errores_medicion": errores_medicion,
        "perfil": cfg.get("comentarios", "anti-ruido"),
    }


def lineas_brief(p: dict, data: dict, f: dict) -> list[str]:
    """Resumen de guardrails activos para `contexto.py brief` (antes de escribir codigo)."""
    try:
        cfg = cargar_config(p)
    except ValueError as exc:
        return ["", f"GUARDRAILS DETERMINISTAS: [!!] {exc}"]
    wt = f.get("worktree")
    arbol = Path(wt) if wt and Path(wt).is_dir() else Path(p["root"])
    sid = _detectar_stack_seguro(arbol)
    reglas, fronteras = _reglas_activas(cfg, sid)
    bloqueantes = [r for r in reglas if r.get("severidad", "block") == "block"]
    L = [
        "",
        f"GUARDRAILS DETERMINISTAS (bloquean gate.py verify y gate.py close · comentarios: {cfg.get('comentarios', 'anti-ruido')}):",
        f"  reglas bloqueantes activas ({len(bloqueantes)}): "
        + (", ".join(r["id"] for r in bloqueantes[:10]) or "ninguna"),
    ]
    if fronteras:
        L.append("  fronteras de modulos: " + ", ".join(fr["id"] for fr in fronteras))
    if cfg.get("comandos"):
        L.append("  comandos guardrail: " + ", ".join(f"{c.get('id')}(`{c.get('comando')}`)" for c in cfg["comandos"]))
    L.append("  comprueba antes de commitear: guardrails.py check --feature " + str(f["id"]))
    return L


def resumen_estado(p: dict) -> str:
    try:
        cfg = cargar_config(p)
    except ValueError as exc:
        return f"[!!] {exc}"
    existe = ruta_config(p).is_file()
    n_reglas = len(cfg.get("reglas") or [])
    n_cmds = len(cfg.get("comandos") or [])
    com = cfg.get("comentarios", "anti-ruido")
    if not existe:
        return f"defaults seguros activos (comentarios={com}; personaliza con guardrails.py init)"
    return (
        f"perfil {cfg.get('perfil', 'custom')} · comentarios={com} · "
        f"{n_reglas} regla(s) proyecto + defaults · {n_cmds} comando(s)"
    )


def resumen_hook(p: dict) -> str | None:
    """En cuantos repos del proyecto esta el hook pre-push; None si no se pudo evaluar."""
    try:
        repos = repos_del_proyecto(p)
    except Exception:
        return None
    return f"hook pre-push en {sum(1 for r in repos if hook_propio(r))}/{len(repos)} repo(s)" if repos else None


# --- CLI -------------------------------------------------------------------

def cmd_init(args) -> None:
    p = paths()
    ruta = ruta_config(p)
    if ruta.exists() and not args.forzar:
        print(f"[i]  {ruta} ya existe; no se sobreescribe (usa --forzar para reemplazar)")
        return
    cfg = config_default(args.perfil)
    guardar_config(p, cfg)
    bitacora(p, f"guardrails inicializados (perfil={args.perfil}, comentarios={cfg['comentarios']})")
    print(f"[ok] guardrails inicializados ({args.perfil}) -> {ruta}")


def _agregar_regla(
    p: dict,
    *,
    rid: str,
    patron: str,
    mensaje: str,
    globs: list[str],
    excluir: list[str],
    severidad: str,
    stacks: list[str],
    origen_skill: str | None = None,
) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,63}", rid):
        sys.exit(f"[!!] --id invalido '{rid}': usa minusculas, digitos y guiones (2-64 chars)")
    try:
        re.compile(patron)
    except re.error as exc:
        sys.exit(f"[!!] --patron regex invalido: {exc}")
    if not mensaje.strip():
        sys.exit("[!!] --mensaje no puede estar vacio")

    cfg = cargar_config(p)
    nueva: dict[str, Any] = {
        "id": rid,
        "descripcion": mensaje.strip(),
        "severidad": severidad,
        "patron": patron,
        "mensaje": mensaje.strip(),
        "excluir_no_prod": True,
        "added_at": now_iso(),
    }
    if globs:
        nueva["globs"] = globs
    if excluir:
        nueva["excluir"] = excluir
    if stacks:
        nueva["stacks"] = stacks
    if origen_skill:
        nueva["origen_skill"] = origen_skill

    reglas = [r for r in (cfg.get("reglas") or []) if r.get("id") != rid]
    reglas.append(nueva)
    cfg["reglas"] = reglas
    (cfg.get("reglas_desactivadas") or {}).pop(rid, None)
    guardar_config(p, cfg)
    return nueva


def _exigir_si(args, accion: str) -> str:
    """Un guardrail prohibe algo en todo el proyecto: lo propone el agente y lo decide el usuario."""
    quien = (getattr(args, "por", None) or "").strip()
    if args.yes and quien:
        return quien
    try:
        re.compile(args.patron)
    except re.error as exc:
        sys.exit(f"[!!] --patron regex invalido: {exc}")
    print(f"guardrail propuesto: {args.id}")
    print(f"  patron:    {args.patron}")
    print(f"  en:        {', '.join(args.glob) or 'todos los archivos de codigo'}"
          + (f" (salvo {', '.join(args.excluir)})" if args.excluir else ""))
    print(f"  mensaje:   {args.mensaje}")
    print(f"  severidad: {getattr(args, 'severidad', 'block')}")
    sys.exit(f"[!!] {accion} un guardrail lo decide el USUARIO: prohibe algo en todo el proyecto.\n"
             "     PREGUNTALE con un formulario (que prohibe, donde y que error lo motivo) y, con su SI,\n"
             "     repite el comando con --yes --por <su nombre>.")


def cmd_agregar(args) -> None:
    quien = _exigir_si(args, "agregar")
    p = paths()
    _agregar_regla(
        p,
        rid=args.id,
        patron=args.patron,
        mensaje=args.mensaje,
        globs=args.glob or [],
        excluir=args.excluir or [],
        severidad=args.severidad,
        stacks=args.stack or [],
    )
    bitacora(p, f"guardrail agregado con el si de {quien}: {args.id} ({args.severidad})")
    print(f"[ok] guardrail '{args.id}' ({args.severidad}) guardado en {ruta_config(p)}")


def cmd_promover(args) -> None:
    """Promueve una regla que vivia en una skill/leccion a un guardrail determinista duro."""
    import leccion
    p = paths()
    if not leccion.buscar(args.desde_skill):
        sys.exit(f"[!!] la skill/leccion '{args.desde_skill}' no existe (revisa con leccion.py list)")
    quien = _exigir_si(args, "promover a")
    _agregar_regla(
        p,
        rid=args.id,
        patron=args.patron,
        mensaje=args.mensaje,
        globs=args.glob or [],
        excluir=args.excluir or [],
        severidad="block",
        stacks=args.stack or [],
        origen_skill=args.desde_skill,
    )
    bitacora(p, f"guardrail promovido desde skill '{args.desde_skill}' con el si de {quien}: {args.id} (block)")
    print(f"[ok] regla de skill '{args.desde_skill}' promovida a guardrail BLOQUEANTE '{args.id}' -> {ruta_config(p)}")


def cmd_desactivar(args) -> None:
    if not args.yes:
        sys.exit(
            "[!!] desactivar un guardrail requiere --yes: quitar una barrera determinista es "
            "decision explicita del USUARIO."
        )
    if not (args.motivo or "").strip() or len(args.motivo.strip()) < 10:
        sys.exit("[!!] --motivo debe explicar por que se desactiva (al menos 10 caracteres)")
    p = paths()
    cfg = cargar_config(p)
    cfg.setdefault("reglas_desactivadas", {})[args.id] = args.motivo.strip()
    guardar_config(p, cfg)
    bitacora(p, f"guardrail desactivado con --yes: {args.id} ({args.motivo.strip()})")
    print(f"[ok] guardrail '{args.id}' desactivado en {ruta_config(p)}")


def cmd_list(args) -> None:
    p = paths()
    try:
        cfg = cargar_config(p)
    except ValueError as exc:
        sys.exit(f"[!!] {exc}")
    repo = Path(args.repo).resolve() if args.repo else p["root"]
    sid = _detectar_stack_seguro(repo)
    reglas, fronteras = _reglas_activas(cfg, sid)
    print(f"== Guardrails activos (stack={sid or 'generico'} · comentarios={cfg.get('comentarios', 'anti-ruido')}) ==")
    for r in reglas:
        orig = f" [desde skill: {r['origen_skill']}]" if r.get("origen_skill") else ""
        print(f"   - [{r.get('severidad', 'block').upper():<5}] {r['id']}{orig}: {r.get('mensaje', r.get('descripcion', ''))}")
    for fr in fronteras:
        print(f"   - [FRONTERA/{fr.get('severidad', 'block').upper()}] {fr['id']}: {fr.get('origen')} -> {fr.get('mensaje', '')}")
    for c in cfg.get("comandos") or []:
        print(f"   - [CMD/{c.get('severidad', 'block').upper()}] {c.get('id')}: `{c.get('comando')}`")
    if cfg.get("reglas_desactivadas"):
        print("   Desactivadas:")
        for rid, mot in cfg["reglas_desactivadas"].items():
            print(f"     - {rid}: {mot}")


def cmd_check(args) -> None:
    p = paths()
    data = load_backlog(p)
    try:
        if args.feature:
            f = get_feature(data, args.feature)
            res = auditar_feature(p, data, f)
        else:
            cfg = cargar_config(p)
            repo = Path(args.repo).resolve() if args.repo else p["root"]
            sid = _detectar_stack_seguro(repo)
            diff = _diff_repo_pendiente(repo)
            scan = escanear_diff_guardrails(diff, cfg, stack_id=sid)
            cb, ca, ce = _ejecutar_comandos_guardrail(cfg, repo)
            res = {
                "bloqueos": scan["bloqueos"] + cb,
                "avisos": scan["avisos"] + ca,
                "errores_medicion": ce,
                "perfil": cfg.get("comentarios", "anti-ruido"),
            }
    except ValueError as exc:
        sys.exit(f"[!!] guardrails: {exc}")

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for av in res["avisos"]:
            loc = f"{av['file']}:{av['line']}" if av["line"] else av["file"]
            print(f"[!]  [{av['id']}] {loc} — {av['mensaje']}")
        for bl in res["bloqueos"]:
            loc = f"{bl['file']}:{bl['line']}" if bl["line"] else bl["file"]
            print(f"[!!] BLOQUEADO [{bl['id']}] {loc} — {bl['mensaje']}")
        for em in res["errores_medicion"]:
            print(f"[!!] NO SE PUDO MEDIR: {em}")

    if res["errores_medicion"]:
        sys.exit(2)
    if res["bloqueos"]:
        sys.exit(1)
    if not args.json:
        print(f"[ok] guardrails limpios (comentarios={res['perfil']}, {len(res['avisos'])} aviso(s))")

# --- hook pre-push ---------------------------------------------------------
#
# verify y close miden la feature. El hook mide lo que se sube: bloquea la subida
# de lineas que infringen un guardrail aunque nadie haya corrido un gate. Lo
# instala el usuario (configuracion persistente en su repo) y no se versiona.

MARCA_HOOK = "harness-flow:guardrails"
_CEROS = "0" * 40


def repos_del_proyecto(p: dict) -> list[Path]:
    """Repos git del proyecto: la raiz del arnes y los destinos con stack."""
    import stack
    candidatos = [p["root"], *[Path(d["path"]) for d in stack.detectar_todos_los_destinos(p["root"])]]
    repos: list[Path] = []
    for c in candidatos:
        code, out = git(["rev-parse", "--show-toplevel"], c) if Path(c).is_dir() else (1, "")
        top = Path(out.strip()).resolve() if code == 0 and out.strip() else None
        if top and top not in repos:
            repos.append(top)
    return repos


def _ruta_hook(repo: Path) -> Path | None:
    code, out = git(["rev-parse", "--git-path", "hooks/pre-push"], repo)
    if code != 0 or not out.strip():
        return None
    r = Path(out.strip())
    return r if r.is_absolute() else repo / r


def hook_propio(repo: Path) -> bool:
    h = _ruta_hook(repo)
    try:
        return bool(h) and h.is_file() and MARCA_HOOK in h.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def _texto_hook(p: dict) -> str:
    orden = " ".join(shlex.quote(Path(x).as_posix()) for x in (sys.executable, Path(__file__).resolve()))
    return ("#!/bin/sh\n"
            f"# {MARCA_HOOK}: instalado por guardrails.py instalar-hook. Lo quita: guardrails.py quitar-hook\n"
            "# Bloquea la subida si las lineas nuevas infringen un guardrail del proyecto.\n"
            f"exec {orden} hook-pre-push --raiz {shlex.quote(p['root'].as_posix())} "
            f"--desde {now_iso()} \"$@\"\n")


def _base_de_subida(repo: Path, local: str, remoto_sha: str, remoto: str, rama_base: str) -> str | None:
    if remoto_sha != _CEROS:
        return remoto_sha
    for ref in (f"{remoto}/{rama_base}", rama_base):   # rama nueva: lo que no venia de la rama base
        code, out = git(["merge-base", local, ref], repo)
        if code == 0 and out.strip():
            return out.strip()
    return None


def _epoch(iso: str | None) -> float | None:
    try:
        return datetime.strptime(str(iso), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def _linea_anterior_a_la_regla(repo: Path, sha: str, bloqueo: dict, cfg: dict, desde: str | None) -> bool:
    """True si la linea se commiteo ANTES de que la regla rigiera: es heredada y no bloquea la subida.

    Una subida puede llevar trabajo viejo (promover la rama de integracion). Una regla
    del proyecto rige desde su `added_at`; un default del stack o la politica de
    comentarios, desde que se instalo el hook. Si no se puede saber cuando se escribio
    la linea, bloquea.
    """
    propia = next((r for r in cfg.get("reglas") or [] if r.get("id") == bloqueo.get("id")), None)
    limite = _epoch((propia or {}).get("added_at")) or _epoch(desde)
    if limite is None or not bloqueo.get("line"):
        return False
    code, out = git(["blame", "--porcelain", "-L", f"{bloqueo['line']},{bloqueo['line']}", sha, "--",
                     bloqueo["file"]], repo)
    m = re.search(r"^committer-time (\d+)$", out, flags=re.M) if code == 0 else None
    return bool(m) and int(m.group(1)) < limite


def cmd_instalar_hook(args) -> None:
    p = paths()
    repos = [Path(args.repo).resolve()] if args.repo else repos_del_proyecto(p)
    if not args.yes:
        print("El hook pre-push bloquea la subida si las lineas nuevas infringen un guardrail. Se instalaria en:")
        for repo in repos:
            print(f"  - {repo}")
        sys.exit("[!!] es configuracion persistente en los repos: lo decide el USUARIO. Con su SI: --yes")
    hechos = 0
    for repo in repos:
        code, out = git(["config", "--get", "core.hooksPath"], repo)
        destino = _ruta_hook(repo)
        orden = _texto_hook(p).splitlines()[-1]
        if destino is None:
            print(f"[!] {repo}: no es un repo git; no se instala")
        elif code == 0 and out.strip():
            print(f"[!] {repo}: usa core.hooksPath ({out.strip()}); no se toca. Agrega tu esta linea a "
                  f"su pre-push:\n      {orden}")
        elif destino.exists() and not hook_propio(repo):
            print(f"[!] {repo}: ya tiene un pre-push propio; no se reemplaza. Agrega tu esta linea:\n"
                  f"      {orden}")
        else:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(_texto_hook(p), encoding="utf-8")
            destino.chmod(0o755)
            hechos += 1
            print(f"[ok] {repo}: hook pre-push instalado")
    print(f"[i]  {hechos}/{len(repos)} repo(s) con el hook. No se versiona: cada clon lo instala.")


def cmd_quitar_hook(args) -> None:
    p = paths()
    for repo in [Path(args.repo).resolve()] if args.repo else repos_del_proyecto(p):
        if hook_propio(repo):
            _ruta_hook(repo).unlink()
            print(f"[ok] {repo}: hook pre-push quitado")
        else:
            print(f"[i]  {repo}: sin hook de guardrails")


def cmd_hook_pre_push(args) -> None:
    """Lo llama git: remoto y url por argumento, y por stdin `<ref local> <sha> <ref remoto> <sha>`."""
    raiz = Path(args.raiz)
    if not (raiz / "harness" / "feature_list.json").is_file():
        sys.exit(f"[!!] guardrails: no se encuentra el arnes en {raiz}. Un chequeo que no se puede "
                 "medir no pasa: reinstala (guardrails.py instalar-hook) o quita el hook (quitar-hook).")
    p = paths(raiz)
    try:
        cfg = cargar_config(p)
    except ValueError as exc:
        sys.exit(f"[!!] guardrails: {exc}")
    repo = Path.cwd()
    remoto = args.resto[0] if args.resto else "origin"
    rama_base = (load_backlog(p).get("rules") or {}).get("rama_base") or "develop"
    sid = _detectar_stack_seguro(repo)
    fallos: list[str] = []
    for renglon in sys.stdin.read().splitlines():
        partes = renglon.split()
        if len(partes) != 4 or partes[1] == _CEROS:      # borrar una rama no sube lineas
            continue
        base = _base_de_subida(repo, partes[1], partes[3], remoto, rama_base)
        if base is None:
            fallos.append(f"{partes[0]}: no se pudo medir contra que se sube (sin base comun con "
                          f"{rama_base}); un guardrail sin medir no pasa")
            continue
        r = subprocess.run(["git", "diff", "--no-ext-diff", "--no-textconv", "-U0", base, partes[1], "--"],
                           cwd=str(repo), capture_output=True, text=True)
        if r.returncode != 0:
            fallos.append(f"{partes[0]}: git diff fallo; un guardrail sin medir no pasa")
            continue
        try:
            res = escanear_diff_guardrails(r.stdout, cfg, stack_id=sid)
        except ValueError as exc:
            sys.exit(f"[!!] guardrails: {exc}")
        for bl in res["bloqueos"]:
            if _linea_anterior_a_la_regla(repo, partes[1], bl, cfg, args.desde):
                continue
            loc = f"{bl['file']}:{bl['line']}" if bl["line"] else bl["file"]
            fallos.append(f"[{bl['id']}] {loc}: {bl['mensaje']}")
    if fallos:
        print(f"[!!] subida BLOQUEADA por {len(fallos)} infraccion(es) de guardrails del proyecto:",
              file=sys.stderr)
        for x in fallos:
            print(f"     - {x}", file=sys.stderr)
        print("     Corrige las lineas y vuelve a subir. Los guardrails: guardrails.py list", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Guardrails deterministas de harness-flow")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="crea harness/guardrails.json")
    s.add_argument("--perfil", choices=["estandar", "spacex"], default="estandar")
    s.add_argument("--forzar", action="store_true")
    s.set_defaults(fn=cmd_init)

    s = sub.add_parser("check", help="audita diff y comandos contra los guardrails (exit 1 bloqueo, 2 error medicion)")
    s.add_argument("--feature")
    s.add_argument("--repo")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_check)

    s = sub.add_parser("agregar", help="agrega una regla determinista a harness/guardrails.json")
    s.add_argument("--id", required=True)
    s.add_argument("--patron", required=True)
    s.add_argument("--mensaje", required=True)
    s.add_argument("--glob", action="append", default=[])
    s.add_argument("--excluir", action="append", default=[])
    s.add_argument("--severidad", choices=["block", "warn"], default="block")
    s.add_argument("--stack", action="append", default=[])
    s.add_argument("--yes", action="store_true", help="el SI del usuario; sin el solo se muestra la propuesta")
    s.add_argument("--por", help="nombre del usuario que aprobo")
    s.set_defaults(fn=cmd_agregar)

    s = sub.add_parser("promover", help="promueve una regla de una skill/leccion a guardrail bloqueante")
    s.add_argument("--desde-skill", required=True, dest="desde_skill")
    s.add_argument("--id", required=True)
    s.add_argument("--patron", required=True)
    s.add_argument("--mensaje", required=True)
    s.add_argument("--glob", action="append", default=[])
    s.add_argument("--excluir", action="append", default=[])
    s.add_argument("--stack", action="append", default=[])
    s.add_argument("--yes", action="store_true", help="el SI del usuario; sin el solo se muestra la propuesta")
    s.add_argument("--por", help="nombre del usuario que aprobo")
    s.set_defaults(fn=cmd_promover)

    s = sub.add_parser("desactivar", help="desactiva una regla default (requiere --yes del usuario)")
    s.add_argument("--id", required=True)
    s.add_argument("--motivo", required=True)
    s.add_argument("--yes", action="store_true")
    s.set_defaults(fn=cmd_desactivar)

    s = sub.add_parser("list", help="lista los guardrails activos")
    s.add_argument("--repo")
    s.set_defaults(fn=cmd_list)

    s = sub.add_parser("instalar-hook", help="hook pre-push en los repos del proyecto (decision del usuario)")
    s.add_argument("--repo")
    s.add_argument("--yes", action="store_true")
    s.set_defaults(fn=cmd_instalar_hook)

    s = sub.add_parser("quitar-hook", help="quita el hook pre-push de guardrails")
    s.add_argument("--repo")
    s.set_defaults(fn=cmd_quitar_hook)

    s = sub.add_parser("hook-pre-push", help="lo llama git desde el hook instalado")
    s.add_argument("--raiz", required=True)
    s.add_argument("--desde")
    s.add_argument("resto", nargs="*")
    s.set_defaults(fn=cmd_hook_pre_push)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
