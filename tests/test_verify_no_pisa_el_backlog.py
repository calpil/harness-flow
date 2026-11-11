"""verify escribe solo su propia medicion: no pisa lo que otro gate sello mientras corria.

Bug (realestate, 2026-11-10/11): `gate.py verify` cargaba el backlog al empezar
y lo reescribia ENTERO al terminar. Una cadena de verify de seis features (horas
de suites Go) borro en silencio el sello de la enmienda E-5 de la #227 y el
review r1 de la #227, puestos con `gate.py enmienda`/`revision` mientras corria.
Ya habia pasado el 2026-11-06 (specs 242/243 y el close de la 241). Cada vez
hubo que detectar la perdida y re-sellar a mano.

Contrato:
  - lo que otro gate escriba en OTRA feature durante el verify sobrevive;
  - lo que otro gate escriba en la MISMA feature (una enmienda, un review)
    tambien sobrevive;
  - `last_verify.enmiendas` registra las enmiendas que habia al EMPEZAR: un
    verify que midio el spec anterior a una enmienda no la cubre.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

SELLAR = """\
import json, pathlib
p = pathlib.Path('harness/feature_list.json')
d = json.loads(p.read_text(encoding='utf-8'))
otra = [f for f in d['features'] if f['id'] == '2'][0]
otra['veredicto'] = 'changes_requested'
misma = [f for f in d['features'] if f['id'] == '1'][0]
misma.setdefault('enmiendas', []).append({'id': 'E-1', 'por': 'test'})
misma['veredicto'] = 'changes_requested'
p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')
"""


def harness(script, *args, cwd):
    env = dict(os.environ, HARNESS_SIN_CONTEXTO="1", HARNESS_SIN_CBM="1")
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          cwd=str(cwd), capture_output=True, text=True, env=env)


class VerifyNoPisaElBacklogTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="verify-pisa-")
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name).resolve() / "repo"
        (self.repo / "harness").mkdir(parents=True)
        (self.repo / "docs").mkdir()
        subprocess.run(["git", "init", "-q", "-b", "develop", "."], cwd=self.repo, check=True)
        self.backlog = self.repo / "harness" / "feature_list.json"
        self.backlog.write_text(json.dumps({"project": "t", "features": [
            {"id": "1", "name": "medida", "status": "in_progress", "veredicto": "approved"},
            {"id": "2", "name": "vecina", "status": "in_progress", "veredicto": "approved"},
        ]}), encoding="utf-8")
        (self.repo / "sellar.py").write_text(SELLAR, encoding="utf-8")

    def spec(self, comando):
        (self.repo / "docs" / "spec-feature-1-medida.md").write_text(
            f"# Spec 1\nEstado: approved\n\n- AC-1: x `verificar: {comando}`\n",
            encoding="utf-8")

    def features(self):
        d = json.loads(self.backlog.read_text(encoding="utf-8"))
        return {f["id"]: f for f in d["features"]}

    def verify_con_un_sello_en_medio(self):
        self.spec(f"{sys.executable} sellar.py")
        r = harness("gate.py", "verify", "--feature", "1", cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return self.features()

    def test_el_sello_de_otra_feature_sobrevive(self):
        fs = self.verify_con_un_sello_en_medio()
        self.assertEqual(fs["2"]["veredicto"], "changes_requested",
                         "verify borro el review que otro gate sello en la #2")

    def test_la_enmienda_y_el_review_de_la_misma_feature_sobreviven(self):
        fs = self.verify_con_un_sello_en_medio()
        self.assertEqual([e["id"] for e in fs["1"].get("enmiendas", [])], ["E-1"],
                         "verify borro la enmienda sellada mientras corria")
        self.assertEqual(fs["1"]["veredicto"], "changes_requested")

    def test_la_medicion_queda_registrada_con_las_enmiendas_del_comienzo(self):
        fs = self.verify_con_un_sello_en_medio()
        lv = fs["1"]["last_verify"]
        self.assertEqual((lv["fallos"], lv["total"]), (0, 1))
        self.assertEqual(lv["enmiendas"], 0,
                         "un verify que midio el spec previo no cubre la enmienda nueva")

    def test_sin_sellos_en_medio_solo_agrega_last_verify(self):
        self.spec("true")
        antes = self.features()
        r = harness("gate.py", "verify", "--feature", "1", cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        despues = self.features()
        self.assertEqual(despues["2"], antes["2"])
        sin_verify = {k: v for k, v in despues["1"].items() if k != "last_verify"}
        self.assertEqual(sin_verify, antes["1"])


if __name__ == "__main__":
    unittest.main()
