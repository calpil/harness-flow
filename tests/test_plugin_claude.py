"""Regresiones de la capa nativa de Claude Code (plugin skills-dir).

El modo de fallo que cubren: `.claude-plugin/plugin.json` apunta a rutas que ya
no existen (renombraste un comando, moviste el agente) y Claude Code carga
silenciosamente nada. No hay exit!=0 que avise: el plugin sigue "loaded" y los
comandos simplemente no aparecen.
"""
import json
from pathlib import Path
import re
import unittest

RAIZ = Path(__file__).resolve().parents[1]
MANIFIESTO = RAIZ / ".claude-plugin" / "plugin.json"


def frontmatter(md: Path) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", md.read_text(encoding="utf-8"), re.S)
    if not m:
        return {}
    campos = {}
    for linea in m.group(1).splitlines():
        if linea.startswith((" ", "\t")) or ":" not in linea:
            continue
        k, _, v = linea.partition(":")
        campos[k.strip()] = v.strip()
    return campos


class ManifiestoTests(unittest.TestCase):
    def setUp(self):
        self.datos = json.loads(MANIFIESTO.read_text(encoding="utf-8"))

    def test_nombre_coincide_con_la_skill(self):
        """El namespace de comandos y agente sale de aqui: /harness-flow:estado."""
        skill = frontmatter(RAIZ / "SKILL.md")
        self.assertEqual(self.datos["name"], skill.get("name"))

    def test_la_raiz_se_declara_como_skill(self):
        self.assertIn("./", self.datos.get("skills", []))

    def test_cada_ruta_declarada_existe(self):
        for clave in ("commands", "agents", "skills"):
            for rel in self.datos.get(clave, []):
                with self.subTest(clave=clave, ruta=rel):
                    self.assertTrue((RAIZ / rel).exists(), f"{clave}: falta {rel}")

    def test_no_hay_comandos_ni_agentes_sin_declarar(self):
        """Un .md suelto en commands/ no lo carga Claude Code si no esta listado."""
        declarados = {
            (RAIZ / r).resolve()
            for clave in ("commands", "agents")
            for r in self.datos.get(clave, [])
        }
        en_disco = set((RAIZ / "commands").glob("*.md")) | set((RAIZ / "agents").glob("*.md"))
        huerfanos = sorted(p.name for p in en_disco if p.resolve() not in declarados)
        self.assertEqual([], huerfanos, f"sin declarar en plugin.json: {huerfanos}")


class ComponentesTests(unittest.TestCase):
    def test_cada_comando_tiene_description(self):
        """Sin description, Claude Code no sabe cuando ofrecer el comando."""
        for md in sorted((RAIZ / "commands").glob("*.md")):
            with self.subTest(comando=md.name):
                self.assertTrue(frontmatter(md).get("description"), f"{md.name} sin description")

    def test_el_agente_declara_name_y_description(self):
        fm = frontmatter(RAIZ / "agents" / "revisor.md")
        self.assertEqual("revisor", fm.get("name"))
        self.assertTrue(fm.get("description"))

    def test_el_agente_no_puede_editar_codigo(self):
        """Solo lee y escribe su acta; arreglar lo que revisa lo invalida como revisor."""
        tools = [t.strip() for t in frontmatter(RAIZ / "agents" / "revisor.md").get("tools", "").split(",")]
        self.assertIn("Read", tools)
        self.assertNotIn("Edit", tools)

    def test_el_comando_de_review_apunta_al_agente_real(self):
        """Si el agente se renombra, este comando delega a un subagent_type inexistente."""
        texto = (RAIZ / "commands" / "review.md").read_text(encoding="utf-8")
        datos = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
        fm = frontmatter(RAIZ / "agents" / "revisor.md")
        self.assertIn(f"{datos['name']}:{fm['name']}", texto)

    def test_ningun_comando_hardcodea_la_ruta_de_la_skill(self):
        """La ruta cambia por host, SO y perfil: va por ${CLAUDE_PLUGIN_ROOT}."""
        for md in sorted((RAIZ / "commands").glob("*.md")):
            texto = md.read_text(encoding="utf-8")
            with self.subTest(comando=md.name):
                self.assertNotIn("/.claude/skills/harness-flow", texto)
                self.assertNotIn("/.hermes/skills/", texto)

    def test_cada_comando_documenta_el_fallback_de_powershell(self):
        """En Windows sin Git for Windows, la tool Bash de Claude Code ES PowerShell.

        Ahi `eval "$(...)"` no existe y el interprete se llama `python`, no
        `python3`: un comando que solo trae la forma bash no corre. La primera
        version de estos comandos solo traia esa forma.
        """
        for md in sorted((RAIZ / "commands").glob("*.md")):
            texto = md.read_text(encoding="utf-8")
            with self.subTest(comando=md.name):
                self.assertIn("--powershell", texto)
                self.assertIn("Invoke-Expression", texto)

    def test_cada_llamada_a_un_script_trae_su_eval(self):
        """En Claude Code $PY y $H no sobreviven entre llamadas Bash."""
        for md in sorted((RAIZ / "commands").glob("*.md")):
            for linea in md.read_text(encoding="utf-8").splitlines():
                if '"$PY" "$H/' not in linea:
                    continue
                with self.subTest(comando=md.name, linea=linea.strip()[:60]):
                    self.assertIn("entorno.py", linea, "falta el eval de entorno en la misma llamada")


if __name__ == "__main__":
    unittest.main()
