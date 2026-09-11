"""El gate de cierre exige una leccion que exista DE VERDAD.

Es el objetivo 4 del proceso: cerrar sin memoria procedural es un falso verde.
Aqui se ejercita la regla end-to-end, no solo la funcion buscar().
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


class GateLeccionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.raiz = self.home / "skills"
        (self.raiz / "cat" / "una-leccion").mkdir(parents=True)
        (self.raiz / "cat" / "una-leccion" / "SKILL.md").write_text(
            "---\nname: una-leccion\ndescription: real\n---\n", encoding="utf-8")

    def cerrar(self, leccion):
        """Invoca la regla de leccion del gate tal como la ejecuta cmd_close."""
        codigo = (
            "import sys; sys.path.insert(0, %r)\n"
            "from leccion import buscar\n"
            "print('BLOQUEA' if not buscar(%r) else 'PASA')\n" % (str(SCRIPTS), leccion)
        )
        env = dict(os.environ)
        env["HARNESS_SKILLS_DIR"] = str(self.raiz)
        env.pop("CLAUDECODE", None)
        env.pop("CLAUDE_CONFIG_DIR", None)
        r = subprocess.run([sys.executable, "-c", codigo], capture_output=True,
                           text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_leccion_real_pasa(self):
        self.assertEqual(self.cerrar("una-leccion"), "PASA")

    def test_leccion_inexistente_bloquea(self):
        self.assertEqual(self.cerrar("no-existe"), "BLOQUEA")

    def test_comodines_no_cuelan_una_leccion_cualquiera(self):
        # el falso verde original: close --leccion '*' pasaba el gate
        for comodin in ("*", "**", "?", "[a-z]*", "cat/*", "una-leccion*", "*leccion"):
            with self.subTest(comodin=comodin):
                self.assertEqual(self.cerrar(comodin), "BLOQUEA",
                                 "un comodin no es una leccion")

    def test_no_se_escapa_de_la_raiz_de_skills(self):
        for ruta in ("../../etc", "/etc/passwd", "cat/../../fuera"):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.cerrar(ruta), "BLOQUEA")


if __name__ == "__main__":
    unittest.main()
