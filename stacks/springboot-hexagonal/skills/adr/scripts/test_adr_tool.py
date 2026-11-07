#!/usr/bin/env python3
"""Pruebas sin dependencias: python3 .../scripts/test_adr_tool.py"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from adr_tool import create_adr, make_index, merge_index, metadata, report_issues, main


class ADRToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "docs" / "adr"

    def test_creates_sequential_proposals(self):
        a = create_adr(self.folder, "Resolución de servicios", owner="EA", scope="Plataforma", date="2026-10-22")
        b = create_adr(self.folder, "Gestión de contratos")
        self.assertEqual(a.name, "ADR-0001-resolucion-de-servicios.md")
        self.assertTrue(b.name.startswith("ADR-0002-"))
        f = metadata(a.read_text())
        self.assertEqual(f["Estado"], "Propuesto")
        self.assertEqual(f["Responsable"], "EA")
        self.assertEqual(f["Fecha"], "2026-10-22")

    def test_never_recycles_duplicate_id(self):
        create_adr(self.folder, "Contrato de datos")
        with self.assertRaisesRegex(ValueError, "Ya existe"):
            create_adr(self.folder, "Otra decisión", forced_id=1)

    def test_preserves_template_sections(self):
        create_adr(self.folder, "Patrón BFF")
        issues, summary = report_issues(self.folder)
        self.assertEqual(len(summary), 1)
        self.assertEqual(issues, [])

    def test_approved_cannot_contain_placeholders(self):
        p = create_adr(self.folder, "Estrategia de APIs")
        p.write_text(p.read_text().replace("| **Estado** | Propuesto |", "| **Estado** | Aprobado |"))
        issues, _ = report_issues(self.folder)
        self.assertTrue(any("placeholders" in i["message"] for i in issues))

    def test_replaced_needs_successor(self):
        p = create_adr(self.folder, "Estrategia de APIs")
        p.write_text(p.read_text().replace("| **Estado** | Propuesto |", "| **Estado** | Reemplazado |"))
        issues, _ = report_issues(self.folder)
        self.assertTrue(any("Reemplazado por" in i["message"] for i in issues))

    def test_index_merges_and_keeps_manual_text(self):
        create_adr(self.folder, "Patrón API")
        generated = make_index(self.folder)
        content = merge_index("# Gobierno\n\nTexto manual.\n", generated)
        self.assertIn("Texto manual", content)
        content2 = merge_index(content, generated)
        self.assertEqual(content2, content)
        self.assertEqual(content.count("<!-- ADR-INDEX:START -->"), 1)

    def test_index_check_returns_one_when_missing(self):
        create_adr(self.folder, "Prueba")
        self.assertEqual(main(["index", "--dir", str(self.folder), "--check"]), 1)
        self.assertEqual(main(["index", "--dir", str(self.folder), "--write"]), 0)
        self.assertEqual(main(["index", "--dir", str(self.folder), "--check"]), 0)

    def test_missing_replacement_target(self):
        p = create_adr(self.folder, "Migración")
        p.write_text(p.read_text().replace("| **Reemplaza a** | [ADR-XXXX o N/A] |", "| **Reemplaza a** | ADR-0042 |"))
        issues, _ = report_issues(self.folder)
        self.assertTrue(any("inexistente" in i["message"] for i in issues))

    def test_reject_bad_date(self):
        with self.assertRaisesRegex(ValueError, "fecha"):
            create_adr(self.folder, "X", date="2026-13-99")

    def test_invalid_filename_is_reported(self):
        self.folder.mkdir(parents=True)
        (self.folder / "ADR-FINAL.md").write_text("incorrecto")
        issues, _ = report_issues(self.folder)
        self.assertTrue(any("Nombre incorrecto" in i["message"] for i in issues))

    def test_id_metadata_mismatch(self):
        p = create_adr(self.folder, "Contrato")
        p.write_text(p.read_text().replace("| **ID** | ADR-0001 |", "| **ID** | ADR-0999 |"))
        issues, _ = report_issues(self.folder)
        self.assertTrue(any("no coincide" in i["message"] for i in issues))


    def test_legacy_ids_are_reserved_for_new_adrs(self):
        self.folder.mkdir(parents=True)
        (self.folder / "0001-architecture-profile.md").write_text(
            "# ADR 0001 — Arquitectura\nEstado: Aceptado · Fecha: 2026-08-03\n")
        first = create_adr(self.folder, "Nueva decision")
        self.assertEqual(first.name, "ADR-0002-nueva-decision.md")
        with self.assertRaisesRegex(ValueError, "Ya existe"):
            create_adr(self.folder, "Colision", forced_id=1)

    def test_legacy_is_indexed_without_rewriting_historical_adr(self):
        self.folder.mkdir(parents=True)
        original = "# ADR 0001 — Arquitectura\nEstado: Aceptado · Fecha: 2026-08-03\n"
        legacy = self.folder / "0001-architecture-profile.md"
        legacy.write_text(original)
        body = make_index(self.folder)
        self.assertIn("ADR-0001", body)
        self.assertIn("0001-architecture-profile.md", body)
        self.assertIn("Aceptado (legado)", body)
        issues,info = report_issues(self.folder)
        self.assertEqual(issues, [])
        self.assertEqual(info[0]["id"], "ADR-0001")
        self.assertEqual(legacy.read_text(), original)

    def test_legacy_and_modern_collision_is_flagged(self):
        self.folder.mkdir(parents=True)
        (self.folder / "0001-legacy.md").write_text("# ADR 0001 — Legacy\n")
        p = create_adr(self.folder, "Modern", forced_id=2)
        renamed = p.with_name("ADR-0001-modern.md")
        p.rename(renamed)
        issues,_ = report_issues(self.folder)
        self.assertTrue(any("duplicado" in it["message"] for it in issues))


if __name__ == "__main__":
    unittest.main(verbosity=2)
