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
    """Frontmatter YAML, incluidos los escalares de bloque (`>-`, `|`, ...).

    Un `description: >-` con el texto indentado debajo es YAML perfectamente
    valido y es como se escribe una description larga sin una linea kilometrica.
    Leyendo solo `k: v` el valor quedaba en ">-" y este archivo daba por buena
    una description de dos caracteres.
    """
    m = re.match(r"^---\n(.*?)\n---\n", md.read_text(encoding="utf-8"), re.S)
    if not m:
        return {}
    campos, clave, bloque = {}, None, []

    def cerrar():
        if clave is not None:
            campos[clave] = " ".join(x.strip() for x in bloque).strip()

    for linea in m.group(1).splitlines():
        if clave is not None and (linea.startswith((" ", "\t")) or not linea.strip()):
            bloque.append(linea)
            continue
        cerrar()
        clave, bloque = None, []
        if ":" not in linea or linea.startswith((" ", "\t")):
            continue
        k, _, v = linea.partition(":")
        v = v.strip()
        if v in (">", ">-", ">+", "|", "|-", "|+"):
            clave = k.strip()          # el valor viene indentado en las lineas de abajo
        else:
            campos[k.strip()] = v.strip('"').strip("'")
    cerrar()
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


class FrontmatterTests(unittest.TestCase):
    """El parser de este archivo decide si los demas tests miden algo.

    Con `description: >-` (bloque YAML) leia ">-" como valor: el test de la
    description daba por buena una de dos caracteres.
    """

    def leer(self, texto):
        import tempfile
        f = Path(tempfile.mkdtemp()) / "SKILL.md"
        f.write_text(texto, encoding="utf-8")
        return frontmatter(f)

    def test_escalar_de_bloque(self):
        for marca in (">-", ">", "|", "|-"):
            with self.subTest(marca=marca):
                d = self.leer(f"---\nname: x\ndescription: {marca}\n  linea uno\n"
                              "  linea dos\n---\n# t\n")
                self.assertEqual(d["name"], "x")
                self.assertEqual(d["description"], "linea uno linea dos")

    def test_valor_en_la_misma_linea_con_y_sin_comillas(self):
        d = self.leer('---\nname: x\ndescription: "una sola linea"\n---\n# t\n')
        self.assertEqual(d["description"], "una sola linea")
        d = self.leer("---\nname: x\ndescription: sin comillas\n---\n# t\n")
        self.assertEqual(d["description"], "sin comillas")

    def test_el_bloque_no_se_come_la_clave_siguiente(self):
        d = self.leer("---\ndescription: >-\n  texto\nmodel: opus\n---\n# t\n")
        self.assertEqual(d["description"], "texto")
        self.assertEqual(d["model"], "opus")


class PresupuestoDeContextoTests(unittest.TestCase):
    """SKILL.md se carga ENTERO y se queda en contexto mientras dura la sesion.

    La doc de Claude Code lo dice sin rodeos: "Keep SKILL.md under 500 lines.
    Move detailed reference material to separate files". Este arnes ya aplica un
    tope de 250 lineas a las lecciones (leccion.py) y se saltaba a si mismo en
    ese chequeo, con 549 lineas.
    """

    TOPE_LINEAS = 500

    def test_skill_md_cabe_en_el_presupuesto(self):
        n = len((RAIZ / "SKILL.md").read_text(encoding="utf-8").splitlines())
        self.assertLessEqual(
            n, self.TOPE_LINEAS,
            f"SKILL.md tiene {n} lineas: muevele detalle a references/ y deja un "
            "resumen con el enlace")

    def test_la_description_sirve_para_decidir_si_activar_la_skill(self):
        """Es lo UNICO que ve Claude al decidir, y esta siempre en contexto."""
        d = frontmatter(RAIZ / "SKILL.md").get("description", "")
        self.assertTrue(d, "sin description, Claude usa la primera linea del cuerpo")
        self.assertGreater(len(d), 120,
                           "una linea suelta no alcanza para que la active sola: "
                           "di que hace y cuando usarla")
        self.assertLessEqual(len(d), 1536, "se trunca en el listado de skills")
        self.assertIn("harness/feature_list.json", d,
                      "el disparador concreto tiene que estar en la description")

    def test_todas_las_referencias_enlazadas_existen(self):
        texto = (RAIZ / "SKILL.md").read_text(encoding="utf-8")
        for rel in sorted(set(re.findall(r"references/[a-z0-9-]+\.md", texto))):
            with self.subTest(ruta=rel):
                self.assertTrue((RAIZ / rel).is_file(), f"SKILL.md enlaza {rel}, que no existe")

    def test_cada_referencia_del_repo_se_menciona_en_el_skill(self):
        """Una referencia que SKILL.md no nombra no la va a abrir nadie."""
        texto = (RAIZ / "SKILL.md").read_text(encoding="utf-8")
        for md in sorted((RAIZ / "references").glob("*.md")):
            with self.subTest(ruta=md.name):
                self.assertIn(f"references/{md.name}", texto,
                              f"{md.name} existe pero SKILL.md no dice cuando leerlo")




if __name__ == "__main__":
    unittest.main()
