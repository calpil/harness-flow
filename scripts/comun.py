"""Nucleo compartido del harness-flow: rutas, backlog, firmas, AC y sellos."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
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

# --- spec: el AC declarado --------------------------------------------------
#
# Una sola gramatica para declarar un AC, la misma que reconoce declara_ac para
# abrir su seccion en la evidencia. Eran dos: "## AC-3: ..." abria seccion pero
# NO declaraba el AC en el spec, asi que ese criterio desaparecia del flujo
# entero -- sellado, review, PRD -- con el check en verde.
#
#   adorno   citas, encabezados, filas de tabla, listas y enfasis
#   titulo   cero o mas grupos (...) o [...], con un nivel de anidamiento
#   [^\S\n]  espacio que NO es salto de linea: todo tiene que caber en UNA
#            linea. Con \s a secas el match arrancaba en la linea anterior (y
#            la devolvia como la linea del AC) y aceptaba un 'AC-5' suelto cuyos
#            dos puntos estaban en la siguiente.
#
# Lo que esta gramatica NO entiende no pasa en silencio: acs_no_reconocidos lo
# denuncia y approve-spec se niega.
_H = r"[^\S\n]*"
_GRUPO = r"\((?:[^()\n]|\([^()\n]*\))*\)|\[[^\[\]\n]*\]"
_TITULO = rf"(?:{_H}(?:{_GRUPO}))*"
_ADORNO = (rf"{_H}(?:>{_H})*(?:#{{1,6}}{_H})?(?:\|{_H})?"
           rf"(?:(?:[-*+]|\d+[.)]){_H})?[*_`]*")
AC_RE = re.compile(
    rf"^{_ADORNO}(AC-\d+)[*_`]*{_H}{_TITULO}{_H}:", re.MULTILINE)
# --- la cita archivo:linea --------------------------------------------------
#
# Una cita es `archivo.ext:linea`, no cualquier cosa con dos puntos y un numero.
# El regex anterior daba por cubierto un AC citado con la URL del ticket
# (`https://jira.empresa.com:8080/...` casa como `//jira.empresa.com:8080`) o
# con una version (`1.2:34`): el falso verde exacto que este gate existe para
# impedir, y con atlassian.py en el flujo pegar URLs de Jira es lo natural.
#
# URL_RE borra las URL antes de buscar. No usa \S+ porque se llevaba por delante
# la cita que venia pegada detras ('[ABC-1](https://jira.io/x)<br>src/pago.ts:88'):
# corta en los cierres que en markdown no pueden ser parte del enlace.
URL_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9+.-]*://[^\s)\]|<>\"']+")
# El cuerpo puede estar vacio antes del punto: '.env:3' y 'src/.env:12' son
# citas legitimas (y .env es una ruta protegida, asi que se citan). La
# extension empieza por letra -- eso es lo que mata '1.2:34' -- y se deja
# margen para extensiones largas tipo '.cloudformation'.
CITA_RE = re.compile(r"[\w.\\/-]*\.[A-Za-z][A-Za-z0-9]{0,15}:\d+(?!\d*/)")


# Sufijos de red: nunca son la extension de un archivo que se cite. Sin esto,
# la misma URL de Jira pegada SIN esquema ('jira.empresa.com:8080') o un
# 'pagos.svc:8443' contaban como cita, que es el falso verde que URL_RE mata
# solo cuando el autor escribio 'https://'.
_SUFIJOS_DE_RED = frozenset((
    "com", "net", "org", "io", "dev", "app", "local", "svc", "internal",
    "cluster", "cloud", "es", "cl", "ar", "co", "uk", "ai", "me", "info", "tv",
))


def hay_cita(linea: str) -> bool:
    """True si la linea trae una cita archivo:linea real (sin contar URLs)."""
    for m in CITA_RE.finditer(URL_RE.sub(" ", linea or "")):
        token = m.group(0)
        ext = token.rsplit(".", 1)[1].split(":", 1)[0].lower()
        # 'src/schema.io:12' SI es un archivo; 'pagos.svc:8443' es un host.
        if ext in _SUFIJOS_DE_RED and "/" not in token and "\\" not in token:
            continue
        return True
    return False

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

def spec_ac_lineas(text: str) -> dict[str, str]:
    """AC-n -> su linea declarada, ya sin el adorno de lista.

    Existe porque cada consumidor se habia escrito su propio parser: el PRD
    (documentacion.py) exigia `AC-n:` pegado y perdia los AC con titulo entre
    parentesis, y el brief/briefing casaban con startswith, que hace que
    'AC-1' enganche la linea de 'AC-10'. Un solo parser, el de spec_acs.
    """
    out: dict[str, str] = {}
    for m in AC_RE.finditer(text):
        ac = m.group(1)
        if ac in out:
            continue
        pos = m.start(1)                    # anclado al id, no al adorno
        ini = text.rfind("\n", 0, pos) + 1
        fin = text.find("\n", pos)
        linea = (text[ini:] if fin == -1 else text[ini:fin]).strip()
        out[ac] = _sin_adorno(linea)
    return out


def acs_no_reconocidos(text: str, acs: list[str] | None = None) -> list[str]:
    """Ids que una linea parece declarar y que spec_acs NO reconocio.

    acs_faltantes solo ve huecos por debajo del mayor declarado: si el AC que el
    parser se comio es el ultimo, no hay hueco y nadie se entera. Esto compara
    contra la gramatica laxa de declara_ac, asi que cualquier "- AC-7 ..." mal
    escrito sale a la luz aunque sea el de numero mas alto.
    """
    declarados = set(acs if acs is not None else spec_acs(text))
    sospechosos: list[str] = []
    for linea in text.splitlines():
        for ac in set(re.findall(r"AC-\d+", linea)):
            if ac in declarados or ac in sospechosos:
                continue
            if declara_ac(linea, ac):
                sospechosos.append(ac)
    return sorted(sospechosos, key=lambda x: int(x.split("-", 1)[1]))


def acs_faltantes(acs: list[str]) -> list[str]:
    """Numeros ausentes entre AC-1 y el mayor declarado.

    templates/spec.md promete "sin saltos". Es una senal debil y complementaria
    a acs_no_reconocidos: solo ve el hueco cuando el AC que falta esta por
    debajo del mayor declarado, y no distingue un borrado a proposito.
    """
    numeros = sorted(int(x.split("-", 1)[1]) for x in acs)
    if not numeros:
        return []
    return [f"AC-{n}" for n in range(1, numeros[-1]) if n not in numeros]


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

def _sin_adorno(linea: str) -> str:
    """Quita el adorno markdown del principio de la linea. Uno solo, compartido."""
    limpia = linea.strip()
    limpia = re.sub(r"^[>\s]*", "", limpia)                 # citas
    limpia = re.sub(r"^#{1,6}\s*", "", limpia)              # encabezados
    limpia = re.sub(r"^\|\s*", "", limpia)                  # filas de tabla
    limpia = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", limpia)   # listas
    return re.sub(r"^[*_`]+", "", limpia)                   # enfasis


def declara_ac(linea: str, ac: str) -> bool:
    """True si la linea DECLARA la seccion del AC, no si solo lo menciona.

    Una mencion en prosa ('...que tambien cubre lo pedido en AC-1') no puede
    abrir una seccion: heredaba la cita de la seccion vecina y daba por
    cubierto un AC sin evidencia propia, mientras truncaba la seccion del AC
    que si la tenia. Declarar es empezar la linea con el AC, admitiendo el
    adorno de markdown: '## AC-1', '- AC-1:', '* AC-1', '| AC-1 |', '3. AC-1'.
    """
    return bool(re.match(re.escape(ac) + r"\b", _sin_adorno(linea)))


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
            if any(hay_cita(l) for l in lines[ini:fin]):
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
    """Datos de stdout al tener exito; diagnostico completo al fallar."""
    try:
        # LC_ALL=C: el codigo compara mensajes de git ("already exists"). Con
        # git localizado (gettext en Linux) esas ramas nunca disparaban.
        env = dict(os.environ, LC_ALL="C", LANGUAGE="")
        r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                           text=True, timeout=60, env=env)
        if r.returncode != 0:
            return r.returncode, (r.stdout + r.stderr).strip()
        # Los consumidores parsean status, ramas y SHAs. Una advertencia en
        # stderr (p.ej. confstr en el sandbox macOS) no es parte de esos datos.
        if r.stderr:
            print(r.stderr, file=sys.stderr, end="")
        return 0, r.stdout
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
