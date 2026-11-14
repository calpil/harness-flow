"""En Grok, el rol deja las rules y skills del stack en .grok/ de la sesion.

Un front en la raiz y un servicio fuera no comparten directorio. Grok no
camina al repo hermano: sin esta copia, la sesion del front no tiene las
skills del backend. La copia lleva marca, se ignora en git y el rol siguiente
sustituye el conjunto.
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
import grok_sesion  # noqa: E402
from comun import load_backlog, micros_declarados, paths  # noqa: E402

SPEC = ("# Spec\n\nEstado: draft\n\n## Criterios de aceptacion\n\n"
        "- AC-1: dado un carro, cuando pago, entonces cobra.\n")


def escribir(ruta: Path, texto: str = "") -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


class SesionGrokTests(unittest.TestCase):
    def setUp(self):
        self._host = os.environ.get("HARNESS_HOST")
        os.environ["HARNESS_HOST"] = "grok"
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = self.tmp / "front"
        self.go = self.tmp / "servicios" / "ms-pagos"
        self.wt = self.tmp / "wt-cobro"
        escribir(self.root / "angular.json", "{}")
        escribir(self.root / "package.json", json.dumps({"dependencies": {"@angular/core": "19.0.0"}}))
        escribir(self.go / "go.mod", "module example.com/ms-pagos\n")
        # El worktree es el arbol de la feature: tiene que traer el stack del front.
        escribir(self.wt / "angular.json", "{}")
        escribir(self.wt / "package.json", json.dumps({"dependencies": {"@angular/core": "19.0.0"}}))
        escribir(self.root / "harness" / "grafos.json", json.dumps({"raices": [
            {"nombre": "front", "path": "."},
            {"nombre": "servicios", "path": str(self.go.parent)}]}))
        escribir(self.root / "docs" / "spec-feature-1-cobro.md", SPEC)
        self.backlog({"id": 1, "name": "cobro", "status": "in_progress",
                      "microservicios": ["ms-pagos"], "worktree": str(self.wt)})
        self._git(self.root, "init")
        escribir(self.root / "README.md", "front\n")
        self._git(self.root, "add", "-A")
        self._git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "init")
        self.p = paths(self.root)

    def tearDown(self):
        if self._host is None:
            os.environ.pop("HARNESS_HOST", None)
        else:
            os.environ["HARNESS_HOST"] = self._host
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _git(self, repo: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(repo), *args], check=True,
                              capture_output=True, text=True)

    def backlog(self, feature: dict, rules: dict | None = None) -> None:
        escribir(self.root / "harness" / "feature_list.json",
                 json.dumps({"project": "demo", "rules": rules or {"rama_base": "main"},
                             "features": [feature]}))

    def reglas(self) -> str:
        data = load_backlog(self.p)
        f = data["features"][0]
        return "\n".join(contexto.lineas_reglas(self.p, data, f, micros_declarados(f)))

    def test_el_brief_publica_front_y_backend_en_la_raiz_el_servicio_y_el_worktree(self):
        out = self.reglas()
        self.assertIn("grok sesion (feature)", out)
        self.assertIn("angular-product", out)
        self.assertIn("golang-hexagonal", out)
        for base in (self.root, self.go, self.wt):
            go_skill = base / ".grok" / "skills" / "golang-hexagonal--add-api-endpoint" / "SKILL.md"
            ang_skill = base / ".grok" / "skills" / "angular-product--add-ui-component" / "SKILL.md"
            regla = base / ".grok" / "rules" / "golang-hexagonal--architecture.md"
            self.assertTrue(go_skill.is_file(), base)
            self.assertTrue(ang_skill.is_file(), base)
            self.assertIn("name: golang-hexagonal--add-api-endpoint", go_skill.read_text(encoding="utf-8"))
            self.assertIn("Stack golang-hexagonal.", go_skill.read_text(encoding="utf-8"))
            self.assertIn("Capa Domain", regla.read_text(encoding="utf-8"))
            self.assertIn("Rol: feature.",
                          (base / ".grok" / "rules" / "harness-flow-sesion.md").read_text(encoding="utf-8"))

    def test_la_copia_no_ensucia_git(self):
        self.reglas()
        estado = self._git(self.root, "status", "--porcelain")
        self.assertEqual("", estado.stdout)
        ignorada = subprocess.run(
            ["git", "-C", str(self.root), "check-ignore", "-q",
             ".grok/skills/golang-hexagonal--add-api-endpoint"],
            capture_output=True, text=True)
        self.assertEqual(0, ignorada.returncode, ignorada.stderr)

    def test_una_skill_excluida_no_se_copia_y_la_del_usuario_se_queda(self):
        mia = self.root / ".grok" / "skills" / "mia" / "SKILL.md"
        escribir(mia, "---\nname: mia\ndescription: La mia.\n---\n\n# Mia\n")
        self.backlog({"id": 1, "name": "cobro", "status": "in_progress",
                      "microservicios": ["ms-pagos"], "worktree": str(self.wt)},
                     {"rama_base": "main",
                      "stack_skills_excluidas": {"golang-hexagonal": ["add-persistence"]}})
        self.reglas()
        self.assertFalse((self.root / ".grok" / "skills" / "golang-hexagonal--add-persistence").exists())
        self.assertTrue((self.root / ".grok" / "skills" / "golang-hexagonal--add-api-endpoint").is_dir())
        self.assertTrue(mia.is_file())

    def test_el_rol_siguiente_retira_el_stack_que_ya_no_toca(self):
        self.reglas()
        self.assertTrue((self.root / ".grok" / "skills" / "golang-hexagonal--add-api-endpoint").is_dir())
        data = load_backlog(self.p)
        f = data["features"][0]
        f["microservicios"] = []
        self.backlog(f)
        self.reglas()
        self.assertFalse((self.root / ".grok" / "skills" / "golang-hexagonal--add-api-endpoint").exists())
        self.assertTrue((self.root / ".grok" / "skills" / "angular-product--add-ui-component").is_dir())
        self.assertFalse((self.wt / ".grok" / "skills" / "golang-hexagonal--add-api-endpoint").exists())

    def test_el_sdd_publica_el_proyecto_y_el_prd_no_lo_hace(self):
        os.environ["HARNESS_HOST"] = "claude"
        # Un arbol limpio, sin la copia de los tests de arriba: este caso crea el suyo.
        limpio = self.tmp / "limpio"
        shutil.copytree(self.root, limpio, ignore=shutil.ignore_patterns(".git", ".grok"))
        # copytree no llevo .git; el PRD no debe crear .grok
        env = dict(os.environ, HARNESS_HOST="claude", HARNESS_SIN_CONTEXTO="1",
                   HARNESS_SIN_HUB="1", HARNESS_SIN_CBM="1")
        r = subprocess.run([sys.executable, str(SCRIPTS / "producto.py"), "borrador", "--doc", "prd"],
                           cwd=str(limpio), capture_output=True, text=True, env=env)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertFalse((limpio / ".grok").exists())
        self.assertNotIn("grok sesion", r.stdout)

        os.environ["HARNESS_HOST"] = "grok"
        env["HARNESS_HOST"] = "grok"
        r = subprocess.run([sys.executable, str(SCRIPTS / "producto.py"), "borrador", "--doc", "sdd"],
                           cwd=str(limpio), capture_output=True, text=True, env=env)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("grok sesion (sdd)", r.stdout)
        self.assertTrue((limpio / ".grok" / "rules" / "angular-product--architecture.md").is_file())
        self.assertTrue((self.go / ".grok" / "skills" / "angular-product--add-ui-component").is_dir())

    def test_otro_host_no_escribe_grok(self):
        os.environ["HARNESS_HOST"] = "claude"
        self.reglas()
        self.assertFalse((self.root / ".grok").exists())
        self.assertNotIn("grok sesion", self.reglas())


if __name__ == "__main__":
    unittest.main()
