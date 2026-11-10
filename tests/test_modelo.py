"""Fable 5.2 u Opus 5.5 en los roles Producto y Leader: lo elige el usuario.

Antes los cinco comandos fijaban `claude-opus-5-5` en su frontmatter: aunque la
sesion estuviera en Fable 5.2, invocar /harness-flow:spec pasaba el turno a
Opus sin preguntar. El `model` de un comando es fijo y ningun comando puede
cambiar el modelo de la sesion, asi que la eleccion se guarda en el backlog
(`modelo.py`) y, si la sesion no coincide, el rol se detiene y pide `/model`.

Decisiones del usuario que estos tests fijan: se pregunta una vez por feature
(por documento en el rol producto), solo eligen Producto y Leader, Fable corre
en `high` y Opus en `xhigh`.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"


def frontmatter(md: Path) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", md.read_text(encoding="utf-8"), re.S)
    return dict(l.split(":", 1) for l in m.group(1).splitlines() if ":" in l) if m else {}


class ScriptTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        (self.root / "harness").mkdir()
        (self.root / "harness" / "feature_list.json").write_text(json.dumps({
            "project": "demo", "rules": {},
            "features": [{"id": 7, "name": "cobro", "status": "todo"},
                         {"id": 8, "name": "reporte", "status": "todo"}]}))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def modelo(self, *args, effort="high"):
        env = dict(os.environ, HARNESS_SIN_CONTEXTO="1")
        env.pop("CLAUDE_EFFORT", None)
        if effort:
            env["CLAUDE_EFFORT"] = effort
        return subprocess.run([sys.executable, str(SCRIPTS / "modelo.py"), *args],
                              cwd=str(self.root), capture_output=True, text=True, env=env)

    def backlog(self) -> dict:
        return json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))

    def test_sin_eleccion_sale_distinto_de_cero_y_manda_a_preguntar(self):
        r = self.modelo("ver", "--feature", "7")
        self.assertEqual(3, r.returncode, r.stdout + r.stderr)
        self.assertIn("sin elegir", r.stdout)
        self.assertIn("formulario", r.stdout)

    def test_elegir_guarda_la_eleccion_en_la_feature(self):
        r = self.modelo("elegir", "--feature", "7", "--modelo", "fable")
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        feats = {f["id"]: f for f in self.backlog()["features"]}
        self.assertEqual("fable", feats[7]["modelo_claude"])
        self.assertNotIn("modelo_claude", feats[8], "la eleccion es por feature")

    def test_ya_elegido_no_vuelve_a_mandar_a_preguntar(self):
        self.modelo("elegir", "--feature", "7", "--modelo", "opus")
        r = self.modelo("ver", "--feature", "7", effort="xhigh")
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("claude-opus-5-5", r.stdout)
        self.assertNotIn("PREGUNTA", r.stdout)

    def test_fable_corre_en_high_y_opus_en_xhigh(self):
        fable = self.modelo("elegir", "--feature", "7", "--modelo", "fable").stdout
        self.assertIn("claude-fable-5-2", fable)
        self.assertIn("esfuerzo: high", fable)
        opus = self.modelo("elegir", "--feature", "8", "--modelo", "opus").stdout
        self.assertIn("esfuerzo: xhigh", opus)

    def test_dice_si_el_esfuerzo_de_la_sesion_coincide(self):
        self.assertIn("(coincide)", self.modelo("elegir", "--feature", "7", "--modelo", "fable").stdout)
        mal = self.modelo("elegir", "--feature", "7", "--modelo", "opus").stdout   # sesion en high
        self.assertIn("NO coincide con xhigh", mal)

    def test_xhigh_con_fable_no_es_un_error_pero_se_avisa(self):
        salida = self.modelo("elegir", "--feature", "7", "--modelo", "fable", effort="xhigh").stdout
        self.assertNotIn("NO coincide", salida)
        self.assertIn("riesgo concreto", salida)

    def test_sin_dato_del_esfuerzo_no_afirma_que_coincide(self):
        """Un gate que no puede medir no devuelve verdadero."""
        salida = self.modelo("elegir", "--feature", "7", "--modelo", "fable", effort=None).stdout
        self.assertNotIn("(coincide)", salida)
        self.assertIn("no se pudo leer", salida)

    def test_manda_a_aplicar_la_eleccion_y_no_a_pedirsela_al_usuario(self):
        """Si elige Opus, Opus va en xhigh: no hay nada mas que preguntarle."""
        for alias in ("fable", "opus"):
            salida = self.modelo("elegir", "--feature", "7", "--modelo", alias).stdout
            with self.subTest(modelo=alias):
                self.assertIn(f"/harness-flow:usar-{alias}", salida)
                self.assertIn("no le pidas /model ni /effort", salida)
                self.assertNotIn("DETENTE", salida)

    def test_el_rol_producto_elige_por_documento(self):
        self.assertEqual(3, self.modelo("ver", "--doc", "prd").returncode)
        self.modelo("elegir", "--doc", "prd", "--modelo", "fable")
        self.assertEqual({"prd": "fable"}, self.backlog()["modelos_claude"])
        self.assertEqual(3, self.modelo("ver", "--doc", "sdd").returncode, "prd y sdd se eligen aparte")

    def test_cambiar_la_eleccion_queda_en_la_bitacora(self):
        self.modelo("elegir", "--feature", "7", "--modelo", "opus")
        self.modelo("elegir", "--feature", "7", "--modelo", "fable")
        historia = (self.root / "harness" / "progress" / "history.md").read_text(encoding="utf-8")
        self.assertIn("modelo claude de feature #7: fable (antes opus)", historia)

    def test_solo_admite_fable_u_opus(self):
        r = self.modelo("elegir", "--feature", "7", "--modelo", "sonnet")
        self.assertNotEqual(0, r.returncode)
        self.assertNotIn("modelo_claude", self.backlog()["features"][0])

    def test_exige_feature_o_documento_y_no_los_dos(self):
        self.assertNotEqual(0, self.modelo("ver").returncode)
        self.assertNotEqual(0, self.modelo("ver", "--feature", "7", "--doc", "prd").returncode)


class ComandosTests(unittest.TestCase):
    ELIGEN = ("producto.md", "spec.md")

    def test_producto_y_spec_no_fijan_modelo_ni_esfuerzo(self):
        """`inherit`: el turno corre en el modelo de la sesion, no pasa a Opus por su cuenta."""
        for nombre in self.ELIGEN:
            fm = frontmatter(RAIZ / "commands" / nombre)
            with self.subTest(comando=nombre):
                self.assertEqual("inherit", fm.get("model", "").strip())
                self.assertNotIn("effort", fm)

    def test_producto_y_spec_preguntan_en_formulario_y_guardan_la_eleccion(self):
        for nombre, clave in zip(self.ELIGEN, ("--doc", "--feature")):
            texto = (RAIZ / "commands" / nombre).read_text(encoding="utf-8")
            with self.subTest(comando=nombre):
                self.assertIn("AskUserQuestion", texto)
                self.assertIn(f'modelo.py" ver {clave} $ARGUMENTS[0]', texto)
                self.assertIn(f'modelo.py" elegir {clave} $ARGUMENTS[0] --modelo fable|opus', texto)
                self.assertLess(texto.index("## 0. Modelo del rol"), texto.index("## 1. "),
                                "se elige antes de empezar el rol")

    def test_si_la_sesion_no_coincide_el_rol_aplica_la_eleccion_solo(self):
        """Elegir Opus no puede terminar en "escribe /model opus y /effort xhigh"."""
        for nombre in self.ELIGEN:
            texto = (RAIZ / "commands" / nombre).read_text(encoding="utf-8")
            with self.subTest(comando=nombre):
                self.assertIn("harness-flow:usar-opus", texto)
                self.assertIn("harness-flow:usar-fable", texto)
                self.assertIn("NO le pidas `/model` ni `/effort`", texto)
                aplica, detiene = texto.index("aplica la eleccion tu mismo"), texto.index("DETENTE")
                self.assertLess(aplica, detiene, "detenerse es solo si no se pudo aplicar")

    def test_los_comandos_que_fijan_modelo_traen_el_modelo_y_el_esfuerzo_de_la_eleccion(self):
        esperado = {"usar-opus.md": ("claude-opus-5-5", "xhigh"), "usar-fable.md": ("claude-fable-5-2", "high")}
        for nombre, (modelo, effort) in esperado.items():
            fm = frontmatter(RAIZ / "commands" / nombre)
            with self.subTest(comando=nombre):
                self.assertEqual(modelo, fm.get("model", "").strip())
                self.assertEqual(effort, fm.get("effort", "").strip())
                self.assertNotIn("user-invocable", fm, "debe comportarse como los comandos ya probados")

    def test_los_comandos_que_fijan_modelo_estan_declarados_en_el_plugin(self):
        manifiesto = json.loads((RAIZ / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        for nombre in ("usar-opus.md", "usar-fable.md"):
            self.assertIn(f"./commands/{nombre}", manifiesto["commands"])

    def test_los_demas_roles_siguen_fijos(self):
        """Decision del usuario: solo eligen Producto y Leader."""
        esperado = {"cierre.md": "claude-opus-5-5", "review.md": "claude-opus-5-5",
                    "implementar.md": "claude-opus-5-5", "estado.md": "claude-haiku-5-5"}
        for nombre, modelo in esperado.items():
            texto = (RAIZ / "commands" / nombre).read_text(encoding="utf-8")
            with self.subTest(comando=nombre):
                self.assertEqual(modelo, frontmatter(RAIZ / "commands" / nombre).get("model", "").strip())
                self.assertNotIn("modelo.py", texto)
                self.assertNotIn("usar-fable", texto)
        self.assertEqual("claude-opus-5-5", frontmatter(RAIZ / "agents" / "revisor.md")["model"].strip())
        self.assertEqual("claude-sonnet-5-5", frontmatter(RAIZ / "agents" / "implementer.md")["model"].strip())

    def test_modelos_md_ya_no_dice_que_fable_queda_fuera(self):
        texto = (RAIZ / "references" / "modelos.md").read_text(encoding="utf-8")
        self.assertNotIn("Fable queda fuera", texto)
        self.assertIn("claude-fable-5-2", texto)


if __name__ == "__main__":
    unittest.main()
