#!/usr/bin/env python3
"""CLI conservadora para ADRs en Markdown. Solo biblioteca estándar de Python 3.9+.

Uso:
  python3 .claude/skills/adr/scripts/adr_tool.py new --title "Decisión" --dir docs/adr
  python3 .claude/skills/adr/scripts/adr_tool.py validate --dir docs/adr
  python3 .claude/skills/adr/scripts/adr_tool.py index --dir docs/adr --write
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "ADR-TEMPLATE.md"
STATES = {"Propuesto", "Aprobado", "Rechazado", "Obsoleto", "Reemplazado"}
FILE_RE = re.compile(r"^ADR-(\d{4,})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
LEGACY_RE = re.compile(r"^(\d{4,})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
META_RE = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|\s*$", re.M)
HEADINGS = [
    "Metadatos", "Resumen ejecutivo", "Contexto y problema",
    "Objetivos y criterios de decisión", "Alternativas consideradas",
    "Decisión", "Consecuencias y trade-offs", "Implicancias de arquitectura",
    "Plan de adopción y validación", "Referencias y trazabilidad",
    "Historial de decisiones",
]
START = "<!-- ADR-INDEX:START -->"
END = "<!-- ADR-INDEX:END -->"


def slugify(raw: str) -> str:
    normalized = unicodedata.normalize("NFKD", raw)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug[:80].rstrip("-") or "decision"


def metadata(body: str) -> dict[str, str]:
    return {key.strip(): value.strip() for key, value in META_RE.findall(body)}


def adr_files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        raise ValueError(f"No existe el directorio de ADR: {folder}")
    return sorted((x for x in folder.glob("*.md") if x.is_file() and (x.name.startswith("ADR-") or LEGACY_RE.fullmatch(x.name))), key=lambda p: p.name)


def next_number(folder: Path) -> int:
    return 1 + max((int(match.group(1)) for p in adr_files(folder)
                    if (match := FILE_RE.fullmatch(p.name) or LEGACY_RE.fullmatch(p.name))), default=0)


def set_field(body: str, field: str, value: str) -> str:
    pattern = re.compile(r"^(\|\s*\*\*" + re.escape(field) + r"\*\*\s*\|\s*)(.*?)(\s*\|\s*)$", re.M)
    replacement = lambda m: m.group(1) + value + m.group(3)
    output, found = pattern.subn(replacement, body, count=1)
    if found != 1:
        raise ValueError(f"El template no contiene el campo requerido: {field}")
    return output


def create_adr(folder: Path, title: str, owner: str | None = None,
               scope: str | None = None, domain: str | None = None,
               date: str | None = None, forced_id: int | None = None) -> Path:
    if not title.strip():
        raise ValueError("--title no puede estar vacío")
    folder.mkdir(parents=True, exist_ok=True)
    number = forced_id if forced_id is not None else next_number(folder)
    if not 1 <= number <= 999999:
        raise ValueError("El ID debe ser un entero de 1 a 999999")
    if any(int(match.group(1)) == number for p in adr_files(folder)
           if (match := FILE_RE.fullmatch(p.name) or LEGACY_RE.fullmatch(p.name))):
        raise ValueError(f"Ya existe un ADR con ID {number:04d}; no se permite reciclarlo")
    today = date or dt.date.today().isoformat()
    try:
        dt.date.fromisoformat(today)
    except ValueError as e:
        raise ValueError("La fecha debe tener formato AAAA-MM-DD y ser válida") from e
    adr_id = f"ADR-{number:04d}"
    dest = folder / f"{adr_id}-{slugify(title)}.md"
    body = TEMPLATE.read_text(encoding="utf-8")
    body = body.replace("# ADR-XXXX — [Título de la decisión]", f"# {adr_id} — {title.strip()}", 1)
    for field, value in {
        "ID": adr_id,
        "Estado": "Propuesto",
        "Fecha": today,
        "Última revisión": today,
        "Responsable": owner or "[Pendiente: responsable]",
        "Alcance": scope or "[Pendiente: alcance]",
        "Dominio / capacidad": domain or "[Pendiente: dominio]",
    }.items():
        body = set_field(body, field, value)
    # Nunca sobrescribir: preserva edición humana y evita carreras simples.
    with dest.open("x", encoding="utf-8") as fh:
        fh.write(body)
    return dest


def report_issues(folder: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Devuelve [issues], [summary]. No lee ni escribe fuera del directorio declarado."""
    errors: list[dict[str, str]] = []
    info: list[dict[str, str]] = []
    paths = adr_files(folder)
    by_id: dict[str, Path] = {}
    bodies: dict[str, str] = {}
    metas: dict[str, dict[str, str]] = {}

    def add(severity: str, file: str, message: str) -> None:
        errors.append({"severity": severity, "file": file, "message": message})

    for p in paths:
        match = FILE_RE.fullmatch(p.name)
        if not match:
            legacy = LEGACY_RE.fullmatch(p.name)
            if legacy:
                # Preserve existing CALPIL legacy decisions without forcing a rewrite.
                # Reserve their numeric IDs; index them as historic accepted records.
                adr_id = "ADR-" + legacy.group(1)
                if adr_id in by_id:
                    add("ERROR", p.name, f"ID duplicado con {by_id[adr_id].name}: {adr_id}")
                by_id[adr_id] = p
                body = p.read_text(encoding="utf-8")
                state_match = re.search(r"^Estado:\s*(.*?)(?:\s*·\s*Fecha:|$)", body, re.M)
                date_match = re.search(r"\bFecha:\s*(\d{4}-\d{2}-\d{2})", body)
                fields = {"Estado": (state_match.group(1).strip() if state_match else "Legado (sin estado)"),
                          "Fecha": (date_match.group(1) if date_match else ""),
                          "Alcance": "Legacy"}
                bodies[adr_id] = body
                metas[adr_id] = fields
                info.append({"id": adr_id, "file": p.name, "status": fields["Estado"]})
                continue
            add("ERROR", p.name, "Nombre incorrecto; usar ADR-0001-titulo-corto.md")
            continue
        adr_id = "ADR-" + match.group(1)
        if adr_id in by_id:
            add("ERROR", p.name, f"ID duplicado con {by_id[adr_id].name}: {adr_id}")
        by_id[adr_id] = p
        body = p.read_text(encoding="utf-8")
        fields = metadata(body)
        bodies[adr_id] = body
        metas[adr_id] = fields
        state = fields.get("Estado", "")
        info.append({"id": adr_id, "file": p.name, "status": state})

        if fields.get("ID") != adr_id:
            add("ERROR", p.name, f"Metadato ID no coincide con nombre ({adr_id})")
        first = body.splitlines()[0] if body.splitlines() else ""
        if not first.startswith(f"# {adr_id} — "):
            add("ERROR", p.name, "Título inicial no incluye el mismo ID o formato '# ADR-0001 — ...'")
        if state not in STATES:
            add("ERROR", p.name, f"Estado no permitido: {state or '(vacío)'}")
        for key in ("Fecha", "Última revisión"):
            value = fields.get(key, "")
            try:
                dt.date.fromisoformat(value)
            except ValueError:
                add("ERROR", p.name, f"{key} debe ser fecha ISO válida: {value}")
        for idx, section in enumerate(HEADINGS, 1):
            if not re.search(r"^##\s+" + str(idx) + r"\.\s+" + re.escape(section) + r"\s*$", body, re.M):
                add("ERROR", p.name, f"Falta sección {idx}. {section}")
        if state == "Aprobado":
            # Un placeholder [texto] sin enlace Markdown no se acepta en documentos aprobados.
            placeholders = re.findall(r"\[([^\]\n]+)\](?!\()", body)
            if placeholders or "AAAA-MM-DD" in body:
                examples = ", ".join(placeholders[:3])
                add("ERROR", p.name, f"Aprobado con placeholders: {examples or 'AAAA-MM-DD'}")
            option_count = len(re.findall(r"^### Opción [A-Z]\b", body, re.M))
            if option_count < 2:
                add("WARN", p.name, "No se observan dos alternativas en secciones Opción A/B")
            decision_match = re.search(r"^\*\*Se adopta:\*\*\s*(.+)$", body, re.M)
            if not decision_match or not decision_match.group(1).strip():
                add("ERROR", p.name, "Falta decisión explícita en sección 6")
        if state in ("Aprobado", "Reemplazado") and not fields.get("Responsable", ""):
            add("WARN", p.name, "Falta responsable")

    def adr_refs(value: str) -> list[str]:
        return re.findall(r"\bADR-\d{4,}\b", value)

    for adr_id, fields in metas.items():
        p = by_id[adr_id]
        state = fields.get("Estado", "")
        old_links = adr_refs(fields.get("Reemplaza a", ""))
        new_links = adr_refs(fields.get("Reemplazado por", ""))
        for target in old_links + new_links:
            if target == adr_id:
                add("ERROR", p.name, f"Referencia circular a sí mismo: {target}")
            elif target not in by_id:
                add("ERROR", p.name, f"Referencia de reemplazo inexistente: {target}")
        if state == "Reemplazado" and not new_links:
            add("ERROR", p.name, "El estado Reemplazado requiere metadato 'Reemplazado por'")
        if state == "Aprobado" and old_links:
            for old_id in old_links:
                if old_id in metas:
                    old_fields = metas[old_id]
                    if old_fields.get("Estado") != "Reemplazado":
                        add("WARN", p.name, f"{old_id} debería evaluarse para estado Reemplazado")
                    if adr_id not in adr_refs(old_fields.get("Reemplazado por", "")):
                        add("WARN", p.name, f"Falta vínculo inverso desde {old_id}")
        if state == "Reemplazado" and new_links:
            for new_id in new_links:
                if new_id in metas and adr_id not in adr_refs(metas[new_id].get("Reemplaza a", "")):
                    add("WARN", p.name, f"Falta vínculo inverso en {new_id}")

    return errors, info


def read_title(body: str) -> str:
    first = body.splitlines()[0] if body.splitlines() else ""
    if " — " in first:
        return first.split(" — ", 1)[1].strip()
    return "(sin título)"


def make_index(folder: Path) -> str:
    rows: list[str] = []
    for p in sorted(adr_files(folder), key=lambda path: (int(m.group(1)) if (m := FILE_RE.fullmatch(path.name) or LEGACY_RE.fullmatch(path.name)) else 10**12, path.name)):
        match = FILE_RE.fullmatch(p.name) or LEGACY_RE.fullmatch(p.name)
        if not match:
            continue
        body = p.read_text(encoding="utf-8")
        fields = metadata(body)
        if LEGACY_RE.fullmatch(p.name):
            status_match = re.search(r"^Estado:\s*(.*?)(?:\s*·\s*Fecha:|$)", body, re.M)
            date_match = re.search(r"\bFecha:\s*(\d{4}-\d{2}-\d{2})", body)
            fields.update({"Estado": status_match.group(1).strip() + " (legado)" if status_match else "Legado",
                           "Fecha": date_match.group(1) if date_match else "",
                           "Alcance": "Legacy"})
        title = read_title(body).replace("|", r"\|")
        scope = fields.get("Alcance", "").replace("|", r"\|")
        rows.append(f"| ADR-{match.group(1)} | [{title}](<{p.name}>) | {fields.get('Estado', 'Pendiente')} | {scope} | {fields.get('Fecha', '')} |")
    body = (
        f"{START}\n"
        "| ID | Decisión | Estado | Alcance | Fecha |\n"
        "|---|---|---|---|---|\n" +
        ("\n".join(rows) if rows else "| — | No se han creado ADR | — | — | — |") +
        f"\n{END}"
    )
    return body


def merge_index(existing: str | None, generated: str) -> str:
    if existing is None:
        return "# Catálogo de decisiones de arquitectura (ADR)\n\n" + generated + "\n"
    starts, ends = existing.count(START), existing.count(END)
    if starts != ends or starts > 1:
        raise ValueError("Marcadores ADR-INDEX desbalanceados o duplicados. Corregir manualmente.")
    if starts == 1:
        return re.sub(re.escape(START) + r"[\s\S]*?" + re.escape(END), lambda _: generated, existing)
    return existing.rstrip() + "\n\n" + generated + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Asistente local y no destructivo de Architecture Decision Records")
    sub = parser.add_subparsers(dest="cmd", required=True)
    new = sub.add_parser("new", help="Crear ADR Propuesto, sin sobrescribir archivos")
    new.add_argument("--title", required=True)
    new.add_argument("--dir", type=Path, default=Path("docs/adr"))
    new.add_argument("--owner")
    new.add_argument("--scope")
    new.add_argument("--domain")
    new.add_argument("--date")
    new.add_argument("--id", type=int, dest="forced_id", help="ID numérico explícito, sin reciclar")
    check = sub.add_parser("validate", help="Validar estructura, ID, estados y reemplazos")
    check.add_argument("--dir", type=Path, default=Path("docs/adr"))
    check.add_argument("--strict", action="store_true", help="Warnings generan código de salida 1")
    check.add_argument("--json", action="store_true", help="Salida JSON apta para CI")
    idx = sub.add_parser("index", help="Generar catálogo preservando texto editorial")
    idx.add_argument("--dir", type=Path, default=Path("docs/adr"))
    idx_flags = idx.add_mutually_exclusive_group()
    idx_flags.add_argument("--write", action="store_true")
    idx_flags.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "new":
            p = create_adr(args.dir, args.title, args.owner, args.scope, args.domain, args.date, args.forced_id)
            print(f"CREATED {p} (Propuesto). Completar y validar; no está aprobado.")
            return 0
        if args.cmd == "validate":
            issues, info = report_issues(args.dir)
            severe = sum(1 for i in issues if i["severity"] == "ERROR")
            warnings = sum(1 for i in issues if i["severity"] == "WARN")
            if args.json:
                print(json.dumps({"files": len(info), "errors": severe, "warnings": warnings, "issues": issues}, ensure_ascii=False, indent=2))
            else:
                for issue in issues:
                    print(f"[{issue['severity']}] {issue['file']}: {issue['message']}")
                print(f"ADR revisados: {len(info)} | Errores: {severe} | Advertencias: {warnings}")
            return 1 if severe or (args.strict and warnings) else 0
        if args.cmd == "index":
            generated = make_index(args.dir)
            p = args.dir / "README.md"
            old = p.read_text(encoding="utf-8") if p.exists() else None
            new_body = merge_index(old, generated)
            if args.check:
                if old != new_body:
                    print(f"OUTDATED {p}; ejecutar index --write")
                    return 1
                print(f"OK {p} actualizado")
                return 0
            if args.write:
                if old != new_body:
                    p.write_text(new_body, encoding="utf-8")
                    print(f"UPDATED {p}")
                else:
                    print(f"UNCHANGED {p}")
            else:
                print(new_body)
            return 0
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
