"""La Feature #0 de normalizacion: que cubra lo que hay que normalizar y que se pueda medir.

Tres defectos de origen, reproducidos en un proyecto con un servicio Go y uno
Rust fuera de la raiz:

1. No declaraba a que repos aplica. El brief solo miraba el arbol de la raiz y
   salia sin las reglas del stack que habia que normalizar.
2. Cubria un solo stack: el primer repo con violaciones le daba nombre y spec,
   y los demas solo quedaban anotados como bloqueo.
3. Los comandos de sus AC no corrian: el verificador iba por una ruta relativa
   a la skill (`assets/stacks/...`), que desde el proyecto no existe, y el de
   tests era `go test ./...` tambien para un repo Rust.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"
sys.path.insert(0, str(SCRIPTS))

import comun  # noqa: E402
import contexto  # noqa: E402
import stack  # noqa: E402


def escribir(ruta: Path, texto: str = "") -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


class Proyecto(unittest.TestCase):
    """Raiz sin stack; fuera de ella, un servicio Go y uno Rust, los dos sin composition root."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = self.tmp / "front"
        self.micros = self.tmp / "servicios"
        self.go = self.micros / "ms-pagos"
        self.rust = self.micros / "ms-motor"
        escribir(self.go / "go.mod", "module example.com/ms-pagos\n")
        escribir(self.go / "main.go", "package main\nfunc main() {}\n")
        escribir(self.rust / "Cargo.toml", "[package]\nname = 'ms-motor'\n")
        escribir(self.rust / "src" / "lib.rs", "fn helper() {}\n")
        (self.root / "docs").mkdir(parents=True)
        escribir(self.root / "harness" / "grafos.json", json.dumps({"raices": [
            {"nombre": "front", "path": "."}, {"nombre": "servicios", "path": str(self.micros)}]}))
        self.data = {"project": "demo", "rules": {},
                     "features": [{"id": 1, "name": "cobro", "status": "todo"}]}
        self.guardar()
        self.p = comun.paths(self.root)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def guardar(self) -> None:
        escribir(self.root / "harness" / "feature_list.json", json.dumps(self.data))

    def normalizar(self) -> dict:
        res = stack.auto_normalizar_y_asegurar_cumplimiento(self.root, self.data)
        self.guardar()
        return res

    def f0(self) -> dict:
        return next(f for f in self.data["features"] if f["id"] == 0)

    def spec(self) -> str:
        return comun.spec_path(self.p, self.f0()).read_text(encoding="utf-8")

    def comandos(self) -> dict[str, str]:
        return comun.ac_comandos(self.spec())

    def correr(self, comando: str) -> subprocess.CompletedProcess:
        """Como lo corre gate.py verify: en un shell, con $PY y $H exportados."""
        env = dict(os.environ, PY=sys.executable, H=str(SCRIPTS))
        return subprocess.run(comando, shell=True, cwd=str(self.root), env=env,
                              capture_output=True, text=True, timeout=120)


class AlcanceTests(Proyecto):
    def test_declara_todos_los_repos_con_violaciones(self):
        self.assertTrue(self.normalizar()["f0_creada"])
        self.assertEqual(["ms-motor", "ms-pagos"], sorted(self.f0()["microservicios"]))

    def test_cubre_todos_los_stacks_afectados_y_no_solo_el_primero(self):
        self.normalizar()
        self.assertEqual(["golang-hexagonal", "rust-hexagonal"], sorted(self.f0()["stacks"]))
        texto = self.spec()
        self.assertIn("ms-pagos", texto)
        self.assertIn("ms-motor", texto)

    def test_con_varios_stacks_el_nombre_no_es_el_de_uno_solo(self):
        self.normalizar()
        self.assertEqual("normalizacion-arquitectura", self.f0()["name"])

    def test_con_un_solo_stack_conserva_el_nombre_de_ese_stack(self):
        shutil.rmtree(self.rust)
        self.normalizar()
        self.assertEqual("normalizacion-arquitectura-golang-hexagonal", self.f0()["name"])
        self.assertEqual(["ms-pagos"], self.f0()["microservicios"])

    def test_el_spec_queda_donde_los_gates_lo_buscan(self):
        self.normalizar()
        self.assertTrue(comun.spec_path(self.p, self.f0()).is_file())

    def test_el_brief_trae_las_reglas_de_cada_stack_a_normalizar(self):
        self.normalizar()
        f = self.f0()
        texto = "\n".join(contexto.lineas_reglas(self.p, self.data, f, comun.micros_declarados(f)))
        self.assertIn("REGLAS DEL STACK golang-hexagonal", texto)
        self.assertIn("REGLAS DEL STACK rust-hexagonal", texto)

    def test_una_violacion_nueva_en_otro_repo_se_suma_a_la_0_abierta(self):
        shutil.rmtree(self.rust)
        self.normalizar()
        spec_antes = self.spec()
        escribir(self.rust / "Cargo.toml", "[package]\nname = 'ms-motor'\n")
        escribir(self.rust / "src" / "lib.rs", "fn helper() {}\n")
        res = self.normalizar()
        self.assertFalse(res["f0_creada"], "no se crea una segunda")
        self.assertEqual(["ms-motor", "ms-pagos"], sorted(self.f0()["microservicios"]))
        self.assertEqual(spec_antes, self.spec(), "un spec ya escrito no se reescribe solo")


class ComandosDeLosAcTests(Proyecto):
    def setUp(self):
        super().setUp()
        self.normalizar()

    def test_hay_un_ac_de_arquitectura_y_uno_de_tests_por_repo(self):
        texto = self.spec()
        self.assertEqual(4, len(comun.spec_acs(texto)))
        self.assertEqual(4, len(self.comandos()))

    def test_ningun_comando_usa_la_ruta_relativa_a_la_skill(self):
        for ac, cmd in self.comandos().items():
            with self.subTest(ac=ac):
                self.assertNotIn("assets/stacks/", cmd)

    def test_el_comando_de_tests_es_el_del_stack_de_cada_repo(self):
        cmds = "\n".join(self.comandos().values())
        self.assertIn("cargo test", cmds)
        self.assertIn("go test", cmds)
        rust = next(c for c in self.comandos().values() if "cargo test" in c)
        self.assertIn(str(self.rust), rust, "corre en el repo Rust, no en la raiz")
        # "cargo test" contiene "go test": se busca el comando de Go, no la subcadena.
        self.assertNotRegex(rust, r"(?<![a-z])go test")
        go = next(c for c in self.comandos().values() if "go test" in c and "cargo" not in c)
        self.assertIn(str(self.go), go)

    def arquitectura_de(self, repo: Path) -> str:
        return next(c for c in self.comandos().values() if "stack.py" in c and str(repo) in c)

    def test_el_comando_de_arquitectura_corre_y_hoy_da_rojo(self):
        """El verde no es evidencia: tiene que poder fallar, y fallar por la violacion."""
        r = self.correr(self.arquitectura_de(self.go))
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)
        self.assertIn("Composition Root ausente", r.stdout + r.stderr)

    def test_y_da_verde_cuando_el_repo_queda_normalizado(self):
        escribir(self.go / "cmd" / "server" / "main.go", "package main\nfunc main() {}\n")
        r = self.correr(self.arquitectura_de(self.go))
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_normalizar_un_repo_no_pone_en_verde_el_ac_del_otro(self):
        escribir(self.go / "cmd" / "server" / "main.go", "package main\nfunc main() {}\n")
        self.assertEqual(1, self.correr(self.arquitectura_de(self.rust)).returncode)


class SubcomandoArquitecturaTests(Proyecto):
    def cli(self, *args) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPTS / "stack.py"), "arquitectura", *args],
                              cwd=str(self.root), capture_output=True, text=True, timeout=120)

    def test_devuelve_el_exit_del_verificador(self):
        self.assertEqual(1, self.cli("--repo", str(self.go)).returncode)
        escribir(self.go / "cmd" / "server" / "main.go", "package main\nfunc main() {}\n")
        self.assertEqual(0, self.cli("--repo", str(self.go)).returncode)

    def test_un_repo_sin_stack_no_devuelve_verde(self):
        """Un gate que no puede medir no devuelve verdadero."""
        vacio = self.tmp / "vacio"
        vacio.mkdir()
        r = self.cli("--repo", str(vacio))
        self.assertEqual(2, r.returncode)
        self.assertIn("no se pudo medir", r.stdout + r.stderr)

    def test_un_repo_que_no_existe_no_devuelve_verde(self):
        self.assertEqual(2, self.cli("--repo", str(self.tmp / "no-existe")).returncode)


if __name__ == "__main__":
    unittest.main()
