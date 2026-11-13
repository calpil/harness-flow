"""Modo pair y reglas del stack: garantizados por scripts, no por la obediencia del agente.

Dos cosas dependian de que el agente leyera bien el brief y decidiera cumplir:

1. Las reglas del stack. El brief solo las nombraba. En un repo fuera del
   proyecto de la sesion (o en un worktree) el host no las carga solo, asi que
   el implementer podia escribir sin haberlas visto.
2. El modo pair. Solo se "activaba" si se detectaba un stack, y no dejaba
   rastro: la lista de tests que aprueba el usuario vivia en el chat, y ningun
   gate podia comprobar que hubo pair.

Decisiones del usuario que estos tests fijan: pair por defecto en cualquier
repo (se desactiva solo si lo pide), la lista de tests se sella, y el brief trae
el texto completo de las reglas. Quien sella la lista y cuando hace falta el SI
del usuario esta en test_pair_automatico.py.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"
sys.path.insert(0, str(SCRIPTS))

import contexto  # noqa: E402
from comun import load_backlog, micros_declarados, paths  # noqa: E402

SPEC = ("# Spec - Feature #{id}: cobro\n\nEstado: draft\n\n"
        "## Criterios de aceptacion\n\n"
        "- AC-1: dado un carro, cuando pago, entonces cobra. `verificar: true`\n"
        "- AC-2: dado un rechazo, cuando reintento, entonces no cobra dos veces.\n\n"
        "## Fuera de alcance\n\nFacturas.\n")
LISTA = ("# Lista de tests - Feature #5\n\nEstado: draft\n\n"
         "- AC-1: cobra_un_carro_valido [costura: endpoint]\n"
         "- AC-2: el_reintento_no_cobra_dos_veces [costura: servicio]\n")
FRASE_GO = "Capa Domain"          # texto de assets/stacks/golang-hexagonal/rules/architecture.md
SIN_REGLAS = {"rama_base": "main", "require_docs_al_dia": False, "require_spec_approved": False,
              "require_review": False, "require_leccion": False, "require_verify_green": False}


def sh(*args, cwd):
    r = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)
    assert r.returncode == 0, f"{args}: {r.stdout}{r.stderr}"
    return r.stdout.strip()


def harness(script, *args, cwd):
    env = dict(os.environ, HARNESS_SIN_CONTEXTO="1")
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          cwd=str(cwd), capture_output=True, text=True, env=env)


def escribir(ruta: Path, texto: str = "") -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


class Proyecto(unittest.TestCase):
    """Raiz sin stack (repo git) y dos servicios Go fuera de ella."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = self.tmp / "proyecto"
        self.micros = self.tmp / "servicios"
        for ms in ("ms-pagos", "ms-media"):
            escribir(self.micros / ms / "go.mod", f"module example.com/{ms}\n")
        escribir(self.root / "harness" / "grafos.json", json.dumps({"raices": [
            {"nombre": "raiz", "path": "."}, {"nombre": "servicios", "path": str(self.micros)}]}))
        escribir(self.root / "docs" / "spec-feature-5-cobro.md", SPEC.format(id=5))
        escribir(self.root / "docs" / "impl-5.md", "## AC-1\nsrc/a.go:1\n## AC-2\nsrc/a.go:2\n")
        escribir(self.root / "src" / "a.go", "package src\n")
        self.backlog({"id": 5, "name": "cobro", "status": "in_progress",
                      "microservicios": ["ms-pagos", "ms-media"]})
        sh("git", "init", "-q", "-b", "main", cwd=self.root)
        sh("git", "config", "user.email", "t@example.com", cwd=self.root)
        sh("git", "config", "user.name", "T", cwd=self.root)
        self.commit("base")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def backlog(self, feature: dict, rules: dict | None = None) -> None:
        escribir(self.root / "harness" / "feature_list.json",
                 json.dumps({"project": "demo", "rules": rules or SIN_REGLAS, "features": [feature]}))

    def feature(self) -> dict:
        return json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))["features"][0]

    def commit(self, mensaje: str) -> None:
        sh("git", "add", "-A", cwd=self.root)
        sh("git", "commit", "-q", "-m", mensaje, cwd=self.root)

    def reglas(self) -> str:
        p = paths(self.root)
        f = self.feature()
        return "\n".join(contexto.lineas_reglas(p, load_backlog(p), f, micros_declarados(f)))


class ReglasEnElBriefTests(Proyecto):
    def test_trae_el_texto_completo_y_no_solo_el_nombre_del_archivo(self):
        out = self.reglas()
        self.assertIn(FRASE_GO, out)
        self.assertIn("architecture.md", out)
        self.assertIn("testing.md", out)

    def test_dice_en_que_repos_son_obligatorias(self):
        out = self.reglas()
        self.assertIn("golang-hexagonal", out)
        self.assertIn("ms-pagos", out)
        self.assertIn("ms-media", out)

    def test_dos_repos_del_mismo_stack_no_duplican_el_texto(self):
        self.assertEqual(1, self.reglas().count(FRASE_GO))

    def test_el_frontmatter_no_entra(self):
        out = self.reglas()
        self.assertNotIn("globs:", out)
        self.assertNotIn("description:", out)

    def test_la_copia_del_proyecto_gana_a_la_plantilla_de_la_skill(self):
        """Si el proyecto adapto la regla, lo que vale es lo que el repo tiene."""
        escribir(self.micros / "ms-pagos" / ".agents" / "rules" / "architecture.md",
                 "---\ndescription: x\n---\n\nREGLA PROPIA DEL PROYECTO\n")
        out = self.reglas()
        self.assertIn("REGLA PROPIA DEL PROYECTO", out)
        self.assertNotIn(FRASE_GO, out)

    def test_sin_stack_normativo_no_hay_bloque(self):
        self.backlog({"id": 5, "name": "cobro", "status": "in_progress"})
        self.assertEqual("", self.reglas())

    def test_el_recorte_del_brief_no_se_lleva_las_reglas(self):
        """--max-lineas corta el indice; las reglas no son parte de lo que se puede cortar."""
        r = harness("contexto.py", "brief", "--feature", "5", "--max-lineas", "6", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("recortadas", r.stdout)
        self.assertIn(FRASE_GO, r.stdout)

    def test_el_briefing_del_revisor_las_trae_una_vez(self):
        r = harness("revision.py", "--feature", "5", "--briefing", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertEqual(1, r.stdout.count(FRASE_GO), "una vez: en el bloque de normativa, no tambien en el brief")


class ModoTests(Proyecto):
    def start(self, *extra):
        self.backlog({"id": 5, "name": "cobro", "status": "todo"})
        self.commit("backlog")
        return harness("worktree.py", "start", "--feature", "5", *extra, cwd=self.root)

    def test_start_registra_pair_por_defecto_aunque_el_repo_no_tenga_stack(self):
        r = self.start()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertEqual("pair", self.feature()["modo"])
        self.assertIn("modo pair", r.stdout)

    def test_delegado_es_una_decision_explicita(self):
        r = self.start("--delegado")
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertEqual("delegado", self.feature()["modo"])

    def test_el_modo_se_puede_cambiar_y_queda_en_la_bitacora(self):
        self.start()
        r = harness("worktree.py", "modo", "--feature", "5", "--delegado", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertEqual("delegado", self.feature()["modo"])
        historia = (self.root / "harness" / "progress" / "history.md").read_text(encoding="utf-8")
        self.assertIn("modo de #5: delegado (antes pair)", historia)

    def brief(self, modo=None) -> str:
        f = {"id": 5, "name": "cobro", "status": "in_progress"}
        if modo:
            f["modo"] = modo
        self.backlog(f)
        r = harness("contexto.py", "brief", "--feature", "5", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        return r.stdout

    def test_el_brief_ordena_pair_sin_depender_de_que_haya_stack(self):
        out = self.brief("pair")
        self.assertIn("modo pair automatico: ACTIVADO", out)
        self.assertIn("sellar-tests", out)
        self.assertNotIn("por normativa de stack", out)

    def test_el_brief_dice_delegado_cuando_el_usuario_lo_pidio(self):
        out = self.brief("delegado")
        self.assertIn("modo delegado", out)
        self.assertNotIn("modo pair automatico: ACTIVADO", out)

    def test_una_feature_anterior_sin_modo_no_se_inventa_uno(self):
        out = self.brief()
        self.assertIn("sin registrar", out)
        self.assertNotIn("modo pair automatico: ACTIVADO", out)


class ListaDeTestsTests(Proyecto):
    def aprobar(self, *extra):
        return harness("gate.py", "aprobar-tests", "--feature", "5", "--por", "T", *extra, cwd=self.root)

    def lista(self, texto=LISTA) -> Path:
        ruta = self.root / "docs" / "tests-5.md"
        escribir(ruta, texto)
        return ruta

    def test_la_lista_completa_se_sella_sin_yes(self):
        """Antes pedia el SI del usuario: 17 formularios de 17 aprobados sin cambios
        (test_pair_automatico.py). Lo que si lo pide esta en ese archivo."""
        ruta = self.lista()
        r = self.aprobar()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("Estado: sellada", ruta.read_text(encoding="utf-8"))
        self.assertIn("tests_sig", self.feature())

    def test_sin_archivo_se_niega(self):
        r = self.aprobar("--yes")
        self.assertNotEqual(0, r.returncode)
        self.assertIn("tests-5.md", r.stdout + r.stderr)

    def test_un_ac_sin_test_en_la_lista_se_niega_y_lo_nombra(self):
        self.lista(LISTA.replace("- AC-2: el_reintento_no_cobra_dos_veces [costura: servicio]\n", ""))
        r = self.aprobar("--yes")
        self.assertNotEqual(0, r.returncode)
        self.assertIn("AC-2", r.stdout + r.stderr)

    def test_una_mencion_de_pasada_no_cuenta_como_test_del_ac(self):
        """Una mencion no es una declaracion (leccion del arnes)."""
        self.lista(LISTA.replace("- AC-2: el_reintento_no_cobra_dos_veces [costura: servicio]\n",
                                 "Nota: el AC-2 se cubre despues.\n"))
        self.assertNotEqual(0, self.aprobar("--yes").returncode)

    def test_la_lista_completa_se_sella_con_la_firma_del_gate(self):
        ruta = self.lista()
        r = self.aprobar("--yes")
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        texto = ruta.read_text(encoding="utf-8")
        self.assertIn("Estado: sellada", texto)
        self.assertIn("Sellada: T", texto)
        self.assertIn("gate.py sellar-tests", texto)
        self.assertIn("tests_sig", self.feature())

    def test_la_verificacion_manual_es_una_entrada_valida(self):
        self.lista(LISTA.replace("el_reintento_no_cobra_dos_veces [costura: servicio]",
                                 "verificacion manual: el boton queda deshabilitado"))
        self.assertEqual(0, self.aprobar("--yes").returncode)


class CloseTests(Proyecto):
    def cerrar(self, modo, preparar=None):
        f = {"id": 5, "name": "cobro", "kind": "feature", "status": "in_progress",
             "branch": "feature/5", "base_sha": sh("git", "rev-parse", "HEAD", cwd=self.root)}
        if modo:
            f["modo"] = modo
        self.backlog(f)
        self.commit("backlog")
        sh("git", "checkout", "-q", "-b", "feature/5", cwd=self.root)
        if preparar:
            preparar()
        escribir(self.root / "src" / "b.go", "package src\n")
        self.commit("trabajo")
        return harness("gate.py", "close", "--feature", "5", "--status", "done", "--to", "main", cwd=self.root)

    def aprobar_lista(self):
        escribir(self.root / "docs" / "tests-5.md", LISTA)
        r = harness("gate.py", "aprobar-tests", "--feature", "5", "--yes", "--por", "T", cwd=self.root)
        assert r.returncode == 0, r.stdout + r.stderr

    def test_pair_sin_lista_aprobada_no_cierra(self):
        r = self.cerrar("pair")
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)
        self.assertIn("lista de tests", r.stdout)
        self.assertEqual("in_progress", self.feature()["status"])

    def test_pair_con_la_lista_aprobada_cierra(self):
        r = self.cerrar("pair", self.aprobar_lista)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertEqual("done", self.feature()["status"])

    def test_cambiar_la_lista_despues_de_aprobarla_invalida_el_sello(self):
        def preparar():
            self.aprobar_lista()
            ruta = self.root / "docs" / "tests-5.md"
            ruta.write_text(ruta.read_text(encoding="utf-8") + "- AC-1: otro_test_agregado\n", encoding="utf-8")
        r = self.cerrar("pair", preparar)
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)
        self.assertIn("cambio despues de sellarla", r.stdout)

    def test_delegado_cierra_sin_lista(self):
        """El control: el gate es del modo pair, no de toda feature."""
        r = self.cerrar("delegado")
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_una_feature_anterior_sin_modo_no_queda_sujeta_al_gate(self):
        """No se le cambia la regla a lo que ya estaba en curso."""
        r = self.cerrar(None)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
