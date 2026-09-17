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

    def test_leccion_de_agents_vale_desde_los_tres_hosts(self):
        self.crear(".agents", "solo-en-agents")
        for host in ("hermes", "claude", "gpt"):
            with self.subTest(host=host):
                r = self.existe("solo-en-agents", host)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_inexistente_sigue_bloqueando_en_todos_los_hosts(self):
        for host in ("hermes", "claude", "gpt"):
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


if __name__ == "__main__":
    unittest.main()
