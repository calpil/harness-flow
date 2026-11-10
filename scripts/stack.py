#!/usr/bin/env python3
"""Gestor de Stacks Tecnologicos de CALPIL en Harness Flow.

Soporta:
- Deteccion automatica de stack (Golang Hexagonal, Angular Product).
- Verificacion de cumplimiento normativo (Rules, Skills, Arquitectura, Testing).
- Normalizacion automatica multi-LLM (Claude Code, Codex, Gemini/AGY, Hermes, Grok, Kimi).
- Refactorizacion guiada de arquitectura (scaffolding y plan expand-contract).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Directorio base de stacks en harness-flow
# Bajo assets/ a proposito: Hermes recorre la skill entera y registra como skill
# propia cada SKILL.md que encuentra, salvo en references/, templates/, assets/ y
# scripts/. En la raiz, las plantillas de cada stack entraban a su indice.
STACKS_DIR = Path(__file__).resolve().parent.parent / "assets" / "stacks"


def cargar_manifest(stack_id: str) -> dict[str, Any]:
    manifest_path = STACKS_DIR / stack_id / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"[!!] Stack '{stack_id}' no encontrado en {STACKS_DIR}")
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"[!!] Error leyendo manifest de stack '{stack_id}': {exc}")


def listar_stacks_disponibles() -> list[dict[str, Any]]:
    stacks = []
    if not STACKS_DIR.exists():
        return stacks
    for sub in STACKS_DIR.iterdir():
        if sub.is_dir() and (sub / "manifest.json").exists():
            try:
                data = json.loads((sub / "manifest.json").read_text(encoding="utf-8"))
                stacks.append(data)
            except Exception:
                pass
    return stacks


# ---------------------------------------------------------------------------
# 1. Detección de Stack
# ---------------------------------------------------------------------------

def evaluar_stack_manifest(manifest: dict[str, Any], repo: Path) -> tuple[int, list[str]]:
    """Evalúa un manifest de stack contra un repositorio devolviendo (confianza, indicadores)."""
    detection = manifest.get("detection", {})
    if not detection:
        return 0, []

    score = 0
    indicators: list[str] = []

    # 1. Anti-indicadores: descalifican inmediatamente
    for anti in detection.get("anti_indicators", []):
        if (repo / anti).exists() or list(repo.glob(anti)):
            return 0, []

    # 2. Files any: al menos uno debe existir si se declaran
    files_any = detection.get("files_any", [])
    if files_any:
        matched_any = False
        for f in files_any:
            if (repo / f).exists() or list(repo.glob(f)):
                matched_any = True
                indicators.append(f)
                score += 25
                break
        if not matched_any:
            return 0, []

    # 3. Files all: todos deben existir si se declaran
    files_all = detection.get("files_all", [])
    if files_all:
        for f in files_all:
            if not ((repo / f).exists() or list(repo.glob(f))):
                return 0, []
            indicators.append(f)
            score += 20

    # 4. Extensiones: al menos un archivo con la extensión
    extensions = detection.get("extensions", [])
    if extensions:
        has_ext = False
        for ext in extensions:
            pattern = f"*{ext}" if ext.startswith(".") else f"*.{ext}"
            if list(repo.glob(pattern)) or list(repo.glob(f"**/{pattern}")):
                has_ext = True
                indicators.append(f"archivos {ext}")
                score += 15
                break
        if not has_ext and not files_any:
            return 0, []

    # 5. Dependencias de package.json
    package_deps = detection.get("package_deps", [])
    pkg_json = repo / "package.json"
    if package_deps and pkg_json.exists():
        try:
            pkg_data = json.loads(pkg_json.read_text(encoding="utf-8", errors="ignore"))
            all_deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
            for dep in package_deps:
                if dep in all_deps:
                    score += 15
                    indicators.append(f"dep:{dep}")
        except Exception:
            pass

    # 6. Content matches: búsqueda de palabras clave en archivos de manifiesto
    content_matches = detection.get("content_matches", {})
    for filename, patterns in content_matches.items():
        target_file = repo / filename
        if target_file.exists():
            try:
                content = target_file.read_text(encoding="utf-8", errors="ignore")
                for pat in patterns:
                    if pat in content:
                        score += 15
                        indicators.append(f"{filename} contiene '{pat}'")
            except Exception:
                pass

    # 7. Strong indicators: carpetas o patrones estructurales clave
    strong_indicators = detection.get("strong_indicators", [])
    for strong in strong_indicators:
        if (repo / strong).exists() or list(repo.glob(strong)):
            score += 15
            indicators.append(strong)

    confidence = min(100, score)
    return confidence, indicators


def detectar_stack_directorio(repo: Path) -> dict[str, Any]:
    """Detecta dinámicamente el stack tecnológico predominante usando los manifests de assets/stacks/."""
    repo = repo.resolve()
    manifests = listar_stacks_disponibles()

    candidatos = []
    for man in manifests:
        conf, ind = evaluar_stack_manifest(man, repo)
        if conf >= 25:
            candidatos.append({
                "stack": man.get("id"),
                "name": man.get("name", man.get("id")),
                "confidence": conf,
                "indicators": ind,
                "path": str(repo),
            })

    if not candidatos:
        return {
            "stack": "generico",
            "name": "Generico / Sin Stack CALPIL identificado",
            "confidence": 0,
            "indicators": [],
            "path": str(repo),
            "candidates": [],
        }

    # Ordenar por confianza descendente
    candidatos.sort(key=lambda x: x["confidence"], reverse=True)
    ganador = candidatos[0]
    ganador["candidates"] = candidatos
    return ganador


def detectar_todos_los_destinos(root: Path) -> list[dict[str, Any]]:
    """Detecta stacks en la raiz o en microservicios declarados en multi-repo."""
    # 1. Raices declaradas en harness/grafos.json
    declaradas = _raices_declaradas(root)

    # 2. Si no hay ninguna, los subdirectorios inmediatos que sean repos; si tampoco, la raiz
    if not declaradas:
        raices = _subrepos(root) or [root]
        return [detectar_stack_directorio(r) for r in raices]

    # 3. Una raiz declarada puede ser un repo o una carpeta que agrupa microservicios
    #    (~/GolandProjects/<proyecto>/ms-*): si no tiene stack propio, se recorren sus repos.
    resultados: list[dict[str, Any]] = []
    vistas: set[Path] = set()

    def agregar(res: dict[str, Any]) -> None:
        ruta = Path(res["path"])
        if ruta not in vistas:
            vistas.add(ruta)
            resultados.append(res)

    for r in declaradas:
        res = detectar_stack_directorio(r)
        subrepos = _subrepos(r) if res["stack"] == "generico" else []
        if not subrepos:
            agregar(res)
        for sub in subrepos:
            agregar(detectar_stack_directorio(sub))

    return resultados


_MARCAS_DE_REPO = ("go.mod", "angular.json", "package.json", ".git")


def _subrepos(carpeta: Path) -> list[Path]:
    """Subdirectorios inmediatos que son un repo o traen marcadores de stack."""
    return sorted(
        item for item in carpeta.iterdir()
        if item.is_dir() and not item.name.startswith((".", "harness", "docs", "graphify"))
        and any((item / marca).exists() for marca in _MARCAS_DE_REPO)
    )


def _raices_declaradas(root: Path) -> list[Path]:
    """Raices de harness/grafos.json que existen en disco.

    El formato es el de `comun.grafos_config`: objetos `{"nombre", "path"}`, con
    `path` relativo a la raiz, absoluto o con `~`. Se aceptan tambien strings.
    Leerlas como strings rompia con TypeError, que se tragaba: el diagnostico
    caia a los subdirectorios de la raiz y nunca veia los microservicios.
    """
    grafos_file = root / "harness" / "grafos.json"
    if not grafos_file.is_file():
        return []
    try:
        data = json.loads(grafos_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    entradas = data.get("raices") if isinstance(data, dict) else None
    raices: list[Path] = []
    for entrada in entradas if isinstance(entradas, list) else []:
        valor = entrada.get("path") if isinstance(entrada, dict) else entrada
        if not isinstance(valor, str) or not valor:
            continue
        ruta = Path(valor).expanduser()
        ruta = (ruta if ruta.is_absolute() else root / ruta).resolve()
        if ruta.is_dir() and ruta not in raices:
            raices.append(ruta)
    return raices


# ---------------------------------------------------------------------------
# 2. Verificación Normativa
# ---------------------------------------------------------------------------

REGLA_SKILLS_EXCLUIDAS = "stack_skills_excluidas"


def skills_excluidas(rules: dict | None, stack_id: str) -> set[str]:
    """Skills del stack que el proyecto retiro a proposito.

    `rules.stack_skills_excluidas` en harness/feature_list.json:
    `{"<stack-id>": ["<skill>", ...]}`. Sin esto, la normalizacion reinstalaba en
    cada arranque de sesion las skills que el usuario habia quitado porque no
    aplican al proyecto. Un valor que no se entiende no apaga la regla: falla.
    """
    valor = (rules or {}).get(REGLA_SKILLS_EXCLUIDAS)
    if valor is None:
        return set()
    forma = f'rules.{REGLA_SKILLS_EXCLUIDAS} debe ser {{"<stack-id>": ["<skill>", ...]}}'
    if not isinstance(valor, dict):
        raise ValueError(f"{forma}; se encontro {type(valor).__name__}")
    for clave, lista in valor.items():
        if not isinstance(lista, list) or not all(isinstance(x, str) and x for x in lista):
            raise ValueError(f"{forma}; la entrada '{clave}' no es una lista de nombres")
    return set(valor.get(stack_id, []))


def rules_del_proyecto(*inicios: Path) -> dict:
    """`rules` del primer harness/feature_list.json que contenga a alguno de los inicios."""
    for inicio in inicios:
        inicio = inicio.resolve()
        for carpeta in (inicio, *inicio.parents):
            backlog = carpeta / "harness" / "feature_list.json"
            if not backlog.is_file():
                continue
            try:
                data = json.loads(backlog.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ValueError(f"{backlog} ilegible: {exc}")
            rules = data.get("rules") if isinstance(data, dict) else None
            return rules if isinstance(rules, dict) else {}
    return {}


def verificar_cumplimiento(repo: Path, stack_id: str | None = None,
                          rules: dict | None = None) -> dict[str, Any]:
    """Evalúa cumplimiento con el estándar de rules, skills, arquitectura y testing.

    `rules` son las reglas del proyecto; sin ellas se leen del arnes que contiene al repo.
    """
    repo = repo.resolve()
    if not stack_id:
        det = detectar_stack_directorio(repo)
        stack_id = det["stack"]

    if stack_id == "generico":
        return {
            "compliant": True,
            "stack": "generico",
            "repo": str(repo),
            "findings": ["No se identifico stack CALPIL especifico para este repositorio."],
            "rules_ok": True,
            "skills_ok": True,
            "architecture_ok": True,
        }

    manifest = cargar_manifest(stack_id)
    findings: list[str] = []
    warnings: list[str] = []

    # A. Chequeo de Rules Multi-LLM (.claude/rules/, .agents/rules/, .gemini/rules/ y AGENTS.md)
    rules_claude = repo / ".claude" / "rules"
    rules_agents = repo / ".agents" / "rules"
    rules_gemini = repo / ".gemini" / "rules"
    expected_rules = manifest.get("normative", {}).get("rules", [])
    missing_rules = []
    for r in expected_rules:
        if not ((rules_claude / r).exists() or (rules_agents / r).exists() or (rules_gemini / r).exists()):
            missing_rules.append(r)

    agents_md = repo / "AGENTS.md"
    has_agents_md = agents_md.exists()

    if missing_rules:
        findings.append(f"Reglas modulares faltantes en (.claude/rules/ o .agents/rules/): {', '.join(missing_rules)}")
    if not has_agents_md:
        warnings.append("Falta AGENTS.md en la raiz del microservicio/repo (recomendado para LLMs no-Claude: Codex, Gemini, Grok, Kimi)")

    # B. Chequeo de Skills (.claude/skills/ o .agents/skills/)
    skills_claude = repo / ".claude" / "skills"
    skills_agents = repo / ".agents" / "skills"
    excluidas = skills_excluidas(rules_del_proyecto(repo) if rules is None else rules, stack_id)
    normativas = manifest.get("normative", {}).get("skills", [])
    expected_skills = [s for s in normativas if s not in excluidas]
    missing_skills = []

    conocidas = set(normativas) | _skills_del_stack(stack_id)
    for nombre in sorted(excluidas - conocidas):
        warnings.append(f"rules.{REGLA_SKILLS_EXCLUIDAS}: '{nombre}' no es una skill del stack {stack_id} (revisa el nombre)")

    for s in expected_skills:
        found = (skills_claude / s / "SKILL.md").exists() or (skills_agents / s / "SKILL.md").exists()
        if not found:
            missing_skills.append(s)

    if missing_skills:
        findings.append(f"Skills normativas faltantes ({len(missing_skills)}/{len(expected_skills)}): {', '.join(missing_skills[:5])}{'...' if len(missing_skills) > 5 else ''}")

    # C. Chequeo de Arquitectura
    arch_ok = True
    arch_errors: list[str] = []
    arch_script = STACKS_DIR / stack_id / "scripts" / "check-architecture.py"
    if arch_script.exists():
        code, out = _run_cmd([sys.executable, str(arch_script), "--repo", str(repo)])
        if code != 0:
            arch_ok = False
            for line in out.splitlines():
                if line.startswith("  - "):
                    arch_errors.append(line.strip())
                    findings.append(f"Arquitectura {stack_id}: {line.strip()}")

    # D. Multi-LLM Readiness y Paridad
    has_claude_rules = all((rules_claude / r).exists() for r in expected_rules) if expected_rules else True
    has_agents_rules = all((rules_agents / r).exists() for r in expected_rules) if expected_rules else True
    has_gemini_rules = all((rules_gemini / r).exists() for r in expected_rules) if expected_rules else True

    has_claude_skills = all((skills_claude / s / "SKILL.md").exists() for s in expected_skills) if expected_skills else True
    has_agents_skills = all((skills_agents / s / "SKILL.md").exists() for s in expected_skills) if expected_skills else True

    full_multi_llm_parity = (
        has_claude_rules and has_agents_rules and has_gemini_rules
        and has_claude_skills and has_agents_skills
        and has_agents_md
    )

    hosts_active: list[str] = []
    if has_claude_rules and has_claude_skills:
        hosts_active.append("claude-code")
    if has_agents_rules and has_agents_skills:
        hosts_active.append("openai-codex/hermes/grok/kimi")
    if has_gemini_rules and (has_agents_skills or has_claude_skills):
        hosts_active.append("gemini-cli/agy")

    multi_llm_ready = (not missing_rules) and (len(missing_skills) == 0) and has_agents_md

    compliant = (len(findings) == 0)

    return {
        "compliant": compliant,
        "stack": stack_id,
        "repo": str(repo),
        "rules_ok": len(missing_rules) == 0,
        "missing_rules": missing_rules,
        "skills_ok": len(missing_skills) == 0,
        "missing_skills": missing_skills,
        "skills_excluidas": sorted(excluidas),
        "architecture_ok": arch_ok,
        "architecture_errors": arch_errors,
        "multi_llm_ready": multi_llm_ready,
        "full_multi_llm_parity": full_multi_llm_parity,
        "hosts_active": hosts_active,
        "findings": findings,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# 3. Normalización Multi-LLM
# ---------------------------------------------------------------------------

def _skills_del_stack(stack_id: str) -> set[str]:
    origen = STACKS_DIR / stack_id / "skills"
    if not origen.is_dir():
        return set()
    return {d.name for d in origen.iterdir() if (d / "SKILL.md").is_file()}


def normalizar_repositorio(repo: Path, stack_id: str | None = None, dry_run: bool = False,
                           rules: dict | None = None) -> dict[str, Any]:
    """Aplica la normativa de CALPIL (copia rules, skills, AGENTS.md, checkers) al repo.

    Solo agrega lo que falta. No instala las skills de `rules.stack_skills_excluidas`
    ni reemplaza un AGENTS.md que ya existe: ambos son decisiones del usuario.
    """
    repo = repo.resolve()
    if not stack_id:
        det = detectar_stack_directorio(repo)
        stack_id = det["stack"]

    if stack_id == "generico":
        return {"status": "skipped", "message": "Repo generico; no aplica stack especifico."}

    manifest = cargar_manifest(stack_id)
    stack_source_dir = STACKS_DIR / stack_id
    actions_taken: list[str] = []
    avisos: list[str] = []
    # Antes de escribir nada: una regla que no se entiende no deja el repo a medio instalar.
    excluidas = skills_excluidas(rules_del_proyecto(repo) if rules is None else rules, stack_id)

    # 1. Instalar Rules Multi-LLM (.claude/rules/, .agents/rules/, .gemini/rules/)
    target_claude_rules = repo / ".claude" / "rules"
    target_agents_rules = repo / ".agents" / "rules"
    target_gemini_rules = repo / ".gemini" / "rules"
    source_rules_dir = stack_source_dir / "rules"
    if source_rules_dir.exists():
        if not dry_run:
            target_claude_rules.mkdir(parents=True, exist_ok=True)
            target_agents_rules.mkdir(parents=True, exist_ok=True)
            target_gemini_rules.mkdir(parents=True, exist_ok=True)
        for r_file in source_rules_dir.glob("*.md"):
            # A. Instalar en .claude/rules (Claude Code)
            dest_claude = target_claude_rules / r_file.name
            if not dest_claude.exists():
                if not dry_run:
                    shutil.copy2(r_file, dest_claude)
                actions_taken.append(f"Instalada regla: .claude/rules/{r_file.name}")
            # B. Instalar en .agents/rules (OpenAI Codex, Grok, Kimi, Hermes)
            dest_agents = target_agents_rules / r_file.name
            if not dest_agents.exists():
                if not dry_run:
                    shutil.copy2(r_file, dest_agents)
                actions_taken.append(f"Instalada regla compartida: .agents/rules/{r_file.name}")
            # C. Instalar en .gemini/rules (Gemini CLI, Antigravity AGY)
            dest_gemini = target_gemini_rules / r_file.name
            if not dest_gemini.exists():
                if not dry_run:
                    shutil.copy2(r_file, dest_gemini)
                actions_taken.append(f"Instalada regla Gemini/AGY: .gemini/rules/{r_file.name}")

    # 2. Instalar Skills tanto en .claude/skills/ como en .agents/skills/ (para Hermes, Codex, Gemini)
    target_claude_skills = repo / ".claude" / "skills"
    target_shared_skills = repo / ".agents" / "skills"
    source_skills_dir = stack_source_dir / "skills"

    if source_skills_dir.exists():
        if not dry_run:
            target_claude_skills.mkdir(parents=True, exist_ok=True)
            target_shared_skills.mkdir(parents=True, exist_ok=True)
        for skill_dir in source_skills_dir.iterdir():
            if skill_dir.name in excluidas:
                continue
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                dest_claude = target_claude_skills / skill_dir.name
                dest_shared = target_shared_skills / skill_dir.name
                if not dest_claude.exists():
                    if not dry_run:
                        shutil.copytree(skill_dir, dest_claude)
                    actions_taken.append(f"Instalada skill: .claude/skills/{skill_dir.name}")
                if not dest_shared.exists():
                    if not dry_run:
                        shutil.copytree(skill_dir, dest_shared)
                    actions_taken.append(f"Instalada skill compartida: .agents/skills/{skill_dir.name}")

    # 3. Generar / Sincronizar AGENTS.md (contrato multi-LLM)
    agents_md = repo / "AGENTS.md"
    if not agents_md.exists():
        agents_content = _generar_agents_md(stack_id, manifest)
        if not dry_run:
            agents_md.write_text(agents_content, encoding="utf-8")
        actions_taken.append("Generado contrato multi-LLM en AGENTS.md")
    elif "CALPIL" not in agents_md.read_text(encoding="utf-8", errors="ignore"):
        # Antes se reemplazaba entero por la plantilla del stack: el AGENTS.md del
        # proyecto se perdia. Un archivo que ya existe es del usuario.
        avisos.append("AGENTS.md ya existe y no se reemplaza: el contrato del stack queda en las rules instaladas")

    # 4. Instalar scripts de verificación si existen en el stack
    scripts_dir = repo / "scripts"
    stack_scripts_dir = stack_source_dir / "scripts"
    if stack_scripts_dir.exists():
        if not dry_run:
            scripts_dir.mkdir(parents=True, exist_ok=True)
        for s_file in stack_scripts_dir.glob("*"):
            if s_file.is_file():
                dest_file = scripts_dir / s_file.name
                if not dest_file.exists():
                    if not dry_run:
                        shutil.copy2(s_file, dest_file)
                        if s_file.suffix in (".py", ".sh", ".mjs"):
                            dest_file.chmod(0o755)
                    actions_taken.append(f"Instalado validador: scripts/{s_file.name}")

    return {
        "status": "normalized",
        "stack": stack_id,
        "repo": str(repo),
        "actions": actions_taken,
        "warnings": avisos,
        "skills_excluidas": sorted(excluidas),
        "dry_run": dry_run,
    }


def _leer_cuerpo_sin_frontmatter(p: Path) -> str:
    """Lee un archivo markdown descartando el encabezado YAML frontmatter si existe."""
    if not p.exists():
        return ""
    txt = p.read_text(encoding="utf-8")
    if txt.startswith("---"):
        partes = txt.split("---", 2)
        if len(partes) >= 3:
            return partes[2].strip()
    return txt.strip()


def _generar_agents_md(stack_id: str, manifest: dict[str, Any]) -> str:
    """Genera AGENTS.md unificado para interoperabilidad en todos los LLMs."""
    name = manifest.get("name", stack_id)
    desc = manifest.get("description", "")
    rules = manifest.get("normative", {}).get("rules", [])
    skills = manifest.get("normative", {}).get("skills", [])
    constraints = manifest.get("normative", {}).get("architecture_constraints", {})

    lines = [
        f"# AGENTS.md — Contrato Operativo y Normativo ({name})",
        "",
        f"> **Stack Tecnológico:** `{stack_id}`  ",
        f"> **Descripción:** {desc}  ",
        "> **Modo de Operación:** Pair Interactivo activado por defecto para implementación y refactorización.",
        "",
        "## 1. Normas de Arquitectura Obligatorias",
        "",
    ]

    for k, v in constraints.items():
        if isinstance(v, dict):
            lines.append(f"### {k.replace('_', ' ').capitalize()}")
            for sub_k, sub_v in v.items():
                lines.append(f"- **{sub_k}:** `{sub_v}`")
            lines.append("")
        else:
            lines.append(f"- **{k.replace('_', ' ').capitalize()}:** {v}")
    lines.append("")

    arch_file = STACKS_DIR / stack_id / "rules" / "architecture.md"
    arch_body = _leer_cuerpo_sin_frontmatter(arch_file)
    if arch_body:
        lines.append("### Límites de Arquitectura Detallados")
        lines.append("")
        lines.append(arch_body)
        lines.append("")

    lines.extend([
        "## 2. Reglas Modulares Activas (Multi-LLM)",
        "",
        "Todo agente de IA (Claude Code, OpenAI/Codex, Gemini/AGY, Grok, Kimi, Hermes) debe respetar las reglas modulares sincronizadas en `.agents/rules/`, `.claude/rules/` y `.gemini/rules/`:",
    ])
    for r in rules:
        lines.append(f"- `{r}` (rutas: `.agents/rules/{r}`, `.claude/rules/{r}`, `.gemini/rules/{r}`)")
    lines.append("")

    lines.extend([
        "## 3. Skills y Runbooks Disponibles",
        "",
        "Disponibles en `.agents/skills/` y `.claude/skills/`:",
    ])
    for s in skills:
        lines.append(f"- `{s}`")
    lines.append("")

    doc_cfg = manifest.get("documentation", {})
    sec_cfg = manifest.get("security_audit", {})
    context7_cfg = doc_cfg.get("context7", {})

    lines.extend([
        "## 4. Modo Pair Interactivo y Preguntas de Formulario",
        "",
        "- **Modo Pair Interactivo:** Al aplicar skills o implementar features, la IA actúa como Driver y el humano como Navigator.",
        "- **Preguntas de Formulario:** La IA debe consultar al humano mediante formulario/pregunta interactiva **SOLO** ante decisiones de arquitectura no previstas, breaking changes o tras 2 intentos fallidos en TDD.",
        "",
        "## 5. Actualización Continua: Context7 y Documentación Oficial",
        "",
        f"- **Context7 MCP:** Al implementar APIs o agregar librerías, utiliza Context7 (`https://mcp.context7.com/mcp` o prompt `'use context7'`) con library `{context7_cfg.get('library_id', stack_id)}`.",
        f"- **Documentación Oficial:** Consulta siempre fuentes oficiales actualizadas en {doc_cfg.get('official_docs', 'sitio oficial del stack')}.",
        f"- **Auditoría de Seguridad:** Prohibido introducir paquetes con vulnerabilidades conocidas (CVEs críticas/altas). Ejecutar `{sec_cfg.get('command', 'auditoría de paquetes')}`.",
        "",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. Auditoría de Versiones y Seguridad (Context7 & Oficial)
# ---------------------------------------------------------------------------

def auditar_seguridad_y_versiones(
    repo: Path,
    stack_id: str | None = None,
    dast: bool = False,
    openapi_path: str | None = None,
    target_url: str | None = None
) -> dict[str, Any]:
    """Audita versiones del stack, dependencias y ejecuta escáner de seguridad si está disponible."""
    repo = repo.resolve()
    if not stack_id:
        det = detectar_stack_directorio(repo)
        stack_id = det["stack"]

    if stack_id == "generico":
        return {"status": "skipped", "message": "Repo genérico sin stack CALPIL identificado"}

    manifest = cargar_manifest(stack_id)
    doc_cfg = manifest.get("documentation", {})
    sec_cfg = manifest.get("security_audit", {})
    context7_cfg = doc_cfg.get("context7", {})

    audit_cmd = sec_cfg.get("command")
    min_version = sec_cfg.get("minimum_version")
    findings = []
    warnings = []
    audit_output = ""

    # 1. Comprobar escáner de seguridad si existe comando
    if audit_cmd:
        tool_name = audit_cmd.split()[0]
        if shutil.which(tool_name):
            code, out = _run_cmd(audit_cmd.split(), cwd=repo)
            audit_output = out
            if code != 0:
                warnings.append(f"Escáner de seguridad detectó posibles avisos ({tool_name})")
        else:
            warnings.append(f"Herramienta de auditoría '{tool_name}' no instalada en el PATH.")

    # 2. Comprobar versión mínima declarada
    if min_version:
        if stack_id == "golang-hexagonal" and (repo / "go.mod").exists():
            mod_text = (repo / "go.mod").read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"^go\s+([0-9.]+)", mod_text, re.MULTILINE)
            if m:
                detected_ver = m.group(1)
                min_prefix = ".".join(min_version.split(".")[:2])
                if detected_ver < min_prefix:
                    warnings.append(f"Versión de Go en go.mod ({detected_ver}) es inferior a la mínima recomendada ({min_version})")
        elif stack_id == "dotnet-hexagonal":
            for csproj in repo.glob("**/*.csproj"):
                text = csproj.read_text(encoding="utf-8", errors="ignore")
                m = re.search(r"<TargetFramework>net([0-9.]+)</TargetFramework>", text)
                if m:
                    detected_ver = m.group(1)
                    det_parts = tuple(int(x) for x in re.findall(r"\d+", detected_ver))
                    min_parts = tuple(int(x) for x in re.findall(r"\d+", min_version))
                    if det_parts < min_parts:
                        warnings.append(f"Versión de .NET en {csproj.name} (net{detected_ver}) es inferior a la mínima recomendada (net{min_version})")
                    break
        elif stack_id == "rust-hexagonal":
            cargo_files = [p for p in repo.glob("**/Cargo.toml") if "target" not in p.parts]
            for cargo_toml in cargo_files:
                text = cargo_toml.read_text(encoding="utf-8", errors="ignore")
                m = re.search(r'edition\s*=\s*["\']([0-9]+)["\']', text)
                if m:
                    detected_edition = m.group(1)
                    if int(detected_edition) < int(min_version):
                        warnings.append(f"Edición de Rust en {cargo_toml.relative_to(repo)} ({detected_edition}) es inferior a la mínima recomendada ({min_version})")
                    break
        elif stack_id == "ios-swiftui-clean":
            pkg_file = repo / "Package.swift"
            if pkg_file.exists():
                txt = pkg_file.read_text(encoding="utf-8", errors="ignore")
                m = re.search(r"swift-tools-version:\s*([0-9.]+)", txt)
                if m:
                    det_ver = m.group(1)
                    det_parts = tuple(int(x) for x in re.findall(r"\d+", det_ver))
                    min_parts = tuple(int(x) for x in re.findall(r"\d+", min_version))
                    if det_parts < min_parts:
                        warnings.append(f"Versión de Swift en Package.swift ({det_ver}) es inferior a la mínima recomendada ({min_version})")
        elif stack_id == "android-compose-clean":
            versions_file = repo / "gradle" / "libs.versions.toml"
            if versions_file.exists():
                txt = versions_file.read_text(encoding="utf-8", errors="ignore")
                m = re.search(r'kotlin\s*=\s*["\']([0-9.]+)["\']', txt)
                if m:
                    det_ver = m.group(1)
                    det_parts = tuple(int(x) for x in re.findall(r"\d+", det_ver))
                    min_parts = tuple(int(x) for x in re.findall(r"\d+", min_version))
                    if det_parts < min_parts:
                        warnings.append(f"Versión de Kotlin en libs.versions.toml ({det_ver}) es inferior a la mínima recomendada ({min_version})")

    # 3. Escaneo dinámico DAST (OWASP ZAP) si fue solicitado
    dast_info = None
    if dast:
        dast_tool = "OWASP ZAP (zaproxy/zap-stable)"
        has_docker = False
        if shutil.which("docker"):
            code_d, _ = _run_cmd(["docker", "info"], timeout=2)
            has_docker = (code_d == 0)

        # Determinar contrato OpenAPI o target
        found_openapi = None
        if openapi_path:
            p_api = (repo / openapi_path).resolve() if not Path(openapi_path).is_absolute() else Path(openapi_path)
            if p_api.exists():
                found_openapi = p_api
        else:
            candidates = [
                "openapi.json", "openapi.yaml", "openapi.yml",
                "swagger.json", "swagger.yaml", "swagger.yml",
                "docs/openapi.json", "docs/openapi.yaml",
                "api/openapi.json", "api/openapi.yaml"
            ]
            for c in candidates:
                cand_path = repo / c
                if cand_path.exists():
                    found_openapi = cand_path
                    break

        target = target_url or "http://localhost:8080"
        dast_output = ""
        dast_status = "pending"
        dast_mode = "openapi" if found_openapi else "baseline"
        dast_cmd_str = ""

        if has_docker:
            if found_openapi:
                rel_api = found_openapi.relative_to(repo) if found_openapi.is_relative_to(repo) else found_openapi.name
                docker_cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{repo}:/zap/wrk/:rw",
                    "-t", "zaproxy/zap-stable",
                    "zap-api-scan.py",
                    "-t", f"/zap/wrk/{rel_api}",
                    "-f", "openapi",
                    "-I"
                ]
                dast_cmd_str = " ".join(docker_cmd)
                code, out = _run_cmd(docker_cmd, cwd=repo)
                dast_output = out
                dast_status = "passed" if code == 0 else "warnings"
                if code != 0:
                    warnings.append(f"OWASP ZAP DAST detectó posibles advertencias en contrato {rel_api}")
            else:
                docker_cmd = [
                    "docker", "run", "--rm",
                    "-t", "zaproxy/zap-stable",
                    "zap-baseline.py",
                    "-t", target,
                    "-I"
                ]
                dast_cmd_str = " ".join(docker_cmd)
                code, out = _run_cmd(docker_cmd, cwd=repo)
                dast_output = out
                dast_status = "passed" if code == 0 else "warnings"
                if code != 0:
                    warnings.append(f"OWASP ZAP DAST detectó posibles alertas en {target}")
        else:
            dast_status = "skipped"
            suggested_cmd = (
                f"docker run --rm -v {repo}:/zap/wrk/:rw -t zaproxy/zap-stable zap-api-scan.py -t /zap/wrk/{found_openapi.name} -f openapi -I"
                if found_openapi else
                f"docker run --rm -t zaproxy/zap-stable zap-baseline.py -t {target} -I"
            )
            dast_cmd_str = suggested_cmd
            warnings.append("Docker no disponible para ejecutar OWASP ZAP DAST en local. Se sugiere ejecutar en pipeline.")

        dast_info = {
            "enabled": True,
            "tool": dast_tool,
            "mode": dast_mode,
            "status": dast_status,
            "target": target if not found_openapi else str(found_openapi),
            "command": dast_cmd_str,
            "output": dast_output,
        }

    return {
        "stack": stack_id,
        "repo": str(repo),
        "official_docs": doc_cfg.get("official_docs"),
        "security_advisories": doc_cfg.get("security_advisories"),
        "context7_library": context7_cfg.get("library_id"),
        "context7_queries": context7_cfg.get("suggested_queries", []),
        "audit_command": audit_cmd,
        "minimum_version": min_version,
        "findings": findings,
        "warnings": warnings,
        "audit_output": audit_output,
        "dast": dast_info,
    }


# ---------------------------------------------------------------------------
# 4. Refactorización y Scaffolding
# ---------------------------------------------------------------------------

def generar_plan_refactor(repo: Path, stack_id: str | None = None) -> dict[str, Any]:
    """Genera un plan de refactorizacion paso a paso si el repo no cumple la normativa."""
    repo = repo.resolve()
    diag = verificar_cumplimiento(repo, stack_id)
    stack_id = diag["stack"]

    if diag["compliant"]:
        return {
            "needed": False,
            "message": "El repositorio ya cumple con la normativa arquitectonica.",
            "steps": [],
        }

    steps = []
    if stack_id == "golang-hexagonal":
        # Revisar composition root
        if not (repo / "cmd" / "server" / "main.go").exists():
            steps.append({
                "step": 1,
                "title": "Crear Composition Root canónico",
                "action": "scaffold",
                "target": "cmd/server/main.go",
                "description": "Centralizar el arranque del servidor HTTP, cableado de adaptadores e inyección de dependencias en cmd/server/main.go."
            })

        # Revisar capas hexagonales
        has_internal = (repo / "internal").exists()
        if not has_internal:
            steps.append({
                "step": 2,
                "title": "Migrar lógica de negocio a internal/ con separación hexagonal",
                "action": "reorganize",
                "target": "internal/<modulo>/(domain|application|adapter)",
                "description": "Aislar entidades de negocio en domain (Go puro), casos de uso y puertos en application, y transporte/persistencia en adapter."
            })

        for err in diag.get("architecture_errors", []):
            if "domain no permite dependencia" in err:
                steps.append({
                    "step": len(steps) + 1,
                    "title": f"Desacoplar dependencias impuras en capa domain",
                    "action": "refactor_domain",
                    "target": err.split(":")[0],
                    "description": f"Extraer transporte/SQL a adaptadores e interfaces de puertos: {err}"
                })
            elif "application no debe importar adapters" in err:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "Invertir dependencia en application mediante puertos (DIP)",
                    "action": "invert_dependency",
                    "target": err.split(":")[0],
                    "description": f"Application debe definir interfaces (ports/out.go) en lugar de importar implementaciones concretas: {err}"
                })
            elif "time.Sleep" in err:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "Eliminar time.Sleep arbitrario en tests",
                    "action": "fix_test_determinism",
                    "target": err.split(":")[0],
                    "description": "Reemplazar sleeps con channels, sincronización o Fake Clock determinista."
                })

    elif stack_id == "angular-product":
        if not (repo / "src" / "app" / "app.routes.ts").exists():
            steps.append({
                "step": 1,
                "title": "Configurar Composition Root de rutas",
                "action": "scaffold",
                "target": "src/app/app.routes.ts",
                "description": "Crear app.routes.ts con carga perezosa (loadChildren / loadComponent)."
            })

        for err in diag.get("architecture_errors", []):
            if "domain no permite dependencia" in err:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "Aislar modelo de dominio de frameworks",
                    "action": "refactor_domain",
                    "target": err.split(":")[0],
                    "description": f"Dominio debe ser TypeScript puro; desacoplar de Angular/RxJS/UI: {err}"
                })
            elif "application ->" in err or "ui -> data-access" in err:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "Restablecer límites de capas (Layer Boundaries)",
                    "action": "enforce_boundaries",
                    "target": err.split(":")[0],
                    "description": f"Corregir import prohibido entre capas: {err}"
                })

    elif stack_id == "dotnet-hexagonal":
        program_files = [p for p in repo.glob("**/Program.cs") if "obj" not in p.parts and "bin" not in p.parts]
        if not program_files:
            steps.append({
                "step": 1,
                "title": "Crear Composition Root canónico (Program.cs)",
                "action": "scaffold",
                "target": "src/WebApi/Program.cs",
                "description": "Centralizar arranque de ASP.NET Core, middlewares RFC 7807, CORS e inyección de dependencias en Program.cs."
            })
        has_domain = any("domain" in p.name.lower() for p in repo.glob("src/*")) or any("domain" in p.name.lower() for p in repo.glob("*"))
        if not has_domain:
            steps.append({
                "step": 2,
                "title": "Separar solución en proyectos hexagonales (.Domain, .Application, .Infrastructure, .WebApi)",
                "action": "reorganize",
                "target": "src/(Domain|Application|Infrastructure|WebApi)",
                "description": "Aislar entidades en Domain (C# puro), use cases en Application, Dapper en Infrastructure y controllers en WebApi."
            })
        for err in diag.get("architecture_errors", []):
            if "Domain no permite dependencia" in err or "no debe referenciar" in err:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "Desacoplar dependencias impuras en proyecto Domain",
                    "action": "refactor_domain",
                    "target": err.split(":")[0],
                    "description": f"Extraer transporte/SQL a adaptadores e interfaces de puertos: {err}"
                })
            elif "Application no debe importar" in err:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "Invertir dependencia en Application mediante puertos (DIP)",
                    "action": "invert_dependency",
                    "target": err.split(":")[0],
                    "description": f"Application debe depender de interfaces (Ports/I...Repository.cs) en lugar de implementaciones concretas: {err}"
                })
            elif "Thread.Sleep" in err:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "Eliminar Thread.Sleep arbitrario en pruebas",
                    "action": "fix_test_determinism",
                    "target": err.split(":")[0],
                    "description": "Reemplazar Thread.Sleep con FakeClock o sincronización asíncrona determinista."
                })

    elif stack_id == "rust-hexagonal":
        main_files = [p for p in repo.glob("**/main.rs") if "target" not in p.parts and ".git" not in p.parts]
        if not main_files:
            steps.append({
                "step": 1,
                "title": "Crear Composition Root canónico (src/main.rs o crates/api/src/main.rs)",
                "action": "scaffold",
                "target": "src/main.rs",
                "description": "Centralizar arranque del runtime Tokio, router Axum, middlewares RFC 7807 e inyección de adaptadores."
            })
        has_domain = any("domain" in p.name.lower() for p in repo.glob("crates/*")) or any("domain" in p.name.lower() for p in repo.glob("src/*")) or any("domain" in p.name.lower() for p in repo.glob("*"))
        if not has_domain:
            steps.append({
                "step": 2,
                "title": "Separar capas hexagonales (domain, application, infrastructure, api)",
                "action": "reorganize",
                "target": "src/(domain|application|infrastructure) o crates/*",
                "description": "Aislar entidades en Domain (Rust puro), use cases y puertos en Application, SQLx en Infrastructure y handlers en API."
            })
        for err in diag.get("architecture_errors", []):
            if "Domain no permite dependencia" in err or "Domain no debe" in err:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "Desacoplar dependencias impuras en capa Domain",
                    "action": "refactor_domain",
                    "target": err.split(":")[0],
                    "description": f"Extraer transporte HTTP (Axum) o base de datos (SQLx) a adaptadores de infraestructura: {err}"
                })
            elif "Application no debe" in err:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "Invertir dependencia en Application mediante traits (DIP)",
                    "action": "invert_dependency",
                    "target": err.split(":")[0],
                    "description": f"Application debe depender de traits (out_ports) y no de adaptadores concretos de infraestructura: {err}"
                })
            elif "Infrastructure no debe acoplarse a transporte" in err:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "Desacoplar transporte HTTP de Infrastructure",
                    "action": "isolate_transport",
                    "target": err.split(":")[0],
                    "description": f"Mover handlers y tipos de transporte HTTP a la capa API: {err}"
                })
            elif "sleep" in err.lower():
                steps.append({
                    "step": len(steps) + 1,
                    "title": "Eliminar llamadas a sleep arbitrario en pruebas",
                    "action": "fix_test_determinism",
                    "target": err.split(":")[0],
                    "description": "Reemplazar thread::sleep o tokio::time::sleep en tests con mock clock o sincronización determinista."
                })

    elif stack_id == "ios-swiftui-clean":
        has_app = any("app.swift" in p.name.lower() for p in repo.glob("**/*.swift"))
        if not has_app:
            steps.append({
                "step": 1,
                "title": "Crear Composition Root canónico (CalpilApp.swift)",
                "action": "scaffold",
                "target": "Sources/CalpilApp/CalpilApp.swift",
                "description": "Centralizar el punto de entrada de la aplicación, cableado de adaptadores e inyección de dependencias en CalpilApp.swift."
            })
        has_domain = any("calpildomain" in p.name.lower() or "domain" in p.name.lower() for p in repo.glob("Sources/*")) or any("domain" in p.name.lower() for p in repo.glob("*"))
        if not has_domain:
            steps.append({
                "step": 2,
                "title": "Separar targets modulares (CalpilDomain, CalpilData, CalpilUI, CalpilApp)",
                "action": "reorganize",
                "target": "Sources/(CalpilDomain|CalpilData|CalpilUI|CalpilApp)",
                "description": "Aislar entidades en CalpilDomain (Swift puro), adaptadores en CalpilData y vistas en CalpilUI."
            })
        for err in diag.get("architecture_errors", []):
            if "Domain no debe" in err or "dependencia externa" in err:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "Desacoplar dependencias impuras en capa Domain",
                    "action": "refactor_domain",
                    "target": err.split(":")[0],
                    "description": f"Extraer frameworks visuales (SwiftUI/UIKit) o persistencia a adaptadores externos: {err}"
                })
            elif "UI no debe importar" in err:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "Invertir dependencia en UI consumiendo protocolos de Domain",
                    "action": "invert_dependency",
                    "target": err.split(":")[0],
                    "description": f"CalpilUI debe depender de protocolos de CalpilDomain y no directamente de adaptadores de CalpilData: {err}"
                })

    elif stack_id == "android-compose-clean":
        has_app = any("application.kt" in p.name.lower() for p in repo.glob("**/*.kt")) or any("mainactivity.kt" in p.name.lower() for p in repo.glob("**/*.kt"))
        if not has_app:
            steps.append({
                "step": 1,
                "title": "Crear Composition Root canónico (CalpilApplication.kt)",
                "action": "scaffold",
                "target": "app/src/main/java/com/calpil/template/CalpilApplication.kt",
                "description": "Centralizar la inicialización de la aplicación e inyección de dependencias en CalpilApplication.kt."
            })
        has_domain = any("domain" in p.parts for p in repo.glob("app/src/main/**"))
        if not has_domain:
            steps.append({
                "step": 2,
                "title": "Organizar paquetes según Clean Architecture (domain, data, presentation, core)",
                "action": "reorganize",
                "target": "app/src/main/java/.../(domain|data|presentation)",
                "description": "Aislar entidades en domain (Kotlin puro), DTOs y repositorios en data, y pantallas en presentation."
            })
        for err in diag.get("architecture_errors", []):
            if "Domain no debe" in err:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "Desacoplar dependencias de Android framework en Domain",
                    "action": "refactor_domain",
                    "target": err.split(":")[0],
                    "description": f"El módulo domain debe ser Kotlin puro sin dependencias de Android SDK: {err}"
                })
            elif "Presentation no debe importar" in err:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "Invertir dependencia consumiendo casos de uso de Domain",
                    "action": "invert_dependency",
                    "target": err.split(":")[0],
                    "description": f"Presentation debe consumir casos de uso y modelos de Domain, sin acceder a DTOs ni DAOs directamente: {err}"
                })

    return {
        "needed": True,
        "stack": stack_id,
        "repo": str(repo),
        "steps": steps,
        "recommendation": "Ejecutar refactorizacion mediante Vertical Slices usando el Modo Pair interactivo."
    }


def ejecutar_scaffolding(repo: Path, stack_id: str | None = None) -> list[str]:
    """Crea la estructura de carpetas y archivos base requeridos si faltan."""
    repo = repo.resolve()
    if not stack_id:
        det = detectar_stack_directorio(repo)
        stack_id = det["stack"]

    creados = []
    if stack_id == "golang-hexagonal":
        carpetas = [
            repo / "cmd" / "server",
            repo / "internal" / "platform" / "config",
            repo / "internal" / "platform" / "middleware",
            repo / "internal" / "platform" / "health",
        ]
        for c in carpetas:
            if not c.exists():
                c.mkdir(parents=True, exist_ok=True)
                creados.append(str(c.relative_to(repo)))

        main_go = repo / "cmd" / "server" / "main.go"
        if not main_go.exists():
            main_go.write_text("""package main

import (
\t"context"
\t"log/slog"
\t"net/http"
\t"os"
\t"os/signal"
\t"syscall"
\t"time"
)

func main() {
\tlogger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
\tslog.SetDefault(logger)

\tslog.Info("iniciando servidor", "stack", "calpil-golang-hexagonal")

\tmux := http.NewServeMux()
\tmux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
\t\tw.WriteHeader(http.StatusOK)
\t\t_, _ = w.Write([]byte(`{"status":"ok"}`))
\t})

\tsrv := &http.Server{
\t\tAddr:         ":8080",
\t\tHandler:      mux,
\t\tReadTimeout:  5 * time.Second,
\t\tWriteTimeout: 10 * time.Second,
\t}

\tctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
\tdefer stop()

\tgo func() {
\t\tif err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
\t\t\tslog.Error("error en servidor", "error", err)
\t\t\tos.Exit(1)
\t\t}
\t}()

\t<-ctx.Done()
\tslog.Info("deteniendo servidor...")
}
""", encoding="utf-8")
            creados.append(str(main_go.relative_to(repo)))

    elif stack_id == "angular-product":
        carpetas = [
            repo / "src" / "app" / "core",
            repo / "src" / "app" / "shared",
            repo / "src" / "app" / "features",
        ]
        for c in carpetas:
            if not c.exists():
                c.mkdir(parents=True, exist_ok=True)
                creados.append(str(c.relative_to(repo)))

    elif stack_id == "dotnet-hexagonal":
        carpetas = [
            repo / "src" / "Domain",
            repo / "src" / "Application",
            repo / "src" / "Infrastructure",
            repo / "src" / "WebApi",
            repo / "tests" / "Domain.Tests",
            repo / "tests" / "Application.Tests",
            repo / "tests" / "WebApi.Tests",
        ]
        for c in carpetas:
            if not c.exists():
                c.mkdir(parents=True, exist_ok=True)
                creados.append(str(c.relative_to(repo)))

        program_cs = repo / "src" / "WebApi" / "Program.cs"
        existing_program = [p for p in repo.glob("**/Program.cs") if "obj" not in p.parts and "bin" not in p.parts]
        if not program_cs.exists() and not existing_program:
            program_cs.write_text("""var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();

var app = builder.Build();

app.Use(async (context, next) =>
{
    context.Response.Headers.Append("X-Content-Type-Options", "nosniff");
    context.Response.Headers.Append("X-Frame-Options", "DENY");
    context.Response.Headers.Append("X-XSS-Protection", "1; mode=block");
    await next();
});

app.MapGet("/health", () => Results.Ok(new { status = "ok" }));
app.MapControllers();

app.Run();
""", encoding="utf-8")
            creados.append(str(program_cs.relative_to(repo)))

    elif stack_id == "rust-hexagonal":
        carpetas = [
            repo / "src" / "domain",
            repo / "src" / "application",
            repo / "src" / "infrastructure",
            repo / "tests",
        ]
        for c in carpetas:
            if not c.exists():
                c.mkdir(parents=True, exist_ok=True)
                creados.append(str(c.relative_to(repo)))

        cargo_toml = repo / "Cargo.toml"
        if not cargo_toml.exists():
            cargo_toml.write_text("""[package]
name = "calpil_rust_service"
version = "0.1.0"
edition = "2021"

[dependencies]
axum = "0.8"
tokio = { version = "1.40", features = ["full"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
tower-http = { version = "0.6", features = ["cors", "trace"] }
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }

[dev-dependencies]
tower = { version = "0.5", features = ["util"] }
http-body-util = "0.1"
""", encoding="utf-8")
            creados.append(str(cargo_toml.relative_to(repo)))

        main_rs = repo / "src" / "main.rs"
        existing_main = [p for p in repo.glob("**/main.rs") if "target" not in p.parts and ".git" not in p.parts]
        if not main_rs.exists() and not existing_main:
            main_rs.write_text("""use axum::{routing::get, Json, Router};
use serde_json::{json, Value};
use std::net::SocketAddr;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let app = Router::new()
        .route("/health", get(health_handler));

    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn health_handler() -> Json<Value> {
    Json(json!({ "status": "ok" }))
}
""", encoding="utf-8")
            creados.append(str(main_rs.relative_to(repo)))

    elif stack_id == "ios-swiftui-clean":
        carpetas = [
            repo / "Sources" / "CalpilDomain" / "Models",
            repo / "Sources" / "CalpilDomain" / "Repositories",
            repo / "Sources" / "CalpilDomain" / "UseCases",
            repo / "Sources" / "CalpilDomain" / "Errors",
            repo / "Sources" / "CalpilData" / "Repositories",
            repo / "Sources" / "CalpilData" / "Network",
            repo / "Sources" / "CalpilData" / "DTOs",
            repo / "Sources" / "CalpilUI" / "Features",
            repo / "Sources" / "CalpilUI" / "Core",
            repo / "Sources" / "CalpilApp",
            repo / "Tests" / "CalpilDomainTests",
            repo / "Tests" / "CalpilDataTests",
            repo / "Tests" / "CalpilPresentationTests",
        ]
        for c in carpetas:
            if not c.exists():
                c.mkdir(parents=True, exist_ok=True)
                creados.append(str(c.relative_to(repo)))

        package_swift = repo / "Package.swift"
        if not package_swift.exists():
            package_swift.write_text("""// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "CalpilApp",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "CalpilDomain", targets: ["CalpilDomain"]),
        .library(name: "CalpilData", targets: ["CalpilData"]),
        .library(name: "CalpilUI", targets: ["CalpilUI"]),
    ],
    targets: [
        .target(name: "CalpilDomain"),
        .target(name: "CalpilData", dependencies: ["CalpilDomain"]),
        .target(name: "CalpilUI", dependencies: ["CalpilDomain"]),
        .target(name: "CalpilApp", dependencies: ["CalpilDomain", "CalpilData", "CalpilUI"]),
        .testTarget(name: "CalpilDomainTests", dependencies: ["CalpilDomain"]),
    ]
)
""", encoding="utf-8")
            creados.append(str(package_swift.relative_to(repo)))

        app_swift = repo / "Sources" / "CalpilApp" / "CalpilApp.swift"
        if not app_swift.exists():
            app_swift.write_text("""import SwiftUI
import CalpilDomain
import CalpilData
import CalpilUI

@main
struct CalpilApp: App {
    var body: some Scene {
        WindowGroup {
            Text("CALPIL iOS SwiftUI Clean Architecture")
        }
    }
}
""", encoding="utf-8")
            creados.append(str(app_swift.relative_to(repo)))

    elif stack_id == "android-compose-clean":
        carpetas = [
            repo / "app" / "src" / "main" / "java" / "com" / "calpil" / "template" / "core" / "ui" / "theme",
            repo / "app" / "src" / "main" / "java" / "com" / "calpil" / "template" / "core" / "network",
            repo / "app" / "src" / "main" / "java" / "com" / "calpil" / "template" / "features" / "workitems" / "domain" / "model",
            repo / "app" / "src" / "main" / "java" / "com" / "calpil" / "template" / "features" / "workitems" / "domain" / "repository",
            repo / "app" / "src" / "main" / "java" / "com" / "calpil" / "template" / "features" / "workitems" / "domain" / "usecases",
            repo / "app" / "src" / "main" / "java" / "com" / "calpil" / "template" / "features" / "workitems" / "data" / "repository",
            repo / "app" / "src" / "main" / "java" / "com" / "calpil" / "template" / "features" / "workitems" / "presentation",
            repo / "app" / "src" / "test" / "java" / "com" / "calpil" / "template",
        ]
        for c in carpetas:
            if not c.exists():
                c.mkdir(parents=True, exist_ok=True)
                creados.append(str(c.relative_to(repo)))

        app_kt = repo / "app" / "src" / "main" / "java" / "com" / "calpil" / "template" / "CalpilApplication.kt"
        if not app_kt.exists():
            app_kt.write_text("""package com.calpil.template

class CalpilApplication {
    fun onCreate() {
        // Composition Root: inicialización de dependencias
    }
}
""", encoding="utf-8")
            creados.append(str(app_kt.relative_to(repo)))

    return creados


# ---------------------------------------------------------------------------
# 6. Auto-Normalización Nivel 1 y Creación de Feature #0 para Nivel 2
# ---------------------------------------------------------------------------

def auto_normalizar_y_asegurar_cumplimiento(
    repo_root: Path,
    data: dict | None = None,
    auto_normalizar_nivel_1: bool = True
) -> dict[str, Any]:
    """Auto-normaliza Nivel 1 (reglas/skills) y crea Feature #0 prioritaria para Nivel 2 (arquitectura)."""
    repo_root = repo_root.resolve()
    destinos = detectar_todos_los_destinos(repo_root)
    st_calpil = [d for d in destinos if d["stack"] != "generico"]

    resultado: dict[str, Any] = {
        "destinos": len(st_calpil),
        "nivel_1_acciones": [],
        "nivel_2_violaciones": [],
        "f0_creada": False,
        "f0_id": None,
        "bloqueos_activados": False,
    }

    if not st_calpil:
        return resultado

    p_paths = None
    try:
        from comun import paths as get_paths, load_backlog, save_backlog, now_iso, bitacora
        p_paths = get_paths(repo_root)
        if data is None and p_paths["backlog"].exists():
            data = load_backlog(p_paths)
    except Exception:
        p_paths = None

    # Las reglas del proyecto valen para todos sus repos, tambien los que viven fuera de la raiz.
    rules_proj = (data.get("rules") or {}) if isinstance(data, dict) else None

    for d in st_calpil:
        target_path = Path(d["path"])
        stack_id = d["stack"]
        try:
            diag = verificar_cumplimiento(target_path, stack_id, rules=rules_proj)
        except ValueError as exc:
            # No se instala nada con una regla que no se entiende, y se dice.
            resultado["nivel_1_acciones"].append(f"[!] {target_path.name}: {exc}. No se normaliza.")
            continue

        # -------------------------------------------------------------
        # Nivel 1: Entorno y Metadatos (.claude/rules, .agents/rules, .gemini/rules, skills, AGENTS.md)
        # -------------------------------------------------------------
        if not diag["rules_ok"] or not diag["skills_ok"] or not diag["multi_llm_ready"]:
            if auto_normalizar_nivel_1:
                norm_res = normalizar_repositorio(target_path, stack_id, dry_run=False, rules=rules_proj)
                acciones = norm_res.get("actions", norm_res.get("actions_taken", []))
                if acciones:
                    msg = f"Auto-normalizado Nivel 1 en {target_path.name} ({d['name']}): {len(acciones)} elementos instalados."
                    resultado["nivel_1_acciones"].append(msg)
                for aviso in norm_res.get("warnings", []):
                    resultado["nivel_1_acciones"].append(f"[i] {target_path.name}: {aviso}")
                # Re-verificar tras normalizar
                diag = verificar_cumplimiento(target_path, stack_id, rules=rules_proj)

        # -------------------------------------------------------------
        # Nivel 2: Código Fuente / Arquitectura (check-architecture.py)
        # -------------------------------------------------------------
        if not diag["architecture_ok"] and diag["architecture_errors"]:
            resultado["nivel_2_violaciones"].extend([
                f"{target_path.name} [{stack_id}]: {err}" for err in diag["architecture_errors"]
            ])

            # Con el trinquete adoptado (arquitectura.py) lo heredado se mide y solo baja:
            # no se crea la #0 ni se bloquea el backlog entero.
            if (data is not None and p_paths is not None
                    and not (p_paths["harness"] / "arquitectura-base.json").is_file()):
                feats = data.get("features", [])
                f0 = next((x for x in feats if str(x.get("id")) == "0"), None)

                if f0 is None:
                    manifest = cargar_manifest(stack_id)
                    test_runner = manifest.get("runners", {}).get("test", "npm test" if any(k in stack_id for k in ("angular", "nextjs", "nest")) else "go test ./...")
                    rel_checker = f"assets/stacks/{stack_id}/scripts/check-architecture.py"
                    try:
                        rel_target = str(target_path.relative_to(p_paths["root"])) if target_path != p_paths["root"] else "."
                    except Exception:
                        rel_target = "."

                    f0 = {
                        "id": 0,
                        "name": f"normalizacion-arquitectura-{stack_id}",
                        "description": f"Normalización y alineación arquitectónica de {d['name']} ({len(diag['architecture_errors'])} violaciones detectadas por check-architecture.py)",
                        "status": "todo",
                        "kind": "refactor",
                        "created_at": now_iso(),
                        "stack": stack_id,
                        "is_architecture_norm": True
                    }
                    feats.insert(0, f0)
                    resultado["f0_creada"] = True
                    resultado["f0_id"] = 0

                    # Bloquear todas las demás features abiertas para que requieran #0
                    for other in feats:
                        if str(other.get("id")) != "0" and other.get("status") not in ("done", "superseded"):
                            reqs = other.get("requiere") or []
                            if isinstance(reqs, (str, int)):
                                reqs = [reqs]
                            if 0 not in reqs and "#0" not in reqs:
                                reqs.append(0)
                                other["requiere"] = reqs
                    resultado["bloqueos_activados"] = True

                    save_backlog(p_paths, data)
                    bitacora(p_paths, f"creada Feature #0 de normalización arquitectónica obligatoria para {d['name']}")

                    # Crear spec para Feature #0
                    spec_file = p_paths["docs"] / f"spec-feature-0-normalizacion-arquitectura-{stack_id}.md"
                    if not spec_file.exists():
                        lista_errs = "\n".join(f"- {err}" for err in diag["architecture_errors"][:15])
                        spec_content = f"""# Spec - Feature #0: normalizacion-arquitectura-{stack_id}

Estado: draft

## Contexto

Normalización arquitectónica obligatoria para el stack {manifest.get('name', stack_id)} en `{target_path.name}`.
El verificador de arquitectura detectó {len(diag['architecture_errors'])} violaciones estructurales en el código existente.
Esta feature es un prerrequisito obligatorio antes de implementar cualquier feature de negocio.

Violaciones detectadas por el arnés:
{lista_errs}

## Criterios de aceptacion

- AC-1 [costura: integracion]: El verificador check-architecture.py finaliza con exit code 0 y cero violaciones.
  Comando: `python3 {rel_checker} --repo {rel_target}`
- AC-2 [costura: test]: La suite de pruebas del proyecto ejecuta sin regresiones respecto a la base.
  Comando: `{test_runner}`

## Plan vertical

- Paso 1: Identificar módulos y archivos con violaciones de arquitectura reportadas por check-architecture.py.
- Paso 2: Extraer capas canónicas (domain, application, infrastructure/ports) desacoplando dependencias indebidas.
- Paso 3: Re-ejecutar check-architecture.py y la suite de tests hasta lograr verde integral con cero regresiones.

## Fuera de alcance

Nuevas funcionalidades de negocio. Esta feature es estrictamente refactorización y alineación arquitectónica.
"""
                        spec_file.write_text(spec_content, encoding="utf-8")
                else:
                    if f0.get("status") != "done":
                        for other in feats:
                            if str(other.get("id")) != "0" and other.get("status") not in ("done", "superseded"):
                                reqs = other.get("requiere") or []
                                if isinstance(reqs, (str, int)):
                                    reqs = [reqs]
                                if 0 not in reqs and "#0" not in reqs:
                                    reqs.append(0)
                                    other["requiere"] = reqs
                        resultado["bloqueos_activados"] = True
                        resultado["f0_id"] = 0

    return resultado


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            cwd=str(cwd) if cwd else None,
            timeout=timeout
        )
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired:
        return 124, f"Comando excedió el timeout de {timeout}s: {' '.join(cmd)}"
    except Exception as exc:
        return 1, str(exc)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Gestor de Stacks Tecnologicos CALPIL (Harness Flow)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # detectar
    p_det = sub.add_parser("detectar", help="Detecta el stack de un repositorio o proyecto multi-repo")
    p_det.add_argument("--repo", default=".", help="Ruta del repositorio o proyecto")
    p_det.add_argument("--json", action="store_true", help="Salida en formato JSON")

    # verificar
    p_ver = sub.add_parser("verificar", help="Verifica cumplimiento de rules, skills, arquitectura y testing")
    p_ver.add_argument("--repo", default=".", help="Ruta del repositorio")
    p_ver.add_argument("--stack", default=None, help="Forzar stack especifico")
    p_ver.add_argument("--json", action="store_true", help="Salida en formato JSON")

    # normalizar
    p_norm = sub.add_parser("normalizar", help="Instala/sincroniza rules, skills y AGENTS.md multi-LLM")
    p_norm.add_argument("--repo", default=".", help="Ruta del repositorio")
    p_norm.add_argument("--stack", default=None, help="Forzar stack especifico")
    p_norm.add_argument("--dry-run", action="store_true", help="Solo simular cambios")

    # auditar
    p_aud = sub.add_parser("auditar", help="Audita versiones del stack, vulnerabilidades (CVEs) y fuentes Context7/Oficiales")
    p_aud.add_argument("--repo", default=".", help="Ruta del repositorio")
    p_aud.add_argument("--stack", default=None, help="Forzar stack especifico")
    p_aud.add_argument("--dast", action="store_true", help="Ejecuta escaneo dinámico DAST con OWASP ZAP (zaproxy/zap-stable)")
    p_aud.add_argument("--openapi", default=None, help="Ruta al archivo openapi.json/yaml para escaneo DAST de API")
    p_aud.add_argument("--target-url", default=None, help="URL objetivo para escaneo DAST (default: http://localhost:8080)")
    p_aud.add_argument("--json", action="store_true", help="Salida en formato JSON")

    # refactorizar
    p_ref = sub.add_parser("refactorizar", help="Planifica o ejecuta scaffolding para alinear con la arquitectura")
    p_ref.add_argument("--repo", default=".", help="Ruta del repositorio")
    p_ref.add_argument("--stack", default=None, help="Forzar stack especifico")
    p_ref.add_argument("--scaffold", action="store_true", help="Crear carpetas y esqueleto canónico faltante")
    p_ref.add_argument("--json", action="store_true", help="Salida en formato JSON")

    # stacks
    sub.add_parser("stacks", help="Lista los stacks soportados en harness-flow")

    args = ap.parse_args()

    if args.cmd == "stacks":
        stacks = listar_stacks_disponibles()
        print(f"Stacks soportados en harness-flow ({len(stacks)}):")
        for st in stacks:
            print(f"  - [{st.get('id')}] {st.get('name')}: {st.get('description')}")
        sys.exit(0)

    repo_path = Path(args.repo).resolve()

    if args.cmd == "detectar":
        todos = detectar_todos_los_destinos(repo_path)
        if args.json:
            print(json.dumps(todos, indent=2))
        else:
            print(f"Detección de Stacks en {repo_path.name}:")
            for t in todos:
                print(f"  - Ruta: {t['path']}")
                print(f"    Stack: {t['stack']} ({t['name']}) [Confianza: {t['confidence']}%]")
                if t["indicators"]:
                    print(f"    Indicadores: {', '.join(t['indicators'])}")
        sys.exit(0)

    if args.cmd in ("verificar", "normalizar"):
        # Los microservicios pueden vivir fuera de la raiz del arnes: cuenta tambien el cwd.
        try:
            rules_cli = rules_del_proyecto(repo_path, Path.cwd())
            skills_excluidas(rules_cli, args.stack or "")
        except ValueError as exc:
            print(f"[!!] {exc}", file=sys.stderr)
            sys.exit(1)

    if args.cmd == "verificar":
        diag = verificar_cumplimiento(repo_path, args.stack, rules=rules_cli)
        if args.json:
            print(json.dumps(diag, indent=2))
        else:
            print("=" * 68)
            print(f"DIAGNÓSTICO NORMATIVO CALPIL: {diag['stack']} en {repo_path.name}")
            print("=" * 68)
            print(f"Estado global: {'✅ COMPLIANT' if diag['compliant'] else '❌ NON-COMPLIANT'}")
            print(f"Rules modulares:     {'OK (multi-LLM)' if diag['rules_ok'] else 'FALTAN (' + ', '.join(diag['missing_rules']) + ')'}")
            missing_skills_cnt = len(diag['missing_skills'])
            skills_status = 'OK' if diag['skills_ok'] else f"FALTAN {missing_skills_cnt} skills"
            print(f"Skills operativas:   {skills_status}")
            if diag.get("skills_excluidas"):
                print(f"Skills excluidas:    {', '.join(diag['skills_excluidas'])} (rules.{REGLA_SKILLS_EXCLUIDAS})")
            print(f"Arquitectura:        {'OK' if diag['architecture_ok'] else 'VIOLACIONES DETECTADAS'}")
            print(f"Multi-LLM Ready:     {'SI' if diag['multi_llm_ready'] else 'NO'}")
            parity_label = 'TOTAL (todos los hosts)' if diag.get('full_multi_llm_parity') else f"PARCIAL (hosts sincronizados: {', '.join(diag.get('hosts_active', [])) if diag.get('hosts_active') else 'ninguno'})"
            print(f"Paridad Multi-LLM:   {parity_label}")
            if diag["findings"]:
                print("\nHallazgos a corregir:")
                for f in diag["findings"]:
                    print(f"  [!] {f}")
            if diag["warnings"]:
                print("\nAdvertencias:")
                for w in diag["warnings"]:
                    print(f"  [i] {w}")
        sys.exit(0 if diag["compliant"] else 1)

    if args.cmd == "auditar":
        res = auditar_seguridad_y_versiones(
            repo_path,
            args.stack,
            dast=getattr(args, "dast", False),
            openapi_path=getattr(args, "openapi", None),
            target_url=getattr(args, "target_url", None),
        )
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print("=" * 68)
            print(f"AUDITORÍA DE VERSIONES Y SEGURIDAD: {res.get('stack')} en {repo_path.name}")
            print("=" * 68)
            print(f"Documentación Oficial: {res.get('official_docs') or 'No declarada'}")
            print(f"Avisos de Seguridad:   {res.get('security_advisories') or 'No declarada'}")
            print(f"Context7 Library ID:   {res.get('context7_library') or 'No declarada'}")
            if res.get("context7_queries"):
                print("Context7 Queries sugeridas:")
                for q in res["context7_queries"]:
                    print(f"  - {q}")
            print(f"Versión Mínima:        {res.get('minimum_version') or 'N/A'}")
            print(f"Comando de Seguridad:  {res.get('audit_command') or 'No configurado'}")
            if res.get("warnings"):
                print("\nAdvertencias de versión / entorno:")
                for w in res["warnings"]:
                    print(f"  [i] {w}")
            if res.get("findings"):
                print("\nHallazgos:")
                for f in res["findings"]:
                    print(f"  [!] {f}")
            if res.get("audit_output"):
                print("\nSalida del escáner de seguridad:")
                for line in res["audit_output"].splitlines()[:15]:
                    print(f"  | {line}")
            if res.get("dast"):
                dast_info = res["dast"]
                print("\n" + "-" * 68)
                print(f"ANÁLISIS DINÁMICO DAST (OWASP ZAP): {dast_info.get('status').upper()}")
                print(f"Herramienta: {dast_info.get('tool')}")
                print(f"Modo:        {dast_info.get('mode')}")
                print(f"Objetivo:    {dast_info.get('target')}")
                if dast_info.get("command"):
                    print(f"Comando:     {dast_info.get('command')}")
                if dast_info.get("output"):
                    print("Salida DAST:")
                    for line in dast_info["output"].splitlines()[:15]:
                        print(f"  | {line}")
        sys.exit(0)

    if args.cmd == "normalizar":
        res = normalizar_repositorio(repo_path, args.stack, args.dry_run, rules=rules_cli)
        print(f"Normalización de stack '{res.get('stack')}' en {repo_path.name}:")
        if res.get("skills_excluidas"):
            print(f"  = Skills excluidas por el proyecto: {', '.join(res['skills_excluidas'])}")
        for aviso in res.get("warnings", []):
            print(f"  [i] {aviso}")
        actions = res.get("actions", [])
        if actions:
            for act in actions:
                print(f"  + {act}")
            print(f"\nTotal: {len(actions)} acciones aplicadas. El repositorio ahora cumple la normativa multi-LLM.")
        else:
            print("  - Todas las rules, skills y contratos ya se encontraban normalizados.")
        sys.exit(0)

    if args.cmd == "refactorizar":
        if args.scaffold:
            creados = ejecutar_scaffolding(repo_path, args.stack)
            if creados:
                print(f"Scaffolding aplicado en {repo_path.name}:")
                for c in creados:
                    print(f"  + Creado: {c}")
            else:
                print("La estructura canónica básica ya existe.")
        plan = generar_plan_refactor(repo_path, args.stack)
        if args.json:
            print(json.dumps(plan, indent=2))
        else:
            if not plan["needed"]:
                print(f"✅ {plan['message']}")
            else:
                print(f"\nPLAN DE REFACTORIZACIÓN ARQUITECTÓNICA ({plan['stack']}):")
                for s in plan["steps"]:
                    print(f"  Paso {s['step']}: {s['title']}")
                    print(f"    Acción: {s['action']} -> {s['target']}")
                    print(f"    Detalle: {s['description']}")
                print(f"\nRecomendación: {plan['recommendation']}")
        sys.exit(0)


if __name__ == "__main__":
    main()
