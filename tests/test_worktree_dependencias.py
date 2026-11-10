"""El worktree de una feature nace con las dependencias de la raiz enlazadas.

Bug (realestate, 2026-11-10): `worktree.py start` creaba el worktree del front
sin `node_modules` (no esta versionado). El `gate.py verify` corrio los 6 AC de
la #242 -dos suites completas de integracion Go incluidas- y los dos AC del
front cayeron con exit 1 solo porque `npx ng test` no encontro Angular. Hubo
que enlazar a mano y repetir todo el verify: tiempo y tokens perdidos por un
rojo que no media nada.

Contrato:
  - start enlaza cada directorio de `rules.worktree_enlaces` (por defecto
    `node_modules`) desde la raiz al worktree, si existe en la raiz y falta en
    el worktree;
  - verify repara el enlace antes de correr los AC (worktrees creados antes del
    arreglo o a mano);
  - nunca pisa lo que ya este en el worktree, y sin el directorio en la raiz no
    hace nada.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def sh(*args, cwd):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, check=True)


def harness(script, *args, cwd):
    env = dict(os.environ, HARNESS_SIN_CONTEXTO="1", HARNESS_SIN_CBM="1")
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          cwd=str(cwd), capture_output=True, text=True, env=env)


class DependenciasDelWorktreeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="wt-deps-")
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name).resolve() / "repo"
        self.repo.mkdir()
        sh("git", "init", "-q", "-b", "develop", ".", cwd=self.repo)
        sh("git", "config", "user.email", "t@t.invalid", cwd=self.repo)
        sh("git", "config", "user.name", "T", cwd=self.repo)
        (self.repo / "harness").mkdir()
        (self.repo / "docs").mkdir()
        self.backlog = self.repo / "harness" / "feature_list.json"
        self.backlog.write_text(json.dumps(
            {"project": "t", "features": [{"id": "1", "name": "front"}]}), encoding="utf-8")
        (self.repo / ".gitignore").write_text("node_modules/\n.venv/\n", encoding="utf-8")
        (self.repo / "package.json").write_text("{}\n", encoding="utf-8")
        sh("git", "add", "-A", cwd=self.repo)
        sh("git", "commit", "-qm", "init", cwd=self.repo)

    def con_node_modules(self):
        nm = self.repo / "node_modules" / "@angular" / "cli"
        nm.mkdir(parents=True)
        (nm / "package.json").write_text("{}\n", encoding="utf-8")

    def feature(self):
        return json.loads(self.backlog.read_text(encoding="utf-8"))["features"][0]

    def start(self):
        r = harness("worktree.py", "start", "--feature", "1", cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return Path(self.feature()["worktree"]), r.stdout

    def spec(self, comando):
        (self.repo / "docs" / "spec-feature-1-front.md").write_text(
            f"# Spec 1\nEstado: approved\n\n- AC-1: x `verificar: {comando}`\n", encoding="utf-8")

    def test_start_enlaza_node_modules_de_la_raiz(self):
        self.con_node_modules()
        wt, salida = self.start()
        enlace = wt / "node_modules"
        self.assertTrue(enlace.is_symlink(), "el worktree nacio sin node_modules")
        self.assertEqual(enlace.resolve(), (self.repo / "node_modules").resolve())
        self.assertTrue((enlace / "@angular" / "cli" / "package.json").is_file())
        self.assertIn("node_modules", salida, "el enlace se hace en silencio")
        estado = sh("git", "status", "--porcelain", cwd=wt).stdout
        self.assertEqual(estado.strip(), "", "el enlace ensucia el arbol de la feature")

    def test_sin_node_modules_en_la_raiz_no_enlaza_nada(self):
        wt, _ = self.start()
        self.assertFalse(os.path.lexists(wt / "node_modules"))

    def test_respeta_lo_que_ya_esta_en_el_worktree(self):
        self.con_node_modules()
        wt, _ = self.start()
        (wt / "node_modules").unlink()
        propio = wt / "node_modules"
        propio.mkdir()
        (propio / "propio.txt").write_text("x", encoding="utf-8")
        self.spec("test -f node_modules/propio.txt")
        r = harness("gate.py", "verify", "--feature", "1", cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(propio.is_symlink(), "piso el node_modules propio del worktree")

    def test_verify_repara_un_worktree_sin_enlace(self):
        self.con_node_modules()
        wt, _ = self.start()
        (wt / "node_modules").unlink()  # como un worktree creado antes del arreglo
        self.spec("test -f node_modules/@angular/cli/package.json")
        r = harness("gate.py", "verify", "--feature", "1", cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((wt / "node_modules").is_symlink())

    def test_rules_worktree_enlaces_amplia_la_lista(self):
        self.con_node_modules()
        (self.repo / ".venv").mkdir()
        data = json.loads(self.backlog.read_text(encoding="utf-8"))
        data["rules"] = {"worktree_enlaces": ["node_modules", ".venv"]}
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        wt, _ = self.start()
        self.assertTrue((wt / "node_modules").is_symlink())
        self.assertTrue((wt / ".venv").is_symlink())

    def test_lista_vacia_desactiva_el_enlace(self):
        self.con_node_modules()
        data = json.loads(self.backlog.read_text(encoding="utf-8"))
        data["rules"] = {"worktree_enlaces": []}
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        wt, _ = self.start()
        self.assertFalse(os.path.lexists(wt / "node_modules"))


if __name__ == "__main__":
    unittest.main()
