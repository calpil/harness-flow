"""La norma del stack y el modo pair llegan a cada rol por la salida de un script.

Tres huecos medidos en un proyecto con el front en la raiz y un servicio fuera:

1. El rol producto no veia el stack. No pasa por el brief de una feature, asi
   que el SDD de arquitectura se redactaba sin la norma de los stacks que el
   proyecto ya usa.
2. Las skills del stack solo se nombraban, y la lista del stack principal se
   cortaba a seis. Usarlas dependia de que estuvieran instaladas en el repo de
   la sesion.
3. El modo pair lo registraba solo `worktree.py start`. Una feature que llega
   al codigo por `worktree.py register` (raiz multi-repo) cerraba sin modo, y
   sin modo `close` no exige la lista de tests.

Y un defecto que aparecio al medir: el briefing del revisor imprimia vacias las
restricciones de arquitectura que no traen `rationale`.
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
sys.path.insert(0, str(SCRIPTS))

import contexto  # noqa: E402
import stack  # noqa: E402
from comun import load_backlog, micros_declarados, paths  # noqa: E402

SPEC = ("# Spec - Feature #1: cobro\n\nEstado: draft\n\n"
        "## Criterios de aceptacion\n\n"
        "- AC-1: dado un carro, cuando pago, entonces cobra. `verificar: true`\n\n"
        "## Fuera de alcance\n\nFacturas.\n")
REGLAS = {"rama_base": "main", "require_docs_al_dia": False}


def escribir(ruta: Path, texto: str = "") -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


def harness(script, *args, cwd):
    env = dict(os.environ, HARNESS_SIN_CONTEXTO="1", HARNESS_SIN_HUB="1", HARNESS_SIN_CBM="1")
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          cwd=str(cwd), capture_output=True, text=True, env=env)


class Proyecto(unittest.TestCase):
    """Front Angular en la raiz y un servicio Go fuera de ella."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = self.tmp / "front"
        self.go = self.tmp / "servicios" / "ms-pagos"
        escribir(self.root / "angular.json", "{}")
        escribir(self.root / "package.json", json.dumps({"dependencies": {"@angular/core": "19.0.0"}}))
        escribir(self.go / "go.mod", "module example.com/ms-pagos\n")
        escribir(self.root / "harness" / "grafos.json", json.dumps({"raices": [
            {"nombre": "front", "path": "."}, {"nombre": "servicios", "path": str(self.go.parent)}]}))
        escribir(self.root / "docs" / "spec-feature-1-cobro.md", SPEC)
        self.backlog({"id": 1, "name": "cobro", "status": "todo", "microservicios": ["ms-pagos"]})
        self.p = paths(self.root)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def backlog(self, feature: dict, rules: dict | None = None) -> None:
        escribir(self.root / "harness" / "feature_list.json",
                 json.dumps({"project": "demo", "rules": rules or REGLAS, "features": [feature]}))

    def feature(self) -> dict:
        return load_backlog(self.p)["features"][0]

    def normativa(self) -> str:
        data = load_backlog(self.p)
        f = data["features"][0]
        return "\n".join(contexto.lineas_reglas(self.p, data, f, micros_declarados(f)))


class SkillsEnElBriefTests(Proyecto):
    def test_el_indice_trae_todas_las_skills_de_cada_stack_y_no_seis(self):
        out = self.normativa()
        for sid in ("angular-product", "golang-hexagonal"):
            skills = stack.cargar_manifest(sid)["normative"]["skills"]
            self.assertGreater(len(skills), 6, "el control: el stack tiene mas de las que se listaban")
            self.assertIn(f"SKILLS DEL STACK {sid} ({len(skills)})", out)
            for nombre in skills:
                with self.subTest(stack=sid, skill=nombre):
                    self.assertRegex(out, rf"(?m)^  - {re.escape(nombre)}(:|$)")

    def test_la_lista_de_nombres_del_brief_tampoco_se_corta(self):
        data = load_backlog(self.p)
        f = data["features"][0]
        out = "\n".join(contexto._lineas_stack(self.p, data, f, micros_declarados(f)))
        ultima = stack.cargar_manifest("angular-product")["normative"]["skills"][-1]
        self.assertIn(ultima, out)
        self.assertNotIn("...", out)

    def test_cada_skill_viene_con_su_descripcion(self):
        self.assertRegex(self.normativa(), r"(?m)^  - add-persistence: \S.{20,}")

    def test_la_ruta_que_da_existe_aunque_el_repo_no_tenga_nada_instalado(self):
        """Lo que hace que una skill se pueda abrir en cualquier host: una ruta que existe."""
        self.assertFalse((self.go / ".claude").exists(), "el control: el repo no tiene nada instalado")
        bases = re.findall(r"(?m)^    en (.+)/<nombre>/SKILL\.md \(", self.normativa())
        self.assertTrue(bases)
        go = next(b for b in bases if "golang-hexagonal" in b)
        self.assertTrue((Path(go) / "add-persistence" / "SKILL.md").is_file())

    def test_la_copia_del_proyecto_gana_a_la_plantilla(self):
        stack.normalizar_repositorio(self.go, "golang-hexagonal", rules={})
        self.assertIn(f"en {self.go}/.claude/skills/<nombre>/SKILL.md", self.normativa())

    def test_una_skill_excluida_por_el_proyecto_no_entra_al_indice(self):
        self.backlog({"id": 1, "name": "cobro", "status": "todo", "microservicios": ["ms-pagos"]},
                     dict(REGLAS, stack_skills_excluidas={"golang-hexagonal": ["add-persistence"]}))
        out = self.normativa()
        self.assertNotIn("add-persistence", out)
        self.assertIn("  - add-api-endpoint", out, "el control: las demas siguen")

    def test_el_recorte_del_brief_no_se_lleva_el_indice(self):
        r = harness("contexto.py", "brief", "--feature", "1", "--max-lineas", "12", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("SKILLS DEL STACK golang-hexagonal", r.stdout)

    def test_el_briefing_del_revisor_trae_el_indice(self):
        r = harness("revision.py", "--feature", "1", "--briefing", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertEqual(1, r.stdout.count("SKILLS DEL STACK golang-hexagonal"))
        self.assertIn("  - security-review", r.stdout)


class DescripcionDeSkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def descripcion(self, frontmatter: str) -> str:
        ruta = self.tmp / "SKILL.md"
        ruta.write_text(f"---\n{frontmatter}\n---\n\n# Cuerpo\n", encoding="utf-8")
        return contexto._descripcion_skill(ruta)

    def test_una_linea(self):
        self.assertEqual("Hace una cosa.", self.descripcion("name: x\ndescription: Hace una cosa."))

    def test_entre_comillas(self):
        self.assertEqual("Hace: una cosa.", self.descripcion('name: x\ndescription: "Hace: una cosa."'))

    def test_escalar_de_bloque(self):
        self.assertEqual("Hace una cosa en dos lineas.",
                         self.descripcion("name: x\ndescription: >\n  Hace una cosa\n  en dos lineas.\nlicense: MIT"))

    def test_larga_se_corta_y_lo_dice(self):
        out = self.descripcion("description: " + "palabra " * 60)
        self.assertLessEqual(len(out), 160)
        self.assertTrue(out.endswith("..."))

    def test_sin_descripcion_no_inventa(self):
        self.assertEqual("", self.descripcion("name: x"))

    def test_toda_skill_de_todo_stack_tiene_descripcion_legible(self):
        for ruta in sorted(stack.STACKS_DIR.glob("*/skills/*/SKILL.md")):
            with self.subTest(skill=str(ruta.relative_to(stack.STACKS_DIR))):
                self.assertTrue(contexto._descripcion_skill(ruta))


class RolProductoTests(Proyecto):
    def borrador(self, doc: str) -> str:
        r = harness("producto.py", "borrador", "--doc", doc, cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        return r.stdout

    def test_el_borrador_del_sdd_llega_con_la_norma_de_cada_stack_del_proyecto(self):
        out = self.borrador("sdd")
        self.assertIn("STACKS DEL PROYECTO", out)
        self.assertIn("angular-product (", out)
        self.assertIn("REGLAS DEL STACK angular-product", out)
        self.assertIn("REGLAS DEL STACK golang-hexagonal", out)
        self.assertIn("Capa Domain", out, "el texto de la regla, no solo su nombre")
        self.assertIn("SKILLS DEL STACK golang-hexagonal", out)

    def test_dice_en_que_repo_esta_cada_stack(self):
        self.assertRegex(self.borrador("sdd"), r"(?m)^golang-hexagonal \(.+\): ms-pagos$")

    def test_el_del_prd_trae_solo_el_resumen(self):
        out = self.borrador("prd")
        self.assertIn("STACKS DEL PROYECTO", out)
        self.assertIn("golang-hexagonal (", out)
        self.assertNotIn("REGLAS DEL STACK", out)

    def test_si_el_borrador_ya_existe_la_norma_llega_igual(self):
        self.borrador("sdd")
        self.assertIn("REGLAS DEL STACK golang-hexagonal", self.borrador("sdd"))

    def test_un_proyecto_sin_stack_lo_dice_y_nombra_los_que_tienen_norma(self):
        (self.root / "angular.json").unlink()
        (self.root / "package.json").unlink()
        shutil.rmtree(self.go)
        out = self.borrador("sdd")
        self.assertIn("ningun repo del proyecto tiene un stack normativo", out)
        self.assertIn("rust-hexagonal", out)
        self.assertNotIn("REGLAS DEL STACK", out)

    def test_el_subcomando_stacks_da_lo_mismo_bajo_demanda(self):
        r = harness("contexto.py", "stacks", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("REGLAS DEL STACK golang-hexagonal", r.stdout)
        r = harness("contexto.py", "stacks", "--resumen", cwd=self.root)
        self.assertNotIn("REGLAS DEL STACK", r.stdout)


class RestriccionesTests(Proyecto):
    def test_ninguna_restriccion_de_ningun_stack_sale_vacia(self):
        for manifest in stack.listar_stacks_disponibles():
            for clave, valor in manifest.get("normative", {}).get("architecture_constraints", {}).items():
                with self.subTest(stack=manifest.get("id"), restriccion=clave):
                    self.assertTrue(contexto.texto_restriccion(valor).strip())

    def test_una_restriccion_sin_rationale_dice_sus_sub_reglas(self):
        out = contexto.texto_restriccion({"forbidden_calls": ["time.Sleep"], "inmemory": True})
        self.assertEqual("forbidden_calls: time.Sleep; inmemory: si", out)

    def test_el_briefing_del_revisor_no_trae_restricciones_en_blanco(self):
        r = harness("revision.py", "--feature", "1", "--briefing", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"(?m)^  \* layer_boundaries: \S")
        self.assertNotRegex(r.stdout, r"(?m)^  \* \w+: *$")


class ModoAlAprobarElSpecTests(Proyecto):
    def aprobar(self):
        return harness("gate.py", "approve-spec", "--feature", "1", "--yes", "--por", "T", cwd=self.root)

    def test_la_primera_aprobacion_deja_la_feature_en_pair(self):
        r = self.aprobar()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertEqual("pair", self.feature()["modo"])
        self.assertIn("modo pair", r.stdout)

    def test_sin_start_ni_register_close_ya_exige_la_lista(self):
        """El hueco: una feature que llega al codigo sin pasar por `start` no tenia modo."""
        import gate
        self.aprobar()
        fallos = gate.fallos_lista_tests(self.p, self.feature(), ["AC-1"])
        self.assertEqual(1, len(fallos))
        self.assertIn("falta la lista de tests", fallos[0])

    def test_un_spec_que_ya_estaba_sellado_no_cambia_de_regla(self):
        """Puede tener el trabajo hecho: no se le exige una lista 'antes de implementar'."""
        self.aprobar()
        f = self.feature()
        del f["modo"]                     # como quedo una feature sellada antes de este cambio
        self.backlog(f)
        r = self.aprobar()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertNotIn("modo", self.feature())
        self.assertNotIn("modo pair", r.stdout)

    def test_no_pisa_la_decision_de_delegar(self):
        self.backlog({"id": 1, "name": "cobro", "status": "todo", "modo": "delegado"})
        self.aprobar()
        self.assertEqual("delegado", self.feature()["modo"])

    def test_el_usuario_puede_delegar_antes_de_arrancar(self):
        self.aprobar()
        r = harness("worktree.py", "modo", "--feature", "1", "--delegado", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertEqual("delegado", self.feature()["modo"])

    def test_sin_yes_no_queda_modo(self):
        r = harness("gate.py", "approve-spec", "--feature", "1", cwd=self.root)
        self.assertNotEqual(0, r.returncode)
        self.assertNotIn("modo", self.feature())


if __name__ == "__main__":
    unittest.main()
