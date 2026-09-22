"""Advertencias de Git no son cambios pendientes, ramas ni SHAs."""
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import comun
import gate


WARNING = "git: warning: could not determine temporary directory; using /tmp instead\n"


class GitDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        self.real_run = subprocess.run
        self.raw("init", "-q", "-b", "develop")
        self.raw("config", "user.name", "Fixture")
        self.raw("config", "user.email", "fixture@example.invalid")
        self.raw("config", "commit.gpgsign", "false")
        self.raw("config", "core.hooksPath", str(self.repo / "no-hooks"))
        self.raw("commit", "-qm", "base", "--allow-empty")
        self.raw("checkout", "-qb", "feature/fixture")
        (self.repo / "feature.txt").write_text("feature\n", encoding="utf-8")
        self.raw("add", "feature.txt")
        self.raw("commit", "-qm", "feature")
        self.source = self.raw("rev-parse", "HEAD").stdout.strip()
        self.raw("checkout", "-q", "develop")

    def raw(self, *args):
        return self.real_run(["git", *args], cwd=self.repo, capture_output=True,
                             text=True, check=True)

    def with_warning(self, *args, **kwargs):
        result = self.real_run(*args, **kwargs)
        result.stderr += WARNING
        return result

    def test_cierre_integra_arbol_limpio_aunque_git_emita_advertencias(self):
        diagnostics = io.StringIO()
        with mock.patch.object(comun.subprocess, "run", side_effect=self.with_warning), \
                contextlib.redirect_stderr(diagnostics):
            sha = gate.git_merge({"root": self.repo}, {"id": "1", "branch": "feature/fixture"}, "develop")
        self.assertEqual(sha, self.raw("rev-parse", "--short", "HEAD").stdout.strip())
        self.raw("merge-base", "--is-ancestor", self.source, "develop")
        self.assertEqual(self.raw("status", "--porcelain").stdout, "")
        self.assertIn(WARNING, diagnostics.getvalue())

    def test_cierre_sigue_bloqueando_cambios_reales(self):
        (self.repo / "sin-commit.txt").write_text("pendiente\n", encoding="utf-8")
        before = self.raw("rev-parse", "HEAD").stdout
        with mock.patch.object(comun.subprocess, "run", side_effect=self.with_warning), \
                contextlib.redirect_stderr(io.StringIO()), \
                self.assertRaisesRegex(SystemExit, "sin commitear"):
            gate.git_merge({"root": self.repo}, {"id": "1", "branch": "feature/fixture"}, "develop")
        self.assertEqual(self.raw("rev-parse", "HEAD").stdout, before)

    def test_stdout_conserva_el_formato_porcelain(self):
        self.raw("checkout", "-q", "feature/fixture")
        (self.repo / "feature.txt").write_text("modificado\n", encoding="utf-8")
        with mock.patch.object(comun.subprocess, "run", side_effect=self.with_warning), \
                contextlib.redirect_stderr(io.StringIO()):
            code, output = comun.git(["status", "--porcelain"], self.repo)
        self.assertEqual(code, 0)
        self.assertEqual(output, " M feature.txt\n")

    def test_error_preserva_stdout_y_stderr(self):
        result = subprocess.CompletedProcess(["git", "merge"], 1,
                                             stdout="CONFLICT: fixture\n", stderr="merge failed\n")
        with mock.patch.object(comun.subprocess, "run", return_value=result):
            code, output = comun.git(["merge", "feature/fixture"], self.repo)
        self.assertEqual(code, 1)
        self.assertIn("CONFLICT: fixture", output)
        self.assertIn("merge failed", output)


if __name__ == "__main__":
    unittest.main()
