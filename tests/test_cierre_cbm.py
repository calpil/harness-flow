"""El cierre real (gate.py close) ante un cbm que no atendio.

Que el daemon compartido no responda no es un fallo del cierre: el cierre termina
bien, el aviso sale por el camino real de gate.main() y dice que NO hacer (matar el
daemon), no solo lo que paso. Se reutiliza el fixture de cierre multi-repo; solo
`contexto.refrescar` se sustituye (lanzaria graphify de verdad).
"""
import contextlib
import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

import test_multirepo_close as fixtures

sys.path.insert(0, str(fixtures.SCRIPTS))
import contexto
import gate

PENDIENTE = {"front": {"nombre": "front", "motivo": "CBM daemon connection capacity reached",
                       "intentos": 3, "diagnostico": {"procesos": {"sesion": 9},
                                                      "sesiones_cortadas": 9, "carga": [2.5, 2.0, 1.8]}}}


class CierreCbmPendiente(unittest.TestCase):
    def setUp(self):
        self.t = fixtures.MultiRepoCloseTests()
        self.t.setUp()
        self.addCleanup(self.t.doCleanups)

    def _cerrar(self, parte):
        t = self.t
        t.register()
        t.seal()
        args = ['gate.py', 'close', '--feature', '7', '--status', 'done', '--to', 'develop',
                '--leccion', 'closure-contract', '--integrated', '--postmerge', str(t.postmerge_path)]
        out = io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(t.root)
            with mock.patch.dict(os.environ, t.env, clear=True), \
                    mock.patch.object(sys, 'argv', args), \
                    mock.patch.object(contexto, 'refrescar', return_value=parte), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                try:
                    gate.main()
                    code = 0
                except (Exception, SystemExit) as exc:
                    code = 1
                    print(type(exc).__name__, str(exc))
        finally:
            os.chdir(previous)
        return code, out.getvalue()

    def test_cbm_pendiente_no_tumba_el_cierre_y_avisa_que_no_hacer(self):
        parte = {"fallos": [], "cbm": {"pendientes": PENDIENTE}}
        code, salida = self._cerrar(parte)
        self.assertEqual(code, 0, salida)
        self.assertEqual(self.t.load()['status'], 'done')
        self.assertIn("[ok] contexto refrescado", salida)
        self.assertIn("cbm pendiente (el cierre no depende de el): front", salida)
        self.assertIn("No lo reintentes a mano", salida)
        self.assertIn("limpiar-cbm", salida)
        self.assertIn("Al fallar: 9 sesiones cbm (9 cortadas), carga 2.5", salida)
        self.assertNotIn("contexto NO quedo refrescado", salida)

    def test_un_fallo_real_sigue_viendose_como_fallo_aunque_haya_pendiente(self):
        parte = {"fallos": ["graphify update front: roto"], "cbm": {"pendientes": PENDIENTE}}
        code, salida = self._cerrar(parte)
        self.assertEqual(code, 0, salida)
        self.assertIn("contexto NO quedo refrescado", salida)
        self.assertIn("graphify update front: roto", salida)
        self.assertIn("cbm pendiente", salida)

    def test_sin_cbm_en_el_parte_el_cierre_es_el_de_siempre(self):
        code, salida = self._cerrar({"fallos": []})
        self.assertEqual(code, 0, salida)
        self.assertIn("[ok] contexto refrescado", salida)
        self.assertNotIn("cbm pendiente", salida)


if __name__ == "__main__":
    unittest.main()
