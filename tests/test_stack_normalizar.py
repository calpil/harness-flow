"""Regresiones de `stack.py normalizar` sobre decisiones del usuario.

Dos cosas que la normalizacion deshacia en un proyecto real, y que `estado.py`
repetia sola en cada arranque de sesion:

1. Reemplazaba un `AGENTS.md` existente por la plantilla del stack si el texto
   no contenia la palabra "CALPIL". El del proyecto se perdia entero.
2. Reinstalaba las skills del stack que el usuario habia quitado porque no
   aplican al proyecto: para la herramienta "faltaban".

La salida es `rules.stack_skills_excluidas` en `harness/feature_list.json`:
`{"<stack-id>": ["<skill>", ...]}`. Un valor que no se entiende no apaga la
regla ni instala nada: se niega y lo dice.
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

GO = "golang-hexagonal"
EXCLUIDA = "prepare-release"
REGLA = {"stack_skills_excluidas": {GO: [EXCLUIDA]}}
PROPIO = "# AGENTS.md del proyecto\n\nProceso propio: no usar Vitest.\n"


def instalada(repo: Path, skill: str) -> bool:
    return any((repo / raiz / "skills" / skill).exists() for raiz in (".claude", ".agents"))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def repo_go(self, nombre: str = "ms-pagos", dentro_de: Path | None = None) -> Path:
        repo = (dentro_de or self.tmp) / nombre
        repo.mkdir(parents=True)
        (repo / "go.mod").write_text(f"module example.com/{nombre}\n", encoding="utf-8")
        return repo

    def proyecto(self, rules: dict) -> tuple[Path, dict]:
        """Raiz con arnes que ademas es el repo Go: el caso de un solo repo."""
        raiz = self.repo_go("proyecto")
        (raiz / "harness").mkdir()
        (raiz / "docs").mkdir()
        data = {"project": "proyecto", "rules": rules, "features": []}
        (raiz / "harness" / "feature_list.json").write_text(json.dumps(data), encoding="utf-8")
        return raiz, data


class AgentsMdTests(Base):
    def test_un_agents_md_existente_no_se_reemplaza(self):
        repo = self.repo_go()
        (repo / "AGENTS.md").write_text(PROPIO, encoding="utf-8")
        stack.normalizar_repositorio(repo, GO, rules={})
        self.assertEqual(PROPIO, (repo / "AGENTS.md").read_text(encoding="utf-8"))

    def test_conservarlo_se_avisa_y_no_se_cuenta_como_instalado(self):
        repo = self.repo_go()
        (repo / "AGENTS.md").write_text(PROPIO, encoding="utf-8")
        res = stack.normalizar_repositorio(repo, GO, rules={})
        self.assertTrue(any("AGENTS.md" in w for w in res["warnings"]), res["warnings"])
        self.assertFalse(any("AGENTS.md" in a for a in res["actions"]), res["actions"])

    def test_sin_agents_md_se_genera_el_del_stack(self):
        repo = self.repo_go()
        res = stack.normalizar_repositorio(repo, GO, rules={})
        self.assertIn("CALPIL", (repo / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertTrue(any("AGENTS.md" in a for a in res["actions"]))

    def test_dry_run_no_escribe_agents_md(self):
        repo = self.repo_go()
        stack.normalizar_repositorio(repo, GO, dry_run=True, rules={})
        self.assertFalse((repo / "AGENTS.md").exists())

    def test_el_arranque_de_sesion_no_lo_pisa_ni_entra_en_bucle(self):
        raiz, data = self.proyecto({})
        (raiz / "AGENTS.md").write_text(PROPIO, encoding="utf-8")
        stack.auto_normalizar_y_asegurar_cumplimiento(raiz, data)
        segunda = stack.auto_normalizar_y_asegurar_cumplimiento(raiz, data)
        self.assertEqual(PROPIO, (raiz / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertEqual([], segunda["nivel_1_acciones"])


class SkillsExcluidasTests(Base):
    def test_normalizar_no_instala_la_skill_excluida(self):
        repo = self.repo_go()
        res = stack.normalizar_repositorio(repo, GO, rules=REGLA)
        self.assertFalse(instalada(repo, EXCLUIDA))
        self.assertTrue(instalada(repo, "add-feature"), "las demas se instalan igual")
        self.assertEqual([EXCLUIDA], res["skills_excluidas"])

    def test_sin_la_regla_la_skill_si_se_instala(self):
        """El control: si esto no instalara nada, el test de arriba pasaria vacio."""
        repo = self.repo_go()
        stack.normalizar_repositorio(repo, GO, rules={})
        self.assertTrue(instalada(repo, EXCLUIDA))

    def test_verificar_no_cuenta_la_excluida_como_faltante(self):
        repo = self.repo_go()
        stack.normalizar_repositorio(repo, GO, rules=REGLA)
        con = stack.verificar_cumplimiento(repo, GO, rules=REGLA)
        sin = stack.verificar_cumplimiento(repo, GO, rules={})
        self.assertTrue(con["skills_ok"], con["missing_skills"])
        self.assertTrue(con["multi_llm_ready"])
        self.assertEqual([EXCLUIDA], con["skills_excluidas"])
        self.assertEqual([EXCLUIDA], sin["missing_skills"], "sin la regla, sigue faltando")

    def test_la_regla_de_otro_stack_no_aplica(self):
        repo = self.repo_go()
        stack.normalizar_repositorio(repo, GO, rules={"stack_skills_excluidas": {"angular-product": [EXCLUIDA]}})
        self.assertTrue(instalada(repo, EXCLUIDA))

    def test_una_skill_retirada_no_vuelve_en_el_arranque_de_sesion(self):
        """El caso real: instalada, el usuario la quita, y estado.py la reponia."""
        raiz, data = self.proyecto({})
        stack.auto_normalizar_y_asegurar_cumplimiento(raiz, data)
        self.assertTrue(instalada(raiz, EXCLUIDA))
        for base in (".claude", ".agents"):
            shutil.rmtree(raiz / base / "skills" / EXCLUIDA)
        data["rules"].update(REGLA)

        res = stack.auto_normalizar_y_asegurar_cumplimiento(raiz, data)
        self.assertFalse(instalada(raiz, EXCLUIDA))
        self.assertEqual([], res["nivel_1_acciones"])

    def test_sin_la_regla_el_arranque_de_sesion_la_repone(self):
        """El control del test anterior."""
        raiz, data = self.proyecto({})
        stack.auto_normalizar_y_asegurar_cumplimiento(raiz, data)
        for base in (".claude", ".agents"):
            shutil.rmtree(raiz / base / "skills" / EXCLUIDA)
        stack.auto_normalizar_y_asegurar_cumplimiento(raiz, data)
        self.assertTrue(instalada(raiz, EXCLUIDA))

    def test_la_regla_se_lee_del_arnes_que_contiene_al_repo(self):
        raiz = self.tmp / "proyecto"
        (raiz / "harness").mkdir(parents=True)
        (raiz / "harness" / "feature_list.json").write_text(
            json.dumps({"rules": REGLA, "features": []}), encoding="utf-8")
        repo = self.repo_go("ms-pagos", dentro_de=raiz)
        stack.normalizar_repositorio(repo, GO)
        self.assertFalse(instalada(repo, EXCLUIDA))

    def test_la_cli_lee_la_regla_del_proyecto_donde_se_corre(self):
        """Los microservicios viven fuera de la raiz del arnes: cuenta el cwd."""
        raiz, _ = self.proyecto(REGLA)
        repo = self.repo_go("ms-afuera")
        r = subprocess.run(
            [sys.executable, str(RAIZ / "scripts" / "stack.py"), "normalizar",
             "--repo", str(repo), "--stack", GO],
            cwd=str(raiz), capture_output=True, text=True, timeout=120)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertFalse(instalada(repo, EXCLUIDA))
        self.assertIn(EXCLUIDA, r.stdout)

    def test_una_skill_excluida_que_no_existe_en_el_stack_se_avisa(self):
        repo = self.repo_go()
        mal = {"stack_skills_excluidas": {GO: ["prepare-relase"]}}
        diag = stack.verificar_cumplimiento(repo, GO, rules=mal)
        self.assertTrue(any("prepare-relase" in w for w in diag["warnings"]), diag["warnings"])


class ReglaMalFormadaTests(Base):
    MALAS = (
        {"stack_skills_excluidas": [EXCLUIDA]},
        {"stack_skills_excluidas": {GO: EXCLUIDA}},
        {"stack_skills_excluidas": {GO: [EXCLUIDA, 7]}},
        {"stack_skills_excluidas": "todas"},
    )

    def test_normalizar_y_verificar_se_niegan(self):
        for rules in self.MALAS:
            with self.subTest(rules=rules):
                repo = self.repo_go(f"ms-{self.MALAS.index(rules)}")
                with self.assertRaises(ValueError):
                    stack.normalizar_repositorio(repo, GO, rules=rules)
                with self.assertRaises(ValueError):
                    stack.verificar_cumplimiento(repo, GO, rules=rules)
                self.assertFalse((repo / ".claude").exists(), "no instala nada si no entiende la regla")

    def test_el_arranque_de_sesion_no_instala_y_lo_dice(self):
        raiz, data = self.proyecto(self.MALAS[0])
        res = stack.auto_normalizar_y_asegurar_cumplimiento(raiz, data)
        self.assertFalse((raiz / ".claude").exists())
        self.assertTrue(any("stack_skills_excluidas" in m for m in res["nivel_1_acciones"]),
                        res["nivel_1_acciones"])

    def test_la_cli_sale_con_error(self):
        raiz, _ = self.proyecto(self.MALAS[1])
        r = subprocess.run(
            [sys.executable, str(RAIZ / "scripts" / "stack.py"), "normalizar", "--stack", GO],
            cwd=str(raiz), capture_output=True, text=True, timeout=120)
        self.assertNotEqual(0, r.returncode)
        self.assertIn("stack_skills_excluidas", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
