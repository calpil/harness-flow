"""limpiar-cbm: avisa que procesos cbm estan en uso y mata solo los huerfanos.

Lo que se prueba es la decision de matar: un servidor MCP cuya sesion sigue viva
NO se toca (matarlo deja a esa sesion con cbm caido), y nunca se mata al propio
comando, al daemon ni a un pid que cambio de programa. Todo con procesos y kill
simulados: ninguna prueba mata nada real.
"""
from __future__ import annotations

import contextlib
import io
import os
import signal
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import cbm_procesos as cp  # noqa: E402

BIN = "/Users/x/.local/bin/codebase-memory-mcp"


def proc(pid, ppid, args="", rss=1.0, etime="00:10"):
    cmd = f"{BIN} {args}".strip()
    return {"pid": pid, "ppid": ppid, "etime": etime, "cmd": cmd, "rss_mb": rss,
            "rol": cp.rol(args.split())}


# pid -> (ppid, comando): lo que ve `ps` de todo el sistema
TODOS = {1: (0, "/sbin/launchd"), 100: (1, "-zsh"), 200: (100, "claude"),
         300: (200, "claude --resume x"), 50: (1, "-zsh"), 60: (50, "contexto.py")}


class RolTests(unittest.TestCase):
    def test_roles(self):
        for args, esperado in (
                ("", "sesion"),
                ("--cbm-daemon-internal", "daemon"),
                ("--cbm-daemon-permanent", "daemon"),
                ("cli --index-worker --index-worker-build ab index_repository {}", "worker"),
                ("cli --quiet index_repository {}", "cli"),
                ("hook-augment", "otro"),
                ("config list", "otro")):
            self.assertEqual(cp.rol(args.split()), esperado, args)


class ClasificarTests(unittest.TestCase):
    def _c(self, procesos, protegidos=frozenset()):
        return {p["pid"]: p for p in cp.clasificar(procesos, TODOS, set(protegidos))}

    def test_sesion_con_padre_vivo_esta_en_uso_aunque_este_inactiva(self):
        r = self._c([proc(900, 200)])
        self.assertEqual(r[900]["estado"], "EN USO")
        self.assertIn("claude", r[900]["motivo"])

    def test_sesion_cuyo_padre_murio_es_huerfana(self):
        self.assertEqual(self._c([proc(901, 1)])[901]["estado"], "HUERFANO")

    def test_worker_y_cli_se_juzgan_por_su_padre(self):
        procs = [proc(910, 1, "cli --index-worker x"), proc(911, 920, "cli --index-worker x"),
                 proc(912, 1, "cli --quiet index_repository {}"),
                 proc(913, 60, "cli --quiet index_repository {}")]
        r = self._c(procs)
        self.assertEqual([r[i]["estado"] for i in (910, 911, 912, 913)],
                         ["HUERFANO", "EN USO", "HUERFANO", "EN USO"])

    def test_el_daemon_nunca_se_toca_ni_con_ppid_1(self):
        # un daemon siempre cuelga de init: no es evidencia de orfandad
        r = self._c([proc(930, 1, "--cbm-daemon-internal")])
        self.assertEqual(r[930]["estado"], "EN USO")
        self.assertIn("daemon stop", r[930]["motivo"])

    def test_procesos_cortos_no_se_tocan(self):
        self.assertEqual(self._c([proc(940, 1, "hook-augment")])[940]["estado"], "EN USO")

    def test_este_comando_y_sus_ancestros_estan_protegidos(self):
        self.assertEqual(cp.protegidos(TODOS, yo=60), {60, 50, 1})
        r = self._c([proc(60, 1)], protegidos={60})
        self.assertEqual(r[60]["estado"], "EN USO")


class MatarTests(unittest.TestCase):
    def test_sigterm_y_listo(self):
        p = proc(901, 1)
        vivos = {901}
        envios = []

        def kill(pid, sig):
            envios.append((pid, sig))
            vivos.discard(pid)

        r = cp.matar(p, kill=kill, vivo=lambda pid: pid in vivos,
                     comando=lambda pid: p["cmd"], dormir=lambda s: None)
        self.assertEqual(r, "matado")
        self.assertEqual(envios, [(901, signal.SIGTERM)])

    def test_escala_a_sigkill_si_ignora_sigterm(self):
        p = proc(901, 1)
        vivos = {901}
        envios = []

        def kill(pid, sig):
            envios.append(sig)
            if sig == signal.SIGKILL:
                vivos.discard(pid)

        r = cp.matar(p, kill=kill, vivo=lambda pid: pid in vivos,
                     comando=lambda pid: p["cmd"], dormir=lambda s: None)
        self.assertEqual(r, "matado (SIGKILL)")
        self.assertEqual(envios, [signal.SIGTERM, signal.SIGKILL])

    def test_si_no_muere_lo_dice(self):
        p = proc(901, 1)
        r = cp.matar(p, kill=lambda *a: None, vivo=lambda pid: True,
                     comando=lambda pid: p["cmd"], dormir=lambda s: None)
        self.assertIn("NO SE PUDO", r)

    def test_pid_reutilizado_por_otro_programa_no_se_mata(self):
        p = proc(901, 1)
        kill = mock.Mock()
        r = cp.matar(p, kill=kill, vivo=lambda pid: True,
                     comando=lambda pid: "/usr/bin/vim notas.txt", dormir=lambda s: None)
        kill.assert_not_called()
        self.assertIn("otro programa", r)

    def test_pid_que_ya_no_existe(self):
        kill = mock.Mock()
        r = cp.matar(proc(901, 1), kill=kill, comando=lambda pid: None,
                     dormir=lambda s: None)
        kill.assert_not_called()
        self.assertIn("ya no existia", r)


class LimpiarTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = Path(self.tmp.name)
        for patcher in (mock.patch.object(cp, "cache_dir", return_value=self.cache),
                        mock.patch.object(cp, "ES_WINDOWS", False)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _correr(self, procesos, **kw):
        muertos = []
        salida = io.StringIO()
        inyectado = dict(kill=lambda pid, sig: muertos.append(pid),
                         vivo=lambda pid: pid not in muertos,
                         comando=lambda pid: next(p["cmd"] for p in procesos if p["pid"] == pid),
                         dormir=lambda s: None)
        with mock.patch.object(cp, "leer_procesos", return_value=(procesos, TODOS)), \
                mock.patch.object(cp, "protegidos", return_value={60, 50, 1}), \
                contextlib.redirect_stdout(salida):
            rc = cp.limpiar(**kw, **inyectado)
        return rc, muertos, salida.getvalue()

    def _stage(self, nombre="X.db.stage.abc", edad_s=7200):
        f = self.cache / nombre
        f.write_text("x")
        t = time.time() - edad_s
        os.utime(f, (t, t))
        return f

    def test_mata_solo_los_huerfanos_y_dice_que_estan_en_uso_los_demas(self):
        procs = [proc(900, 200), proc(901, 1), proc(902, 300),
                 proc(930, 1, "--cbm-daemon-internal")]
        rc, muertos, out = self._correr(procs)
        self.assertEqual(muertos, [901])
        self.assertEqual(rc, 0)
        self.assertEqual(out.count("EN USO"), 3)
        self.assertEqual(out.count("HUERFANO"), 1)

    def test_solo_avisar_no_mata_ni_borra_nada(self):
        f = self._stage()
        rc, muertos, out = self._correr([proc(901, 1)], matar_huerfanos=False)
        self.assertEqual(muertos, [])
        self.assertTrue(f.exists())
        self.assertIn("se matarian", out)
        self.assertIn("se borraria", out)

    def test_nada_huerfano_no_mata(self):
        rc, muertos, out = self._correr([proc(900, 200), proc(902, 300)])
        self.assertEqual(muertos, [])
        self.assertIn("nada que matar", out)

    def test_sin_procesos_cbm(self):
        rc, muertos, out = self._correr([])
        self.assertEqual((rc, muertos), (0, []))
        self.assertIn("(ninguno)", out)

    def test_stage_viejo_sin_daemon_se_borra(self):
        viejo, reciente = self._stage("A.db.stage.x"), self._stage("B.db.stage.y", edad_s=60)
        sesion = proc(900, 200)             # una sesion viva no indexa: no impide limpiar
        self._correr([sesion])
        self.assertFalse(viejo.exists())
        self.assertTrue(reciente.exists())  # puede ser de un indexado que acaba de terminar

    def test_stage_no_se_toca_con_un_indexado_vivo(self):
        f = self._stage()
        for vivo in (proc(930, 1, "--cbm-daemon-internal"),
                     proc(931, 930, "cli --index-worker x"),
                     proc(932, 60, "cli --quiet index_repository {}")):
            self._correr([vivo])
            self.assertTrue(f.exists(), vivo["cmd"])

    def test_no_toca_archivos_que_no_son_stage(self):
        db = self.cache / "Users-x-proyecto.db"
        db.write_text("x")
        os.utime(db, (0, 0))
        self._correr([])
        self.assertTrue(db.exists())

    def test_un_kill_fallido_sale_con_1(self):
        p = proc(901, 1)
        with mock.patch.object(cp, "leer_procesos", return_value=([p], TODOS)), \
                mock.patch.object(cp, "protegidos", return_value={60}), \
                contextlib.redirect_stdout(io.StringIO()):
            rc = cp.limpiar(kill=lambda *a: None, vivo=lambda pid: True,
                            comando=lambda pid: p["cmd"], dormir=lambda s: None)
        self.assertEqual(rc, 1)

    def test_windows_no_hace_nada(self):
        with mock.patch.object(cp, "ES_WINDOWS", True), \
                mock.patch.object(cp, "leer_procesos") as m, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cp.limpiar(), 0)
        m.assert_not_called()


class LeerProcesosTests(unittest.TestCase):
    def test_parsea_ps_y_filtra_solo_cbm(self):
        ps = (f"  900   200 03-01:59:40   1280 {BIN}\n"
              f"  901     1    05:10  2048000 {BIN} cli --index-worker --index-worker-build ab x\n"
              "  902   200    00:05     500 /usr/bin/python3 script.py\n"
              "  903   200    00:05     500 /Users/x/bin/my-codebase-memory-mcp-fork run\n"
              "basura sin formato\n")
        with mock.patch.object(cp.subprocess, "run",
                               return_value=mock.Mock(stdout=ps)):
            cbm, todos = cp.leer_procesos()
        self.assertEqual([(p["pid"], p["rol"]) for p in cbm], [(900, "sesion"), (901, "worker")])
        self.assertEqual(todos[902][0], 200)
        self.assertEqual(round(cbm[1]["rss_mb"]), 2000)


if __name__ == "__main__":
    unittest.main()
