"""El briefing del revisor fija QUE decide el veredicto y cuando parar.

Regla del usuario (2026-09-28): una feature con todos sus AC verdes paso cinco
rondas de review porque cada revisor salia a buscar mutantes nuevos y trataba
cualquier hallazgo menor como motivo de otra ronda. Desde entonces:
  - approved = cada AC cumplido y medido, sin hallazgos bloqueantes ni mayores;
  - lo menor e informativo va a Observaciones y NO abre ronda;
  - la ronda de seguimiento verifica lo que la anterior pidio y los AC, sin
    salir a buscar hallazgos nuevos; tope de dos rondas, lo mayor se escala.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def sh(*args, cwd):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, check=True)


def briefing(cwd):
    env = dict(os.environ, HARNESS_SIN_CONTEXTO="1")
    r = subprocess.run([sys.executable, str(SCRIPTS / "revision.py"), "--feature", "1",
                        "--briefing"], cwd=str(cwd), capture_output=True, text=True, env=env)
    return r.stdout + r.stderr


class RondasDeReviewTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / "repo"
        (self.repo / "harness").mkdir(parents=True)
        (self.repo / "docs").mkdir()
        sh("git", "init", "-q", "-b", "develop", ".", cwd=self.repo)
        sh("git", "config", "user.email", "t@t.invalid", cwd=self.repo)
        sh("git", "config", "user.name", "T", cwd=self.repo)
        (self.repo / "harness" / "feature_list.json").write_text(json.dumps(
            {"project": "t", "features": [{"id": "1", "name": "probar rondas"}]}),
            encoding="utf-8")
        (self.repo / "docs" / "spec-feature-1-probar-rondas.md").write_text(
            "# Spec 1\nEstado: approved\n\n- AC-1: x\n- AC-2: y\n", encoding="utf-8")
        sh("git", "add", "-A", cwd=self.repo)
        sh("git", "commit", "-qm", "init", cwd=self.repo)

    def review(self, sello):
        (self.repo / "docs" / "review-1.md").write_text(
            "| AC | Veredicto | Cita |\n|---|---|---|\n| AC-1 | falla | a.go:1 |\n\n"
            "### H-1 (mayor) algo\n\n" + sello + "\n", encoding="utf-8")

    def test_el_briefing_dice_que_decide_el_veredicto(self):
        out = briefing(self.repo)
        self.assertIn("Criterio del veredicto global", out)
        self.assertIn("approved: cada AC cumplido y medido", out)
        self.assertIn("bloqueante / mayor / menor / info", out)
        self.assertIn("NO bajan el veredicto ni abren otra ronda", out,
                      "lo menor sigue pudiendo abrir una ronda")

    def test_primera_ronda_no_se_presenta_como_seguimiento(self):
        out = briefing(self.repo)
        self.assertNotIn("RONDA DE SEGUIMIENTO", out)

    def test_tras_un_changes_requested_sellado_la_ronda_es_de_seguimiento(self):
        self.review("Revisado: changes_requested · 2026-09-28T00:00:00Z · t · "
                    "estampado por gate.py revision")
        out = briefing(self.repo)
        self.assertIn("RONDA DE SEGUIMIENTO", out)
        self.assertIn("no salgas a buscar hallazgos nuevos", out)
        self.assertIn("escalalo al usuario", out,
                      "la ronda de seguimiento no dice que hacer con algo mayor nuevo")

    def test_un_sello_blocked_tambien_abre_seguimiento(self):
        self.review("Revisado: blocked · 2026-09-28T00:00:00Z · t · "
                    "estampado por gate.py revision")
        self.assertIn("RONDA DE SEGUIMIENTO", briefing(self.repo))

    def test_un_veredicto_tipeado_sin_sello_no_cuenta_como_ronda(self):
        self.review("Veredicto propuesto: changes_requested")
        self.assertNotIn("RONDA DE SEGUIMIENTO", briefing(self.repo),
                         "una propuesta sin sellar se tomo como ronda cerrada")

    def test_un_approved_sellado_no_abre_seguimiento(self):
        self.review("Revisado: approved · 2026-09-28T00:00:00Z · t · "
                    "estampado por gate.py revision")
        self.assertNotIn("RONDA DE SEGUIMIENTO", briefing(self.repo))


class RevisorMdTests(unittest.TestCase):
    def test_el_cuerpo_del_revisor_lleva_la_regla(self):
        texto = (ROOT / "agents" / "revisor.md").read_text(encoding="utf-8")
        self.assertIn("La severidad decide el veredicto", texto)
        self.assertIn("Ronda de seguimiento", texto)


if __name__ == "__main__":
    unittest.main()
