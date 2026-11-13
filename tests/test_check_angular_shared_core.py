"""El verificador Angular mide que `shared/**` y `core/**` no importen `features/**`.

Hueco (ADR, 2026-11-13, ficha #200): la regla de la #156 dice que `core/` y
`shared/` no importan nunca de `features/`; lo que otra feature o `shared`
necesita se promueve a `shared/<area>/`. `check-architecture.py` recorria solo
`src/app/features/**`, asi que decia `[ARCH-OK]` con `shared/cuenta/olvido-cuenta.ts`
importando cuatro stores de `features/cuenta/application/`.

Contrato: en CADA aplicacion del workspace, un import relativo de un `*.ts` de
`src/app/shared/**` o `src/app/core/**` que resuelve dentro de `src/app/features/`
sale con exit 1 y nombra el archivo y `shared -> features` o `core -> features`.
La direccion contraria (`features/` usa `shared/` y `core/`) sigue permitida, y
los `*.spec.ts` no se miden, como en `features/`.
"""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

CHECK_NG = (Path(__file__).resolve().parents[1] / "assets" / "stacks" / "angular-product"
            / "scripts" / "check-architecture.py")

APPS = ("storefront", "admin", "cafeterias")


def escribir(p: Path, texto: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texto, encoding="utf-8")


def correr(raiz: Path):
    return subprocess.run([sys.executable, str(CHECK_NG), "--repo", str(raiz)],
                          capture_output=True, text=True)


class SharedCoreNoImportanFeaturesTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="ng-shared-core-")
        self.addCleanup(tmp.cleanup)
        self.raiz = Path(tmp.name) / "front"
        proyectos = {n: {"projectType": "application", "root": f"projects/{n}",
                         "sourceRoot": f"projects/{n}/src"} for n in APPS}
        proyectos["ui"] = {"projectType": "library", "root": "projects/ui"}
        escribir(self.raiz / "angular.json", json.dumps({"projects": proyectos}))
        for n in APPS:
            app = self.app(n)
            escribir(app / "app.routes.ts", "export const routes = [];\n")
            # Una feature limpia que usa shared y core: la direccion permitida.
            escribir(app / "features" / "inicio" / "ui" / "inicio.ts",
                     "import { util } from '../../../shared/util';\n"
                     "import { sesion } from '../../../core/sesion';\n"
                     "export const Inicio = [util, sesion];\n")
            escribir(app / "shared" / "util.ts",
                     "import { signal } from '@angular/core';\nexport const util = signal(1);\n")
            escribir(app / "core" / "sesion.ts",
                     "import { util } from '../shared/util';\nexport const sesion = util;\n")

    def app(self, nombre: str) -> Path:
        return self.raiz / "projects" / nombre / "src" / "app"

    def sonda(self, nombre: str, carpeta: str, destino: str = "../features/inicio/ui/inicio") -> Path:
        ruta = self.app(nombre) / carpeta / "zz-sonda.ts"
        escribir(ruta, f"import {{ Inicio }} from '{destino}';\nexport const sonda = Inicio;\n")
        return ruta

    def test_shared_que_importa_features_falla_y_nombra_el_archivo(self):
        self.sonda("storefront", "shared")
        r = correr(self.raiz)
        self.assertEqual(1, r.returncode, "un shared que importa features paso en verde")
        self.assertIn("storefront/src/app/shared/zz-sonda.ts", r.stderr)
        self.assertIn("shared -> features", r.stderr)

    def test_core_que_importa_features_falla_y_nombra_el_archivo(self):
        self.sonda("storefront", "core")
        r = correr(self.raiz)
        self.assertEqual(1, r.returncode, "un core que importa features paso en verde")
        self.assertIn("storefront/src/app/core/zz-sonda.ts", r.stderr)
        self.assertIn("core -> features", r.stderr)

    def test_la_regla_corre_en_cada_aplicacion_del_workspace(self):
        """No solo la primera app: admin y cafeterias se miden igual."""
        for nombre in APPS:
            for carpeta in ("shared", "core"):
                with self.subTest(app=nombre, carpeta=carpeta):
                    sonda = self.sonda(nombre, carpeta)
                    r = correr(self.raiz)
                    sonda.unlink()
                    self.assertEqual(1, r.returncode, f"{nombre}/{carpeta} -> features paso en verde")
                    self.assertIn(f"projects/{nombre}/src/app/{carpeta}/zz-sonda.ts", r.stderr)
                    self.assertIn(f"{carpeta} -> features", r.stderr)

    def test_import_profundo_desde_un_subdirectorio_de_shared_falla(self):
        """`shared/cuenta/x.ts` -> `../../features/...`: es el caso real de olvido-cuenta."""
        ruta = self.app("storefront") / "shared" / "cuenta" / "olvido-cuenta.ts"
        escribir(ruta, "import { Inicio } from '../../features/inicio/ui/inicio';\nexport const O = Inicio;\n")
        r = correr(self.raiz)
        self.assertEqual(1, r.returncode)
        self.assertIn("storefront/src/app/shared/cuenta/olvido-cuenta.ts", r.stderr)
        self.assertIn("shared -> features (../../features/inicio/ui/inicio)", r.stderr)

    def test_workspace_limpio_pasa_y_nombra_las_tres_aplicaciones(self):
        """Control positivo: features usa shared y core, y shared/core se usan entre si,
        de `@angular` y de paquetes (la regla no es un rechazo a todo)."""
        r = correr(self.raiz)
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertIn("[ARCH-OK]", r.stdout)
        self.assertIn("Aplicaciones verificadas (3): storefront, admin, cafeterias", r.stdout)

    def test_un_spec_de_shared_no_se_mide(self):
        escribir(self.app("storefront") / "shared" / "util.spec.ts",
                 "import { Inicio } from '../features/inicio/ui/inicio';\nexport const s = Inicio;\n")
        r = correr(self.raiz)
        self.assertEqual(0, r.returncode, r.stderr)


if __name__ == "__main__":
    unittest.main()
