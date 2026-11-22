#!/usr/bin/env python3
"""Mecanismo 2 (Agent Evals): evaluacion empirica de skills y lecciones en bucle.

Evita acumular decenas de skills/lecciones contradictorias o desactualizadas sin
saber si los agentes realmente las siguen. Host-neutral (patron `revision.py`):
los scripts gestionan el examen, los briefings para N corridas paralelas y el
juez aislado, y validan/sellan el puntaje con exit != 0 y hash SHA-256 de la skill.

  evals.py init      <skill> [--global] [--umbral 0.85] [--corridas 3] [--skill-path <ruta>]
  evals.py briefing  <skill> [--fase ejecutar|juez] [--ronda N] [--corridas K] [--skill-path <ruta>]
  evals.py registrar <skill> --resultado <json> [--ronda N] [--por <autor>] [--skill-path <ruta>]
  evals.py estado    [--skill <skill>] [--json]
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
import comun  # noqa: E402
import leccion  # noqa: E402

UMBRAL_DEFAULT = 0.85
CORRIDAS_DEFAULT = 3
MAX_RONDAS_DEFAULT = 3
TOPE_SKILLS_HIGIENE = 15
_PLACEHOLDER_RE = re.compile(r"<[^>\n]{2,}>|<!--")
_STOPWORDS = frozenset({
    "use", "when", "para", "como", "cuando", "esta", "este", "esto", "sobre",
    "desde", "hasta", "entre", "todos", "todas", "una", "uno", "unos", "unas",
    "los", "las", "del", "con", "sin", "por", "que", "the", "and", "for", "with",
    "from", "that", "this", "skill", "reglas", "leccion",
})


def sha256_archivo(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def _proyecto_opcional() -> dict | None:
    try:
        return comun.paths()
    except SystemExit:
        return None


def resolver_skill(skill: str, skill_path: str | None = None) -> Path:
    """Devuelve la ruta real al SKILL.md de `skill`; aborta si es invalida o no existe."""
    if not leccion.nombre_valido(skill):
        sys.exit(f"[!!] nombre de skill invalido: {skill!r} (no admite rutas ni comodines)")
    if skill_path:
        cand = Path(skill_path).expanduser().resolve()
        if cand.is_dir():
            cand = cand / "SKILL.md"
        if not cand.is_file():
            sys.exit(f"[!!] --skill-path no apunta a un SKILL.md valido: {cand}")
        return cand
    sm = leccion.buscar(skill)
    if sm is None:
        sys.exit(f"[!!] no existe la skill '{skill}'. Revisa con: leccion.py list")
    return sm


def rutas_eval(
    skill: str,
    p: dict | None = None,
    *,
    skill_md: Path | None = None,
    global_mode: bool = False,
) -> tuple[Path, Path]:
    """(ruta_suite, ruta_resultados) con contencion estricta de nombre."""
    if not leccion.nombre_valido(skill):
        raise ValueError(f"nombre de skill invalido: {skill!r}")
    if not global_mode and p is not None:
        base = p["harness"] / "evals"
        suite = base / f"{skill}.json"
        res = base / f"{skill}-resultados.json"
        if suite.resolve().parent != base.resolve():
            raise ValueError(f"ruta de eval fuera de harness/evals: {skill!r}")
        return suite, res
    sm = skill_md or leccion.buscar(skill)
    if sm is None:
        raise ValueError(f"no existe la skill '{skill}' para ubicar su eval global")
    return sm.parent / "evals.json", sm.parent / "eval-resultados.json"


def localizar_eval_existente(
    skill: str,
    p: dict | None = None,
    *,
    skill_md: Path | None = None,
) -> tuple[Path, Path] | None:
    """Busca primero en harness/evals/<skill>.json (proyecto) y luego junto a la skill."""
    if not leccion.nombre_valido(skill):
        return None
    if p is not None:
        s_proj, r_proj = rutas_eval(skill, p, global_mode=False)
        if s_proj.is_file():
            return s_proj, r_proj
    sm = skill_md or leccion.buscar(skill)
    if sm is not None:
        s_glob = sm.parent / "evals.json"
        r_glob = sm.parent / "eval-resultados.json"
        if s_glob.is_file():
            return s_glob, r_glob
    return None


def _escribir_json(destino: Path, datos: dict[str, Any]) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(f".{destino.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, destino)


def _extraer_reglas_skill(skill_md: Path) -> list[str]:
    """Extrae bullets bajo `## Reglas` (o primeros bullets) para sugerir criterios."""
    texto = skill_md.read_text(encoding="utf-8")
    en_reglas = False
    reglas: list[str] = []
    for ln in texto.splitlines():
        s = ln.strip()
        if re.match(r"^#{1,3}\s+reglas\b", s, re.I):
            en_reglas = True
            continue
        if en_reglas and s.startswith("#"):
            break
        if en_reglas and s.startswith(("- ", "* ")):
            item = s[2:].strip()
            if item and not _PLACEHOLDER_RE.search(item):
                reglas.append(item[:160])
    return reglas[:5]


def validar_suite(suite: Any) -> list[str]:
    """Valida el contrato de una suite de eval (sin placeholders ni criterios vacios)."""
    if not isinstance(suite, dict):
        return ["la suite debe ser un objeto JSON"]
    fallos: list[str] = []
    umbral = suite.get("umbral", UMBRAL_DEFAULT)
    if not isinstance(umbral, (int, float)) or not (0.0 < float(umbral) <= 1.0):
        fallos.append(f"umbral invalido ({umbral!r}): debe estar en (0, 1]")
    corridas = suite.get("corridas_por_caso", CORRIDAS_DEFAULT)
    if not isinstance(corridas, int) or corridas < 1:
        fallos.append(f"corridas_por_caso invalido ({corridas!r}): debe ser entero >= 1")
    casos = suite.get("casos")
    if not isinstance(casos, list) or not casos:
        fallos.append("la suite debe declarar al menos un caso en 'casos'")
        return fallos
    ids_vistos: set[str] = set()
    for idx, c in enumerate(casos, 1):
        if not isinstance(c, dict):
            fallos.append(f"caso #{idx} debe ser un objeto")
            continue
        cid = str(c.get("id") or "").strip()
        if not cid or cid in ids_vistos:
            fallos.append(f"caso #{idx} sin id unico ('{cid}')")
        ids_vistos.add(cid)
        tarea = str(c.get("tarea") or "").strip()
        if not tarea or _PLACEHOLDER_RE.search(tarea):
            fallos.append(f"caso {cid or idx}: falta 'tarea' concreta sin placeholders")
        criterios = c.get("criterios")
        if not isinstance(criterios, list) or not criterios:
            fallos.append(f"caso {cid or idx}: debe declarar al menos un criterio")
            continue
        cids: set[str] = set()
        for j, cr in enumerate(criterios, 1):
            if not isinstance(cr, dict):
                fallos.append(f"caso {cid} criterio #{j}: debe ser un objeto")
                continue
            crid = str(cr.get("id") or "").strip()
            desc = str(cr.get("descripcion") or "").strip()
            peso = cr.get("peso", 1.0)
            if not crid or crid in cids:
                fallos.append(f"caso {cid}: criterio #{j} sin id unico")
            cids.add(crid)
            if not desc or _PLACEHOLDER_RE.search(desc):
                fallos.append(f"caso {cid}/{crid or j}: falta descripcion concreta sin placeholders")
            if not isinstance(peso, (int, float)) or float(peso) <= 0:
                fallos.append(f"caso {cid}/{crid or j}: peso debe ser > 0")
    return fallos


def evaluar_ronda(suite: dict[str, Any], payload: Any) -> dict[str, Any]:
    """Valida y califica deterministamente el JSON devuelto por el juez aislado.

    Rechaza resultados parciales, corridas insuficientes o criterios sin evidencia.
    """
    if not isinstance(payload, dict):
        raise ValueError("el archivo de resultado debe ser un objeto JSON")
    corridas_raw = payload.get("corridas")
    if not isinstance(corridas_raw, list) or not corridas_raw:
        raise ValueError("el resultado debe incluir una lista no vacia 'corridas'")

    umbral = float(suite.get("umbral", UMBRAL_DEFAULT))
    min_corridas = int(suite.get("corridas_por_caso", CORRIDAS_DEFAULT))
    casos_map = {str(c["id"]): c for c in suite["casos"]}

    por_caso: dict[str, dict[int, dict[str, Any]]] = {cid: {} for cid in casos_map}
    errores: list[str] = []

    for idx, row in enumerate(corridas_raw, 1):
        if not isinstance(row, dict):
            errores.append(f"corrida #{idx}: debe ser un objeto")
            continue
        cid = str(row.get("caso_id") or "").strip()
        if cid not in casos_map:
            errores.append(f"corrida #{idx}: caso_id desconocido '{cid}'")
            continue
        num = row.get("corrida")
        if type(num) is not int or num < 1:
            errores.append(f"corrida #{idx} ({cid}): 'corrida' debe ser entero >= 1")
            continue
        if num in por_caso[cid]:
            errores.append(f"caso {cid}: corrida #{num} duplicada")
            continue

        caso = casos_map[cid]
        criterios_esperados = {str(cr["id"]): cr for cr in caso["criterios"]}
        criterios_eval = row.get("criterios")
        if not isinstance(criterios_eval, list):
            errores.append(f"caso {cid} corrida #{num}: falta lista 'criterios'")
            continue
        evaluados: dict[str, dict[str, Any]] = {}
        for cr_row in criterios_eval:
            if not isinstance(cr_row, dict):
                continue
            crid = str(cr_row.get("id") or "").strip()
            if crid not in criterios_esperados:
                errores.append(f"caso {cid} corrida #{num}: criterio desconocido '{crid}'")
                continue
            cumplido = cr_row.get("cumplido")
            evidencia = str(cr_row.get("evidencia") or "").strip()
            if type(cumplido) is not bool:
                errores.append(f"caso {cid} corrida #{num} {crid}: 'cumplido' debe ser booleano")
                continue
            if len(evidencia) < 5 or _PLACEHOLDER_RE.search(evidencia):
                errores.append(
                    f"caso {cid} corrida #{num} {crid}: 'evidencia' vacia o con placeholder (no cuenta)"
                )
                continue
            evaluados[crid] = {"cumplido": cumplido, "evidencia": evidencia}

        faltan = [crid for crid in criterios_esperados if crid not in evaluados]
        if faltan:
            errores.append(f"caso {cid} corrida #{num}: faltan criterios {', '.join(faltan)}")
            continue

        prohibidas = row.get("senales_prohibidas_detectadas") or []
        if not isinstance(prohibidas, list):
            errores.append(f"caso {cid} corrida #{num}: 'senales_prohibidas_detectadas' debe ser una lista")
            continue
        prohibidas_limpias = [str(x).strip() for x in prohibidas if str(x).strip()]

        por_caso[cid][num] = {
            "criterios": evaluados,
            "senales_prohibidas_detectadas": prohibidas_limpias,
        }

    for cid, runs in por_caso.items():
        if len(runs) < min_corridas:
            errores.append(
                f"caso {cid}: se evaluaron {len(runs)} corrida(s) y la suite exige al menos {min_corridas}"
            )

    if errores:
        raise ValueError("resultado de eval invalido:\n" + "\n".join(f"  - {e}" for e in errores))

    # Calculo determinista de puntajes, fallos obligatorios y brechas
    detalle_casos: dict[str, Any] = {}
    fallos_obligatorios: list[str] = []
    brechas_cuenta: dict[str, dict[str, Any]] = {}
    scores_casos: list[float] = []

    for cid, caso in casos_map.items():
        runs = por_caso[cid]
        criterios_def = {str(cr["id"]): cr for cr in caso["criterios"]}
        peso_total = sum(float(cr.get("peso", 1.0)) for cr in caso["criterios"])
        scores_run: list[float] = []

        for num, rdata in sorted(runs.items()):
            prohibidas = rdata["senales_prohibidas_detectadas"]
            if prohibidas:
                scores_run.append(0.0)
                fallos_obligatorios.append(
                    f"{cid} corrida #{num}: senal prohibida detectada ({', '.join(prohibidas)})"
                )
            else:
                obtenido = sum(
                    float(criterios_def[crid].get("peso", 1.0))
                    for crid, ev in rdata["criterios"].items()
                    if ev["cumplido"]
                )
                scores_run.append(obtenido / peso_total if peso_total else 0.0)

            for crid, cr in criterios_def.items():
                if not rdata["criterios"][crid]["cumplido"]:
                    clave = f"{cid}/{crid}"
                    b = brechas_cuenta.setdefault(clave, {
                        "caso": cid,
                        "criterio": crid,
                        "descripcion": cr["descripcion"],
                        "obligatorio": bool(cr.get("obligatorio", False)),
                        "fallos": 0,
                        "total": len(runs),
                    })
                    b["fallos"] += 1
                    if cr.get("obligatorio"):
                        fallos_obligatorios.append(
                            f"{cid}/{crid} (obligatorio) fallo en corrida #{num}: {cr['descripcion']}"
                        )

        media_caso = sum(scores_run) / len(scores_run)
        scores_casos.append(media_caso)
        detalle_casos[cid] = {
            "score": round(media_caso, 4),
            "corridas": len(runs),
            "scores_corridas": [round(s, 4) for s in scores_run],
        }

    score_global = round(sum(scores_casos) / len(scores_casos), 4)
    brechas = sorted(brechas_cuenta.values(), key=lambda x: (-x["fallos"], x["caso"], x["criterio"]))
    aprobado = (score_global >= umbral) and (not fallos_obligatorios)

    return {
        "score": score_global,
        "umbral": umbral,
        "aprobado": aprobado,
        "casos": detalle_casos,
        "fallos_obligatorios": fallos_obligatorios,
        "brechas": brechas,
        "juez": str(payload.get("juez") or "sin-declarar").strip(),
    }


def estado_eval(skill: str, p: dict | None = None, *, skill_md: Path | None = None) -> dict[str, Any]:
    """Estado verificado de la eval de `skill`: nunca devuelve 'pass' si la skill cambio."""
    sm = skill_md or leccion.buscar(skill)
    if sm is None or not sm.is_file():
        return {"skill": skill, "estado": "sin_skill", "motivo": "SKILL.md no encontrado"}

    ubic = localizar_eval_existente(skill, p, skill_md=sm)
    if ubic is None:
        return {"skill": skill, "estado": "sin_eval", "skill_path": str(sm)}

    suite_p, res_p = ubic
    try:
        suite = json.loads(suite_p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"skill": skill, "estado": "invalido", "motivo": f"suite corrupta: {exc}"}

    errs_suite = validar_suite(suite)
    if errs_suite:
        return {"skill": skill, "estado": "invalido", "motivo": "; ".join(errs_suite[:3])}

    if not res_p.is_file():
        return {
            "skill": skill,
            "estado": "sin_resultados",
            "suite_path": str(suite_p),
            "umbral": float(suite.get("umbral", UMBRAL_DEFAULT)),
        }

    try:
        hist = json.loads(res_p.read_text(encoding="utf-8"))
        rondas = hist.get("rondas") or []
        if not isinstance(rondas, list) or not rondas:
            raise ValueError("sin rondas registradas")
        ultima = rondas[-1]
    except (OSError, ValueError, KeyError) as exc:
        return {"skill": skill, "estado": "invalido", "motivo": f"resultados corruptos: {exc}"}

    sha_skill_actual = sha256_archivo(sm)
    sha_suite_actual = sha256_archivo(suite_p)
    info = {
        "skill": skill,
        "suite_path": str(suite_p),
        "resultados_path": str(res_p),
        "ronda": ultima.get("ronda"),
        "score": ultima.get("score"),
        "umbral": ultima.get("umbral", suite.get("umbral", UMBRAL_DEFAULT)),
        "at": ultima.get("at"),
        "aprobado": bool(ultima.get("aprobado")),
        "max_rondas_mejora": int(suite.get("max_rondas_mejora", MAX_RONDAS_DEFAULT)),
    }

    if ultima.get("skill_sha256") != sha_skill_actual:
        info["estado"] = "stale_skill"
        info["motivo"] = "SKILL.md cambio despues de la ultima evaluacion: re-evalua"
    elif ultima.get("suite_sha256") != sha_suite_actual:
        info["estado"] = "stale_suite"
        info["motivo"] = "la suite de eval cambio despues de la ultima evaluacion: re-evalua"
    elif ultima.get("aprobado"):
        info["estado"] = "pass"
    else:
        info["estado"] = "fail"
        info["motivo"] = f"score {ultima.get('score', 0):.0%} < umbral {info['umbral']:.0%} o criterio obligatorio fallido"
    return info


def insignia_eval(skill: str, p: dict | None = None, *, skill_md: Path | None = None) -> str:
    """Etiqueta compacta para `leccion.py list` (vacia si no tiene eval)."""
    est = estado_eval(skill, p, skill_md=skill_md)
    codigo = est["estado"]
    if codigo == "pass":
        return f"  [eval: PASS {est['score']:.0%}]"
    if codigo == "fail":
        return f"  [eval: FAIL {est['score']:.0%}]"
    if codigo in ("stale_skill", "stale_suite"):
        return "  [eval: STALE]"
    if codigo == "sin_resultados":
        return "  [eval: PENDIENTE]"
    if codigo == "invalido":
        return "  [eval: INVALIDO]"
    return ""


def validar_leccion_para_cierre(p: dict, data: dict, clase: str) -> tuple[list[str], list[str]]:
    """Valida la eval de la leccion al cerrar (`gate.py close`).

    - `rules.require_skill_eval` es opt-in (False por defecto).
    - Si esta activa y `clase != 'ninguna'`, exige estado == 'pass' (fresco).
    - Si esta apagada, avisa si existe una eval en estado FAIL o STALE.
    """
    if not clase or clase == "ninguna":
        return [], []
    req = (data.get("rules") or {}).get("require_skill_eval", False)
    if not isinstance(req, bool):
        return [f"rules.require_skill_eval invalido ({req!r}): debe ser true o false"], []
    est = estado_eval(clase, p)
    codigo = est["estado"]
    if req:
        if codigo == "pass":
            return [], []
        motivo = est.get("motivo") or codigo
        return [
            f"evals: la leccion '{clase}' no tiene una eval aprobada y vigente ({codigo}: {motivo}). "
            f"Ejecuta evals.py init/briefing/registrar {clase} antes de cerrar"
        ], []
    # Opt-in apagado: avisar si hay eval fallida o vencida
    if codigo in ("fail", "stale_skill", "stale_suite", "invalido"):
        return [], [
            f"evals: la leccion '{clase}' tiene eval en estado '{codigo}' ({est.get('motivo', '')}); "
            f"re-evalua con evals.py briefing {clase}"
        ]
    return [], []


def _tokens_higiene(texto: str) -> set[str]:
    palabras = re.findall(r"[a-záéíóúñ0-9]{4,}", (texto or "").lower())
    return {w for w in palabras if w not in _STOPWORDS}


def auditar_higiene_skills(p: dict | None = None) -> dict[str, Any]:
    """Detecta acumulacion excesiva, skills largas y posibles solapamientos."""
    skills: list[dict[str, Any]] = []
    vistas: set[str] = set()
    try:
        raices = leccion.skills_roots(todos_los_hosts=True)
    except SystemExit:
        raices = []
    for raiz in raices:
        for sm in sorted(raiz.glob("*/*/SKILL.md")) + sorted(raiz.glob("*/SKILL.md")):
            nombre = sm.parent.name
            if nombre in vistas or nombre == "harness-flow":
                continue
            vistas.add(nombre)
            lineas = len(sm.read_text(encoding="utf-8", errors="replace").splitlines())
            desc = leccion.descripcion(sm)
            est = estado_eval(nombre, p, skill_md=sm)
            skills.append({
                "nombre": nombre,
                "path": str(sm),
                "lineas": lineas,
                "descripcion": desc,
                "eval": est,
                "tokens": _tokens_higiene(nombre.replace("-", " ") + " " + desc),
            })

    avisos: list[str] = []
    if len(skills) > TOPE_SKILLS_HIGIENE:
        avisos.append(
            f"acumulacion de skills: hay {len(skills)} lecciones (tope recomendado {TOPE_SKILLS_HIGIENE}); "
            "audita cuales siguen aportando valor con evals.py y fusiona o retira las redundantes"
        )
    for sk in skills:
        if sk["lineas"] > leccion.TOPE_LINEAS:
            avisos.append(
                f"{sk['nombre']}: {sk['lineas']} lineas (supera tope {leccion.TOPE_LINEAS}); "
                "mueve detalle a references/"
            )
    # Solapamientos por similitud Jaccard en descripcion/nombre
    for i in range(len(skills)):
        t1 = skills[i]["tokens"]
        if len(t1) < 3:
            continue
        for j in range(i + 1, len(skills)):
            t2 = skills[j]["tokens"]
            if len(t2) < 3:
                continue
            inter = len(t1 & t2)
            union = len(t1 | t2)
            if union and (inter / union) >= 0.60:
                avisos.append(
                    f"posible solapamiento/contradiccion entre '{skills[i]['nombre']}' y "
                    f"'{skills[j]['nombre']}' ({inter}/{union} terminos en comun): revisa si conviene fusionarlas"
                )
    for sk in skills:
        sk.pop("tokens", None)
    return {"skills": skills, "avisos": avisos}


def resumen_estado(p: dict, data: dict) -> str | None:
    """Resumen compacto para `estado.py` cuando existen evals o la regla esta activa."""
    ev_dir = p["harness"] / "evals"
    req = bool((data.get("rules") or {}).get("require_skill_eval", False))
    suites = sorted(ev_dir.glob("*.json")) if ev_dir.is_dir() else []
    suites = [s for s in suites if not s.name.endswith("-resultados.json")]
    if not suites and not req:
        return None
    if not suites:
        return "[!] require_skill_eval activo pero sin suites en harness/evals/ (evals.py init <skill>)"
    conteo = {"pass": 0, "fail": 0, "stale": 0, "pendiente": 0}
    for s in suites:
        est = estado_eval(s.stem, p)["estado"]
        if est == "pass":
            conteo["pass"] += 1
        elif est in ("stale_skill", "stale_suite"):
            conteo["stale"] += 1
        elif est == "sin_resultados":
            conteo["pendiente"] += 1
        else:
            conteo["fail"] += 1
    partes = [f"{conteo['pass']} pass"]
    if conteo["fail"]:
        partes.append(f"{conteo['fail']} fail")
    if conteo["stale"]:
        partes.append(f"{conteo['stale']} stale")
    if conteo["pendiente"]:
        partes.append(f"{conteo['pendiente']} pendiente(s)")
    tag = "obligatorio al cerrar" if req else "opt-in"
    return f"{len(suites)} suite(s) ({', '.join(partes)}; {tag})"


# --- CLI -------------------------------------------------------------------

def cmd_init(args) -> None:
    p = None if args.global_mode else _proyecto_opcional()
    sm = resolver_skill(args.skill, args.skill_path)
    suite_p, _ = rutas_eval(args.skill, p, skill_md=sm, global_mode=args.global_mode)
    if suite_p.exists() and not args.forzar:
        sys.exit(f"[!!] ya existe {suite_p}. Usa --forzar para sobreescribirla.")

    reglas = _extraer_reglas_skill(sm)
    criterios = [
        {
            "id": f"C-{i}",
            "descripcion": r,
            "peso": 1.0,
            "obligatorio": i == 1,
        }
        for i, r in enumerate(reglas, 1)
    ] or [
        {
            "id": "C-1",
            "descripcion": "<regla critica de la skill que el agente debe cumplir>",
            "peso": 1.0,
            "obligatorio": True,
        }
    ]

    suite = {
        "version": 1,
        "skill": args.skill,
        "umbral": float(args.umbral),
        "corridas_por_caso": int(args.corridas),
        "max_rondas_mejora": int(args.max_rondas),
        "casos": [
            {
                "id": "E-1",
                "tarea": f"<tarea realista donde el agente debe aplicar la skill '{args.skill}'>",
                "criterios": criterios,
                "senales_prohibidas": [],
            }
        ],
    }
    _escribir_json(suite_p, suite)
    print(f"[ok] suite de eval creada: {suite_p}")
    print(f"     skill objetivo: {sm}")
    print("     siguiente paso: reemplaza los '<...>' en los casos y corre:")
    print(f"       evals.py briefing {args.skill} --fase ejecutar")


def cmd_briefing(args) -> None:
    p = _proyecto_opcional()
    sm = resolver_skill(args.skill, args.skill_path)
    ubic = localizar_eval_existente(args.skill, p, skill_md=sm)
    if ubic is None:
        sys.exit(f"[!!] no hay suite de eval para '{args.skill}'. Creala con: evals.py init {args.skill}")
    suite_p, res_p = ubic
    try:
        suite = json.loads(suite_p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        sys.exit(f"[!!] suite ilegible ({suite_p}): {exc}")
    errs = validar_suite(suite)
    if errs:
        sys.exit("[!!] la suite tiene errores o placeholders sin completar:\n"
                 + "\n".join(f"     - {e}" for e in errs))

    ronda = args.ronda
    if ronda is None:
        if res_p.is_file():
            try:
                hist = json.loads(res_p.read_text(encoding="utf-8"))
                ronda = len(hist.get("rondas") or []) + 1
            except (OSError, ValueError):
                ronda = 1
        else:
            ronda = 1
    corridas = args.corridas or int(suite.get("corridas_por_caso", CORRIDAS_DEFAULT))

    print("=" * 72)
    print(f"AGENT EVAL [{args.fase.upper()}] — skill '{args.skill}' · ronda {ronda}")
    print("=" * 72)
    print(f"Skill:  {sm}")
    print(f"Suite:  {suite_p}")
    print(f"Umbral: {float(suite.get('umbral', UMBRAL_DEFAULT)):.0%} · "
          f"corridas por caso: {corridas} · max rondas de mejora: {suite.get('max_rondas_mejora', MAX_RONDAS_DEFAULT)}\n")

    if args.fase == "ejecutar":
        print("INSTRUCCIONES PARA EL COORDINADOR (host-neutral):")
        print(f"- Lanza {corridas} subagentes independientes EN PARALELO por cada caso usando la herramienta de tu host:")
        print("    * AGY:         invoke_subagent(TypeName='self', Model='inherit') o swarm(action='add', n=K)")
        print("    * Claude Code: tool Agent (en paralelo)")
        print("    * Hermes:      delegate_task (en paralelo)")
        print("    * Grok:        spawn_subagent (en paralelo)")
        print("    * Codex / CLI: codex exec / gemini -p en sesiones limpias")
        print("- Entrega a cada subagente SOLO el texto de la skill y la tarea del caso.")
        print("- PROHIBIDO mostrar la rubrica del juez ni las senales prohibidas a los ejecutores.")
        print("- Guarda cada salida en un archivo (ej. /tmp/eval-<skill>-r<ronda>-<caso>-c<n>.md).\n")
        print("CASOS A EJECUTAR:")
        for c in suite["casos"]:
            print(f"\n### {c['id']}")
            print(f"Tarea: {c['tarea']}")
        print("\nCUANDO TERMINEN TODAS LAS CORRIDAS:")
        print(f"  1. Genera el paquete del juez aislado: evals.py briefing {args.skill} --fase juez --ronda {ronda}")
        print(f"  2. Lanza UN subagente juez AISLADO (sin historial de los ejecutores) con ese briefing + las salidas.")
        print(f"  3. Registra el JSON devuelto por el juez: evals.py registrar {args.skill} --resultado <archivo.json> --ronda {ronda}")
        return

    # Fase juez aislado
    print("INSTRUCCIONES PARA EL AGENTE JUEZ AISLADO (AI-as-a-Judge neutralizado):")
    print("- NO compartas historial ni contexto con los agentes que ejecutaron las tareas.")
    print("- Evalua cada corrida de forma independiente contra la rubrica de abajo.")
    print("- Prohibido calificar 'cumplido: true' sin citar evidencia concreta de la salida evaluada.")
    print("- Si detectas una senal prohibida, registrala en 'senales_prohibidas_detectadas' (anula la corrida).\n")
    print("RUBRICA POR CASO:")
    for c in suite["casos"]:
        print(f"\n### {c['id']} — {c['tarea']}")
        for cr in c["criterios"]:
            ob = " [OBLIGATORIO]" if cr.get("obligatorio") else ""
            print(f"  - {cr['id']} (peso {cr.get('peso', 1.0)}){ob}: {cr['descripcion']}")
        if c.get("senales_prohibidas"):
            print(f"  - Senales prohibidas: {', '.join(c['senales_prohibidas'])}")

    ejemplo = {
        "ronda": ronda,
        "juez": "<modelo-y-host>",
        "corridas": [
            {
                "caso_id": suite["casos"][0]["id"],
                "corrida": 1,
                "criterios": [
                    {
                        "id": suite["casos"][0]["criterios"][0]["id"],
                        "cumplido": True,
                        "evidencia": "Cita exacta de la salida del agente evaluado",
                    }
                ],
                "senales_prohibidas_detectadas": [],
            }
        ],
    }
    print("\nENTREGABLE EXACTO (guardalo en un archivo .json y pasalo a `evals.py registrar`):")
    print(json.dumps(ejemplo, ensure_ascii=False, indent=2))


def cmd_registrar(args) -> None:
    p = _proyecto_opcional()
    sm = resolver_skill(args.skill, args.skill_path)
    ubic = localizar_eval_existente(args.skill, p, skill_md=sm)
    if ubic is None:
        sys.exit(f"[!!] no hay suite de eval para '{args.skill}'. Creala con: evals.py init {args.skill}")
    suite_p, res_p = ubic
    try:
        suite = json.loads(suite_p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        sys.exit(f"[!!] suite ilegible: {exc}")
    errs = validar_suite(suite)
    if errs:
        sys.exit("[!!] suite invalida:\n" + "\n".join(f"     - {e}" for e in errs))

    res_in = Path(args.resultado).expanduser()
    if not res_in.is_file():
        sys.exit(f"[!!] no existe el archivo de resultado: {res_in}")
    try:
        payload = json.loads(res_in.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        sys.exit(f"[!!] resultado JSON invalido: {exc}")

    try:
        ev = evaluar_ronda(suite, payload)
    except ValueError as exc:
        sys.exit(f"[!!] {exc}")

    hist: dict[str, Any] = {"version": 1, "skill": args.skill, "rondas": []}
    if res_p.is_file():
        try:
            prev = json.loads(res_p.read_text(encoding="utf-8"))
            if isinstance(prev, dict) and isinstance(prev.get("rondas"), list):
                hist = prev
        except (OSError, ValueError):
            pass

    ronda = args.ronda or payload.get("ronda") or (len(hist["rondas"]) + 1)
    registro = {
        "ronda": int(ronda),
        "at": comun.now_iso(),
        "por": (args.por or getpass.getuser()).strip(),
        "juez": ev["juez"],
        "skill_sha256": sha256_archivo(sm),
        "suite_sha256": sha256_archivo(suite_p),
        "score": ev["score"],
        "umbral": ev["umbral"],
        "aprobado": ev["aprobado"],
        "casos": ev["casos"],
        "fallos_obligatorios": ev["fallos_obligatorios"],
        "brechas": ev["brechas"],
    }
    if args.notas:
        registro["notas"] = args.notas.strip()

    hist["rondas"].append(registro)
    _escribir_json(res_p, hist)

    if p is not None:
        comun.bitacora(
            p,
            f"eval skill '{args.skill}' ronda {ronda}: "
            f"{'PASS' if ev['aprobado'] else 'FAIL'} ({ev['score']:.0%}, umbral {ev['umbral']:.0%})",
        )

    if ev["aprobado"]:
        print(f"[ok] eval '{args.skill}' ronda {ronda}: PASS ({ev['score']:.0%} >= {ev['umbral']:.0%}) -> {res_p}")
        return

    print(f"[!!] eval '{args.skill}' ronda {ronda}: FAIL ({ev['score']:.0%}, umbral {ev['umbral']:.0%}) -> {res_p}")
    for fo in ev["fallos_obligatorios"][:5]:
        print(f"     - obligatorio fallido: {fo}")
    for b in ev["brechas"][:5]:
        print(f"     - brecha {b['caso']}/{b['criterio']} ({b['fallos']}/{b['total']} corridas fallaron): {b['descripcion']}")
    max_r = int(suite.get("max_rondas_mejora", MAX_RONDAS_DEFAULT))
    if int(ronda) >= max_r:
        print(f"[!]  alcanzado el tope de {max_r} rondas de mejora para '{args.skill}'.")
        print("     Las instrucciones en texto no bastan para esta regla: PROMUEVELA a guardrail determinista:")
        print(f"       guardrails.py promover --desde-skill {args.skill} --id <regla-id> --patron '<regex>' --mensaje '<motivo>'")
    else:
        print(f"[i]  bucle de mejora: refina {sm} atacando las brechas de arriba y repite la ronda {int(ronda) + 1}:")
        print(f"       evals.py briefing {args.skill} --fase ejecutar --ronda {int(ronda) + 1}")
    sys.exit(1)


def cmd_estado(args) -> None:
    p = _proyecto_opcional()
    if args.skill:
        est = estado_eval(args.skill, p)
        if args.json:
            print(json.dumps(est, ensure_ascii=False, indent=2))
        else:
            sc = f" ({est['score']:.0%}, umbral {est['umbral']:.0%})" if est.get("score") is not None else ""
            print(f"{est['skill']}: {est['estado'].upper()}{sc}")
            if est.get("motivo"):
                print(f"   motivo: {est['motivo']}")
        sys.exit(0 if est["estado"] == "pass" else 1)

    rep = auditar_higiene_skills(p)
    # Sumar tambien suites del proyecto cuya skill este fuera o sin listar
    if p is not None and (p["harness"] / "evals").is_dir():
        vistas = {s["nombre"] for s in rep["skills"]}
        for s in sorted((p["harness"] / "evals").glob("*.json")):
            if s.name.endswith("-resultados.json") or s.stem in vistas:
                continue
            rep["skills"].append({"nombre": s.stem, "eval": estado_eval(s.stem, p)})

    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return

    print(f"== Agent Evals e higiene de skills ({len(rep['skills'])} skills) ==")
    for sk in rep["skills"]:
        ev = sk["eval"]
        est = ev["estado"].upper()
        sc = f" {ev['score']:.0%}" if ev.get("score") is not None else ""
        print(f"   - {sk['nombre']:<38} {est}{sc}")
        if ev.get("motivo") and ev["estado"] != "sin_eval":
            print(f"       {ev['motivo']}")
    if rep["avisos"]:
        print("\nAvisos de higiene:")
        for a in rep["avisos"]:
            print(f"   [!] {a}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Agent Evals de skills y lecciones (host-neutral)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="crea la suite de eval para una skill/leccion")
    s.add_argument("skill")
    s.add_argument("--global", action="store_true", dest="global_mode",
                   help="guardar evals.json junto al SKILL.md en vez de harness/evals/")
    s.add_argument("--umbral", type=float, default=UMBRAL_DEFAULT)
    s.add_argument("--corridas", type=int, default=CORRIDAS_DEFAULT)
    s.add_argument("--max-rondas", type=int, default=MAX_RONDAS_DEFAULT, dest="max_rondas")
    s.add_argument("--skill-path", dest="skill_path", help="ruta explicita al SKILL.md o carpeta")
    s.add_argument("--forzar", action="store_true")
    s.set_defaults(fn=cmd_init)

    s = sub.add_parser("briefing", help="genera briefing host-neutral para ejecutores paralelos o juez aislado")
    s.add_argument("skill")
    s.add_argument("--fase", choices=["ejecutar", "juez"], default="ejecutar")
    s.add_argument("--ronda", type=int)
    s.add_argument("--corridas", type=int)
    s.add_argument("--skill-path", dest="skill_path")
    s.set_defaults(fn=cmd_briefing)

    s = sub.add_parser("registrar", help="valida y sella los resultados del juez aislado (exit!=0 si reprueba)")
    s.add_argument("skill")
    s.add_argument("--resultado", required=True, help="JSON devuelto por el juez aislado")
    s.add_argument("--ronda", type=int)
    s.add_argument("--por")
    s.add_argument("--notas")
    s.add_argument("--skill-path", dest="skill_path")
    s.set_defaults(fn=cmd_registrar)

    s = sub.add_parser("estado", help="estado de evals e higiene de skills")
    s.add_argument("--skill")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_estado)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
