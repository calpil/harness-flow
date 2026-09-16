"""Regresiones del gate post-merge de integracion."""
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "postmerge.py"


class PostmergeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        (self.repo / "README.md").write_text("repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-q", "-m", "init"],
            cwd=self.repo,
            check=True,
        )

    def run_postmerge(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            capture_output=True,
        )

    def cmd_con_salida(self, texto: str) -> str:
        codigo = "import sys; sys.stdout.write(%r)" % texto
        return f"{shlex.quote(sys.executable)} -c {shlex.quote(codigo)}"

    def test_base_guarda_rojos_preexistentes(self):
        base = Path(self.tmp.name) / "base.json"
        cmd = self.cmd_con_salida("=== RUN   TestViejo\n--- FAIL: TestViejo (0.00s)\n")

        r = self.run_postmerge("base", "--repo", str(self.repo), "--cmd", cmd, "--guardar", str(base))

        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        data = json.loads(base.read_text(encoding="utf-8"))
        rama = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(data["rojos"], ["TestViejo"])
        self.assertEqual(data["rama"], rama)
        self.assertIn("base guardada", r.stdout)

    def test_check_pasa_si_solo_quedan_rojos_preexistentes(self):
        base = Path(self.tmp.name) / "base.json"
        base.write_text(json.dumps({"repo": str(self.repo), "rama": "master", "sha": "abc123", "rojos": ["TestViejo"]}), encoding="utf-8")
        cmd = self.cmd_con_salida("=== RUN   TestViejo\n--- FAIL: TestViejo (0.00s)\n")

        r = self.run_postmerge("check", "--repo", str(self.repo), "--cmd", cmd, "--base", str(base))

        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("no agrego rojos nuevos", r.stdout)

    def test_check_falla_si_el_merge_agrega_rojos_nuevos(self):
        base = Path(self.tmp.name) / "base.json"
        base.write_text(json.dumps({"repo": str(self.repo), "rama": "master", "sha": "abc123", "rojos": ["TestViejo"]}), encoding="utf-8")
        cmd = self.cmd_con_salida(
            "=== RUN   TestViejo\n--- FAIL: TestViejo (0.00s)\n"
            "=== RUN   TestNuevo\n--- FAIL: TestNuevo (0.00s)\n"
        )

        r = self.run_postmerge("check", "--repo", str(self.repo), "--cmd", cmd, "--base", str(base))

        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("agrego 1 rojo", r.stdout)
        self.assertIn("TestNuevo", r.stdout)

    def test_se_niega_a_opinar_si_no_hay_evidencia_de_ejecucion(self):
        base = Path(self.tmp.name) / "base.json"
        cmd = self.cmd_con_salida("no tests to run\n")

        r = self.run_postmerge("base", "--repo", str(self.repo), "--cmd", cmd, "--guardar", str(base))

        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertFalse(base.exists())
        self.assertIn("no reporto NI UN", r.stdout)

    def test_se_niega_si_go_reporta_ok_pero_no_corrio_tests(self):
        base = Path(self.tmp.name) / "base.json"
        cmd = self.cmd_con_salida("ok  \texample.com/pkg\t0.123s [no tests to run]\n")

        r = self.run_postmerge("base", "--repo", str(self.repo), "--cmd", cmd, "--guardar", str(base))

        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertFalse(base.exists())
        self.assertIn("no corrio", r.stdout)


if __name__ == "__main__":
    unittest.main()
