"""Nucleo compartido del harness-flow: rutas, backlog, firmas, AC y sellos."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

# --- rutas -----------------------------------------------------------------

def find_root(start: Path | None = None) -> Path:
    """Sube desde cwd hasta encontrar harness/feature_list.json."""
    cur = (start or Path.cwd()).resolve()
    for d in [cur, *cur.parents]:
        if (d / "harness" / "feature_list.json").exists():
            return d
    raise SystemExit(
        "No se encontro harness/feature_list.json desde " + str(cur) +
        "\nEstas fuera de un proyecto con harness-flow, o falta inicializarlo:\n"
        "  python <skill>/scripts/init.py --project <NOMBRE>"
    )

def paths(root: Path | None = None) -> dict:
    r = root or find_root()
    p = {
        "root": r,
        "harness": r / "harness",
        "backlog": r / "harness" / "feature_list.json",
        "progress": r / "harness" / "progress",
        "docs": r / "docs",
        "vault": r / "docs" / "vault",
        "grafos": r / "harness" / "grafos.json",
        "atlassian": r / "harness" / "atlassian.json",
    }
    # "graph" es el grafo que TODO el arnes consulta. Con varias raices
    # declaradas es el combinado; con una sola, el de esa raiz. Nunca se
    # inventa: si no hay combinado se cae al de la raiz del arnes.
    p["graph"] = graph_path(p)
    return p

# --- grafos (una o varias raices) ------------------------------------------

def grafos_config(p: dict) -> dict:
    """harness/grafos.json: raices declaradas. Ausente = solo la raiz del arnes.

    Formato:
      {"max_horas": 12,
       "raices": [{"nombre": "front", "path": "."},
                  {"nombre": "micros", "path": "~/GolandProjects/realestate"}],
       "combinado": "graphify-out/merged-graph.json"}
    Se DECLARA a proposito: autodetectar graphify-out por el disco mete repos
    ajenos al proyecto en el grafo y en el hub sin que nadie lo pida.
    """
    f = p.get("grafos") or (p["root"] / "harness" / "grafos.json")
    if not Path(f).exists():
        return {}
    try:
        d = json.loads(Path(f).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"[!!] harness/grafos.json ilegible: {exc}")
    if not isinstance(d, dict):
        raise SystemExit("[!!] harness/grafos.json debe ser un objeto JSON")
    return d

def raices_grafo(p: dict) -> list[dict]:
    cfg = grafos_config(p)
    raices = cfg.get("raices") or []
    if not raices:
        return [{"nombre": p["root"].name, "path": p["root"], "declarada": False}]
    out = []
    for r in raices:
        if not isinstance(r, dict) or not r.get("path"):
            raise SystemExit("[!!] cada raiz de grafos.json necesita 'path'")
        ruta = Path(str(r["path"])).expanduser()
        if not ruta.is_absolute():
            ruta = (p["root"] / ruta).resolve()
        if not ruta.exists():
            raise SystemExit(f"[!!] raiz de grafo inexistente: {ruta}\n"
                             "     corrige harness/grafos.json; no la ignoro en silencio.")
        out.append({"nombre": r.get("nombre") or ruta.name, "path": ruta,
                    "declarada": True})
    return out

def graph_path(p: dict) -> Path:
    cfg = grafos_config(p)
    if len(cfg.get("raices") or []) > 1:
        rel = cfg.get("combinado") or "graphify-out/merged-graph.json"
        q = Path(str(rel)).expanduser()
        return q if q.is_absolute() else p["root"] / q
    raices = raices_grafo(p)
    return raices[0]["path"] / "graphify-out" / "graph.json"

def hub_env() -> dict:
    """Credenciales del hub: entorno gana sobre ~/.harness-hub/.env."""
    hub = Path(os.environ.get("HARNESS_HUB", Path.home() / ".harness-hub"))
    vals: dict[str, str] = {}
    f = hub / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip().strip("'\"")
    for k in ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME", "DB_PORT", "DB_SSL_MODE"):
        if os.environ.get(k):
            vals[k] = os.environ[k]
    vals.setdefault("DB_NAME", "postgres")
    vals.setdefault("DB_PORT", "5432")
    vals.setdefault("DB_SSL_MODE", "require")
    return vals

# --- backlog ---------------------------------------------------------------

DEFAULT_RULES = {
    # Rama de la que SALEN las features y contra la que se miden los diffs.
    # Se declara aqui porque "el HEAD del repo" es la rama de quien hizo
    # checkout ultimo: arrancar desde ahi mete trabajo ajeno en la feature.
    "rama_base": "develop",
    "require_spec_approved": True,
    "require_review": True,
    "require_leccion": True,
    "require_verify_green": True,
    "require_docs_al_dia": True,
    "rutas_protegidas": ["docs/prd/**", "docs/constitution.md", ".env"],
}

def load_backlog(p: dict) -> dict:
    d = json.loads(p["backlog"].read_text(encoding="utf-8"))
    d.setdefault("rules", {})
    for k, v in DEFAULT_RULES.items():
        d["rules"].setdefault(k, v)
    d.setdefault("features", [])
    return d

def save_backlog(p: dict, data: dict) -> None:
    p["backlog"].write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def get_feature(data: dict, fid) -> dict:
    for f in data["features"]:
        if str(f.get("id")) == str(fid):
            return f
    raise SystemExit(f"Feature #{fid} no existe en el backlog.")

def slugify(name: str) -> str:
    n = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    n = re.sub(r"[^a-zA-Z0-9]+", "-", n).strip("-").lower()
    return n[:60] or "feature"

def spec_path(p: dict, f: dict) -> Path:
    return p["docs"] / f"spec-feature-{f['id']}-{slugify(f.get('name',''))}.md"

def impl_path(p: dict, f: dict) -> Path:
    return p["docs"] / f"impl-{f['id']}.md"

def review_path(p: dict, f: dict) -> Path:
    return p["docs"] / f"review-{f['id']}.md"

# --- firmas (freshness) ----------------------------------------------------

def sign(path: Path) -> dict:
    b = path.read_bytes()
    return {
        "path": str(path),
        "size": len(b),
        "hash": hashlib.sha256(b).hexdigest()[:16],
        "at": now_iso(),
    }

def sig_fresh(path: Path, sig: dict | None) -> bool:
    """El sello sigue valido solo si el archivo no cambio desde que se firmo."""
    if not sig or not path.exists():
        return False
    b = path.read_bytes()
    return (sig.get("size") == len(b)
            and sig.get("hash") == hashlib.sha256(b).hexdigest()[:16])

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# --- spec: estado y AC -----------------------------------------------------

AC_RE = re.compile(r"^\s*[-*]?\s*(AC-\d+)\s*:", re.MULTILINE)
CITA_RE = re.compile(r"[\w./\\-]+\.\w+:\d+")

def spec_estado(text: str) -> str:
    m = re.search(r"^Estado:\s*(\w+)", text, re.MULTILINE)
    return (m.group(1).lower() if m else "desconocido")

def spec_acs(text: str) -> list[str]:
    """IDs de AC declarados en el spec, en orden y sin duplicados."""
    out: list[str] = []
    for m in AC_RE.finditer(text):
        if m.group(1) not in out:
            out.append(m.group(1))
    return out

def ac_comandos(text: str) -> dict[str, str]:
    """AC-n -> comando declarado bajo el, si lo hay."""
    out: dict[str, str] = {}
    lines = text.splitlines()
    actual = None
    # dos formas validas:
    #   Comando: `pytest -q`            (palabra fuera del backtick)
    #   `verificar: pytest -q`          (palabra dentro del backtick)
    inline_re = re.compile(
        r"(?:(?:Comando|verificar|verify)\s*:\s*`([^`]+)`"
        r"|`\s*(?:Comando|verificar|verify)\s*:\s*([^`]+)`)",
        re.IGNORECASE)

    def extraer(ln: str) -> str | None:
        m = inline_re.search(ln)
        if not m:
            return None
        return (m.group(1) or m.group(2) or "").strip() or None

    for ln in lines:
        m = AC_RE.match(ln)
        if m:
            actual = m.group(1)
            # el comando puede venir en la MISMA linea del AC
            ci = extraer(ln)
            if ci:
                out[actual] = ci
            continue
        c = extraer(ln)
        if c and actual:
            out[actual] = c
            actual = None
    return out

def declara_ac(linea: str, ac: str) -> bool:
    """True si la linea DECLARA la seccion del AC, no si solo lo menciona.

    Una mencion en prosa ('...que tambien cubre lo pedido en AC-1') no puede
    abrir una seccion: heredaba la cita de la seccion vecina y daba por
    cubierto un AC sin evidencia propia, mientras truncaba la seccion del AC
    que si la tenia. Declarar es empezar la linea con el AC, admitiendo el
    adorno de markdown: '## AC-1', '- AC-1:', '* AC-1', '| AC-1 |', '3. AC-1'.
    """
    limpia = linea.strip()
    limpia = re.sub(r"^[>\s]*", "", limpia)           # citas
    limpia = re.sub(r"^#{1,6}\s*", "", limpia)        # encabezados
    limpia = re.sub(r"^\|\s*", "", limpia)            # filas de tabla
    limpia = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", limpia)  # listas
    limpia = re.sub(r"^[*_`]+", "", limpia)           # enfasis
    return bool(re.match(rf"{re.escape(ac)}\b", limpia))


def cubre_acs(text: str, acs: list[str]) -> tuple[list[str], list[str]]:
    """Devuelve (cubiertos, faltantes).

    Un AC esta cubierto si DECLARA una seccion (ver declara_ac) y hay una cita
    archivo:linea en ella: la misma linea, o las que le siguen hasta que
    empieza otro AC o un nuevo encabezado. Asi vale tanto
    '- AC-1: ... (src/a.ts:42)' como un '## AC-1' con la cita debajo.
    """
    lines = text.splitlines()
    # indice de arranque de cada AC DECLARADO (no de cada mencion)
    arranques: list[tuple[int, str]] = []
    for i, ln in enumerate(lines):
        for ac in acs:
            if declara_ac(ln, ac):
                arranques.append((i, ac))
                break
    cubiertos, faltan = [], []
    for ac in acs:
        propios = [i for i, a in arranques if a == ac]
        ok = False
        for ini in propios:
            # la seccion termina en el proximo AC distinto o el proximo heading
            fin = len(lines)
            for j, a in arranques:
                if j > ini and a != ac:
                    fin = min(fin, j)
                    break
            for j in range(ini + 1, len(lines)):
                if j > ini and lines[j].startswith("#"):
                    fin = min(fin, j)
                    break
            if any(CITA_RE.search(l) for l in lines[ini:fin]):
                ok = True
                break
        (cubiertos if ok else faltan).append(ac)
    return cubiertos, faltan

# --- sellos ----------------------------------------------------------------

REVISADO_RE = re.compile(
    r"^Revisado:\s*(approved|changes_requested|blocked)\s*·\s*"
    r"\d{4}-\d{2}-\d{2}T[\d:]+Z\s*·\s*.+?\s*·\s*"
    r"estampado por gate\.py revision\s*$",
    re.MULTILINE)

def sello_revision(text: str) -> str | None:
    """Solo reconoce el sello COMPLETO que estampa gate.py revision.

    Antes bastaba 'Revisado: approved -' para pasar por sellado: cualquiera
    podia tipear el veredicto a mano, que es justo lo que el sello existe para
    impedir. Se exige la firma entera (fecha ISO, autor y la frase del gate).
    """
    m = REVISADO_RE.search(text or "")
    return m.group(1) if m else None

# --- git / bitacora --------------------------------------------------------

def git(args: list[str], cwd: Path) -> tuple[int, str]:
    try:
        r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                           text=True, timeout=60)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:  # git ausente o repo raro: no es fatal
        return 1, str(e)

def bitacora(p: dict, linea: str) -> None:
    p["progress"].mkdir(parents=True, exist_ok=True)
    h = p["progress"] / "history.md"
    prev = h.read_text(encoding="utf-8") if h.exists() else "# Bitacora\n\n"
    h.write_text(prev + f"- {now_iso()} · {linea}\n", encoding="utf-8")

# --- salida ----------------------------------------------------------------

OK, WARN, BAD, INFO = "[ok]", "[!]", "[!!]", "[i]"

class Reporte:
    def __init__(self) -> None:
        self.fallos: list[str] = []
        self.avisos: list[str] = []

    def ok(self, msg: str) -> None:
        print(f"{OK} {msg}")

    def info(self, msg: str) -> None:
        print(f"{INFO} {msg}")

    def aviso(self, msg: str, remedio: str = "") -> None:
        print(f"{WARN} {msg}" + (f"\n     Remedio: {remedio}" if remedio else ""))
        self.avisos.append(msg)

    def fallo(self, msg: str, remedio: str = "") -> None:
        print(f"{BAD} {msg}" + (f"\n     Remedio: {remedio}" if remedio else ""))
        self.fallos.append(msg)

    def salir(self) -> None:
        print()
        if self.fallos:
            print(f"{BAD} {len(self.fallos)} bloqueo(s), {len(self.avisos)} aviso(s).")
            raise SystemExit(1)
        print(f"{OK} check limpio" + (f" ({len(self.avisos)} aviso(s))" if self.avisos else "."))
        raise SystemExit(0)
