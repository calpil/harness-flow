"""El progreso vivo de una feature cerrada pasa a historial versionado."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import atlassian  # noqa: E402
import gate  # noqa: E402


class ProgressArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.prev_cwd = Path.cwd()
        import os
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
            "features": [{"id": 7, "name": "Historial vivo", "status": "in_progress", "branch": "feat/historial"}],
        }), encoding="utf-8")
        (self.root / "docs" / "spec-feature-7-historial-vivo.md").write_text(
            "Estado: approved\n\n- AC-1: conserva historial\n", encoding="utf-8")
        (self.root / "docs" / "impl-7.md").write_text("## AC-1\nsrc/a.py:1\n", encoding="utf-8")
        self.current = self.root / "harness" / "progress" / "current-7.md"
        self.current.write_text("# Progreso #7\n\n- decision: mantener historial\n", encoding="utf-8")

    def cli(self, *args):
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

    def feature(self):
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        return data["features"][0]

    def test_close_done_archiva_current_y_lo_linkea_en_feature_list(self):
        with mock.patch.object(gate, "git_merge", return_value="abc123"):
            rc, out, err = self.cli("close", "--feature", "7", "--status", "done", "--to", "main")

        self.assertEqual(rc, 0, err)
        archive = self.root / "harness" / "progress" / "archive" / "current-7.md"
        self.assertFalse(self.current.exists())
        self.assertTrue(archive.exists())
        self.assertIn("mantener historial", archive.read_text(encoding="utf-8"))
        feature = self.feature()
        self.assertEqual(feature["progress_archive"], "harness/progress/archive/current-7.md")
        history = (self.root / "harness" / "progress" / "history.md").read_text(encoding="utf-8")
        self.assertIn("progress #7 archivado", history)
        self.assertIn("archivado", out.lower())

    def test_close_blocked_mantiene_current_vivo(self):
        rc, out, err = self.cli("close", "--feature", "7", "--status", "blocked")

        self.assertEqual(rc, 0, err)
        self.assertTrue(self.current.exists())
        self.assertFalse((self.root / "harness" / "progress" / "archive" / "current-7.md").exists())
        self.assertNotIn("progress_archive", self.feature())

    def test_fallo_publicando_atlassian_no_archiva_current(self):
        (self.root / "harness" / "atlassian.json").write_text(json.dumps({
            "site": "example.atlassian.net",
            "jira_project": "ADR",
            "confluence_space": "ARQ",
        }), encoding="utf-8")
        def falla_push(args):
            raise SystemExit("[!!] Confluence rechazo la pagina")

        with mock.patch.object(gate, "git_merge", return_value="abc123"), \
             mock.patch.object(atlassian, "cmd_push", side_effect=falla_push):
            rc, out, err = self.cli(
                "close", "--feature", "7", "--status", "done", "--to", "main",
                "--publicar-atlassian")

        self.assertNotEqual(rc, 0)
        self.assertTrue(self.current.exists())
        self.assertFalse((self.root / "harness" / "progress" / "archive" / "current-7.md").exists())
        feature = self.feature()
        self.assertEqual(feature["status"], "in_progress")
        self.assertNotIn("progress_archive", feature)


if __name__ == "__main__":
    unittest.main()
