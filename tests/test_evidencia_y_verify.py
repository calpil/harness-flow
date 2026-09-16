"""La evidencia y el verify no pueden dar por cubierto lo que no midieron.

Regresiones de tres falsos verdes reales del gate maestro:
  1. cubre_acs abria una seccion por cada MENCION de un AC: una frase como
     'que tambien cubre lo pedido en AC-1' heredaba la cita del AC vecino y
     daba AC-1 por cubierto sin evidencia propia, y de paso truncaba la
     seccion del AC que si tenia cita, marcandolo incumplido. El gate
     reportaba exactamente al reves de la realidad.
  2. verify medio SOLO los AC con comando declarado y reportaba '1/1 en
     verde' con 3 AC en el spec; close lo aceptaba como verify verde.
  3. sello_revision aceptaba un 'Revisado: approved -' tipeado a mano, que es
     justo lo que el sello existe para impedir.
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
sys.path.insert(0, str(SCRIPTS))

from comun import cubre_acs, now_iso, sello_revision  # noqa: E402


def sh(*args, cwd):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)


def harness(script, *args, cwd):
    env = dict(os.environ, HARNESS_SIN_CONTEXTO="1")
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          cwd=str(cwd), capture_output=True, text=True, env=env)


class CubreAcsTests(unittest.TestCase):
    def test_mencion_en_prosa_no_cubre_ni_trunca(self):
        ev = ("# Evidencia\n\n## AC-1\nNo lo implemente, solo prosa.\n\n"
              "## AC-2\nHecho en src/b.ts:10, que cubre lo pedido en AC-1.\n")
        cubiertos, faltan = cubre_acs(ev, ["AC-1", "AC-2"])
        self.assertEqual(faltan, ["AC-1"], "AC-1 no tiene cita propia")
        self.assertEqual(cubiertos, ["AC-2"], "AC-2 si la tiene")

    def test_declaraciones_con_adorno_markdown_siguen_valiendo(self):
        for linea in ("## AC-1", "- AC-1:", "* AC-1 —", "| AC-1 | ok |",
                      "1. AC-1:", "**AC-1**:"):
            with self.subTest(linea=linea):
                cub, _ = cubre_acs(f"{linea}\nsrc/a.ts:1\n", ["AC-1"])
                self.assertEqual(cub, ["AC-1"], f"no reconocio {linea!r}")

    def test_cita_en_la_misma_linea_sigue_valiendo(self):
        cub, _ = cubre_acs("- AC-1: hecho (src/a.ts:42)\n", ["AC-1"])
        self.assertEqual(cub, ["AC-1"])

    def test_ac_sin_cita_en_ninguna_parte_falta(self):
        _, faltan = cubre_acs("## AC-1\nprosa sin citas\n", ["AC-1"])
        self.assertEqual(faltan, ["AC-1"])


class SelloTests(unittest.TestCase):
    def test_sello_real_del_gate_vale(self):
        real = (f"Revisado: approved · {now_iso()} · alan · "
                "estampado por gate.py revision")
        self.assertEqual(sello_revision(real), "approved")

    def test_sello_tipeado_a_mano_no_vale(self):
        for falso in ("Revisado: approved - lo puse yo",
                      "Revisado: approved · yo",
                      "Revisado: approved · 2026-09-16T21:00:00Z · alan · x"):
            with self.subTest(falso=falso):
                self.assertIsNone(sello_revision(falso))


class VerifyParcialTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / "repo"
        self.repo.mkdir(parents=True)
        sh("git", "init", "-q", "-b", "develop", ".", cwd=self.repo)
        sh("git", "config", "user.email", "t@t.invalid", cwd=self.repo)
        sh("git", "config", "user.name", "T", cwd=self.repo)
        (self.repo / "harness").mkdir()
        (self.repo / "docs").mkdir()
        self.backlog = self.repo / "harness" / "feature_list.json"
        self.backlog.write_text(json.dumps(
            {"project": "t", "features": [{"id": "1", "name": "f uno"}]}),
            encoding="utf-8")
        (self.repo / "a.txt").write_text("a\n", encoding="utf-8")
        sh("git", "add", "-A", cwd=self.repo)
        sh("git", "commit", "-qm", "init", cwd=self.repo)
        # Tres AC, uno solo con comando: el clasico "verde que no mide nada".
        (self.repo / "docs" / "spec-feature-1-f-uno.md").write_text(
            "# Spec\n\n- AC-1: trivial `verificar: true`\n"
            "- AC-2: lo dificil, sin comando\n"
            "- AC-3: lo mas dificil, tampoco\n", encoding="utf-8")
        r = harness("gate.py", "approve-spec", "--feature", "1", "--yes",
                    cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def feature(self):
        return json.loads(self.backlog.read_text(encoding="utf-8"))["features"][0]

    def test_verify_declara_los_ac_que_no_midio(self):
        r = harness("gate.py", "verify", "--feature", "1", cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("NO se midieron", r.stdout,
                      "el verde no dijo que 2 de 3 AC no se midieron")
        lv = self.feature()["last_verify"]
        self.assertEqual(lv["acs_declarados"], 3)
        self.assertEqual(sorted(lv["sin_comando"]), ["AC-2", "AC-3"])

    def test_close_rechaza_un_verify_de_otro_spec(self):
        harness("gate.py", "verify", "--feature", "1", cwd=self.repo)
        data = json.loads(self.backlog.read_text(encoding="utf-8"))
        f = data["features"][0]
        f["branch"] = "develop"
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        # El spec crece DESPUES del verify: el 1/1 verde ya no habla de el.
        spec = self.repo / "docs" / "spec-feature-1-f-uno.md"
        spec.write_text(spec.read_text(encoding="utf-8") +
                        "- AC-4: nuevo `verificar: true`\n", encoding="utf-8")
        harness("gate.py", "approve-spec", "--feature", "1", "--yes", cwd=self.repo)
        for name, body in (
            ("impl-1.md", "## AC-1\nsrc/a.ts:1\n## AC-2\nsrc/a.ts:2\n"
                          "## AC-3\nsrc/a.ts:3\n## AC-4\nsrc/a.ts:4\n"),
            ("review-1.md", "## AC-1\nsrc/a.ts:1\n## AC-2\nsrc/a.ts:2\n"
                            "## AC-3\nsrc/a.ts:3\n## AC-4\nsrc/a.ts:4\n"),
        ):
            (self.repo / "docs" / name).write_text(body, encoding="utf-8")
        harness("gate.py", "revision", "--feature", "1", "--veredicto",
                "approved", cwd=self.repo)
        sh("git", "add", "-A", cwd=self.repo)
        sh("git", "commit", "-qm", "docs", cwd=self.repo)
        r = harness("gate.py", "close", "--feature", "1", "--status", "done",
                    "--to", "develop", "--leccion", "ninguna",
                    "--leccion-motivo", "x", cwd=self.repo)
        self.assertNotEqual(r.returncode, 0,
                            "cerro con un verify que midio otro spec")
        self.assertIn("verify obsoleto", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
