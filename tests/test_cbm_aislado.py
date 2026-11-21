#!/usr/bin/env python3
"""Pruebas de aislamiento CBM por proyecto (`cbm_proyecto.py`) y deteccion `.sock.identity`."""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cbm_procesos as cp  # noqa: E402
import cbm_proyecto as cbp  # noqa: E402
import contexto  # noqa: E402


def escribir(ruta: Path, texto: str) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


def git(cwd: Path, *args: str) -> None:
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    assert r.returncode == 0, f"git {args}: {r.stderr}"


class RaizYDirectoriosCbmTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_resuelve_raiz_harness_desde_subrepo_y_worktree(self):
        proy = self.tmp / "DEREC"
        escribir(proy / "harness" / "feature_list.json", '{"project": "DEREC", "features": []}\n')
        sub = proy / "ms-orders"
        sub.mkdir(parents=True)
        git(sub, "init", "-b", "develop")
        git(sub, "config", "user.email", "t@example.com")
        git(sub, "config", "user.name", "T")
        escribir(sub / "main.go", "package main\n")
        git(sub, "add", ".")
        git(sub, "commit", "-m", "init")

        # Worktree hermano fuera de `proy` (ej. DEREC-wt/1-feat)
        wt = self.tmp / "DEREC-wt" / "1-feat"
        wt.parent.mkdir(parents=True, exist_ok=True)
        git(sub, "worktree", "add", "-b", "feat/1", str(wt))

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HARNESS_CBM_PROJECT_ROOT", None)
            self.assertEqual(proy, cbp.raiz_proyecto_cbm(proy))
            self.assertEqual(proy, cbp.raiz_proyecto_cbm(sub))
            self.assertEqual(proy, cbp.raiz_proyecto_cbm(wt))

    def test_rutas_proyecto_son_deterministas_distintas_por_proyecto_y_caben_en_sun_path(self):
        # Base corta (como ~/.cbm): vive fuera de /tmp sin activar fallback_tmp
        base = Path(f"/tmp/cbm-b-{os.getpid()}")
        if base.exists():
            shutil.rmtree(base)
        self.addCleanup(shutil.rmtree, base, True)
        p1 = self.tmp / "DEREC"
        p2 = self.tmp / "Online-Invoice"
        p1.mkdir(); p2.mkdir()

        i1 = cbp.preparar_directorios(cbp.rutas_proyecto(p1, base=base))
        i2 = cbp.preparar_directorios(cbp.rutas_proyecto(p2, base=base))

        self.assertFalse(i1["fallback_tmp"])
        self.assertNotEqual(i1["key"], i2["key"])
        self.assertNotEqual(i1["runtime_dir"], i2["runtime_dir"])
        self.assertNotEqual(i1["cache_dir"], i2["cache_dir"])
        self.assertTrue(Path(i1["runtime_dir"]).is_dir())
        self.assertTrue(Path(i1["cache_dir"]).is_dir())
        self.assertLessEqual(i1["sun_path_estimado"], 104)

        meta = json.loads(Path(i1["meta_file"]).read_text(encoding="utf-8"))
        self.assertEqual("DEREC", meta["name"])
        self.assertEqual(str(p1), meta["root"])

        # proyecto_de_socket recupera el proyecto tanto en modo normal como con fallback_tmp
        sock = str(Path(i1["runtime_dir"]) / "cbm-daemon-501" / "cbm-abc.sock")
        self.assertEqual("DEREC", cbp.proyecto_de_socket(sock)["name"])

        base_larga = self.tmp / "una-carpeta-muy-larga-para-probar-el-limite-sun-path" / ".cbm"
        i_fb = cbp.preparar_directorios(cbp.rutas_proyecto(p1, base=base_larga))
        self.addCleanup(shutil.rmtree, Path(i_fb["runtime_dir"]), True)
        self.assertTrue(i_fb["fallback_tmp"])
        self.assertLessEqual(i_fb["sun_path_estimado"], 104)
        sock_fb = str(Path(i_fb["runtime_dir"]) / "cbm-daemon-501" / "cbm-abc.sock")
        self.assertEqual("DEREC", cbp.proyecto_de_socket(sock_fb)["name"])

    def test_modo_aislado_precedencia_y_activacion(self):
        base = self.tmp / ".cbm"
        proy = self.tmp / "app"
        proy.mkdir()
        clean_env = {k: v for k, v in os.environ.items()
                     if k not in ("HARNESS_CBM_GLOBAL", "HARNESS_CBM_AISLADO",
                                  "CBM_RUNTIME_DIR", "CBM_CACHE_DIR", "HARNESS_CBM_HOME")}
        with mock.patch.dict(os.environ, clean_env, clear=True):
            self.assertFalse(cbp.modo_aislado_activo(proy, base=base))
            cbp.activar_modo_aislado(True, base=base)
            self.assertTrue(cbp.modo_aislado_activo(proy, base=base))
            cbp.activar_modo_aislado(False, base=base)
            self.assertFalse(cbp.modo_aislado_activo(proy, base=base))

            # Con grafos.json `"cbm_aislado": true` se activa por proyecto
            escribir(proy / "harness" / "grafos.json", '{"cbm_aislado": true, "raices": []}\n')
            self.assertTrue(cbp.modo_aislado_activo(proy, base=base))

            # HARNESS_CBM_GLOBAL=1 siempre apaga el aislamiento
            with mock.patch.dict(os.environ, {"HARNESS_CBM_GLOBAL": "1"}):
                self.assertFalse(cbp.modo_aislado_activo(proy, base=base))

    def test_cli_harness_info_y_config_mcp(self):
        r1 = subprocess.run([sys.executable, str(SCRIPTS / "cbm_proyecto.py"),
                             "--harness-info", "--cwd", str(self.tmp), "--json"],
                            capture_output=True, text=True)
        self.assertEqual(0, r1.returncode, r1.stderr)
        data = json.loads(r1.stdout)
        self.assertEqual(str(self.tmp), data["root"])

        r2 = subprocess.run([sys.executable, str(SCRIPTS / "cbm_proyecto.py"),
                             "--harness-config-mcp"],
                            capture_output=True, text=True)
        self.assertEqual(0, r2.returncode, r2.stderr)
        for host_cfg in ("~/.claude.json", "mcp_config.json", "~/.grok/config.toml", "~/.hermes/config.yaml"):
            self.assertIn(host_cfg, r2.stdout)


class DaemonSinIdentidadTests(unittest.TestCase):
    D = {"pid": 39532, "ppid": 1, "etime": "04-12:53:51",
         "cmd": "/Users/x/.local/bin/codebase-memory-mcp --cbm-daemon-internal",
         "rss_mb": 5.0, "rol": "daemon"}
    TODOS = {1: (0, "/sbin/launchd"), 200: (1, "claude")}

    def test_detecta_daemon_con_sock_pero_sin_sock_identity(self):
        rutas = {39532: ["/tmp/cbm-daemon-501/cbm-abc.anc", "/tmp/cbm-daemon-501/cbm-abc.sock"]}
        # Existe .sock y .anc, falta .sock.identity -> unverified!
        vivos_sin_id = {"/tmp/cbm-daemon-501/cbm-abc.anc", "/tmp/cbm-daemon-501/cbm-abc.sock"}
        self.assertEqual([], cp.daemon_sin_socket([self.D], rutas=lambda p: rutas[p], existe=lambda r: r in vivos_sin_id))
        self.assertEqual([39532], cp.daemon_sin_identidad([self.D], rutas=lambda p: rutas[p], existe=lambda r: r in vivos_sin_id))

        # Si existe .sock.identity -> sano
        vivos_ok = vivos_sin_id | {"/tmp/cbm-daemon-501/cbm-abc.sock.identity"}
        self.assertEqual([], cp.daemon_sin_identidad([self.D], rutas=lambda p: rutas[p], existe=lambda r: r in vivos_ok))

        # En macOS lsof suele devolver solo `.anc`, con `.sock` hermano en disco pero sin `.sock.identity`
        rutas_solo_anc = {39532: ["/tmp/cbm-daemon-501/cbm-abc.anc"]}
        self.assertEqual([39532], cp.daemon_sin_identidad([self.D], rutas=lambda p: rutas_solo_anc[p], existe=lambda r: r in vivos_sin_id))
        self.assertEqual([], cp.daemon_sin_identidad([self.D], rutas=lambda p: rutas_solo_anc[p], existe=lambda r: r in vivos_ok))

        # Si falta el .sock entero -> lo cubre daemon_sin_socket, no se duplica en daemon_sin_identidad
        self.assertEqual([39532], cp.daemon_sin_socket([self.D], rutas=lambda p: rutas[p], existe=lambda r: False))
        self.assertEqual([], cp.daemon_sin_identidad([self.D], rutas=lambda p: rutas[p], existe=lambda r: False))

    def test_limpiar_y_reiniciar_daemon_cubren_sin_identidad(self):
        out = io.StringIO()
        with mock.patch.object(cp, "ES_WINDOWS", False), \
             mock.patch.object(cp, "leer_procesos", return_value=([self.D], self.TODOS)), \
             mock.patch.object(cp, "protegidos", return_value=set()), \
             mock.patch.object(cp, "cache_dir", return_value=Path(tempfile.gettempdir())), \
             contextlib.redirect_stdout(out):
            rc = cp.limpiar(matar_huerfanos=False, enlaces=lambda pids: set(),
                            sin_socket=lambda ps: [], sin_identidad=lambda ps: [39532],
                            cwds=lambda pids: {})
        self.assertEqual(0, rc)
        self.assertIn(".sock.identity", out.getvalue())
        self.assertIn("unverified CBM daemon", out.getvalue())

        muertos: list[int] = []
        out2 = io.StringIO()
        with mock.patch.object(cp, "ES_WINDOWS", False), contextlib.redirect_stdout(out2):
            rc2 = cp.reiniciar_daemon(
                solo_avisar=False, leer=lambda: ([self.D], self.TODOS),
                detectar=lambda ps: [], detectar_identidad=lambda ps: [39532],
                enlaces=lambda pids: set(), verificar=lambda: (True, "0.4 s"),
                cwds=lambda pids: {}, dormir=lambda s: None,
                kill=lambda pid, sig: muertos.append(pid),
                vivo=lambda pid: pid not in muertos,
                comando=lambda pid: self.D["cmd"],
            )
        self.assertEqual(0, rc2)
        self.assertEqual([39532], muertos)
        self.assertIn("sin .sock.identity (unverified)", out2.getvalue())

    def test_lineas_cbm_pendiente_explica_sin_identidad(self):
        lineas = contexto.lineas_cbm_pendiente({}, sin_socket=[], sin_identidad=[39532])
        txt = "\n".join(lineas)
        self.assertIn("39532", txt)
        self.assertIn(".sock.identity", txt)
        self.assertIn("cbm_proyecto.py", txt)


class ContextoAisladoIntegracionTests(unittest.TestCase):
    def test_contexto_cbm_pasa_env_aislado_cuando_esta_activo(self):
        tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, tmp, True)
        base = Path(f"/tmp/cbm-ctx-{os.getpid()}").resolve()
        if base.exists():
            shutil.rmtree(base)
        self.addCleanup(shutil.rmtree, base, True)
        proy = tmp / "mi-proy"
        proy.mkdir()
        git(proy, "init", "-b", "develop")
        git(proy, "config", "user.email", "t@example.com")
        git(proy, "config", "user.name", "T")
        escribir(proy / "main.go", "package main\n")
        escribir(proy / "harness" / "feature_list.json", '{"project": "mi-proy", "features": []}\n')
        git(proy, "add", ".")
        git(proy, "commit", "-m", "init")

        p = {"root": proy, "harness": proy / "harness", "graph": proy / "graphify-out" / "graph.json"}
        capturado: dict = {}

        def fake_cli(tool, args, cwd, *, env_extra=None):
            capturado["env_extra"] = env_extra
            return 0, '{"status":"indexed"}'

        with mock.patch.dict(os.environ, {"HARNESS_CBM_AISLADO": "1", "HARNESS_CBM_HOME": str(base)}, clear=False), \
             mock.patch.object(shutil, "which", return_value="/usr/local/bin/codebase-memory-mcp"), \
             mock.patch.object(contexto, "_cbm_daemon_sin_socket", return_value=[]), \
             mock.patch.object(contexto, "_cbm_daemon_sin_identidad", return_value=[]), \
             mock.patch.object(contexto, "_cbm_cli", side_effect=fake_cli):
            os.environ.pop("HARNESS_SIN_CBM", None)
            os.environ.pop("HARNESS_CBM_GLOBAL", None)
            parte = {"fallos": []}
            contexto.cbm_indexar(p, parte, verboso=False)

        self.assertEqual([], parte["fallos"])
        self.assertIsNotNone(capturado.get("env_extra"))
        self.assertIn("CBM_RUNTIME_DIR", capturado["env_extra"])
        self.assertIn("CBM_CACHE_DIR", capturado["env_extra"])
        self.assertTrue(capturado["env_extra"]["CBM_RUNTIME_DIR"].startswith(str(base)))

    @unittest.skipUnless(shutil.which("codebase-memory-mcp"), "requiere codebase-memory-mcp instalado")
    def test_wrapper_live_funciona_aislado_del_daemon_global(self):
        # Usa una ruta corta en /tmp para garantizar sun_path <= 104 en macOS.
        base = Path(f"/tmp/cbm-ut-{os.getpid()}")
        proy = base / "proj"
        if base.exists():
            shutil.rmtree(base)
        proy.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, base, True)
        escribir(proy / "harness" / "feature_list.json", '{"project": "ut", "features": []}\n')

        env = dict(os.environ, HARNESS_CBM_HOME=str(base / "h"))
        for k in ("CBM_RUNTIME_DIR", "CBM_CACHE_DIR", "HARNESS_CBM_GLOBAL"):
            env.pop(k, None)
        try:
            r = subprocess.run(
                [sys.executable, str(SCRIPTS / "cbm_proyecto.py"), "cli", "--quiet", "list_projects", "{}"],
                cwd=str(proy), stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env, timeout=30,
            )
            self.assertEqual(0, r.returncode, r.stdout + r.stderr)
            self.assertIn("projects:", r.stdout)
        finally:
            subprocess.run(
                [sys.executable, str(SCRIPTS / "cbm_proyecto.py"), "daemon", "stop"],
                cwd=str(proy), stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env, timeout=15,
            )


if __name__ == "__main__":
    unittest.main()
