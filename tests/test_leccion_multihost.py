"""Una leccion vale para el usuario, no para el host que la tipeo.

Si cerras features desde Hermes Y desde Claude Code (skills enlazadas en
~/.claude/skills -> ~/.agents/skills), el gate de leccion buscaba SOLO en las
raices del host detectado: una leccion escrita desde Claude Code no satisfacia
el cierre desde Hermes y viceversa, bloqueando un cierre legitimo por el mero
hecho de donde se habia escrito.

Buscar mira todos los hosts; CREAR sigue respetando la precedencia del host,
para que una skill nueva no se cuele en un host ajeno.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import leccion  # noqa: E402


SKILL = ('---\nname: %s\ndescription: "Use when x. Prueba."\n---\n# t\n')


class MultiHostTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.casa = Path(tmp.name)
        (self.casa / ".claude" / "skills").mkdir(parents=True)
        (self.casa / ".hermes" / "skills").mkdir(parents=True)
        (self.casa / ".agents" / "skills").mkdir(parents=True)
        (self.casa / ".gemini" / "config" / "skills").mkdir(parents=True)
        # Grok y Codex dejan marcas de sesion en el entorno. Estos tests fijan
        # el host por HARNESS_HOST o por la ruta; la marca no puede pisarlos.
        self._marcas = {k: os.environ.pop(k, None) for k in
                        ("GROK_AGENT", "GROK_SESSION_ID", "CODEX_THREAD_ID", "CODEX_SESSION_ID")}
        self.addCleanup(self._restaurar_marcas)

    def _restaurar_marcas(self):
        for k, v in self._marcas.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def crear(self, raiz, nombre):
        d = self.casa / raiz / "skills" / nombre
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(SKILL % nombre, encoding="utf-8")

    def existe(self, nombre, host):
        env = dict(os.environ, HOME=str(self.casa))
        env.pop("HARNESS_SKILLS_DIR", None)
        env.pop("HERMES_SKILLS_DIR", None)
        env.pop("HERMES_HOME", None)
        env.pop("CLAUDE_CONFIG_DIR", None)
        env.pop("CLAUDECODE", None)
        env.pop("CODEX_HOME", None)
        env.pop("KIMI_CODE_HOME", None)
        env.pop("ANTIGRAVITY_AGENT", None)
        env.pop("GROK_AGENT", None)
        env.pop("GROK_SESSION_ID", None)
        env["HARNESS_HOST"] = host
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "leccion.py"), "existe", nombre],
            capture_output=True, text=True, env=env, cwd=str(self.casa))

    def test_leccion_de_claude_vale_cerrando_desde_hermes(self):
        self.crear(".claude", "solo-en-claude")
        r = self.existe("solo-en-claude", "hermes")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_leccion_de_hermes_vale_cerrando_desde_claude(self):
        self.crear(".hermes", "solo-en-hermes")
        r = self.existe("solo-en-hermes", "claude")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_leccion_de_agents_vale_desde_los_hosts(self):
        self.crear(".agents", "solo-en-agents")
        for host in ("hermes", "claude", "gpt", "gemini", "grok"):
            with self.subTest(host=host):
                r = self.existe("solo-en-agents", host)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_leccion_de_gemini_vale_desde_otros_hosts(self):
        d = self.casa / ".gemini" / "config" / "skills" / "solo-en-gemini"
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(SKILL % "solo-en-gemini", encoding="utf-8")
        for host in ("hermes", "claude", "gpt", "gemini", "grok"):
            with self.subTest(host=host):
                r = self.existe("solo-en-gemini", host)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_inexistente_sigue_bloqueando_en_todos_los_hosts(self):
        for host in ("hermes", "claude", "gpt", "gemini", "grok"):
            with self.subTest(host=host):
                r = self.existe("no-existe-xyz", host)
                self.assertNotEqual(r.returncode, 0,
                                    "el gate dejo de morder: " + r.stdout)

    def test_crear_sigue_usando_la_raiz_del_host(self):
        """El fallback multi-host es solo para BUSCAR."""
        propias = leccion.skills_roots()
        todas = leccion.skills_roots(todos_los_hosts=True)
        self.assertEqual(todas[:len(propias)], propias,
                         "la precedencia del host propio debe mandar")
        self.assertGreaterEqual(len(todas), len(propias))

    def test_leccion_escrita_donde_la_instala_cada_CLI_vale_igual(self):
        """Codex, Grok y Kimi Code no guardan las skills en .agents/skills.

        Codex instala en $CODEX_HOME/skills (~/.codex/skills), Grok en
        ~/.grok/skills y Kimi Code en $KIMI_CODE_HOME/skills
        (~/.kimi-code/skills). Escribir la leccion donde tu CLI la lee dejaba
        a `gate.py close --leccion` sin encontrarla: un cierre legitimo
        bloqueado por el mero hecho de donde la tipeaste. Es el mismo bug que
        este archivo mato entre Hermes/Claude/GPT, con las raices nuevas.
        """
        for raiz, nombre in ((".codex", "leccion-de-codex"),
                             (".grok", "leccion-de-grok"),
                             (".kimi-code", "leccion-de-kimi")):
            self.crear(raiz, nombre)
            for host in ("hermes", "claude", "gpt", "generic", "grok"):
                with self.subTest(raiz=raiz, host=host):
                    r = self.existe(nombre, host)
                    self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_CODEX_HOME_y_KIMI_CODE_HOME_mandan_sobre_el_default(self):
        import os as _os
        import subprocess as _sp
        aparte = self.casa / "otro-codex"
        (aparte / "skills" / "leccion-movida").mkdir(parents=True)
        (aparte / "skills" / "leccion-movida" / "SKILL.md").write_text(
            SKILL % "leccion-movida", encoding="utf-8")
        env = dict(_os.environ, HOME=str(self.casa), CODEX_HOME=str(aparte))
        for k in ("HARNESS_SKILLS_DIR", "HERMES_SKILLS_DIR", "HERMES_HOME",
                  "CLAUDE_CONFIG_DIR", "CLAUDECODE", "KIMI_CODE_HOME",
                  "GROK_AGENT", "GROK_SESSION_ID"):
            env.pop(k, None)
        env["HARNESS_HOST"] = "gpt"
        r = _sp.run([sys.executable, str(SCRIPTS / "leccion.py"), "existe", "leccion-movida"],
                    capture_output=True, text=True, env=env, cwd=str(self.casa))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_el_recorrido_por_padres_se_corta_en_la_raiz_del_repo(self):
        """Una skill de un proyecto vecino no puede satisfacer el gate de otro.

        Las raices nuevas (.codex/.grok/.kimi-code por directorio) se recorren
        hacia arriba desde el cwd; sin cortar en la raiz del repo, subir hasta /
        haria que la leccion de un proyecto ajeno diera por cumplido el cierre
        de este. _raices_gpt ya cortaba asi.
        """
        import os as _os
        import subprocess as _sp
        vecino = self.casa / "vecino"           # padre del repo, no es el home
        self.escribir(vecino / ".codex" / "skills" / "leccion-vecina")
        repo = vecino / "repo"
        repo.mkdir(parents=True)
        _sp.run(["git", "init", "-q", "."], cwd=repo, capture_output=True)
        self.escribir(repo / ".codex" / "skills" / "leccion-del-repo")
        hondo = repo / "a" / "b"
        hondo.mkdir(parents=True)

        env = dict(_os.environ, HOME=str(self.casa), HARNESS_HOST="gpt")
        for k in ("HARNESS_SKILLS_DIR", "HERMES_SKILLS_DIR", "HERMES_HOME",
                  "CLAUDE_CONFIG_DIR", "CLAUDECODE", "CODEX_HOME", "KIMI_CODE_HOME",
                  "GROK_AGENT", "GROK_SESSION_ID"):
            env.pop(k, None)

        def existe_desde(nombre):
            return _sp.run([sys.executable, str(SCRIPTS / "leccion.py"), "existe", nombre],
                           capture_output=True, text=True, env=env, cwd=str(hondo)).returncode

        self.assertEqual(existe_desde("leccion-del-repo"), 0, "la del propio repo debe valer")
        self.assertNotEqual(existe_desde("leccion-vecina"), 0,
                            "una skill de un proyecto vecino no cierra esta feature")

    def escribir(self, directorio):
        directorio.mkdir(parents=True, exist_ok=True)
        (directorio / "SKILL.md").write_text(SKILL % directorio.name, encoding="utf-8")

    def test_plugin_kimi_managed_crea_en_la_raiz_kimi(self):
        """La copia managed del plugin no cuelga de una raiz 'skills'.

        Kimi copia el plugin a ~/.kimi-code/plugins/managed/harness-flow/ y corre
        desde ahi. Sin host kimi la deteccion caia a generic, _raiz_propia() no
        encontraba padre 'skills' y 'donde' mandaba crear la leccion en
        ~/.hermes/skills: una raiz que Kimi Code no escanea.
        """
        kimi = self.casa / ".kimi-code" / "skills"
        kimi.mkdir(parents=True)
        managed = self.casa / ".kimi-code" / "plugins" / "managed"
        managed.mkdir(parents=True)
        os.symlink(ROOT, managed / "harness-flow")
        env = dict(os.environ, HOME=str(self.casa))
        for k in ("HARNESS_SKILLS_DIR", "HARNESS_HOST", "HERMES_SKILLS_DIR",
                  "HERMES_HOME", "HERMES_PYTHON", "CLAUDE_CONFIG_DIR", "CLAUDECODE",
                  "CODEX_HOME", "KIMI_CODE_HOME", "ANTIGRAVITY_AGENT", "GEMINI_CLI",
                  "GROK_AGENT", "GROK_SESSION_ID"):
            env.pop(k, None)
        r = subprocess.run(
            [sys.executable, str(managed / "harness-flow" / "scripts" / "leccion.py"), "donde"],
            capture_output=True, text=True, env=env, cwd=str(self.casa))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        primera = r.stdout.splitlines()[0]
        self.assertEqual(Path(primera).resolve(), kimi.resolve(),
                         "la raiz de creacion debe ser la que Kimi escanea: " + r.stdout)

    def test_leccion_de_kimi_vale_desde_todos_los_hosts(self):
        """Una leccion creada en ~/.kimi-code/skills cierra desde cualquier host."""
        self.crear(".kimi-code", "solo-en-kimi")
        for host in ("hermes", "claude", "gpt", "gemini", "grok", "kimi"):
            with self.subTest(host=host):
                r = self.existe("solo-en-kimi", host)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_instalacion_kimi_por_symlink_crea_en_la_raiz_kimi(self):
        """Skill instalada en ~/.kimi-code/skills via symlink a otro clone.

        _raiz_propia() resolvia el symlink y la deduplicacion devolvia la ruta
        fisica: `leccion.py donde` mandaba crear la leccion en el clone de
        Hermes, una raiz que Kimi Code no escanea — la leccion nacia invisible
        para el host que la iba a usar. Crear vale por la ruta declarada
        (alias, la que el host escanea); deduplicar, por la ruta fisica.
        """
        kimi = self.casa / ".kimi-code" / "skills"
        kimi.mkdir(parents=True)
        os.symlink(ROOT, kimi / "harness-flow")
        env = dict(os.environ, HOME=str(self.casa))
        for k in ("HARNESS_SKILLS_DIR", "HARNESS_HOST", "HERMES_SKILLS_DIR",
                  "HERMES_HOME", "HERMES_PYTHON", "CLAUDE_CONFIG_DIR", "CLAUDECODE",
                  "CODEX_HOME", "KIMI_CODE_HOME", "ANTIGRAVITY_AGENT", "GEMINI_CLI",
                  "GROK_AGENT", "GROK_SESSION_ID"):
            env.pop(k, None)
        r = subprocess.run(
            [sys.executable, str(kimi / "harness-flow" / "scripts" / "leccion.py"), "donde"],
            capture_output=True, text=True, env=env, cwd=str(self.casa))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        primera = r.stdout.splitlines()[0]
        self.assertEqual(Path(primera).resolve(), kimi.resolve(),
                         "la raiz de creacion debe ser la que Kimi escanea: " + r.stdout)

    def test_grok_agent_crea_en_grok_aunque_el_script_viva_en_hermes(self):
        """El clone esta en ~/.hermes. Sin la marca, 'donde' mandaria crear ahi."""
        grok = self.casa / ".grok" / "skills"
        grok.mkdir(parents=True)
        env = dict(os.environ, HOME=str(self.casa), GROK_AGENT="1")
        for k in ("HARNESS_SKILLS_DIR", "HARNESS_HOST", "HERMES_SKILLS_DIR",
                  "HERMES_HOME", "HERMES_PYTHON", "CLAUDE_CONFIG_DIR", "CLAUDECODE"):
            env.pop(k, None)
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "leccion.py"), "donde"],
            capture_output=True, text=True, env=env, cwd=str(self.casa))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(Path(r.stdout.splitlines()[0]).resolve(), grok.resolve(),
                         r.stdout)

    def test_las_raices_ajenas_no_sirven_para_crear(self):
        """Solo para buscar: una skill nueva no nace en el CLI de otro.

        Excepcion: si la propia harness-flow esta instalada ahi (p.ej. Kimi
        Code en ~/.kimi-code/skills), ESA es la raiz del host que la corre.
        """
        propias = leccion.skills_roots()
        propia = {p.resolve() for p in leccion._raiz_propia()}
        for raiz in propias:
            if raiz.resolve() in propia:
                continue
            self.assertFalse(
                any(parte in raiz.parts for parte in (".codex", ".grok", ".kimi-code")),
                f"la raiz de creacion {raiz} es de otro agente")


if __name__ == "__main__":
    unittest.main()
