"""Las lecciones escritas desde Claude Code terminan en Hermes, con un enlace de vuelta.

Una sola copia fisica (en Hermes) que Claude Code lee por el symlink: un patch
desde cualquiera de los dos hosts lo ven ambos. Nada de esto toca el HOME real.
"""
import contextlib
import io
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_leccion import Base, leccion  # noqa: E402
import test_multirepo_close as fixtures  # noqa: E402


class EspejoTests(Base):
    def setUp(self):
        super().setUp()
        self.claude = self.home / ".claude" / "skills"
        self.hermes = self.home / ".hermes" / "skills"
        self.hermes.mkdir(parents=True)
        self.md = self.skill(self.claude, "nueva", "cuerpo claude")
        # fuera de cualquier arbol .../skills: _raiz_propia() no aporta la
        # instalacion real de la maquina
        fuera = Path(self.tmp.name) / "fuera" / "scripts" / "leccion.py"
        parche = mock.patch.object(leccion, "__file__", str(fuera))
        parche.start()
        self.addCleanup(parche.stop)

    def test_mueve_a_hermes_y_deja_un_enlace_que_claude_sigue_leyendo(self):
        msg = leccion.espejar("nueva")
        destino = self.hermes / "software-development" / "nueva"
        self.assertIn("espejada", msg)
        self.assertTrue((destino / "SKILL.md").is_file())
        self.assertFalse(destino.is_symlink(), "la copia fisica vive en Hermes")
        origen = self.claude / "nueva"
        self.assertTrue(origen.is_symlink())
        self.assertEqual(origen.resolve(), destino.resolve())
        self.assertIn("cuerpo claude", self.md.read_text(encoding="utf-8"))
        # un patch por el lado de Claude llega a Hermes: no hay dos versiones
        self.md.write_text("patch desde claude\n", encoding="utf-8")
        self.assertEqual((destino / "SKILL.md").read_text(encoding="utf-8"),
                         "patch desde claude\n")

    def test_categoria_elegible(self):
        leccion.espejar("nueva", "devops")
        self.assertTrue((self.hermes / "devops" / "nueva" / "SKILL.md").is_file())

    def test_hermes_la_encuentra_como_propia(self):
        leccion.espejar("nueva")
        os.environ["HARNESS_HOST"] = "hermes"
        self.assertEqual([r.resolve() for r in leccion.skills_roots()], [self.hermes.resolve()])
        self.assertIsNotNone(leccion._buscar_en(self.hermes, "nueva"))

    def test_segunda_vez_no_hace_nada(self):
        leccion.espejar("nueva")
        self.assertIn("ya vive en Hermes", leccion.espejar("nueva"))
        self.assertIsNone(leccion.espejo_al_cerrar("nueva"))

    def test_CLAUDE_CONFIG_DIR_manda_como_origen(self):
        otro = Path(self.tmp.name) / "cfg"
        self.skill(otro / "skills", "de-cfg")
        os.environ["CLAUDE_CONFIG_DIR"] = str(otro)
        leccion.espejar("de-cfg")
        self.assertTrue((otro / "skills" / "de-cfg").is_symlink())
        self.assertTrue((self.hermes / "software-development" / "de-cfg" / "SKILL.md").is_file())

    def test_conflicto_con_una_version_de_hermes_no_mueve_nada(self):
        self.skill(self.hermes / "otra-cat", "nueva", "cuerpo hermes")
        with self.assertRaises(leccion.NoEspejable) as ctx:
            leccion.espejar("nueva")
        self.assertIn("fusiona", str(ctx.exception))
        self.assertFalse((self.claude / "nueva").is_symlink())
        self.assertIn("cuerpo claude", self.md.read_text(encoding="utf-8"))
        self.assertIn("[!]", leccion.espejo_al_cerrar("nueva"))

    def test_destino_existente_sin_skill_no_anida_la_leccion(self):
        (self.hermes / "software-development" / "nueva").mkdir(parents=True)
        with self.assertRaises(leccion.NoEspejable):
            leccion.espejar("nueva")
        self.assertFalse((self.hermes / "software-development" / "nueva" / "nueva").exists())
        self.assertFalse((self.claude / "nueva").is_symlink())

    def test_si_el_enlace_falla_la_leccion_vuelve_a_claude(self):
        with mock.patch.object(leccion.os, "symlink", side_effect=OSError("sin privilegio")):
            with self.assertRaises(leccion.NoEspejable) as ctx:
                leccion.espejar("nueva")
        self.assertIn("sigue en", str(ctx.exception))
        self.assertFalse((self.claude / "nueva").is_symlink())
        self.assertIn("cuerpo claude", self.md.read_text(encoding="utf-8"))
        self.assertFalse((self.hermes / "software-development" / "nueva").exists())

    def test_sin_hermes_instalado_no_hace_nada(self):
        self.hermes.rmdir()
        with self.assertRaises(leccion.NoEspejable):
            leccion.espejar("nueva")
        self.assertIsNone(leccion.espejo_al_cerrar("nueva"))
        self.assertFalse((self.claude / "nueva").is_symlink())

    def test_un_enlace_a_otro_agente_no_se_toca(self):
        agents = self.home / ".agents" / "skills"
        self.skill(agents, "ajena")
        (self.claude / "ajena").symlink_to(agents / "ajena", target_is_directory=True)
        with self.assertRaises(leccion.NoEspejable):
            leccion.espejar("ajena")
        self.assertIsNone(leccion.espejo_al_cerrar("ajena"))
        self.assertEqual((self.claude / "ajena").resolve(), (agents / "ajena").resolve())

    def test_nombres_invalidos(self):
        for clase in ("*", "../nueva", "a/b", ""):
            with self.subTest(clase=clase):
                with self.assertRaises(leccion.NoEspejable):
                    leccion.espejar(clase)
                self.assertIsNone(leccion.espejo_al_cerrar(clase))
        with self.assertRaises(leccion.NoEspejable):
            leccion.espejar("nueva", "../fuera")

    def test_al_cerrar_espeja_salvo_con_raiz_forzada(self):
        os.environ["HARNESS_SKILLS_DIR"] = str(self.claude)
        self.assertIsNone(leccion.espejo_al_cerrar("nueva"))
        self.assertFalse((self.claude / "nueva").is_symlink())
        del os.environ["HARNESS_SKILLS_DIR"]
        self.assertIsNone(leccion.espejo_al_cerrar("ninguna"))
        self.assertIn("espejada", leccion.espejo_al_cerrar("nueva"))
        self.assertTrue((self.claude / "nueva").is_symlink())

    def test_donde_marca_hermes_como_espejo_en_claude(self):
        os.environ["CLAUDECODE"] = "1"
        os.chdir(self.home)
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            leccion.cmd_donde(None)
        lineas = salida.getvalue().splitlines()
        self.assertEqual(Path(lineas[0]).resolve(), self.claude.resolve())
        fila = [x for x in lineas if Path(x.split("   #")[0]).resolve() == self.hermes.resolve()]
        self.assertEqual(len(fila), 1, lineas)
        self.assertIn("espejo", fila[0])


class GateEspejaAlCerrar(unittest.TestCase):
    """Cableado real: gate.py close mueve la leccion de Claude a Hermes."""

    def setUp(self):
        self.t = fixtures.MultiRepoCloseTests()
        self.t.setUp()
        self.addCleanup(self.t.doCleanups)

    def test_close_espeja_la_leccion_de_claude(self):
        t = self.t
        t.register()
        t.seal()
        claude = t.home / ".claude" / "skills" / "closure-contract"
        claude.parent.mkdir(parents=True)
        (t.home / "skills" / "closure-contract").rename(claude)
        hermes = t.home / ".hermes" / "skills"
        hermes.mkdir(parents=True)
        del t.env["HARNESS_SKILLS_DIR"]
        t.env["CLAUDECODE"] = "1"
        r = t.close()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("closure-contract espejada", r.stdout)
        self.assertTrue(claude.is_symlink())
        self.assertTrue((hermes / "software-development" / "closure-contract" / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
