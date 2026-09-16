"""El gate post-merge viejo esta RETIRADO y debe negarse a opinar.

postmerge.py deducia el veredicto de un regex sobre la salida `-v` de `go test`
y nunca leia el exit code, asi que daba VERDE con un paquete que no compila, con
un panic en init() y con tests borrados; ademas identificaba los tests por nombre
sin paquete, con lo que un rojo nuevo se confundia con deuda tolerada de otro.

Los tests que vivian aqui certificaban ese gate (base/check sobre salidas `-v`
sinteticas): se eliminaron porque aseguraban el comportamiento equivocado —
pasaban en verde justo en los escenarios donde el gate mentia. Un gate que miente
es peor que ninguno, asi que el script sale 2 y apunta a postmerge_medido.py,
cuya cobertura real vive en test_measured_runner_go.py y test_measured_runner_json.py.
"""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "postmerge.py"


class PostmergeRetiradoTests(unittest.TestCase):
    def correr(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args],
                              text=True, capture_output=True)

    def test_no_emite_veredicto_en_ningun_subcomando(self):
        for args in ((), ("base", "--repo", ".", "--guardar", "/tmp/x.json"),
                     ("check", "--repo", ".", "--base", "/tmp/x.json")):
            with self.subTest(args=args):
                r = self.correr(*args)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                salida = r.stdout + r.stderr
                self.assertIn("RETIRADO", salida)
                self.assertNotIn("[ok]", salida,
                                 "el gate retirado no puede dar un verde")

    def test_apunta_al_reemplazo_medido(self):
        r = self.correr()
        self.assertIn("postmerge_medido.py", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
