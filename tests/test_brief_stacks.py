"""El brief y el briefing del revisor anuncian el stack de CADA repo de la feature.

Antes detectaban uno solo: el arbol de la feature o el primer microservicio bajo
la raiz. En un proyecto con el front en la raiz y los servicios fuera de ella,
el brief anunciaba el stack del front y callaba el de los servicios: el
implementer no recibia sus reglas ni sus skills, y el revisor auditaba todo con
la norma de un solo stack.

Vale para cualquier combinacion de stacks; aqui se usan tres distintos.
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

import contexto  # noqa: E402
import stack  # noqa: E402
from comun import load_backlog, micros_declarados, paths  # noqa: E402

SPEC = ("# Spec - Feature #1: cobro\n\nEstado: draft\n\n"
        "## Criterios de aceptacion\n\n"
        "- AC-1: dado un carro, cuando pago, entonces cobra. `verificar: true`\n\n"
        "## Fuera de alcance\n\nFacturas.\n")


def escribir(ruta: Path, texto: str = "") -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


class Proyecto(unittest.TestCase):
    """Front Angular en la raiz; un servicio Go y uno Rust fuera de ella; uno Python dentro."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = self.tmp / "front"
        self.micros = self.tmp / "servicios"
        escribir(self.root / "angular.json", "{}")
        escribir(self.root / "package.json", json.dumps({"dependencies": {"@angular/core": "19.0.0"}}))
        escribir(self.micros / "ms-pagos" / "go.mod", "module example.com/ms-pagos\n")
        escribir(self.micros / "ms-media" / "go.mod", "module example.com/ms-media\n")
        escribir(self.micros / "ms-motor" / "Cargo.toml", "[package]\nname = 'ms-motor'\n")
        escribir(self.micros / "ms-motor" / "src" / "main.rs", "fn main() {}\n")
        escribir(self.root / "ms-datos" / "pyproject.toml",
                 "[project]\nname = 'ms-datos'\ndependencies = ['fastapi', 'polars']\n")
        escribir(self.root / "ms-datos" / "src" / "datos" / "domain" / "a.py")
        escribir(self.root / "harness" / "grafos.json", json.dumps({"raices": [
            {"nombre": "front", "path": "."}, {"nombre": "servicios", "path": str(self.micros)}]}))
        (self.root / "docs").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def lineas(self, microservicios, rules=None) -> str:
        f = {"id": 1, "name": "cobro", "status": "in_progress", "microservicios": microservicios}
        data = {"rules": rules or {}, "features": [f]}
        escribir(self.root / "harness" / "feature_list.json", json.dumps(data))
        p = paths(self.root)
        return "\n".join(contexto._lineas_stack(p, load_backlog(p), f, micros_declarados(f)))


class BriefTests(Proyecto):
    def test_anuncia_el_stack_del_arbol_y_el_de_cada_microservicio(self):
        out = self.lineas(["ms-pagos", "ms-motor", "ms-datos"])
        self.assertIn("stack detectado: ", out)
        self.assertIn("(angular-product", out)
        self.assertIn("ms-pagos: ", out)
        self.assertIn("(golang-hexagonal)", out)
        self.assertIn("ms-motor: ", out)
        self.assertIn("(rust-hexagonal)", out)
        self.assertIn("ms-datos: ", out)
        self.assertIn("(python-dataproduct)", out)

    def test_un_microservicio_fuera_de_la_raiz_se_encuentra_por_grafos_json(self):
        out = self.lineas(["ms-pagos"])
        self.assertIn(str(self.micros / "ms-pagos"), out)

    def test_cada_stack_trae_sus_propias_reglas_y_skills(self):
        out = self.lineas(["ms-pagos"])
        bloque = out.split("ms-pagos: ")[1]
        self.assertIn("reglas: architecture.md", bloque)
        self.assertIn("add-persistence", bloque, "una skill que solo tiene el stack Go")

    def test_dos_repos_del_mismo_stack_no_repiten_la_lista(self):
        out = self.lineas(["ms-pagos", "ms-media"])
        self.assertEqual(1, out.count("add-persistence"))
        self.assertIn("mismas reglas y skills de golang-hexagonal", out.split("ms-media: ")[1])

    def test_avisa_si_las_reglas_del_stack_no_estan_instaladas_en_ese_repo(self):
        self.assertIn("NO instaladas", self.lineas(["ms-pagos"]))
        stack.normalizar_repositorio(self.micros / "ms-pagos", "golang-hexagonal", rules={})
        self.assertNotIn("NO instaladas", self.lineas(["ms-pagos"]))

    def test_un_microservicio_sin_repo_se_dice_y_no_se_calla(self):
        out = self.lineas(["ms-pagos", "portal (admin)", "ms-fantasma"])
        self.assertIn("sin repo localizable: portal, ms-fantasma", out)

    def test_las_skills_excluidas_por_el_proyecto_no_se_anuncian(self):
        regla = {"stack_skills_excluidas": {"golang-hexagonal": ["add-persistence"]}}
        self.assertNotIn("add-persistence", self.lineas(["ms-pagos"], regla))

    def test_sin_microservicios_solo_se_anuncia_el_arbol(self):
        out = self.lineas([])
        self.assertIn("(angular-product", out)
        self.assertNotIn("otros repos de la feature", out)

    def test_si_la_raiz_no_tiene_stack_se_anuncia_el_del_primer_repo_que_si(self):
        """Raiz multi-repo sin stack propio. El modo pair ya no sale de aqui: lo registra
        worktree.py start para cualquier repo (tests/test_pair_y_reglas.py)."""
        (self.root / "angular.json").unlink()
        (self.root / "package.json").unlink()
        out = self.lineas(["ms-datos"])
        self.assertIn("stack detectado: ", out)
        self.assertIn("(python-dataproduct", out)
        self.assertIn("· en ms-datos", out)
        self.assertNotIn("modo pair", out)


class BriefingRevisorTests(Proyecto):
    def test_el_briefing_trae_la_normativa_de_cada_stack_con_sus_repos(self):
        f = {"id": 1, "name": "cobro", "status": "in_progress",
             "microservicios": ["ms-pagos", "ms-media", "ms-motor"]}
        escribir(self.root / "harness" / "feature_list.json",
                 json.dumps({"rules": {"rama_base": "main"}, "features": [f]}))
        escribir(self.root / "docs" / "spec-feature-1-cobro.md", SPEC)
        env = dict(os.environ, HARNESS_SIN_CONTEXTO="1")
        r = subprocess.run([sys.executable, str(SCRIPTS / "revision.py"), "--feature", "1", "--briefing"],
                           cwd=str(self.root), capture_output=True, text=True, env=env)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("Stack detectado: angular-product", r.stdout)
        self.assertIn("Stack detectado: golang-hexagonal", r.stdout)
        self.assertIn("en: ms-pagos, ms-media", r.stdout)
        self.assertIn("Stack detectado: rust-hexagonal", r.stdout)
        self.assertEqual(1, r.stdout.count("Stack detectado: golang-hexagonal"),
                         "la normativa va una vez por stack, no una por repo")


if __name__ == "__main__":
    unittest.main()
