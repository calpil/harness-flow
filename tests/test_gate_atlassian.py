"""El cierre puede publicar automaticamente en Atlassian cuando el usuario lo pide."""
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
import gate  # noqa: E402


class GateAtlassianTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.prev_cwd = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(lambda: os.chdir(self.prev_cwd))
        (self.root / "harness" / "progress").mkdir(parents=True)
        (self.root / "docs").mkdir()
        (self.root / "harness" / "atlassian.json").write_text(json.dumps({
            "site": "example.atlassian.net",
            "jira_project": "ADR",
            "confluence_space": "ARQ",
        }), encoding="utf-8")
        (self.root / "harness" / "feature_list.json").write_text(json.dumps({
            "project": "demo",
            "rules": {
                "require_spec_approved": False,
                "require_review": False,
                "require_leccion": False,
                "require_verify_green": False,
                "require_docs_al_dia": False,
            },
            "features": [{"id": 7, "name": "Publicar docs", "status": "in_progress", "branch": "feat/docs"}],
        }), encoding="utf-8")
        (self.root / "docs" / "spec-feature-7-publicar-docs.md").write_text(
            "Estado: approved\n\n- AC-1: publica docs\n", encoding="utf-8")
        (self.root / "docs" / "impl-7.md").write_text("## AC-1\nsrc/a.py:1\n", encoding="utf-8")

    def cli(self, *args):
        out = io.StringIO()
        err = io.StringIO()
        with mock.patch.object(sys, "argv", ["gate.py", *args]), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                gate.main()
                rc = 0
            except SystemExit as exc:
                rc = int(exc.code or 0) if isinstance(exc.code, int) else 1
        return rc, out.getvalue(), err.getvalue()

    def test_close_con_publicar_atlassian_dispara_push_de_jira_y_confluence(self):
        publicados = []
        def fake_push(args):
            publicados.append(args.feature)
        with mock.patch.object(gate, "git_merge", return_value="abc123"), \
             mock.patch.object(atlassian, "cmd_push", side_effect=fake_push):
            rc, out, err = self.cli(
                "close", "--feature", "7", "--status", "done", "--to", "main",
                "--publicar-atlassian")

        self.assertEqual(rc, 0, err)
        self.assertEqual(publicados, ["7"])
        self.assertIn("Atlassian", out)
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        self.assertEqual(data["features"][0]["status"], "done")
    def test_publicar_atlassian_sin_binding_no_cierra_feature(self):
        (self.root / "harness" / "atlassian.json").unlink()
        with mock.patch.object(gate, "git_merge", return_value="abc123") as merge:
            rc, out, err = self.cli(
                "close", "--feature", "7", "--status", "done", "--to", "main",
                "--publicar-atlassian")
        self.assertNotEqual(rc, 0)
        merge.assert_not_called()
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        self.assertEqual(data["features"][0]["status"], "in_progress")

    def test_fallo_publicando_atlassian_no_deja_done_en_backlog(self):
        def falla_push(args):
            raise SystemExit("[!!] Confluence rechazo la pagina")
        with mock.patch.object(gate, "git_merge", return_value="abc123"), \
             mock.patch.object(atlassian, "cmd_push", side_effect=falla_push):
            rc, out, err = self.cli(
                "close", "--feature", "7", "--status", "done", "--to", "main",
                "--publicar-atlassian")
        self.assertNotEqual(rc, 0)
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        feature = data["features"][0]
        self.assertEqual(feature["status"], "in_progress")
        self.assertNotIn("closed_at", feature)
        self.assertNotIn("integrado_en", feature)
        self.assertNotIn("merge_commit", feature)


if __name__ == "__main__":
    unittest.main()
