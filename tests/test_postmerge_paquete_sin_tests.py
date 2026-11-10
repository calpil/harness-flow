"""Un paquete Go que en la base no tenia NINGUN test registrado puede desaparecer.

Caso real (feature #153 de ADR, 2026-11-10): mover el composition root de la raiz
de un micro a `cmd/server` hace desaparecer el paquete raiz. Si ese paquete no
tenia tests, su desaparicion no pierde cobertura y no hay baja que declarar; el
cierre no puede bloquear. Un paquete que SI registro tests (aunque todos fueran
skip) sigue bloqueando como siempre: eso es la firma de una suite escondida.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(os.environ.get("HARNESS_TEST_SCRIPTS", Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(SCRIPTS))
import postmerge_medido  # noqa: E402


def _base(paquetes, resultados):
    return {"paquetes": paquetes, "resultados": resultados}


class PaqueteSinTestsTests(unittest.TestCase):
    def test_un_paquete_sin_tests_que_desaparece_no_bloquea(self):
        base = _base(["m", "m/config"], [{"Package": "m/config", "Test": "TestA", "Action": "pass"}])
        faltan = postmerge_medido.sin_baja(base, {("m/config", "TestA")}, ["m/config", "m/cmd/server"], [])
        self.assertEqual(faltan, [])

    def test_un_paquete_con_tests_solo_skip_que_desaparece_sigue_bloqueando(self):
        base = _base(["m", "m/x"], [{"Package": "m/x", "Test": "TestOculto", "Action": "skip"}])
        faltan = postmerge_medido.sin_baja(base, set(), ["m"], [])
        self.assertEqual(faltan, ["m/x (paquete)"])

    def test_un_paquete_con_tests_medidos_que_desaparece_bloquea_por_sus_tests(self):
        base = _base(["m", "m/x"], [{"Package": "m/x", "Test": "TestA", "Action": "pass"}])
        faltan = postmerge_medido.sin_baja(base, set(), ["m"], [])
        self.assertEqual(faltan, ["m/x::TestA"])


if __name__ == "__main__":
    unittest.main()
