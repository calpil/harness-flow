"""Cierre historico (close --integrated --historico): sin base preintegracion
medible. FIXTURE: Git y Go/frontend reales, sin red. Ver diseno en
docs/diseno-arnes-cierre-historico.md y references/multirepo.md #cierre-historico.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_frontend_runner as frontend_fixture
from test_frontend_runner import SCRIPTS, NODE_FILES

CMD = "go test -tags integration -count=1 -json ./..."
MOD = "fixture.invalid/alpha"


class CierreHistoricoGoTests(unittest.TestCase):
    """Repo Go: base_sha sin la feature, source_sha con su delta, ya integrado
    (worktree == repo). Nunca se corre `postmerge_medido.py base`: no hay base."""

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
        (self.root / "docs" / "spec-feature-15-historico-fixture.md").write_text(
            'Estado: draft\n- AC-1: Given repo When cerrado historico Then integrado\n'
            'Comando: `git -C alpha merge-base --is-ancestor HEAD HEAD`\n')
        (self.root / "docs" / "impl-15.md").write_text("## AC-1\nalpha/feature.txt:1\n")
        (self.root / "harness" / "progress" / "current-15.md").write_text("Fixture progress\n")
        self.backlog.write_text(json.dumps({"project": "fixture", "rules": {}, "features": [
            {"id": 15, "name": "Historico fixture", "status": "in_progress", "microservicios": ["alpha"]}]}))
        self.repo = self.root / "alpha"
        self.repo.mkdir()
        self.git(self.repo, "init", "-b", "develop")
        (self.repo / "go.mod").write_text(f"module {MOD}\n\ngo 1.22\n")
        (self.repo / "contract_test.go").write_text(
            'package contract\nimport "testing"\nfunc TestBaseContract(t *testing.T) {}\n')
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-m", "fixture: baseline (contrato viejo, sin base medible)")
        self.base_sha = self.git(self.repo, "rev-parse", "HEAD")
        self.retirados = self.home / "retirados.json"
        self.ok("gate.py", "approve-spec", "--feature", "15", "--yes", "--por", "Fixture")

    def git(self, path, *args):
        r = subprocess.run(["git", "-C", str(path), *args], env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout.strip()

    def cli(self, script, *args):
        return subprocess.run([sys.executable, "-B", str(SCRIPTS / script), *args], cwd=self.root,
                              env=self.env, capture_output=True, text=True)

    def ok(self, script, *args):
        r = self.cli(script, *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def feature_agrega_test(self, nombre="TestFeatureNueva", contenido=None):
        """La feature agrega su propio test y se integra sin rama nueva (ya
        integrado: worktree == repo, HEAD ya en target)."""
        contenido = contenido or (
            f'package contract\nimport "testing"\nfunc {nombre}(t *testing.T) {{}}\n')
        (self.repo / "feature_test.go").write_text(contenido)
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-m", "fixture: feature agrega test")
        source = self.git(self.repo, "rev-parse", "HEAD")
        return source

    def manifest(self, source_sha, target_sha=None):
        target_sha = target_sha or source_sha
        data = {"version": 1, "feature": "15", "repos": [
            {"microservicio": "alpha", "repo": str(self.repo), "worktree": str(self.repo),
             "base_sha": self.base_sha, "source_sha": source_sha, "target_branch": "develop",
             "target_sha": target_sha}]}
        path = self.home / "manifest.json"
        path.write_text(json.dumps(data))
        return path

    def declarar(self, bajas, feature="15", micro="alpha"):
        self.retirados.write_text(json.dumps({"version": 1, "feature": feature, "retirados": {micro: bajas}}))

    def seal(self, review="## AC-1\nalpha/feature.txt:1\n"):
        (self.root / "docs" / "review-15.md").write_text(review)
        self.ok("gate.py", "verify", "--feature", "15")
        self.ok("gate.py", "revision", "--feature", "15", "--veredicto", "approved", "--por", "Fixture reviewer")

    def close(self, *extra):
        return self.cli("gate.py", "close", "--feature", "15", "--status", "done", "--to", "develop",
                        "--integrated", "--historico", "--yes", "--motivo",
                        "Base preintegracion no medible con el contrato vigente", "--leccion",
                        "closure-contract", *extra)

    def snapshot(self):
        return {str(p): p.read_bytes() for base in (self.root / "docs", self.root / "harness")
                for p in base.rglob("*") if p.is_file()}

    def rechazado(self, razon, *extra):
        before = self.snapshot()
        r = self.close(*extra)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(razon, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(self.snapshot(), before)
        return r

    # -- verdes -------------------------------------------------------------

    def test_cierra_historico_sin_base_y_persiste_motivo(self):
        source = self.feature_agrega_test()
        manifest = self.manifest(source)
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(manifest))
        self.seal()
        r = self.close()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        f = json.loads(self.backlog.read_text())["features"][0]
        self.assertEqual(f["status"], "done")
        self.assertEqual(f["cierre_historico"]["motivo"],
                         "Base preintegracion no medible con el contrato vigente")
        self.assertTrue(f["cierre_historico"]["autorizado_por"])
        self.assertTrue(f["cierre_historico"]["at"])
        medicion = f["mediciones_destino"][0]
        self.assertEqual(medicion["modo"], "historico")
        self.assertEqual(medicion["tests_agregados"], [f"{MOD}::TestFeatureNueva"])
        self.assertNotIn("base", medicion)

    def test_baja_historica_declarada_y_citada_cierra(self):
        source = self.feature_agrega_test()
        # Una feature POSTERIOR borra el test que #15 agrego (misma rama, sin
        # aislamiento nuevo: worktree == repo, sigue integrado).
        (self.repo / "feature_test.go").unlink()
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-m", "fixture: otra feature borra el test")
        target = self.git(self.repo, "rev-parse", "HEAD")
        manifest = self.manifest(source, target)
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(manifest))
        self.declarar([f"{MOD}::TestFeatureNueva"])
        self.seal(review="## AC-1\nalpha/feature.txt:1\nBaja historica revisada: TestFeatureNueva.\n")
        r = self.close("--retirados", str(self.retirados))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        f = json.loads(self.backlog.read_text())["features"][0]
        medicion = f["mediciones_destino"][0]
        self.assertEqual(medicion["retirados"], [f"{MOD}::TestFeatureNueva"])
        self.assertEqual(len(medicion["retirados_sha256"]), 64)

    # -- negativos ------------------------------------------------------------

    def test_sin_yes_bloquea(self):
        source = self.feature_agrega_test()
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.seal()
        before = self.snapshot()
        r = self.cli("gate.py", "close", "--feature", "15", "--status", "done", "--to", "develop",
                     "--integrated", "--historico", "--motivo", "por que", "--leccion", "closure-contract")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--yes", r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_sin_motivo_bloquea(self):
        source = self.feature_agrega_test()
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.seal()
        before = self.snapshot()
        r = self.cli("gate.py", "close", "--feature", "15", "--status", "done", "--to", "develop",
                     "--integrated", "--historico", "--yes", "--leccion", "closure-contract")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--motivo", r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_motivo_con_salto_de_linea_bloquea(self):
        source = self.feature_agrega_test()
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.seal()
        before = self.snapshot()
        r = self.cli("gate.py", "close", "--feature", "15", "--status", "done", "--to", "develop",
                     "--integrated", "--historico", "--yes", "--motivo", "linea 1\nlinea 2",
                     "--leccion", "closure-contract")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--motivo", r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_junto_con_postmerge_bloquea(self):
        source = self.feature_agrega_test()
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.seal()
        mapa = self.home / "postmerge.json"
        mapa.write_text(json.dumps({"version": 1, "feature": "15", "bases": {"alpha": str(self.home / "x.json")}}))
        self.rechazado("mutuamente excluyentes", "--postmerge", str(mapa))

    def test_sin_integrated_bloquea(self):
        source = self.feature_agrega_test()
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.seal()
        before = self.snapshot()
        r = self.cli("gate.py", "close", "--feature", "15", "--status", "done", "--to", "develop",
                     "--historico", "--yes", "--motivo", "por que", "--leccion", "closure-contract")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--integrated", r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_rojo_en_destino_bloquea(self):
        source = self.feature_agrega_test()
        (self.repo / "feature_test.go").write_text(
            'package contract\nimport "testing"\nfunc TestFeatureNueva(t *testing.T) { t.Fatal("rojo") }\n')
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-m", "fixture: target con rojo")
        target = self.git(self.repo, "rev-parse", "HEAD")
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source, target)))
        self.seal()
        self.rechazado("rojos en el destino")

    def test_skip_en_destino_bloquea(self):
        source = self.feature_agrega_test()
        (self.repo / "feature_test.go").write_text(
            'package contract\nimport "testing"\n'
            'func TestFeatureNueva(t *testing.T) { t.Skip("no corre") }\n')
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-m", "fixture: target con skip")
        target = self.git(self.repo, "rev-parse", "HEAD")
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source, target)))
        self.seal()
        self.rechazado("skip")

    def test_test_agregado_ausente_sin_declarar_bloquea(self):
        source = self.feature_agrega_test()
        (self.repo / "feature_test.go").unlink()
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-m", "fixture: se borra sin declarar")
        target = self.git(self.repo, "rev-parse", "HEAD")
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source, target)))
        self.seal()
        r = self.rechazado("ausentes sin declarar")
        self.assertIn("TestFeatureNueva", r.stdout + r.stderr)

    def test_baja_historica_sin_cita_bloquea(self):
        source = self.feature_agrega_test()
        (self.repo / "feature_test.go").unlink()
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-m", "fixture: otra feature borra el test")
        target = self.git(self.repo, "rev-parse", "HEAD")
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source, target)))
        self.declarar([f"{MOD}::TestFeatureNueva"])
        self.seal(review="## AC-1\nalpha/feature.txt:1\nSin mencion de la baja.\n")
        self.rechazado("no cita", "--retirados", str(self.retirados))

    def test_baja_historica_que_sigue_definida_en_destino_bloquea(self):
        source = self.feature_agrega_test()
        # NO se borra: sigue en target_sha == source_sha.
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.declarar([f"{MOD}::TestFeatureNueva"])
        self.seal(review="## AC-1\nalpha/feature.txt:1\nBaja historica: TestFeatureNueva.\n")
        self.rechazado("sigue definido", "--retirados", str(self.retirados))

    def test_retirados_declara_test_preexistente_no_agregado_por_la_feature_bloquea(self):
        """El cierre historico solo puede declarar como baja un test que la
        PROPIA feature agrego (garantia 4): definido en source_sha y AUSENTE
        en base_sha. TestPreexisting ya vivia en base_sha, la feature #15
        nunca lo toco (solo agrega TestFeatureNueva); una feature POSTERIOR lo
        borra. Declararlo en --retirados no es una baja de #15 (hallazgo P2
        ronda 2: 'acepta declarar como baja de la feature un test que la
        feature NUNCA agrego')."""
        (self.repo / "legacy_test.go").write_text(
            'package contract\nimport "testing"\nfunc TestPreexisting(t *testing.T) {}\n')
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-m", "fixture: test preexistente antes de la feature")
        self.base_sha = self.git(self.repo, "rev-parse", "HEAD")
        source = self.feature_agrega_test()
        (self.repo / "legacy_test.go").unlink()
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-m", "fixture: otra feature borra el test preexistente")
        target = self.git(self.repo, "rev-parse", "HEAD")
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source, target)))
        self.declarar([f"{MOD}::TestPreexisting"])
        self.seal(review="## AC-1\nalpha/feature.txt:1\nBaja historica: TestPreexisting.\n")
        r = self.rechazado("ya existia en la base", "--retirados", str(self.retirados))
        self.assertIn("TestPreexisting", r.stdout + r.stderr)

    def test_repo_con_codigo_y_sin_tests_agregados_bloquea(self):
        (self.repo / "otro.go").write_text("package contract\n\nfunc Otra() {}\n")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-m", "fixture: codigo sin test nuevo")
        source = self.git(self.repo, "rev-parse", "HEAD")
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.seal()
        self.rechazado("sin agregar ningun test")

    def test_review_sellado_en_otro_contexto_bloquea(self):
        source = self.feature_agrega_test()
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.seal()
        # El review se re-sella (mismo veredicto) pero el spec cambio despues:
        # el contexto multi-repo ya no corresponde al de verify/review.
        (self.root / "docs" / "impl-15.md").write_text("## AC-1\nalpha/feature.txt:2\n")
        self.rechazado("review no corresponde")

    def test_verify_de_otro_contexto_bloquea(self):
        source = self.feature_agrega_test()
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.seal()
        data = json.loads(self.backlog.read_text())
        data["features"][0]["last_verify"]["total"] = 999
        self.backlog.write_text(json.dumps(data))
        self.rechazado("verify no corresponde")

    def test_motivo_con_separador_unicode_bloquea(self):
        """U+2028 (LINE SEPARATOR) no es 'c < \" \"' (0x2028 > 0x20): el chequeo
        viejo de --motivo lo dejaba pasar aunque se renderiza como salto de
        linea en la mayoria de los visores (hallazgo P3 ronda 1)."""
        source = self.feature_agrega_test()
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.seal()
        before = self.snapshot()
        r = self.cli("gate.py", "close", "--feature", "15", "--status", "done", "--to", "develop",
                     "--integrated", "--historico", "--yes", "--motivo", "linea 1\u2028linea 2",
                     "--leccion", "closure-contract")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--motivo", r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_por_con_separador_unicode_bloquea(self):
        """Mismo hueco que --motivo, en _firmante (gate.py:321, usado por
        `revision --por`): preexistente, no es una regresion de esta feature,
        pero comparte el helper corregido (hallazgo P3 ronda 1)."""
        source = self.feature_agrega_test()
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.seal()
        before = self.snapshot()
        r = self.cli("gate.py", "revision", "--feature", "15", "--veredicto", "approved",
                     "--por", "Fixture\u2028reviewer")
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("--por", r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_mensaje_historico_advierte_que_es_barrera_de_proceso(self):
        """El mensaje de --historico sin --yes deja explicito que la barrera es
        de PROCESO (igual que approve-spec), no una restriccion TECNICA de
        antiguedad ni de intento previo de medir base: nada en el gate impide
        invocar --historico sobre una feature nueva con base medible (hallazgo
        P2 ronda 1: 'no esta restringido tecnicamente a features viejas')."""
        source = self.feature_agrega_test()
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.seal()
        r = self.cli("gate.py", "close", "--feature", "15", "--status", "done", "--to", "develop",
                     "--integrated", "--historico", "--motivo", "por que", "--leccion", "closure-contract")
        self.assertNotEqual(r.returncode, 0)
        salida = r.stdout + r.stderr
        self.assertIn("--yes", salida)
        self.assertIn("barrera de PROCESO", salida)
        self.assertIn("no una restriccion TECNICA", salida)

    def test_medicion_incompleta_bloquea(self):
        """La invariante defensiva `len(results) == len(names)`
        (medicion_destino.py:345, 'historico: medicion incompleta') no es
        alcanzable desde el CLI real: `worktree.py register` ya deduplica
        microservicios (multirepo.py:119, 'microservicio ausente, ajeno o
        duplicado') y los runners Go/frontend canalizan TODA falla real a
        Invalid/SystemExit/OSError/ValueError, ya atrapados antes de esa linea
        (hallazgo P2 ronda 1: 'medicion incompleta' sin negativo). Se ejercita
        EN PROCESO, llamando measure_historico directamente con un manifiesto
        que declara el MISMO microservicio dos veces -- bypass deliberado de
        esa deduplicacion, que solo corre en el camino del CLI -- para probar
        que la red de seguridad bloquea si esa invariante llegara a romperse."""
        source = self.feature_agrega_test()
        manifest_path = self.manifest(source)
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(manifest_path))
        self.seal()
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        import comun
        import medicion_destino
        p = comun.paths(self.root)
        data = comun.load_backlog(p)
        f = comun.get_feature(data, "15")
        fila = json.loads(manifest_path.read_text())["repos"][0]
        manifest_duplicado = {"version": 1, "feature": "15", "repos": [fila, dict(fila)]}
        with self.assertRaises(medicion_destino.Invalid) as ctx:
            medicion_destino.measure_historico(p, f, data["rules"], manifest_duplicado)
        self.assertIn("medicion incompleta", str(ctx.exception))


class CierreHistoricoFrontendTests(unittest.TestCase):
    """Angular22/Vitest4 + node:test real, via test_frontend_runner.FrontendFixture."""

    def setUp(self):
        t = frontend_fixture.FrontendFixture("runTest")
        t.setUp()
        self.addCleanup(t.doCleanups)
        self.t = t
        self.root = t.home / "project"
        (self.root / "docs").mkdir(parents=True)
        (self.root / "harness/progress").mkdir(parents=True)
        repo = self.root / "front"
        t.repo.rename(repo)
        t.repo = repo
        t.env["HARNESS_SKILLS_DIR"] = str(t.home / "skills")
        lesson = t.home / "skills/closure-contract/SKILL.md"
        lesson.parent.mkdir(parents=True)
        lesson.write_text("---\nname: closure-contract\ndescription: Fixture\n---\n")
        self.base_sha = t.git("rev-parse", "HEAD")
        self.backlog = self.root / "harness/feature_list.json"
        self.backlog.write_text(json.dumps(dict(project="fixture", rules={}, features=[
            dict(id=15, name="Historico frontend fixture", status="in_progress", microservicios=["front"])])))
        (self.root / "docs/spec-feature-15-historico-frontend-fixture.md").write_text(
            'Estado: draft\n- AC-1: Given frontend When cerrado historico Then integrado\n'
            'Comando: `git -C front merge-base --is-ancestor HEAD HEAD`\n')
        (self.root / "docs/impl-15.md").write_text("## AC-1\nfront/feature.txt:1\n")
        (self.root / "harness/progress/current-15.md").write_text("Fixture progress\n")
        self.ok("gate.py", "approve-spec", "--feature", "15", "--yes", "--por", "Fixture")

    def command(self, script, *args):
        argv = [sys.executable, "-B", str(SCRIPTS / script), *args]
        return subprocess.run(argv, cwd=self.root, env=self.t.env, capture_output=True, text=True, timeout=180)

    def ok(self, script, *args):
        r = self.command(script, *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def feature_agrega_spec(self):
        spec = self.t.repo / "projects/app/src/a.spec.ts"
        original = spec.read_text()
        spec.write_text(original + "test('nueva de la feature', () => expect(1).toBe(1));\n")
        return self.t.commit("fixture: feature agrega test")

    def feature_agrega_ambiguo(self):
        """Dos tests declarados cuyo sufijo colisiona: `describe('grupo')` +
        `it('el resultado final')` (nombre completo medido: 'grupo el resultado
        final') y un `it('resultado final')` plano en el mismo archivo. Ambos
        titulos literales son sufijos validos del nombre completo del primero."""
        spec = self.t.repo / "projects/app/src/a.spec.ts"
        original = spec.read_text()
        spec.write_text(original +
            "import {describe} from 'vitest';\n"
            "describe('grupo', () => {\n"
            "  test('el resultado final', () => expect(1).toBe(1));\n"
            "});\n"
            "test('resultado final', () => expect(1).toBe(1));\n")
        return self.t.commit("fixture: feature agrega tests con sufijo ambiguo")

    def manifest(self, source_sha, target_sha=None):
        target_sha = target_sha or source_sha
        row = dict(microservicio="front", repo=str(self.t.repo), worktree=str(self.t.repo),
                   base_sha=self.base_sha, source_sha=source_sha, target_sha=target_sha,
                   target_branch="develop")
        path = self.t.home / "manifest.json"
        path.write_text(json.dumps(dict(version=1, feature="15", repos=[row])))
        return path

    def declarar(self, bajas):
        self.retirados = self.t.home / "retirados.json"
        self.retirados.write_text(json.dumps(dict(version=1, feature="15", retirados=dict(front=bajas))))
        return self.retirados

    def seal(self, review="## AC-1\nfront/feature.txt:1\n"):
        (self.root / "docs/review-15.md").write_text(review)
        self.ok("gate.py", "verify", "--feature", "15")
        self.ok("gate.py", "revision", "--feature", "15", "--veredicto", "approved", "--por", "Fixture reviewer")

    def close(self, *extra):
        return self.command("gate.py", "close", "--feature", "15", "--status", "done", "--to", "develop",
                            "--integrated", "--historico", "--yes", "--motivo",
                            "Base preintegracion no medible con el contrato vigente",
                            "--leccion", "closure-contract", *extra)

    def snapshot(self):
        return {str(p): p.read_bytes() for base in (self.root / "docs", self.root / "harness")
                for p in base.rglob("*") if p.is_file()}

    def rechazado(self, razon, *extra):
        before = self.snapshot()
        r = self.close(*extra)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(razon, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(self.snapshot(), before)
        return r

    def test_cierra_historico_frontend_sin_base(self):
        source = self.feature_agrega_spec()
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.seal()
        r = self.close()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        f = json.loads(self.backlog.read_text())["features"][0]
        self.assertEqual(f["status"], "done")
        medicion = f["mediciones_destino"][0]
        self.assertEqual(medicion["modo"], "historico")
        self.assertEqual(medicion["tests_agregados"],
                         ["projects/app/src/a.spec.ts::nueva de la feature"])

    def test_rojo_nuevo_en_destino_bloquea(self):
        source = self.feature_agrega_spec()
        spec = self.t.repo / "projects/app/src/a.spec.ts"
        spec.write_text(spec.read_text().replace(
            "test('nueva de la feature', () => expect(1).toBe(1));",
            "test('nueva de la feature', () => expect(1).toBe(2));"))
        target = self.t.commit("fixture: target con rojo")
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source, target)))
        self.seal()
        r = self.close()
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("rojos", r.stdout + r.stderr)

    def test_test_agregado_ausente_sin_declarar_bloquea(self):
        spec = self.t.repo / "projects/app/src/a.spec.ts"
        original = spec.read_text()
        source = self.feature_agrega_spec()
        spec.write_text(original)
        target = self.t.commit("fixture: se borra sin declarar")
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source, target)))
        self.seal()
        r = self.rechazado("ausentes sin declarar")
        self.assertIn("nueva de la feature", r.stdout + r.stderr)

    def test_baja_historica_sin_cita_bloquea(self):
        spec = self.t.repo / "projects/app/src/a.spec.ts"
        original = spec.read_text()
        source = self.feature_agrega_spec()
        spec.write_text(original)
        target = self.t.commit("fixture: otra feature borra el test")
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source, target)))
        self.declarar([["angular:app", "projects/app/src/a.spec.ts", "nueva de la feature"]])
        self.seal(review="## AC-1\nfront/feature.txt:1\nSin mencion de la baja.\n")
        self.rechazado("no cita", "--retirados", str(self.retirados))

    def test_baja_historica_que_sigue_definida_en_destino_bloquea(self):
        # NO se borra: target_sha == source_sha.
        source = self.feature_agrega_spec()
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.declarar([["angular:app", "projects/app/src/a.spec.ts", "nueva de la feature"]])
        self.seal(review="## AC-1\nfront/feature.txt:1\nBaja historica 'nueva de la feature' en "
                          "projects/app/src/a.spec.ts.\n")
        self.rechazado("sigue definido", "--retirados", str(self.retirados))

    def test_baja_historica_declarada_y_citada_cierra(self):
        spec = self.t.repo / "projects/app/src/a.spec.ts"
        original = spec.read_text()
        source = self.feature_agrega_spec()
        spec.write_text(original)
        target = self.t.commit("fixture: otra feature borra el test")
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source, target)))
        self.declarar([["angular:app", "projects/app/src/a.spec.ts", "nueva de la feature"]])
        self.seal(review="## AC-1\nfront/feature.txt:1\nBaja historica 'nueva de la feature' en "
                          "projects/app/src/a.spec.ts.\n")
        r = self.close("--retirados", str(self.retirados))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        f = json.loads(self.backlog.read_text())["features"][0]
        medicion = f["mediciones_destino"][0]
        self.assertEqual(medicion["retirados"],
                         ["angular:app::projects/app/src/a.spec.ts::nueva de la feature"])
        self.assertEqual(len(medicion["retirados_sha256"]), 64)

    def test_retirados_declara_test_preexistente_no_agregado_por_la_feature_bloquea(self):
        """'healthy' ya vivia declarado en base_sha (fixture inicial); la
        feature #15 solo agrega 'nueva de la feature'. Una feature POSTERIOR
        borra 'healthy' del spec: no es una baja de #15 (hallazgo P2 ronda 2,
        repro simetrico en frontend con Angular/Vitest reales)."""
        spec = self.t.repo / "projects/app/src/a.spec.ts"
        source = self.feature_agrega_spec()
        contenido = spec.read_text()
        self.assertIn("test('healthy', () => expect(1).toBe(1));\n", contenido)
        spec.write_text(contenido.replace("test('healthy', () => expect(1).toBe(1));\n", ""))
        target = self.t.commit("fixture: otra feature borra 'healthy'")
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source, target)))
        self.declarar([["angular:app", "projects/app/src/a.spec.ts", "healthy"]])
        self.seal(review="## AC-1\nfront/feature.txt:1\nBaja historica 'healthy' en "
                          "projects/app/src/a.spec.ts.\n")
        r = self.rechazado("ya estaba declarado en la base", "--retirados", str(self.retirados))
        self.assertIn("healthy", r.stdout + r.stderr)

    def test_repo_con_codigo_y_sin_tests_agregados_bloquea(self):
        """Analogo frontend de CierreHistoricoGoTests.
        test_repo_con_codigo_y_sin_tests_agregados_bloquea: modificar codigo
        (no-test) sin agregar ningun test nuevo bloquea la garantia 4, que
        quedaria vacia (hallazgos P2/P3 ronda 2: sin cobertura en frontend)."""
        (self.t.repo / "projects/app/src/main.ts").write_text("export const x = 1;\n")
        source = self.t.commit("fixture: codigo sin test nuevo")
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.seal()
        self.rechazado("sin agregar ningun test")

    def test_repo_mixto_go_y_frontend_bloquea_en_historico(self):
        """El rechazo de repo mixto Go+frontend (medicion_destino._rechazar_repo_mixto)
        debe aplicar tambien en el camino --historico, no solo en el normal
        (hallazgo P3 ronda 2: el check estaba duplicado sin cobertura propia
        para measure_historico)."""
        (self.t.repo / "go.mod").write_text("module fixture.invalid/mixed\n\ngo 1.22\n")
        source = self.t.commit("fixture: repo mixto Go+frontend")
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.seal()
        self.rechazado("repo mixto no soportado")

    def test_titulo_hoja_ambiguo_bloquea(self):
        source = self.feature_agrega_ambiguo()
        self.ok("worktree.py", "register", "--feature", "15", "--manifest", str(self.manifest(source)))
        self.declarar([["angular:app", "projects/app/src/a.spec.ts", "grupo el resultado final"]])
        self.seal(review="## AC-1\nfront/feature.txt:1\nBaja historica 'grupo el resultado final' en "
                          "projects/app/src/a.spec.ts.\n")
        self.rechazado("ambiguo", "--retirados", str(self.retirados))


if __name__ == "__main__":
    unittest.main()
