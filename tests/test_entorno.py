"""Regresiones de portabilidad sin configuracion ni red de la maquina."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import entorno


class EntornoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        patch = mock.patch.object(Path, "home", return_value=self.home)
        patch.start()
        self.addCleanup(patch.stop)

    def test_claude_en_ejecucion_gana_a_hermes_heredado(self):
        os.environ.update(CLAUDECODE="1", HERMES_HOME=str(self.home / ".hermes"))
        self.assertEqual(entorno.host_agente(), "claude")

    def test_claude_config_dir_tambien_identifica_el_host(self):
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.home / ".claude")
        self.assertEqual(entorno.host_agente(), "claude")

    def test_host_explicito_gana_y_no_normaliza_invalidos(self):
        os.environ.update(HARNESS_HOST="hermes", CLAUDECODE="1")
        self.assertEqual(entorno.host_agente(), "hermes")
        os.environ["HARNESS_HOST"] = "gpt"
        self.assertEqual(entorno.host_agente(), "gpt")
        os.environ["HARNESS_HOST"] = "codex"
        self.assertEqual(entorno.host_agente(), "gpt")
        os.environ["HARNESS_HOST"] = "Claude"
        with self.assertRaises(ValueError):
            entorno.host_agente()

    def test_copia_openai_agents_skills_detecta_host_gpt(self):
        script = self.home / ".agents/skills/harness-flow/scripts/entorno.py"
        script.parent.mkdir(parents=True)
        script.touch()
        with mock.patch.object(entorno, "__file__", str(script)):
            self.assertEqual(entorno.host_agente(), "gpt")

    def test_symlink_claude_no_hereda_host_de_destino(self):
        target = self.home / ".hermes/skills/software-development/harness-flow/scripts"
        target.mkdir(parents=True)
        (target / "entorno.py").touch()
        link = self.home / ".claude/skills/harness-flow"
        link.parent.mkdir(parents=True)
        link.symlink_to(target.parent, target_is_directory=True)
        os.environ["HERMES_HOME"] = str(self.home / ".hermes")
        with mock.patch.object(entorno, "__file__", str(link / "scripts/entorno.py")):
            self.assertEqual(entorno.host_agente(), "claude")

    def test_hermes_perfil_nuevo_no_cae_al_default(self):
        (self.home / ".hermes").mkdir()
        perfil = self.home / ".hermes/profiles/nuevo"
        os.environ["HERMES_HOME"] = str(perfil)
        self.assertEqual(entorno.host_agente(), "hermes")
        self.assertEqual(entorno.hermes_home(), perfil)

    def test_copia_claude_no_se_confunde_con_hermes_home(self):
        script = self.home / ".claude/skills/harness-flow/scripts/entorno.py"
        script.parent.mkdir(parents=True)
        with mock.patch.object(entorno, "__file__", str(script)):
            self.assertEqual(entorno.host_agente(), "claude")
            self.assertIsNone(entorno.hermes_home())

    def test_python_neutro_override_gana_y_invalido_no_cae(self):
        os.environ.update(HARNESS_PYTHON=sys.executable, HERMES_PYTHON="/no/existe")
        self.assertEqual(entorno.python_harness(), Path(sys.executable))
        os.environ["HARNESS_PYTHON"] = str(self.home / "no-existe")
        with self.assertRaises(ValueError):
            entorno.python_harness()

    def test_claude_sin_hermes_usa_python_actual_para_gates(self):
        os.environ.update(HARNESS_HOST="claude", HERMES_PYTHON="/heredado/python")
        with mock.patch.object(entorno, "tiene_psycopg", return_value=False), \
             mock.patch.object(entorno, "_desde_launcher") as launcher:
            self.assertEqual(entorno.python_harness(), Path(sys.executable))
            launcher.assert_not_called()

    def test_venv_neutro_existente_es_reutilizado(self):
        os.environ["HARNESS_HOST"] = "generic"
        py = self.home / ".harness-flow/venv/bin/python"
        py.parent.mkdir(parents=True)
        py.symlink_to(sys.executable)
        with mock.patch.object(entorno, "ES_WINDOWS", False):
            self.assertEqual(entorno.python_harness(), py)

    def test_alias_hermes_y_launcher_siguen_disponibles(self):
        os.environ.update(HARNESS_HOST="hermes", HERMES_PYTHON=sys.executable)
        self.assertEqual(entorno.python_harness(), Path(sys.executable))
        del os.environ["HERMES_PYTHON"]
        with mock.patch.object(entorno, "tiene_psycopg", return_value=False), \
             mock.patch.object(entorno, "_desde_launcher", return_value=Path(sys.executable)):
            self.assertEqual(entorno.python_harness(), Path(sys.executable))

    def cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", ["entorno.py", *args]), \
             contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                rc = entorno.main()
            except SystemExit as exc:
                rc = exc.code
        return rc, stdout.getvalue(), stderr.getvalue()

    def test_shell_exporta_host_y_rutas_literales_para_subprocesos(self):
        ruta = self.home / "scripts con '$HOME` y \"comillas"
        os.environ["HARNESS_PYTHON"] = sys.executable
        with mock.patch.object(entorno, "scripts_dir", return_value=ruta):
            rc, out, err = self.cli("--host", "claude", "--shell")
        self.assertEqual(rc, 0, err)
        self.assertEqual(err, "")
        # Un shell real consume las asignaciones; no se evalua contenido de rutas.
        result = subprocess.run(["/bin/sh", "-c", out + '\n"$PY" -c \'import os,json; print(json.dumps([os.environ[k] for k in ("H","PY","HARNESS_HOST","HARNESS_PYTHON")]))\''],
                                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), [str(ruta), sys.executable, "claude", sys.executable])

    def test_powershell_exporta_literales_y_host_en_environment(self):
        ruta = Path("C:/O'Brien/$datos/scripts")
        os.environ["HARNESS_PYTHON"] = sys.executable
        with mock.patch.object(entorno, "scripts_dir", return_value=ruta):
            rc, out, err = self.cli("--host", "claude", "--powershell")
        self.assertEqual(rc, 0, err)
        self.assertIn("$H = 'C:/O''Brien/$datos/scripts'", out)
        self.assertIn("$env:HARNESS_HOST = 'claude'", out)

    def test_venv_neutro_incompleto_no_gana_a_un_interprete_con_psycopg(self):
        # venv a medio instalar: si el interprete actual si tiene psycopg, usalo
        venv = self.home / ".harness-flow/venv"
        py = entorno._bin_python(venv)
        py.parent.mkdir(parents=True, exist_ok=True)
        py.touch()
        os.environ["HARNESS_HOST"] = "claude"
        with mock.patch.object(entorno, "tiene_psycopg",
                               side_effect=lambda p: Path(p) != py):
            self.assertEqual(entorno.python_harness(), Path(sys.executable))

    def test_diagnostico_sin_psycopg_no_es_error_si_solo_usas_gates(self):
        # exit!=0 permanente para quien no usa el hub convierte el diagnostico en ruido
        os.environ["HARNESS_PYTHON"] = sys.executable
        with mock.patch.object(entorno, "tiene_psycopg", return_value=False):
            rc, out, err = self.cli()
        self.assertEqual(rc, 0, "sin --hub el diagnostico informa, no falla")
        self.assertIn("psycopg", out + err)

    def test_diagnostico_con_hub_si_falla_sin_psycopg(self):
        os.environ["HARNESS_PYTHON"] = sys.executable
        with mock.patch.object(entorno, "tiene_psycopg", return_value=False):
            rc, out, err = self.cli("--hub")
        self.assertEqual(rc, 1, "si declaras que usas el hub, la falta es un error")

    def test_error_python_no_emite_codigo_shell_parcial(self):
        os.environ["HARNESS_PYTHON"] = str(self.home / "missing")
        rc, out, err = self.cli("--shell")
        self.assertEqual(rc, 1)
        self.assertEqual(out, "")
        self.assertIn("HARNESS_PYTHON", err)

    def test_instalacion_sin_venv_no_toca_python_del_sistema(self):
        # El invariante es del comando, no del host: en NINGUN host se instala
        # psycopg en un interprete que no sea un venv.
        for host in ("claude", "hermes", "gpt", "generic"):
            with self.subTest(host=host):
                os.environ["HARNESS_HOST"] = host
                invocados = []
                def comando(args, **kwargs):
                    invocados.append(list(args))
                    return subprocess.CompletedProcess(args, 0)
                venv = self.home / ".harness-flow/venv"
                py = entorno._bin_python(venv)
                with mock.patch.object(entorno, "tiene_psycopg",
                                       side_effect=lambda p: Path(p) == py), \
                     mock.patch.object(entorno.subprocess, "run", side_effect=comando):
                    rc, out, err = self.cli("--instalar-deps", "--shell")
                self.assertEqual(rc, 0, err)
                # se crea el venv neutro (con el interprete que resuelva el host,
                # que en hermes puede ser el del propio agente y no sys.executable)
                self.assertIn(["-m", "venv", str(venv)],
                              [c[1:] for c in invocados if "venv" in c])
                # y psycopg se instala AHI, en ningun otro interprete
                pips = [c for c in invocados if "pip" in c]
                self.assertEqual(pips, [[str(py), "-m", "pip", "install", "psycopg[binary]"]],
                                 "nunca pip en un interprete que no sea el venv neutro")
                self.assertTrue(all(line.startswith("export ") for line in out.splitlines()))

    def test_dentro_de_un_venv_de_proyecto_no_instala_ahi(self):
        # correr el comando con el venv del proyecto activo no debe contaminarlo
        proyecto = self.home / "proyecto/.venv"
        py_proyecto = entorno._bin_python(proyecto)
        py_proyecto.parent.mkdir(parents=True, exist_ok=True)
        py_proyecto.touch()
        (proyecto / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
        os.environ["HARNESS_PYTHON"] = str(py_proyecto)
        invocados = []
        def comando(args, **kwargs):
            invocados.append(list(args))
            return subprocess.CompletedProcess(args, 0)
        neutro = entorno._bin_python(self.home / ".harness-flow/venv")
        with mock.patch.object(entorno, "tiene_psycopg",
                               side_effect=lambda p: Path(p) == neutro), \
             mock.patch.object(entorno.subprocess, "run", side_effect=comando):
            rc, out, err = self.cli("--instalar-deps")
        self.assertEqual(rc, 0, err)
        self.assertNotIn([str(py_proyecto), "-m", "pip", "install", "psycopg[binary]"],
                         invocados, "no se contamina el venv del proyecto del usuario")
        self.assertIn([str(neutro), "-m", "pip", "install", "psycopg[binary]"], invocados)

    def test_hermes_python_no_le_gana_al_venv_neutro(self):
        # el orden documentado es HARNESS_PYTHON -> venv neutro -> extras de Hermes
        neutro = entorno._bin_python(self.home / ".harness-flow/venv")
        neutro.parent.mkdir(parents=True, exist_ok=True)
        neutro.touch()
        otro = self.home / "otro-python"
        otro.touch()
        os.environ["HARNESS_HOST"] = "hermes"
        os.environ["HERMES_PYTHON"] = str(otro)
        with mock.patch.object(entorno, "tiene_psycopg", return_value=True):
            self.assertEqual(entorno.python_harness(), neutro,
                             "HERMES_PYTHON es un extra de host, no gana al venv neutro")

    def test_harness_python_explicito_gana_a_todo(self):
        neutro = entorno._bin_python(self.home / ".harness-flow/venv")
        neutro.parent.mkdir(parents=True, exist_ok=True)
        neutro.touch()
        elegido = self.home / "mi-python"
        elegido.touch()
        os.environ["HARNESS_PYTHON"] = str(elegido)
        with mock.patch.object(entorno, "tiene_psycopg", return_value=True):
            self.assertEqual(entorno.python_harness(), elegido)

    def test_instalacion_fallida_no_emite_exports_ni_falso_ok(self):
        os.environ["HARNESS_PYTHON"] = sys.executable
        with mock.patch.object(entorno, "tiene_psycopg", return_value=False), \
             mock.patch.object(entorno.subprocess, "run", return_value=subprocess.CompletedProcess([], 7)):
            rc, out, err = self.cli("--instalar-deps", "--shell")
        self.assertNotEqual(rc, 0)
        self.assertEqual(out, "")
        self.assertNotIn("[ok]", err)

    def test_pip_exit_cero_sin_import_no_es_instalacion_correcta(self):
        os.environ["HARNESS_PYTHON"] = sys.executable
        with mock.patch.object(entorno, "tiene_psycopg", return_value=False), \
             mock.patch.object(entorno.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)):
            rc, out, err = self.cli("--instalar-deps", "--shell")
        self.assertEqual(rc, 1)
        self.assertEqual(out, "")
        self.assertIn("psycopg", err)

    def test_override_archivo_no_ejecutable_rechazado_antes_de_exportar(self):
        falso = self.home / "python"
        falso.touch()
        os.environ["HARNESS_PYTHON"] = str(falso)
        rc, out, err = self.cli("--shell")
        self.assertEqual(rc, 1)
        self.assertEqual(out, "")
        self.assertIn("Python", err)

    def test_ruta_python_windows_y_override_venv(self):
        os.environ["HARNESS_VENV"] = str(self.home / "mi venv")
        with mock.patch.object(entorno, "ES_WINDOWS", True):
            self.assertEqual(entorno._bin_python(entorno.venv_neutro()), self.home / "mi venv/Scripts/python.exe")


if __name__ == "__main__":
    unittest.main()
