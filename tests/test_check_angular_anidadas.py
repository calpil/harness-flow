"""El verificador Angular mide tambien las features ANIDADAS.

Bug (realestate, 2026-11-10, review de la #248): `check-architecture.py`
tomaba `feature = parts[0]` y `layer = parts[1]` bajo `src/app/features`.
Una feature nueva anidada en una heredada (`condominios/camaras/ui/...`)
tenia `layer = "camaras"`, que no es una capa: el archivo se saltaba y el
verificador decia ARCH-OK sin medir nada. La `ui` de dos pantallas importaba
`data-access` directo y paso en verde; lo encontro el revisor a mano.

Contrato: la capa de un archivo es el PRIMER segmento de su ruta que sea
domain/application/data-access/ui, y la feature es todo lo anterior. El
codigo heredado sin capas sigue sin medirse, como antes.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECK_NG = (Path(__file__).resolve().parents[1] / "assets" / "stacks" / "angular-product"
            / "scripts" / "check-architecture.py")


def escribir(p: Path, texto: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texto, encoding="utf-8")


def correr(raiz: Path):
    return subprocess.run([sys.executable, str(CHECK_NG), "--repo", str(raiz)],
                          capture_output=True, text=True)


class FeaturesAnidadasTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="ng-anidadas-")
        self.addCleanup(tmp.cleanup)
        self.raiz = Path(tmp.name) / "front"
        app = self.raiz / "src" / "app"
        escribir(app / "app.routes.ts", "export const routes = [];\n")
        self.f = app / "features"
        # Codigo heredado sin capas: no se mide, como siempre.
        escribir(self.f / "condominios" / "mes" / "mes.component.ts",
                 "import { HttpClient } from '@angular/common/http';\nexport class Mes {}\n")
        # Feature nueva anidada, limpia.
        cam = self.f / "condominios" / "camaras"
        escribir(cam / "domain" / "camara.ts", "export interface Camara { id: number }\n")
        escribir(cam / "application" / "puerto.ts",
                 "import { Camara } from '../domain/camara';\nexport abstract class Puerto { abstract l(): Camara[] }\n")
        escribir(cam / "data-access" / "camaras.http.ts",
                 "import { Puerto } from '../application/puerto';\nexport class CamarasHttp extends Puerto { l() { return []; } }\n")
        escribir(cam / "ui" / "camaras.component.ts",
                 "import { Puerto } from '../application/puerto';\nexport class CamarasComponent { constructor(p: Puerto) {} }\n")

    def test_feature_anidada_limpia_pasa(self):
        r = correr(self.raiz)
        self.assertEqual(0, r.returncode, r.stderr)

    def test_ui_anidada_que_importa_data_access_falla(self):
        escribir(self.f / "condominios" / "camaras" / "ui" / "camaras.component.ts",
                 "import { CamarasHttp } from '../data-access/camaras.http';\nexport class C {}\n")
        r = correr(self.raiz)
        self.assertEqual(1, r.returncode, "una ui anidada que importa data-access paso en verde")
        self.assertIn("ui -> data-access", r.stderr)
        self.assertIn("condominios/camaras/ui/camaras.component.ts", r.stderr)

    def test_domain_anidado_con_angular_falla(self):
        escribir(self.f / "condominios" / "camaras" / "domain" / "camara.ts",
                 "import { signal } from '@angular/core';\nexport const s = signal(0);\n")
        r = correr(self.raiz)
        self.assertEqual(1, r.returncode)
        self.assertIn("domain no permite dependencia '@angular/core'", r.stderr)

    def test_application_anidada_que_importa_ui_falla(self):
        escribir(self.f / "condominios" / "camaras" / "application" / "puerto.ts",
                 "import { CamarasComponent } from '../ui/camaras.component';\nexport class P {}\n")
        r = correr(self.raiz)
        self.assertEqual(1, r.returncode)
        self.assertIn("application -> ui", r.stderr)

    def test_acceso_a_otra_feature_anidada_falla(self):
        escribir(self.f / "condominios" / "proveedores" / "data-access" / "prov.http.ts",
                 "export class ProvHttp {}\n")
        escribir(self.f / "condominios" / "camaras" / "ui" / "camaras.component.ts",
                 "import { ProvHttp } from '../../proveedores/data-access/prov.http';\nexport class C {}\n")
        r = correr(self.raiz)
        self.assertEqual(1, r.returncode)
        self.assertIn("acceso directo a otra feature 'condominios/proveedores'", r.stderr)

    def test_feature_anidada_puede_usar_codigo_heredado_de_su_padre(self):
        """Lo heredado sin capas no es otra feature: se mantiene como antes."""
        escribir(self.f / "condominios" / "errores.ts", "export const E = 1;\n")
        escribir(self.f / "condominios" / "camaras" / "ui" / "camaras.component.ts",
                 "import { E } from '../../errores';\nexport class C { e = E; }\n")
        r = correr(self.raiz)
        self.assertEqual(0, r.returncode, r.stderr)

    def test_feature_de_primer_nivel_sigue_igual(self):
        g = self.f / "gastos"
        escribir(g / "ui" / "g.component.ts", "import { GHttp } from '../data-access/g.http';\nexport class G {}\n")
        escribir(g / "data-access" / "g.http.ts", "export class GHttp {}\n")
        r = correr(self.raiz)
        self.assertEqual(1, r.returncode)
        self.assertIn("features/gastos/ui/g.component.ts: ui -> data-access", r.stderr)


if __name__ == "__main__":
    unittest.main()
