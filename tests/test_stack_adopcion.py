"""Regresiones de los verificadores de stack ante proyectos reales.

Tres falsos positivos que salieron de un mismo proyecto:

1. Un workspace Angular con varios proyectos (`angular.json` -> `projects`)
   se verificaba en la raiz, donde no hay `src/app/app.routes.ts`: dos
   violaciones falsas y una Feature #0 que bloqueaba el backlog.
2. Un servicio Go sin `internal/` daba error. Con adopcion progresiva lo
   existente no se mueve: es un aviso, y dentro de `internal/` las reglas
   siguen siendo error.
3. `stack.py` leia las raices de `harness/grafos.json` como strings. El formato
   real son objetos `{"nombre", "path"}`: el TypeError se tragaba y el
   diagnostico caia a los subdirectorios de la raiz, sin ver los microservicios.

Los checkers se corren como procesos: lo que se mide es el exit code.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import stack  # noqa: E402

CHECK_GO = stack.STACKS_DIR / "golang-hexagonal" / "scripts" / "check-architecture.py"
CHECK_NG = stack.STACKS_DIR / "angular-product" / "scripts" / "check-architecture.py"


def correr(checker: Path, repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(checker), "--repo", str(repo)],
                          capture_output=True, text=True, timeout=60)


def escribir(ruta: Path, texto: str = "") -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class GoAdopcionProgresivaTests(Base):
    def _servicio(self, con_main: bool = True) -> Path:
        repo = self.tmp / "ms-legacy"
        escribir(repo / "go.mod", "module example.com/legacy\n")
        if con_main:
            escribir(repo / "cmd" / "server" / "main.go", "package main\nfunc main() {}\n")
        return repo

    def test_sin_internal_es_aviso_y_no_error(self):
        r = correr(CHECK_GO, self._servicio())
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertIn("[WARN]", r.stderr)
        self.assertIn("internal/", r.stderr)

    def test_el_verde_sin_internal_dice_que_no_midio_los_limites(self):
        """Un conteo parcial nunca se reporta como total."""
        r = correr(CHECK_GO, self._servicio())
        self.assertIn("NO medidos", r.stdout)

    def test_con_internal_el_dominio_impuro_sigue_siendo_error(self):
        repo = self._servicio()
        escribir(repo / "internal" / "pagos" / "domain" / "pago.go",
                 'package domain\n\nimport "net/http"\n\nvar _ = http.StatusOK\n')
        r = correr(CHECK_GO, repo)
        self.assertEqual(1, r.returncode)
        self.assertIn("domain no permite dependencia externa 'net/http'", r.stderr)

    def test_con_internal_application_no_importa_adapters(self):
        repo = self._servicio()
        escribir(repo / "internal" / "pagos" / "application" / "svc.go",
                 'package application\n\nimport (\n\t"example.com/legacy/internal/pagos/adapter/out"\n)\n')
        r = correr(CHECK_GO, repo)
        self.assertEqual(1, r.returncode)
        self.assertIn("application no debe importar adapters", r.stderr)

    def test_con_internal_limpio_no_anuncia_limites_sin_medir(self):
        repo = self._servicio()
        escribir(repo / "internal" / "pagos" / "domain" / "pago.go", "package domain\n")
        r = correr(CHECK_GO, repo)
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertNotIn("NO medidos", r.stdout)

    def test_sin_composition_root_sigue_siendo_error(self):
        r = correr(CHECK_GO, self._servicio(con_main=False))
        self.assertEqual(1, r.returncode)
        self.assertIn("Composition Root ausente", r.stderr)


class AngularWorkspaceTests(Base):
    def _app(self, ws: Path, raiz: str, con_rutas: bool = True, dominio: str = "export const x = 1;\n"):
        base = ws / raiz / "src" / "app"
        if con_rutas:
            escribir(base / "app.routes.ts", "export const routes = [];\n")
        escribir(base / "features" / "gastos" / "domain" / "gasto.ts", dominio)

    def _workspace(self, **apps) -> Path:
        ws = self.tmp / "front"
        proyectos = {
            "shared-ui": {"projectType": "library", "root": "projects/shared-ui",
                          "sourceRoot": "projects/shared-ui/src"},
        }
        for nombre, kw in apps.items():
            raiz = f"projects/{nombre}"
            proyectos[nombre] = {"projectType": "application", "root": raiz,
                                 "sourceRoot": f"{raiz}/src"}
            self._app(ws, raiz, **kw)
        escribir(ws / "projects" / "shared-ui" / "src" / "public-api.ts", "export {};\n")
        escribir(ws / "angular.json", json.dumps({"version": 1, "projects": proyectos}))
        return ws

    def test_workspace_con_varias_aplicaciones_limpias_pasa(self):
        """En la raiz no hay src/app: antes eran dos violaciones falsas."""
        ws = self._workspace(admin={}, portal={})
        r = correr(CHECK_NG, ws)
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertIn("admin", r.stdout)
        self.assertIn("portal", r.stdout)

    def test_el_verde_nombra_las_librerias_que_no_verifico(self):
        r = correr(CHECK_NG, self._workspace(admin={}))
        self.assertIn("NO verificadas", r.stdout)
        self.assertIn("shared-ui", r.stdout)

    def test_una_violacion_en_una_aplicacion_falla_y_dice_donde(self):
        ws = self._workspace(
            admin={},
            portal={"dominio": "import { signal } from '@angular/core';\nexport const s = signal(0);\n"})
        r = correr(CHECK_NG, ws)
        self.assertEqual(1, r.returncode)
        self.assertIn("projects/portal/src/app/features/gastos/domain/gasto.ts", r.stderr)
        self.assertNotIn("projects/admin/", r.stderr)

    def test_una_aplicacion_sin_composition_root_falla(self):
        ws = self._workspace(admin={}, portal={"con_rutas": False})
        r = correr(CHECK_NG, ws)
        self.assertEqual(1, r.returncode)
        self.assertIn("projects/portal/src/app/app.routes.ts", r.stderr)

    def test_stack_py_no_reporta_arquitectura_rota_por_la_raiz(self):
        """De aqui salia la Feature #0 falsa."""
        ws = self._workspace(admin={}, portal={})
        diag = stack.verificar_cumplimiento(ws, "angular-product")
        self.assertTrue(diag["architecture_ok"], diag.get("architecture_errors"))

    def test_proyecto_unico_en_la_raiz_se_verifica_como_siempre(self):
        ws = self.tmp / "front-simple"
        self._app(ws, ".")
        escribir(ws / "angular.json", json.dumps({"projects": {"app": {
            "projectType": "application", "root": "", "sourceRoot": "src"}}}))
        self.assertEqual(0, correr(CHECK_NG, ws).returncode)

    def test_sin_angular_json_la_raiz_sin_src_sigue_siendo_error(self):
        vacio = self.tmp / "vacio"
        vacio.mkdir()
        r = correr(CHECK_NG, vacio)
        self.assertEqual(1, r.returncode)
        self.assertIn("src/app/app.routes.ts", r.stderr)

    def test_un_proyecto_fuera_del_workspace_no_se_mide_en_silencio(self):
        ws = self.tmp / "front-fuga"
        escribir(ws / "angular.json", json.dumps({"projects": {"app": {
            "projectType": "application", "root": "../otro"}}}))
        r = correr(CHECK_NG, ws)
        self.assertEqual(1, r.returncode)
        self.assertIn("fuera del workspace", r.stderr)


class DestinosDeGrafosTests(Base):
    def _proyecto(self, raices) -> tuple[Path, Path]:
        front = self.tmp / "front"
        micros = self.tmp / "micros"
        escribir(front / "angular.json", json.dumps({"projects": {}}))
        escribir(front / "package.json", json.dumps({"dependencies": {"@angular/core": "19.0.0"}}))
        for ms in ("ms-pagos", "ms-egresos"):
            escribir(micros / ms / "go.mod", f"module example.com/{ms}\n")
        (micros / "notas").mkdir()  # sin marcadores: no es un repo
        escribir(front / "harness" / "grafos.json", json.dumps({"raices": raices(micros)}))
        return front, micros

    def test_raices_como_objetos_incluyen_los_microservicios(self):
        """El formato que documenta comun.grafos_config."""
        front, micros = self._proyecto(lambda m: [
            {"nombre": "front", "path": "."},
            {"nombre": "micros", "path": str(m)},
        ])
        rutas = {Path(d["path"]) for d in stack.detectar_todos_los_destinos(front)}
        self.assertIn(front, rutas)
        self.assertIn(micros / "ms-pagos", rutas)
        self.assertIn(micros / "ms-egresos", rutas)
        self.assertNotIn(micros / "notas", rutas)

    def test_los_microservicios_se_detectan_como_go(self):
        front, micros = self._proyecto(lambda m: [{"nombre": "micros", "path": str(m)}])
        por_ruta = {Path(d["path"]): d["stack"] for d in stack.detectar_todos_los_destinos(front)}
        self.assertEqual("golang-hexagonal", por_ruta[micros / "ms-pagos"])

    def test_raices_como_strings_siguen_funcionando(self):
        front, micros = self._proyecto(lambda m: [str(m / "ms-pagos")])
        rutas = {Path(d["path"]) for d in stack.detectar_todos_los_destinos(front)}
        self.assertEqual({micros / "ms-pagos"}, rutas)

    def test_una_raiz_no_se_repite(self):
        front, micros = self._proyecto(lambda m: [
            {"path": str(m)}, {"path": str(m / "ms-pagos")}])
        rutas = [Path(d["path"]) for d in stack.detectar_todos_los_destinos(front)]
        self.assertEqual(len(rutas), len(set(rutas)))


if __name__ == "__main__":
    unittest.main()
