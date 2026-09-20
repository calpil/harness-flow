"""Abortar un start no puede dejar el arbol a medias.

Bug: si la rama de la feature ya existia y NO descendia de la base,
`worktree.py start` creaba el worktree y recien despues abortaba con exit 1.
Quedaba un worktree registrado en Git que:

  - `worktree.py drop` no podia quitar (el backlog nunca se escribio, asi que
    la feature "no tiene worktree registrado"), y
  - hacia fallar todos los start siguientes con "already exists" sobre la ruta.

Un callejon sin salida del que solo se salia con `git worktree remove` a mano,
en un script cuyo contrato es "la feature NO arranca".
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def harness(script, *args, cwd):
    env = dict(os.environ, HARNESS_SIN_CONTEXTO="1")
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          cwd=str(cwd), capture_output=True, text=True, env=env)


class AbortoDeStartTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="wt-aborto-")
        self.addCleanup(tmp.cleanup)
        self.raiz = Path(tmp.name).resolve() / "proyecto"
        self.raiz.mkdir()
        git("init", "-b", "develop", ".", cwd=self.raiz)
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
            "--allow-empty", "-m", "base", cwd=self.raiz)
        harness("init.py", "--project", "demo", cwd=self.raiz)
        harness("add.py", "--name", "Checkout", cwd=self.raiz)
        self.contenedor = self.raiz.parent / f"{self.raiz.name}-wt"

    def rama_huerfana(self, nombre):
        git("checkout", "-q", "--orphan", nombre, cwd=self.raiz)
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
            "--allow-empty", "-m", "ajeno", cwd=self.raiz)
        git("checkout", "-q", "develop", cwd=self.raiz)

    def worktrees(self):
        salida = git("worktree", "list", "--porcelain", cwd=self.raiz).stdout
        return [l[len("worktree "):] for l in salida.splitlines()
                if l.startswith("worktree ")]

    def test_rama_ajena_aborta_sin_dejar_worktree(self):
        self.rama_huerfana("feature/1-checkout")
        r = harness("worktree.py", "start", "--feature", "1", cwd=self.raiz)

        self.assertNotEqual(r.returncode, 0, "una rama que no desciende de la base no arranca")
        self.assertIn("NO desciende", r.stdout + r.stderr)
        self.assertEqual(self.worktrees(), [str(self.raiz)],
                         "el worktree creado antes de abortar quedo registrado")
        self.assertFalse((self.contenedor / "1-checkout").exists(),
                         "y ademas quedo en disco")

    def test_tras_arreglar_la_rama_el_start_vuelve_a_funcionar(self):
        self.rama_huerfana("feature/1-checkout")
        harness("worktree.py", "start", "--feature", "1", cwd=self.raiz)
        git("branch", "-q", "-D", "feature/1-checkout", cwd=self.raiz)

        r = harness("worktree.py", "start", "--feature", "1", cwd=self.raiz)

        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(str(self.contenedor / "1-checkout"), self.worktrees())

    def test_el_backlog_no_registra_una_feature_que_no_arranco(self):
        import json
        self.rama_huerfana("feature/1-checkout")
        harness("worktree.py", "start", "--feature", "1", cwd=self.raiz)
        backlog = json.loads((self.raiz / "harness" / "feature_list.json").read_text())
        feature = backlog["features"][0]
        self.assertNotIn("worktree", feature)
        self.assertNotEqual(feature.get("status"), "in_progress")


if __name__ == "__main__":
    unittest.main()
