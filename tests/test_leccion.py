"""Lecciones neutrales: viven en las skills del host (Hermes o Claude Code)."""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import leccion  # noqa: E402


VARS = ("HARNESS_SKILLS_DIR", "HARNESS_HOST", "HERMES_SKILLS_DIR", "HERMES_HOME",
        "CLAUDECODE", "CLAUDE_CONFIG_DIR", "HOME", "USERPROFILE")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()
        self.previo = {k: os.environ.get(k) for k in VARS}
        for k in VARS:
            os.environ.pop(k, None)
        os.environ["HOME"] = str(self.home)
        os.environ["USERPROFILE"] = str(self.home)
        self.addCleanup(self.restaurar)
        self.cwd = os.getcwd()
        self.addCleanup(lambda: os.chdir(self.cwd))

    def restaurar(self):
        for k, v in self.previo.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def skill(self, raiz: Path, nombre: str, cuerpo: str = "x") -> Path:
        d = raiz / nombre
        d.mkdir(parents=True, exist_ok=True)
        md = d / "SKILL.md"
        md.write_text("---\nname: %s\ndescription: \"d\"\n---\n%s\n" % (nombre, cuerpo),
                      encoding="utf-8")
        return md


class RaicesTests(Base):
    def test_gpt_codex_usa_agents_skills_personal_y_repo(self):
        personal = self.home / ".agents" / "skills"
        repo = Path(self.tmp.name) / "repo"
        repo_skills = repo / ".agents" / "skills"
        self.skill(personal, "tdd", "personal-gpt")
        self.skill(repo_skills, "repo-only", "repo-gpt")
        os.environ["HARNESS_HOST"] = "gpt"
        os.chdir(repo)
        raices = leccion.skills_roots()
        self.assertEqual(raices[0], repo_skills.resolve())
        self.assertIn(personal.resolve(), raices)
        self.assertIn("repo-gpt", leccion.buscar("repo-only").read_text(encoding="utf-8"))
        self.assertIn("personal-gpt", leccion.buscar("tdd").read_text(encoding="utf-8"))

    def test_gpt_no_escanea_agents_por_arriba_del_repo_root(self):
        import subprocess
        fuera = Path(self.tmp.name) / ".agents" / "skills"
        repo = Path(self.tmp.name) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        repo_skills = repo / ".agents" / "skills"
        self.skill(fuera, "fuera-del-repo")
        self.skill(repo_skills, "dentro-del-repo")
        os.environ["HARNESS_HOST"] = "gpt"
        os.chdir(repo)

        raices = leccion.skills_roots()

        self.assertIn(repo_skills.resolve(), raices)
        self.assertNotIn(fuera.resolve(), raices)
        self.assertIsNone(leccion.buscar("fuera-del-repo"))

    def test_gpt_por_symlink_agents_no_cola_skills_de_hermes(self):
        hermes = self.home / ".hermes" / "skills"
        agents = self.home / ".agents" / "skills"
        self.skill(hermes / "cat", "solo-hermes")
        self.skill(agents, "solo-gpt")
        target = hermes / "software-development" / "harness-flow"
        (target / "scripts").mkdir(parents=True, exist_ok=True)
        link = agents / "harness-flow"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target, target_is_directory=True)
        with mock.patch.object(leccion, "__file__", str(link / "scripts" / "leccion.py")):
            self.assertIsNotNone(leccion.buscar("solo-gpt"))
            self.assertIsNone(leccion.buscar("solo-hermes"))

    def test_claude_prioriza_personal_sobre_proyecto(self):
        # docs de Claude Code: las skills personales ganan a las del proyecto
        personal = self.home / ".claude" / "skills"
        proyecto = Path(self.tmp.name) / "repo" / ".claude" / "skills"
        self.skill(personal, "tdd", "personal")
        self.skill(proyecto, "tdd", "proyecto")
        os.environ["CLAUDECODE"] = "1"
        os.chdir(Path(self.tmp.name) / "repo")
        raices = leccion.skills_roots()
        self.assertEqual(raices[0], personal.resolve())
        self.assertIn(proyecto.resolve(), raices)
        self.assertIn("personal", leccion.buscar("tdd").read_text(encoding="utf-8"))

    def test_override_es_exclusivo_y_no_mezcla_otras_raices(self):
        solo = Path(self.tmp.name) / "solo"
        self.skill(solo, "tdd")
        self.skill(self.home / ".claude" / "skills", "otra")
        os.environ["CLAUDECODE"] = "1"
        os.environ["HARNESS_SKILLS_DIR"] = str(solo)
        self.assertEqual(leccion.skills_roots(), [solo.resolve()])
        self.assertIsNone(leccion.buscar("otra"))

    def test_hermes_no_busca_en_skills_de_claude(self):
        hermes = self.home / ".hermes" / "skills"
        self.skill(hermes, "tdd")
        self.skill(self.home / ".claude" / "skills", "solo-claude")
        os.environ["HERMES_HOME"] = str(self.home / ".hermes")
        os.environ["HARNESS_HOST"] = "hermes"
        # la copia bajo prueba vive en el home simulado: si no, _raiz_propia()
        # aportaria la instalacion real de la maquina y el test leeria el entorno
        instalada = hermes / "cat" / "harness-flow" / "scripts" / "leccion.py"
        instalada.parent.mkdir(parents=True, exist_ok=True)
        instalada.touch()
        with mock.patch.object(leccion, "__file__", str(instalada)):
            self.assertEqual(leccion.skills_roots(), [hermes.resolve()])
            self.assertIsNone(leccion.buscar("solo-claude"))

    def test_sin_host_conocido_cae_a_la_raiz_que_contiene_esta_skill(self):
        # la skill puede estar instalada en cualquier arbol .../skills/<cat>/harness-flow
        raiz = Path(self.tmp.name) / "cualquier-sitio" / "skills"
        self.skill(raiz / "cat", "una-leccion")
        instalada = raiz / "cat" / "harness-flow" / "scripts" / "leccion.py"
        instalada.parent.mkdir(parents=True, exist_ok=True)
        instalada.write_bytes(Path(leccion.__file__).read_bytes())
        os.environ["HARNESS_HOST"] = "generic"
        with mock.patch.object(leccion, "__file__", str(instalada)):
            self.assertEqual(leccion.skills_roots()[0], raiz.resolve(),
                             "en generic manda la raiz que contiene a esta skill")

    def test_sin_ninguna_raiz_falla_con_mensaje_accionable_y_no_crea_nada(self):
        os.environ["HARNESS_SKILLS_DIR"] = str(self.home / "no-existe")
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as ctx:
            leccion.skills_roots()
        self.assertNotEqual(ctx.exception.code, 0)
        self.assertIn("HARNESS_SKILLS_DIR", str(ctx.exception) + err.getvalue())
        self.assertFalse((self.home / "no-existe").exists())


class BusquedaTests(Base):
    def test_list_deduplica_por_precedencia_y_marca_el_origen(self):
        personal = self.home / ".claude" / "skills"
        proyecto = Path(self.tmp.name) / "repo" / ".claude" / "skills"
        self.skill(personal, "tdd", "personal")
        self.skill(proyecto, "tdd", "proyecto")
        self.skill(proyecto, "solo-proyecto")
        os.environ["CLAUDECODE"] = "1"
        os.chdir(Path(self.tmp.name) / "repo")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            leccion.cmd_list(None)
        texto = out.getvalue()
        self.assertEqual(texto.count(" tdd "), 1, "una sola fila para la skill sombreada")
        self.assertIn("solo-proyecto", texto)

    def test_existe_usado_por_el_gate_encuentra_en_cualquier_raiz(self):
        proyecto = Path(self.tmp.name) / "repo" / ".claude" / "skills"
        self.skill(proyecto, "gates-que-no-mienten")
        os.environ["CLAUDECODE"] = "1"
        os.chdir(Path(self.tmp.name) / "repo")
        self.assertIsNotNone(leccion.buscar("gates-que-no-mienten"))

    def test_buscar_no_confunde_prefijos_ni_sale_de_la_raiz(self):
        personal = self.home / ".claude" / "skills"
        self.skill(personal, "tdd-extra")
        os.environ["CLAUDECODE"] = "1"
        self.assertIsNone(leccion.buscar("tdd"))
        self.assertIsNone(leccion.buscar("../../etc"))

    def test_comodines_glob_no_resuelven_una_skill_cualquiera(self):
        # gate.py close --leccion '*' no debe pasar por parecerse a cualquier skill
        personal = self.home / ".claude" / "skills"
        self.skill(personal, "cualquiera")
        os.environ["CLAUDECODE"] = "1"
        for comodin in ("*", "[a-z]*", "**", "?", "cual*"):
            self.assertIsNone(leccion.buscar(comodin),
                              "'%s' no es el nombre de ninguna skill" % comodin)


class PerfilesHermesTests(Base):
    def _instalar(self, raiz_skills: Path) -> Path:
        """Copia leccion.py dentro de una raiz de skills y devuelve el script."""
        destino = raiz_skills / "cat" / "harness-flow" / "scripts"
        destino.mkdir(parents=True, exist_ok=True)
        script = destino / "leccion.py"
        script.write_bytes(Path(leccion.__file__).read_bytes())
        return script

    def test_la_skill_de_un_perfil_resuelve_las_skills_de_SU_perfil(self):
        # regresion: antes del port mandaba la raiz que contiene a la propia skill
        default = self.home / ".hermes" / "skills"
        perfil = self.home / ".hermes" / "profiles" / "trabajo" / "skills"
        self.skill(default / "cat", "tdd", "SOY-DEL-DEFAULT")
        self.skill(perfil / "cat", "tdd", "SOY-DEL-PERFIL")
        self._instalar(perfil)
        os.environ["HARNESS_HOST"] = "hermes"
        with mock.patch.object(leccion, "__file__",
                               str(perfil / "cat" / "harness-flow" / "scripts" / "leccion.py")):
            self.assertEqual(leccion.skills_roots()[0], perfil.resolve())
            texto = leccion.buscar("tdd").read_text(encoding="utf-8")
        self.assertIn("SOY-DEL-PERFIL", texto)


if __name__ == "__main__":
    unittest.main()
