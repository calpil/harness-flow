"""Bajas frontend de un proyecto Angular de raiz (tests en src/, no en projects/<nombre>/)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import retiros  # noqa: E402


class ProyectoDeRaiz(unittest.TestCase):
    def test_un_proyecto_de_raiz_declara_sus_tests_en_src(self):
        item = ["angular:front-admin-dashboard", "src/app/layouts/admin-shell/menu-por-rol.spec.ts",
                "el menu de admin agrega Facturas y SII al de staff"]
        self.assertIsNone(retiros._motivo_frontend(item))

    def test_bajo_projects_solo_vale_la_carpeta_del_proyecto(self):
        self.assertIn("viven bajo projects/otro/",
                      retiros._motivo_frontend(["angular:otro", "projects/app/src/x.spec.ts", "x"]))
        self.assertIsNone(retiros._motivo_frontend(["angular:app", "projects/app/src/x.spec.ts", "x"]))

    def test_las_demas_reglas_siguen(self):
        self.assertIsNotNone(retiros._motivo_frontend(["angular:app", "src/../x.spec.ts", "x"]))
        self.assertIsNotNone(retiros._motivo_frontend(["angular:app", "/src/x.spec.ts", "x"]))
        self.assertIsNotNone(retiros._motivo_frontend(["angular:app", "src/x.spec.ts", "a\nb"]))


if __name__ == "__main__":
    unittest.main()
