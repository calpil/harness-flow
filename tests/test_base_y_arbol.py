"""La feature sale de la rama base y se mide en SU worktree, no en develop.

Regresiones de tres verdes/rojos falsos reales:
  1. worktree.py start creaba la rama desde el HEAD del repo, que es la rama de
     quien hizo checkout ultimo: la feature arrancaba con trabajo ajeno.
  2. revision.py diffeaba HEAD~1: el revisor veia el ultimo commit, no la
     feature; y si no habia worktree caia a la raiz (develop) en silencio.
  3. gate.py verify corria los AC desde la raiz, midiendo la rama de
     integracion en vez del arbol de la feature.
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


def sh(*args, cwd, check=True):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                          check=check)


def harness(script, *args, cwd):
    env = dict(os.environ, HARNESS_SIN_CONTEXTO="1")
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          cwd=str(cwd), capture_output=True, text=True, env=env)


class BaseYArbolTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / "repo"
        self.repo.mkdir(parents=True)
        sh("git", "init", "-q", "-b", "main", ".", cwd=self.repo)
        sh("git", "config", "user.email", "t@t.invalid", cwd=self.repo)
        sh("git", "config", "user.name", "T", cwd=self.repo)
        (self.repo / "harness").mkdir()
        (self.repo / "docs").mkdir()
        self.backlog = self.repo / "harness" / "feature_list.json"
        self.backlog.write_text(json.dumps(
            {"project": "t", "features": [{"id": "1", "name": "probar base"}]}),
            encoding="utf-8")
        (self.repo / "a.txt").write_text("base\n", encoding="utf-8")
        sh("git", "add", "-A", cwd=self.repo)
        sh("git", "commit", "-qm", "init", cwd=self.repo)
        sh("git", "checkout", "-qb", "develop", cwd=self.repo)
        (self.repo / "d.txt").write_text("dev\n", encoding="utf-8")
        sh("git", "add", "-A", cwd=self.repo)
        sh("git", "commit", "-qm", "dev", cwd=self.repo)
        # El repo queda parado en una rama AJENA, como en la vida real.
        sh("git", "checkout", "-qb", "rama-ajena", cwd=self.repo)
        (self.repo / "ajeno.txt").write_text("x\n", encoding="utf-8")
        sh("git", "add", "-A", cwd=self.repo)
        sh("git", "commit", "-qm", "ajeno", cwd=self.repo)

    def feature(self):
        return json.loads(self.backlog.read_text(encoding="utf-8"))["features"][0]

    def start(self, *extra):
        r = harness("worktree.py", "start", "--feature", "1", *extra, cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return Path(self.feature()["worktree"])

    def test_arranca_desde_develop_no_desde_el_head_ajeno(self):
        wt = self.start()
        self.assertTrue((wt / "d.txt").exists(), "el worktree no salio de develop")
        self.assertFalse((wt / "ajeno.txt").exists(),
                         "el worktree arrastro trabajo de la rama ajena")
        f = self.feature()
        self.assertEqual(f["base_branch"], "develop")
        self.assertEqual(
            f["base_sha"],
            sh("git", "rev-parse", "develop", cwd=self.repo).stdout.strip())

    def test_base_inexistente_bloquea_en_vez_de_usar_head(self):
        r = harness("worktree.py", "start", "--feature", "1", "--base", "no-existe",
                    cwd=self.repo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no existe", r.stdout + r.stderr)
        self.assertNotIn("worktree", self.feature())

    def test_diff_de_revision_cubre_toda_la_feature_no_solo_head_menos_uno(self):
        wt = self.start()
        for n in ("f1", "f2"):
            (wt / f"{n}.txt").write_text(n, encoding="utf-8")
            sh("git", "add", "-A", cwd=wt)
            sh("git", "commit", "-qm", n, cwd=wt)
        (self.repo / "docs" / "spec-feature-1-probar-base.md").write_text(
            "# Spec 1\nEstado: approved\n\n- AC-1: x `verificar: test -f f2.txt`\n",
            encoding="utf-8")
        out = harness("revision.py", "--feature", "1", cwd=self.repo).stdout
        self.assertIn("f1.txt", out, "el revisor no vio el primer commit")
        self.assertIn("f2.txt", out)

    def test_verify_corre_en_el_worktree_no_en_la_raiz(self):
        wt = self.start()
        (wt / "f2.txt").write_text("dos", encoding="utf-8")
        sh("git", "add", "-A", cwd=wt)
        sh("git", "commit", "-qm", "c", cwd=wt)
        (self.repo / "docs" / "spec-feature-1-probar-base.md").write_text(
            "# Spec 1\nEstado: approved\n\n- AC-1: x `verificar: test -f f2.txt`\n",
            encoding="utf-8")
        r = harness("gate.py", "verify", "--feature", "1", cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS", r.stdout)

    def test_verify_bloquea_si_el_worktree_declarado_no_existe(self):
        self.start()
        data = json.loads(self.backlog.read_text(encoding="utf-8"))
        data["features"][0]["worktree"] = "/no/existe/jamas"
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        (self.repo / "docs" / "spec-feature-1-probar-base.md").write_text(
            "# Spec 1\nEstado: approved\n\n- AC-1: x `verificar: true`\n",
            encoding="utf-8")
        r = harness("gate.py", "verify", "--feature", "1", cwd=self.repo)
        self.assertNotEqual(r.returncode, 0, "cayo a la raiz en vez de bloquear")
        self.assertIn("no existe", r.stdout + r.stderr)

    def test_briefing_avisa_cuando_el_arbol_no_es_el_de_la_feature(self):
        (self.repo / "docs" / "spec-feature-1-probar-base.md").write_text(
            "# Spec 1\nEstado: approved\n\n- AC-1: x `verificar: true`\n",
            encoding="utf-8")
        out = harness("revision.py", "--feature", "1", "--briefing",
                      cwd=self.repo).stdout
        self.assertIn("no tiene worktree", out)
        self.assertIn("NO selles", out)

    def _spec(self, extra=""):
        (self.repo / "docs" / "spec-feature-1-probar-base.md").write_text(
            "# Spec 1\nEstado: approved\n\n- AC-1: x\n" + extra, encoding="utf-8")

    def test_el_briefing_avisa_cuando_trunca_el_diff(self):
        """Un diff cortado en silencio es un revisor que cree haberlo visto entero.

        El briefing hacia diff[:60000] sin una marca: la cola del diff -- donde
        suele estar lo ultimo escrito -- desaparecia y el revisor dictaminaba
        sobre un paquete mutilado creyendolo completo.
        """
        wt = self.start()
        relleno = "\n".join(f"linea {n} de relleno para pasar el tope" for n in range(8000))
        (wt / "grande.txt").write_text(relleno, encoding="utf-8")
        sh("git", "add", "-A", cwd=wt)
        sh("git", "commit", "-qm", "grande", cwd=wt)
        self._spec()

        out = harness("revision.py", "--feature", "1", "--briefing", cwd=self.repo).stdout

        self.assertIn("DIFF TRUNCADO", out, "el briefing corto el diff sin decirlo")
        self.assertIn("lee esos archivos", out, "no dice que hacer con lo que falta")

    def test_el_diff_usa_la_rama_base_declarada_no_develop_hardcodeado(self):
        """revision.py caia a 'develop' literal ignorando rules.rama_base."""
        wt = self.start()
        (wt / "f1.txt").write_text("uno", encoding="utf-8")
        sh("git", "add", "-A", cwd=wt)
        sh("git", "commit", "-qm", "f1", cwd=wt)
        self._spec()
        # Feature sin base propia (registrada a mano): manda la regla del proyecto.
        datos = json.loads(self.backlog.read_text(encoding="utf-8"))
        datos["rules"] = {"rama_base": "main"}
        for campo in ("base_sha", "base_branch"):
            datos["features"][0].pop(campo, None)
        self.backlog.write_text(json.dumps(datos), encoding="utf-8")

        out = harness("revision.py", "--feature", "1", cwd=self.repo).stdout

        # d.txt solo esta en develop: aparece si la base fue main, no si fue develop.
        self.assertIn("d.txt", out, "diffeo contra develop ignorando rules.rama_base")
        self.assertIn("f1.txt", out)


if __name__ == "__main__":
    unittest.main()
