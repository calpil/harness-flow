"""PRD y SDD se sincronizan desde las features implementadas."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import atlassian  # noqa: E402
import documentacion  # noqa: E402
import gate  # noqa: E402


class DocumentacionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.prev_cwd = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(lambda: os.chdir(self.prev_cwd))
        (self.root / "harness" / "progress").mkdir(parents=True)
        (self.root / "docs").mkdir()
        (self.root / "harness" / "feature_list.json").write_text(json.dumps({
            "project": "demo",
            "rules": {
                "require_spec_approved": False,
                "require_review": False,
                "require_leccion": False,
                "require_verify_green": False,
                "require_docs_al_dia": False,
            },
            "features": [
                {
                    "id": 7,
                    "name": "Historial vivo",
                    "kind": "feature",
                    "status": "done",
                    "microservicios": ["api", "worker"],
                    "branch": "feat/historial",
                    "integrado_en": "main",
                    "merge_commit": "abc123",
                    "closed_at": "2026-09-14T10:00:00-03:00",
                    "progress_archive": "harness/progress/archive/current-7.md",
                },
                {"id": 8, "name": "Pendiente", "kind": "feature", "status": "in_progress"},
            ],
        }), encoding="utf-8")
        (self.root / "docs" / "spec-feature-7-historial-vivo.md").write_text(
            "Estado: approved\n\n## Criterios de aceptacion\n\n- AC-1: conserva historial\n- AC-2: funciona en Claude Code\n",
            encoding="utf-8")
        (self.root / "docs" / "impl-7.md").write_text(
            "## AC-1\nscripts/gate.py:1\n\n## AC-2\nscripts/documentacion.py:1\n",
            encoding="utf-8")
        (self.root / "docs" / "review-7.md").write_text("Sello: approved\n", encoding="utf-8")
        (self.root / "harness" / "progress" / "archive").mkdir()
        (self.root / "harness" / "progress" / "archive" / "current-7.md").write_text(
            "decision tecnica", encoding="utf-8")

    def cli_gate(self, *args):
        out = io.StringIO()
        err = io.StringIO()
        with mock.patch.object(sys, "argv", ["gate.py", *args]), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                gate.main()
                rc = 0
            except SystemExit as exc:
                if isinstance(exc.code, int):
                    rc = int(exc.code or 0)
                elif exc.code:
                    print(exc.code, file=err)
                    rc = 1
                else:
                    rc = 0
        return rc, out.getvalue(), err.getvalue()

    def test_sync_crea_prd_y_sdd_desde_features_done(self):
        documentacion.sync()

        prd = (self.root / "docs" / "prd" / "PRD-master.md").read_text(encoding="utf-8")
        sdd = (self.root / "docs" / "sdd.md").read_text(encoding="utf-8")
        self.assertIn("Feature #7 - Historial vivo", prd)
        self.assertIn("AC-1: conserva historial", prd)
        self.assertIn("AC-2: funciona en Claude Code", prd)
        self.assertIn("Feature #7 - Historial vivo", sdd)
        self.assertIn("api, worker", sdd)
        self.assertIn("abc123", sdd)
        self.assertIn("harness/progress/archive/current-7.md", sdd)
        self.assertNotIn("Pendiente", prd)
        self.assertNotIn("Pendiente", sdd)

    def test_sync_es_idempotente_si_no_cambian_features(self):
        documentacion.sync()
        prd_path = self.root / "docs" / "prd" / "PRD-master.md"
        sdd_path = self.root / "docs" / "sdd.md"
        prd_1 = prd_path.read_text(encoding="utf-8")
        sdd_1 = sdd_path.read_text(encoding="utf-8")

        cambiados = documentacion.sync()

        self.assertEqual(cambiados, [])
        self.assertEqual(prd_1, prd_path.read_text(encoding="utf-8"))
        self.assertEqual(sdd_1, sdd_path.read_text(encoding="utf-8"))

    def test_sync_preserva_contenido_manual_y_actualiza_solo_bloque_generado(self):
        prd_path = self.root / "docs" / "prd" / "PRD-master.md"
        prd_path.parent.mkdir(parents=True)
        prd_path.write_text(
            "# PRD propio\n\nTexto del usuario.\n\n"
            "<!-- harness-flow:features:start -->\ncontenido viejo\n<!-- harness-flow:features:end -->\n",
            encoding="utf-8")
        sdd_path = self.root / "docs" / "sdd.md"
        sdd_path.write_text("# SDD propio\n\nNotas manuales.\n", encoding="utf-8")

        documentacion.sync()

        prd = prd_path.read_text(encoding="utf-8")
        sdd = sdd_path.read_text(encoding="utf-8")
        self.assertIn("Texto del usuario", prd)
        self.assertNotIn("contenido viejo", prd)
        self.assertIn("Feature #7 - Historial vivo", prd)
        self.assertIn("Notas manuales", sdd)
        self.assertIn("Feature #7 - Historial vivo", sdd)

    def test_gate_close_done_regenera_prd_sdd(self):
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        data["features"][0]["status"] = "in_progress"
        data["features"][0].pop("closed_at")
        (self.root / "harness" / "feature_list.json").write_text(json.dumps(data), encoding="utf-8")
        (self.root / "harness" / "progress" / "current-7.md").write_text("nota viva", encoding="utf-8")

        with mock.patch.object(gate, "git_merge", return_value="def456"):
            rc, out, err = self.cli_gate("close", "--feature", "7", "--status", "done", "--to", "main")

        self.assertEqual(rc, 0, err)
        prd = (self.root / "docs" / "prd" / "PRD-master.md").read_text(encoding="utf-8")
        sdd = (self.root / "docs" / "sdd.md").read_text(encoding="utf-8")
        self.assertIn("Feature #7 - Historial vivo", prd)
        self.assertIn("def456", sdd)
        self.assertIn("documentacion", out.lower())
    def test_gate_check_permite_prd_generado_por_sync(self):
        import subprocess
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        data["features"] = [data["features"][0]]
        (self.root / "harness" / "feature_list.json").write_text(json.dumps(data), encoding="utf-8")
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "harness/feature_list.json", "docs", "harness/progress/archive/current-7.md"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=self.root, check=True, capture_output=True)

        documentacion.sync()
        rc, out, err = self.cli_gate("check")

        self.assertEqual(rc, 0, out + err)
        self.assertIn("ruta(s) protegida(s) intactas", out)

    def test_gate_check_bloquea_edicion_manual_del_prd_fuera_del_bloque(self):
        import subprocess
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        data["features"] = [data["features"][0]]
        (self.root / "harness" / "feature_list.json").write_text(json.dumps(data), encoding="utf-8")
        documentacion.sync()
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "harness/feature_list.json", "docs", "harness/progress/archive/current-7.md"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=self.root, check=True, capture_output=True)
        prd_path = self.root / "docs" / "prd" / "PRD-master.md"
        prd_path.write_text(
            prd_path.read_text(encoding="utf-8").replace(
                "Contenido manual arriba; harness-flow mantiene solo el bloque generado.",
                "Texto manual alterado fuera del bloque generado."),
            encoding="utf-8")

        rc, out, err = self.cli_gate("check")

        self.assertNotEqual(rc, 0)
        self.assertIn("rutas protegidas modificadas", out)
        self.assertIn("docs/prd/PRD-master.md", out)

    def test_gate_check_bloquea_otro_archivo_bajo_docs_prd(self):
        import subprocess
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        data["features"] = [data["features"][0]]
        (self.root / "harness" / "feature_list.json").write_text(json.dumps(data), encoding="utf-8")
        documentacion.sync()
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "harness/feature_list.json", "docs", "harness/progress/archive/current-7.md"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=self.root, check=True, capture_output=True)
        (self.root / "docs" / "prd" / "otro.md").write_text("contenido manual", encoding="utf-8")

        rc, out, err = self.cli_gate("check")

        self.assertNotEqual(rc, 0)
        self.assertIn("rutas protegidas modificadas", out)
        self.assertIn("docs/prd/otro.md", out)

    def test_fallo_publicando_atlassian_no_deja_historia_falsa_de_archivo(self):
        (self.root / "harness" / "atlassian.json").write_text(json.dumps({
            "site": "example.atlassian.net",
            "jira_project": "ADR",
            "confluence_space": "ARQ",
        }), encoding="utf-8")
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        data["features"][0]["status"] = "in_progress"
        data["features"][0].pop("closed_at")
        (self.root / "harness" / "feature_list.json").write_text(json.dumps(data), encoding="utf-8")
        (self.root / "harness" / "progress" / "current-7.md").write_text("nota viva", encoding="utf-8")
        def falla_push(args):
            raise SystemExit("[!!] Jira rechazo el cierre")

        with mock.patch.object(gate, "git_merge", return_value="def456"), \
             mock.patch.object(atlassian, "cmd_push", side_effect=falla_push):
            rc, out, err = self.cli_gate(
                "close", "--feature", "7", "--status", "done", "--to", "main",
                "--publicar-atlassian")

        self.assertNotEqual(rc, 0)
        history_path = self.root / "harness" / "progress" / "history.md"
        history = history_path.read_text(encoding="utf-8") if history_path.exists() else ""
        self.assertNotIn("progress #7 archivado", history)
        self.assertNotIn("documentacion PRD/SDD sincronizada para #7", history)

    def test_fallo_publicando_atlassian_no_deja_prd_sdd_como_done(self):
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        data["features"][0]["status"] = "in_progress"
        data["features"][0].pop("closed_at")
        (self.root / "harness" / "feature_list.json").write_text(json.dumps(data), encoding="utf-8")
        (self.root / "harness" / "atlassian.json").write_text(json.dumps({
            "site": "example.atlassian.net",
            "jira_project": "ADR",
            "confluence_space": "ARQ",
        }), encoding="utf-8")
        # Preestado explicito: el rollback nuevo conserva bytes, no genera
        # documentos que no existian antes de un cierre fallido.
        documentacion.sync()
        previous = [(self.root / "docs" / name).read_bytes() for name in ("prd/PRD-master.md", "sdd.md")]
        def falla_push(args):
            raise SystemExit("[!!] Jira rechazo el cierre")

        with mock.patch.object(gate, "git_merge", return_value="def456"), \
             mock.patch.object(atlassian, "cmd_push", side_effect=falla_push):
            rc, out, err = self.cli_gate(
                "close", "--feature", "7", "--status", "done", "--to", "main",
                "--publicar-atlassian")

        self.assertNotEqual(rc, 0)
        prd = (self.root / "docs" / "prd" / "PRD-master.md").read_text(encoding="utf-8")
        sdd = (self.root / "docs" / "sdd.md").read_text(encoding="utf-8")
        self.assertIn("No hay features cerradas todavia", prd)
        self.assertIn("No hay features cerradas todavia", sdd)
        self.assertNotIn("Feature #7 - Historial vivo", prd)
        self.assertNotIn("Feature #7 - Historial vivo", sdd)
        self.assertEqual(previous, [(self.root / "docs" / name).read_bytes() for name in ("prd/PRD-master.md", "sdd.md")])


if __name__ == "__main__":
    unittest.main()
