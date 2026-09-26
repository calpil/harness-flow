"""Bajas de tests declaradas en el cierre medido. FIXTURE: Git y Go reales, sin red."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(os.environ.get("HARNESS_TEST_SCRIPTS", Path(__file__).resolve().parents[1] / "scripts"))
CMD = "go test -tags integration -count=1 -json ./..."
MOD = "fixture.invalid/alpha"
BAJAS = [f"{MOD}::TestRetiredA", f"{MOD}/legacy::TestLegacy"]


class RetiradosTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.root = self.home / "project"
        (self.root / "harness" / "progress").mkdir(parents=True)
        (self.root / "docs").mkdir()
        self.env = {"PATH": os.environ["PATH"], "HOME": str(self.home),
                    "USERPROFILE": str(self.home), "CI": "1", "PYTHONDONTWRITEBYTECODE": "1",
                    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                    "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
                    "HARNESS_SKILLS_DIR": str(self.home / "skills"),
                    "GOPROXY": "off", "GOSUMDB": "off", "GOTOOLCHAIN": "local", "GOWORK": "off",
                    "GOCACHE": os.environ.get("HARNESS_TEST_GOCACHE", str(self.home / "go-cache"))}
        lesson = self.home / "skills" / "closure-contract"
        lesson.mkdir(parents=True)
        (lesson / "SKILL.md").write_text("---\nname: closure-contract\ndescription: Fixture\n---\n")
        self.backlog = self.root / "harness" / "feature_list.json"
        (self.root / "docs" / "spec-feature-7-retiro-fixture.md").write_text(
            'Estado: draft\n- AC-1: Given repo When retired Then integrated\n'
            'Comando: `git -C alpha merge-base --is-ancestor HEAD HEAD`\n')
        (self.root / "docs" / "impl-7.md").write_text("## AC-1\nalpha/feature.txt:1\n")
        (self.root / "harness" / "progress" / "current-7.md").write_text("Fixture progress\n")
        self.backlog.write_text(json.dumps({"project": "fixture", "rules": {}, "features": [
            {"id": 7, "name": "Retiro fixture", "status": "in_progress", "microservicios": ["alpha"]}]}))
        self.repo = self.root / "alpha"
        self.repo.mkdir()
        self.git(self.repo, "init", "-b", "develop")
        (self.repo / "go.mod").write_text(f"module {MOD}\n\ngo 1.22\n")
        (self.repo / "contract_test.go").write_text(
            'package contract\nimport "testing"\nfunc TestBaseContract(t *testing.T) {}\n')
        (self.repo / "retired_test.go").write_text(
            'package contract\nimport "testing"\n'
            'func TestRetiredA(t *testing.T) { t.Run("sub", func(t *testing.T) {}) }\n')
        (self.repo / "legacy").mkdir()
        (self.repo / "legacy" / "legacy_test.go").write_text(
            'package legacy\nimport "testing"\nfunc TestLegacy(t *testing.T) {}\n')
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-m", "fixture: baseline")
        self.base_sha = self.git(self.repo, "rev-parse", "HEAD")
        self.base = self.home / "base-alpha.json"
        self.ok("postmerge_medido.py", "base", "--repo", str(self.repo), "--cmd", CMD, "--guardar", str(self.base))
        self.mapa = self.home / "postmerge-map.json"
        self.mapa.write_text(json.dumps({"version": 1, "feature": "7", "bases": {"alpha": str(self.base)}}))
        self.retirados = self.home / "retirados.json"
        self.ok("gate.py", "approve-spec", "--feature", "7", "--yes", "--por", "Fixture")

    def git(self, path, *args):
        r = subprocess.run(["git", "-C", str(path), *args], env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout.strip()

    def cli(self, script, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=self.root,
                              env=self.env, capture_output=True, text=True)

    def ok(self, script, *args):
        r = self.cli(script, *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def integrar(self, con_build_tag=False, review="Bajas revisadas: TestRetiredA y TestLegacy.\n"):
        """La feature borra (o esconde tras un build tag) los tests retirados."""
        wt = self.home / "worktrees" / "alpha"
        self.git(self.repo, "worktree", "add", "--detach", str(wt))
        (wt / "feature.txt").write_text("fixture feature\n")
        if con_build_tag:
            path = wt / "retired_test.go"
            path.write_text("//go:build never\n\n" + path.read_text())
        else:
            self.git(wt, "rm", "-q", "retired_test.go")
        self.git(wt, "rm", "-q", "-r", "legacy")
        self.git(wt, "add", ".")
        self.git(wt, "commit", "-m", "fixture: retiro")
        source = self.git(wt, "rev-parse", "HEAD")
        self.git(self.repo, "merge", "--ff-only", source)
        manifest = self.home / "manifest.json"
        manifest.write_text(json.dumps({"version": 1, "feature": "7", "repos": [
            {"microservicio": "alpha", "repo": str(self.repo), "worktree": str(wt),
             "base_sha": self.base_sha, "source_sha": source, "target_branch": "develop",
             "target_sha": self.git(self.repo, "rev-parse", "HEAD")}]}))
        self.ok("worktree.py", "register", "--feature", "7", "--manifest", str(manifest))
        (self.root / "docs" / "review-7.md").write_text("## AC-1\nalpha/feature.txt:1\n" + review)
        self.ok("gate.py", "verify", "--feature", "7")
        self.ok("gate.py", "revision", "--feature", "7", "--veredicto", "approved", "--por", "Fixture reviewer")

    def declarar(self, bajas, feature="7", micro="alpha"):
        self.retirados.write_text(json.dumps({"version": 1, "feature": feature, "retirados": {micro: bajas}}))

    def close(self, *extra):
        return self.cli("gate.py", "close", "--feature", "7", "--status", "done", "--to", "develop",
                        "--integrated", "--leccion", "closure-contract", "--postmerge", str(self.mapa), *extra)

    def rechazado(self, razon, *extra):
        before = {str(p): p.read_bytes() for d in (self.root / "docs", self.root / "harness")
                  for p in d.rglob("*") if p.is_file()}
        r = self.close(*extra)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(razon, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        after = {str(p): p.read_bytes() for d in (self.root / "docs", self.root / "harness")
                 for p in d.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        return r

    def check(self, *extra):
        return self.cli("postmerge_medido.py", "check", "--repo", str(self.repo), "--base", str(self.base),
                        "--cmd", CMD, *extra)

    def test_baja_borrada_por_la_feature_y_citada_cierra(self):
        self.integrar()
        self.declarar(BAJAS)
        r = self.close("--retirados", str(self.retirados))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        f = json.loads(self.backlog.read_text())["features"][0]
        self.assertEqual(f["status"], "done")
        medicion = f["mediciones_destino"][0]
        self.assertEqual(sorted(medicion["retirados"]), sorted(BAJAS))
        self.assertEqual(len(medicion["retirados_sha256"]), 64)

    def test_ausencia_sin_declarar_sigue_bloqueando_y_la_nombra(self):
        self.integrar()
        r = self.rechazado("desaparecidos")
        self.assertIn("TestRetiredA", r.stdout + r.stderr)
        self.assertIn("TestLegacy", r.stdout + r.stderr)
        # Declarar solo una no cubre la otra.
        self.declarar(BAJAS[:1])
        r = self.rechazado("desaparecidos", "--retirados", str(self.retirados))
        self.assertIn("TestLegacy", r.stdout + r.stderr)

    def test_build_tag_no_es_baja_aunque_se_declare(self):
        self.integrar(con_build_tag=True)
        self.declarar(BAJAS)
        self.rechazado("sigue definido", "--retirados", str(self.retirados))

    def test_review_que_no_nombra_la_baja_bloquea(self):
        self.integrar(review="Sin mencion de las bajas.\n")
        self.declarar(BAJAS)
        self.rechazado("no cita", "--retirados", str(self.retirados))

    def test_declaraciones_invalidas_no_autorizan_nada(self):
        self.integrar(review="Bajas: TestRetiredA, TestLegacy, TestBaseContract, TestNoExiste.\n")
        casos = [
            ("se sigue midiendo", dict(bajas=BAJAS + [f"{MOD}::TestBaseContract"])),
            ("no se midio en la base", dict(bajas=BAJAS + [f"{MOD}::TestNoExiste"])),
            ("se declara", dict(bajas=[f"{MOD}::TestRetiredA/sub", BAJAS[1]])),
            ("se declara", dict(bajas=["TestRetiredA", BAJAS[1]])),
            ("otra feature", dict(bajas=BAJAS, feature="8")),
            ("ajeno", dict(bajas=BAJAS, micro="beta")),
            ("vacia", dict(bajas=[])),
        ]
        for razon, kwargs in casos:
            with self.subTest(razon=razon, bajas=kwargs.get("bajas")):
                self.declarar(**kwargs)
                self.rechazado(razon, "--retirados", str(self.retirados))

    def test_retirados_exige_cierre_integrado(self):
        self.integrar()
        self.declarar(BAJAS)
        r = self.cli("gate.py", "close", "--feature", "7", "--status", "done", "--to", "develop",
                     "--leccion", "closure-contract", "--retirados", str(self.retirados))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--integrated", r.stdout + r.stderr)

    def test_check_manual_acepta_la_misma_baja_verificada(self):
        self.integrar()
        r = self.check()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("alcance incompleto", r.stdout)
        self.declarar(BAJAS)
        r = self.check("--retirados", str(self.retirados), "--microservicio", "alpha")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("TestLegacy", r.stdout)
        r = self.check("--retirados", str(self.retirados))
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("--microservicio", r.stdout)

    def test_check_manual_rechaza_build_tag(self):
        self.integrar(con_build_tag=True)
        self.declarar(BAJAS)
        r = self.check("--retirados", str(self.retirados), "--microservicio", "alpha")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("sigue definido", r.stdout)


if __name__ == "__main__":
    unittest.main()
