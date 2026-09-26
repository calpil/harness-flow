"""gate.py enmienda: cambiar un spec que ya tiene trabajo encima deja rastro.

Antes se re-sellaba con approve-spec y pasaban tres cosas:
  1. el backlog quedaba solo con la firma nueva: probar que AC habia cambiado
     exigia reconstruir el spec anterior a mano (ADR #13, AC-29);
  2. nada ataba el cambio a lo que el usuario aprobo: un AC podia cambiar de
     paso y quedar sellado junto con el que si se habia pedido;
  3. el review y el verify del spec viejo seguian valiendo para close mientras
     el numero de AC no cambiara.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from comun import comparar_huellas, spec_huella  # noqa: E402

SPEC = ("# Spec - Feature #1: cobro\n\nEstado: draft\n\n"
        "## Criterios de aceptacion\n\n"
        "- AC-1: dado un carro, cuando pago, entonces cobra. `verificar: true`\n"
        "- AC-2: dado un rechazo, cuando reintento, entonces no cobra dos veces.\n"
        "  Comando: `true`\n"
        "- AC-3: dado un reembolso, cuando lo pido, entonces vuelve el dinero.\n\n"
        "## Fuera de alcance\n\nFacturas.\n")

CITAS = "## AC-1\nsrc/a.ts:1\n## AC-2\nsrc/a.ts:2\n## AC-3\nsrc/a.ts:3\n"


def propuesta(nombra=("AC-2",), titulo="el reintento responde 409"):
    cambios = "\n".join(f"- {ac}: texto nuevo." for ac in nombra)
    return (f"# Enmienda - Feature #1: {titulo}\n\nEstado: draft\n"
            "Origen: R-1 del review.\n\n"
            "## Por que\n\nEl review encontro que el reintento cobraba.\n\n"
            f"## Cambios al spec\n\n{cambios}\n\n"
            "## Lo que NO cambia\n\nLos demas AC y sus comandos.\n")


def sh(*args, cwd):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)


def harness(script, *args, cwd):
    env = dict(os.environ, HARNESS_SIN_CONTEXTO="1")
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          cwd=str(cwd), capture_output=True, text=True, env=env)


class HuellaTests(unittest.TestCase):
    def cambio(self, nuevo, antes=SPEC):
        return comparar_huellas(spec_huella(antes), spec_huella(nuevo))

    def test_el_comando_bajo_el_ac_es_parte_del_ac(self):
        c = self.cambio(SPEC.replace("  Comando: `true`", "  Comando: `false`"))
        self.assertEqual(c["cambiados"], ["AC-2"])
        self.assertFalse(c["resto"])

    def test_los_sellos_no_cuentan(self):
        sellado = SPEC.replace("Estado: draft", "Estado: approved\n"
                               "Aprobado: alan · 2026-09-26T00:00:00Z · x")
        c = self.cambio(sellado)
        self.assertEqual(c["cambiados"] + c["nuevos"] + c["retirados"], [])
        self.assertFalse(c["resto"])

    def test_la_seccion_de_enmiendas_no_cuenta(self):
        c = self.cambio(SPEC + "\n## Enmiendas posteriores a la aprobacion\n\n### E-1: x\n")
        self.assertFalse(c["resto"])
        self.assertEqual(c["cambiados"], [])

    def test_texto_fuera_de_los_ac_es_el_resto(self):
        c = self.cambio(SPEC.replace("Facturas.", "Facturas y boletas."))
        self.assertTrue(c["resto"])
        self.assertEqual(c["cambiados"], [])

    def test_un_encabezado_dentro_de_codigo_no_corta_el_ac(self):
        con_codigo = SPEC.replace(
            "entonces vuelve el dinero.\n",
            "entonces vuelve el dinero.\n  ```bash\n  # reembolso\n  curl x\n  ```\n")
        c = self.cambio(con_codigo.replace("curl x", "curl y"), antes=con_codigo)
        self.assertEqual(c["cambiados"], ["AC-3"])
        self.assertFalse(c["resto"])

    def test_ac_nuevo_y_retirado(self):
        c = self.cambio(SPEC.replace("- AC-3: dado un reembolso", "- AC-4: dado un reembolso"))
        self.assertEqual((c["nuevos"], c["retirados"]), (["AC-4"], ["AC-3"]))


class Proyecto(unittest.TestCase):
    spec_inicial = SPEC

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / "repo"
        (self.repo / "harness").mkdir(parents=True)
        (self.repo / "docs").mkdir()
        self.backlog = self.repo / "harness" / "feature_list.json"
        self.backlog.write_text(json.dumps({"project": "t", "features": [
            {"id": "1", "name": "cobro", "status": "in_progress"}]}), encoding="utf-8")
        self.spec = self.repo / "docs" / "spec-feature-1-cobro.md"
        self.spec.write_text(self.spec_inicial, encoding="utf-8")
        self.prop = self.repo / "docs" / "propuesta-1-enmienda-reintento.md"

    def gate(self, *args):
        return harness("gate.py", *args, cwd=self.repo)

    def ok(self, *args):
        r = self.gate(*args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def feature(self):
        return json.loads(self.backlog.read_text(encoding="utf-8"))["features"][0]

    def editar_ac(self, ac, nuevo):
        lineas = self.spec.read_text(encoding="utf-8").splitlines(keepends=True)
        for i, linea in enumerate(lineas):
            if linea.startswith(f"- {ac}:"):
                lineas[i] = f"- {ac}: {nuevo}\n"
        self.spec.write_text("".join(lineas), encoding="utf-8")

    def enmendar(self, *extra):
        return self.gate("enmienda", "--feature", "1", "--propuesta",
                         "docs/" + self.prop.name, *extra)


class EnmiendaTests(Proyecto):
    def setUp(self):
        super().setUp()
        self.ok("approve-spec", "--feature", "1", "--yes", "--por", "alan")
        (self.repo / "docs" / "impl-1.md").write_text(CITAS, encoding="utf-8")
        self.sello = self.feature()["last_spec_sig"]

    def test_approve_spec_ya_no_re_sella_un_spec_con_trabajo_encima(self):
        self.editar_ac("AC-2", "el reintento responde 409.")
        r = self.gate("approve-spec", "--feature", "1", "--yes")
        self.assertNotEqual(r.returncode, 0, "re-sello sin dejar rastro de la enmienda")
        self.assertIn("ENMIENDA", r.stdout + r.stderr)
        self.assertIn("impl-1.md", r.stdout + r.stderr)
        self.assertEqual(self.feature()["last_spec_sig"], self.sello)

    def test_sin_yes_no_toca_nada(self):
        self.editar_ac("AC-2", "el reintento responde 409.")
        self.prop.write_text(propuesta(), encoding="utf-8")
        antes = self.spec.read_text(encoding="utf-8")
        r = self.enmendar()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--yes", r.stdout + r.stderr)
        self.assertEqual(self.spec.read_text(encoding="utf-8"), antes)
        self.assertNotIn("enmiendas", self.feature())

    def test_spec_sin_cambios_no_se_enmienda(self):
        self.prop.write_text(propuesta(), encoding="utf-8")
        r = self.enmendar("--yes")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no cambio desde su ultimo sello", r.stdout + r.stderr)

    def test_enmienda_sella_spec_y_propuesta_y_deja_rastro(self):
        self.editar_ac("AC-2", "el reintento responde 409 y no cobra.")
        self.prop.write_text(propuesta(), encoding="utf-8")
        r = self.enmendar("--yes", "--por", "alan")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("E-1", r.stdout)

        spec = self.spec.read_text(encoding="utf-8")
        self.assertIn("## Enmiendas posteriores a la aprobacion", spec)
        self.assertIn("### E-1: el reintento responde 409\n", spec)
        self.assertIn("Propuesta: `docs/propuesta-1-enmienda-reintento.md`", spec)
        self.assertIn("AC tocados: AC-2 cambiado\n", spec)
        self.assertIn("sellado por gate.py enmienda --yes (E-1)", spec)

        prop = self.prop.read_text(encoding="utf-8")
        self.assertIn("Estado: aprobada\n", prop)
        self.assertIn("E-1 de la #1 · sellada por gate.py enmienda --yes", prop)

        e = self.feature()["enmiendas"]
        self.assertEqual(len(e), 1)
        self.assertEqual(e[0]["id"], "E-1")
        self.assertEqual(e[0]["propuesta"], "docs/propuesta-1-enmienda-reintento.md")
        self.assertEqual(e[0]["acs"]["cambiados"], ["AC-2"])
        self.assertEqual(e[0]["spec_sig_anterior"]["hash"], self.sello["hash"])

        r = self.ok("check-spec", "--feature", "1")
        self.assertIn("AC-1, AC-2, AC-3", r.stdout, "la entrada de la enmienda cambio los AC")
        historia = (self.repo / "harness" / "progress" / "history.md").read_text(encoding="utf-8")
        self.assertIn("enmienda E-1 aprobada por alan", historia)

    def test_un_ac_que_la_propuesta_no_nombra_no_se_sella(self):
        self.editar_ac("AC-2", "el reintento responde 409.")
        self.editar_ac("AC-3", "el reembolso ahora es parcial.")
        self.prop.write_text(propuesta(nombra=("AC-2",)), encoding="utf-8")
        antes = self.spec.read_text(encoding="utf-8")
        r = self.enmendar("--yes")
        self.assertNotEqual(r.returncode, 0, "sello un AC que el usuario no aprobo")
        self.assertIn("el spec cambio AC-3 y la propuesta no lo nombra", r.stdout + r.stderr)
        self.assertEqual(self.spec.read_text(encoding="utf-8"), antes)
        self.assertIn("Estado: draft", self.prop.read_text(encoding="utf-8"))
        self.assertNotIn("enmiendas", self.feature())

    def test_una_mencion_en_la_guia_no_nombra_el_ac(self):
        self.editar_ac("AC-3", "el reembolso ahora es parcial.")
        self.prop.write_text(propuesta(nombra=("AC-2",)).replace(
            "## Lo que NO cambia", "<!-- ojo con AC-3 -->\n\n## Lo que NO cambia"),
            encoding="utf-8")
        r = self.enmendar("--yes")
        self.assertNotEqual(r.returncode, 0, "una guia <!-- --> conto como mencion")
        self.assertIn("AC-3", r.stdout + r.stderr)

    def test_ac_nuevo_y_retirado_quedan_registrados(self):
        texto = self.spec.read_text(encoding="utf-8")
        self.spec.write_text(texto.replace("- AC-3: dado un reembolso",
                                           "- AC-4: dado un reembolso"), encoding="utf-8")
        self.prop.write_text(propuesta(nombra=("AC-3", "AC-4")), encoding="utf-8")
        r = self.enmendar("--yes")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        acs = self.feature()["enmiendas"][0]["acs"]
        self.assertEqual((acs["nuevos"], acs["retirados"]), (["AC-4"], ["AC-3"]))
        self.assertIn("AC tocados: AC-4 nuevo, AC-3 retirado", self.spec.read_text(encoding="utf-8"))

    def test_propuesta_incompleta_no_se_sella(self):
        self.editar_ac("AC-2", "el reintento responde 409.")
        self.prop.write_text("# Enmienda - Feature #1: x\n\nEstado: draft\n\n"
                             "## Por que\n\n<!-- guia sin rellenar -->\n\n"
                             "## Cambios al spec\n\n- AC-2: nuevo.\n", encoding="utf-8")
        r = self.enmendar("--yes")
        self.assertNotEqual(r.returncode, 0)
        salida = r.stdout + r.stderr
        self.assertIn("'## Por que' esta vacia", salida)
        self.assertIn("falta la seccion '## Lo que NO cambia'", salida)

    def test_la_propuesta_vive_en_docs(self):
        self.editar_ac("AC-2", "el reintento responde 409.")
        fuera = self.repo / "propuesta.md"
        fuera.write_text(propuesta(), encoding="utf-8")
        r = self.gate("enmienda", "--feature", "1", "--propuesta", "propuesta.md", "--yes")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("tiene que vivir en docs/", r.stdout + r.stderr)
        self.assertNotIn("enmiendas", self.feature())

    def test_nombrar_ac_10_no_nombra_al_ac_1(self):
        self.editar_ac("AC-1", "dado un carro, cuando pago, entonces cobra una vez.")
        self.prop.write_text(propuesta(nombra=("AC-10",)), encoding="utf-8")
        r = self.enmendar("--yes")
        self.assertNotEqual(r.returncode, 0, "AC-10 conto como mencion de AC-1")
        self.assertIn("el spec cambio AC-1 y la propuesta no lo nombra", r.stdout + r.stderr)

    def test_una_propuesta_sella_una_sola_enmienda(self):
        self.editar_ac("AC-2", "el reintento responde 409.")
        self.prop.write_text(propuesta(), encoding="utf-8")
        self.ok("enmienda", "--feature", "1", "--propuesta", "docs/" + self.prop.name, "--yes")
        self.editar_ac("AC-3", "el reembolso ahora es parcial.")
        self.prop.write_text(propuesta(nombra=("AC-3",)), encoding="utf-8")
        r = self.enmendar("--yes")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ya sello la E-1", r.stdout + r.stderr)

    def test_segunda_enmienda_es_e2_y_mide_contra_la_primera(self):
        self.editar_ac("AC-2", "el reintento responde 409.")
        self.prop.write_text(propuesta(), encoding="utf-8")
        self.ok("enmienda", "--feature", "1", "--propuesta", "docs/" + self.prop.name, "--yes")
        self.editar_ac("AC-3", "el reembolso ahora es parcial.")
        self.prop = self.repo / "docs" / "propuesta-1-enmienda-parcial.md"
        self.prop.write_text(propuesta(nombra=("AC-3",), titulo="reembolso parcial"),
                             encoding="utf-8")
        r = self.enmendar("--yes")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        e = self.feature()["enmiendas"]
        self.assertEqual([x["id"] for x in e], ["E-1", "E-2"])
        self.assertEqual(e[1]["acs"]["cambiados"], ["AC-3"], "midio contra el sello original")
        spec = self.spec.read_text(encoding="utf-8")
        self.assertEqual(spec.count("## Enmiendas posteriores a la aprobacion"), 1)
        self.assertLess(spec.index("### E-1:"), spec.index("### E-2: reembolso parcial"))

    def test_sello_anterior_sin_huella_se_registra_como_no_medido(self):
        data = json.loads(self.backlog.read_text(encoding="utf-8"))
        del data["features"][0]["spec_huella"]
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        self.editar_ac("AC-2", "el reintento responde 409.")
        self.prop.write_text(propuesta(), encoding="utf-8")
        r = self.enmendar("--yes")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("no puedo acotar", r.stdout)
        self.assertIsNone(self.feature()["enmiendas"][0]["acs"])
        self.assertIn("AC tocados: no medidos", self.spec.read_text(encoding="utf-8"))

    def test_sin_huella_la_firma_sigue_frenando_un_spec_sin_cambios(self):
        # Sin huella no hay comparacion por AC: la unica defensa es la firma.
        data = json.loads(self.backlog.read_text(encoding="utf-8"))
        del data["features"][0]["spec_huella"]
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        self.prop.write_text(propuesta(), encoding="utf-8")
        r = self.enmendar("--yes")
        self.assertNotEqual(r.returncode, 0, "sello una enmienda sin cambio alguno")
        self.assertNotIn("enmiendas", self.feature())

    def test_check_avisa_si_la_propuesta_cambia_despues_del_sello(self):
        self.editar_ac("AC-2", "el reintento responde 409.")
        self.prop.write_text(propuesta(), encoding="utf-8")
        self.ok("enmienda", "--feature", "1", "--propuesta", "docs/" + self.prop.name, "--yes")
        self.prop.write_text(self.prop.read_text(encoding="utf-8") + "\nOtra cosa.\n",
                             encoding="utf-8")
        r = self.gate("check")
        self.assertIn("la propuesta de la E-1 falta o cambio", r.stdout)


class SinAprobarTests(Proyecto):
    def test_un_spec_nunca_aprobado_se_aprueba_no_se_enmienda(self):
        self.prop.write_text(propuesta(), encoding="utf-8")
        r = self.enmendar("--yes")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("approve-spec", r.stdout + r.stderr)

    def test_re_aprobar_sin_trabajo_encima_sigue_siendo_approve_spec(self):
        self.ok("approve-spec", "--feature", "1", "--yes")
        self.editar_ac("AC-2", "el reintento responde 409.")
        self.ok("approve-spec", "--feature", "1", "--yes")


class NumeracionTests(Proyecto):
    # Enmiendas escritas a mano antes de que existiera el comando (como en ADR).
    spec_inicial = (SPEC + "\n## Enmiendas posteriores a la aprobacion\n\n"
                    "### E-2 (AC-1): manual\n\nAprobada por Alan.\n\n## Anexo\n\nx\n")

    def test_sigue_la_numeracion_y_entra_en_la_seccion_existente(self):
        self.ok("approve-spec", "--feature", "1", "--yes")
        self.editar_ac("AC-2", "el reintento responde 409.")
        self.prop.write_text(propuesta(), encoding="utf-8")
        r = self.enmendar("--yes")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        spec = self.spec.read_text(encoding="utf-8")
        self.assertEqual(spec.count("## Enmiendas posteriores a la aprobacion"), 1)
        self.assertIn("### E-3: el reintento responde 409", spec, "piso la E-2 escrita a mano")
        self.assertLess(spec.index("### E-2 (AC-1): manual"), spec.index("### E-3:"))
        self.assertLess(spec.index("### E-3:"), spec.index("## Anexo"))


class CierreTrasEnmiendaTests(unittest.TestCase):
    """close no acepta un review ni un verify sellados sobre el spec anterior."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / "repo"
        self.repo.mkdir()
        for args in (("init", "-q", "-b", "develop", "."),
                     ("config", "user.email", "t@t.invalid"), ("config", "user.name", "T")):
            sh("git", *args, cwd=self.repo)
        (self.repo / "harness").mkdir()
        (self.repo / "docs").mkdir()
        self.backlog = self.repo / "harness" / "feature_list.json"
        self.backlog.write_text(json.dumps({"project": "t", "features": [
            {"id": "1", "name": "cobro", "status": "in_progress", "branch": "feat-1"}]}),
            encoding="utf-8")
        self.spec = self.repo / "docs" / "spec-feature-1-cobro.md"
        self.spec.write_text(SPEC, encoding="utf-8")
        self.commit("init")
        sh("git", "checkout", "-q", "-b", "feat-1", cwd=self.repo)
        (self.repo / "cobro.txt").write_text("cobro\n", encoding="utf-8")
        self.commit("feat: cobro")
        sh("git", "checkout", "-q", "develop", cwd=self.repo)

        self.ok("approve-spec", "--feature", "1", "--yes")
        self.ok("verify", "--feature", "1")
        (self.repo / "docs" / "impl-1.md").write_text(CITAS, encoding="utf-8")
        self.review = self.repo / "docs" / "review-1.md"
        self.review.write_text("# Review\n\n" + CITAS, encoding="utf-8")
        self.ok("revision", "--feature", "1", "--veredicto", "approved")

        texto = self.spec.read_text(encoding="utf-8")
        self.spec.write_text(texto.replace("entonces no cobra dos veces.",
                                           "entonces responde 409 y no cobra."), encoding="utf-8")
        prop = self.repo / "docs" / "propuesta-1-enmienda-reintento.md"
        prop.write_text(propuesta(), encoding="utf-8")
        r = self.ok("enmienda", "--feature", "1", "--propuesta", "docs/" + prop.name, "--yes")
        self.assertIn("close ya no lo acepta", r.stdout)
        self.assertIn("vuelve a correr", r.stdout)
        self.commit("docs: enmienda E-1")

    def commit(self, msg):
        sh("git", "add", "-A", cwd=self.repo)
        sh("git", "commit", "-qm", msg, cwd=self.repo)

    def gate(self, *args):
        return harness("gate.py", *args, cwd=self.repo)

    def ok(self, *args):
        r = self.gate(*args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def close(self):
        return self.gate("close", "--feature", "1", "--status", "done", "--to", "develop",
                         "--leccion", "ninguna", "--leccion-motivo", "fixture")

    def estado(self):
        return json.loads(self.backlog.read_text(encoding="utf-8"))["features"][0]["status"]

    def test_close_rechaza_el_review_y_el_verify_del_spec_anterior(self):
        r = self.close()
        self.assertNotEqual(r.returncode, 0, "cerro con veredictos sobre el spec anterior")
        self.assertIn("el review se sello antes de la enmienda E-1", r.stdout)
        self.assertIn("verify anterior a la enmienda E-1", r.stdout)
        self.assertEqual(self.estado(), "in_progress")
        self.assertIn("review approved (anterior a E-1)",
                      harness("estado.py", cwd=self.repo).stdout)
        check = self.gate("check").stdout
        self.assertIn("el review (approved) se sello antes de la enmienda E-1", check)
        self.assertNotIn("review approved y sellado", check)

    def test_re_sellar_el_mismo_review_se_niega(self):
        r = self.gate("revision", "--feature", "1", "--veredicto", "approved")
        self.assertNotEqual(r.returncode, 0, "le puso fecha nueva a un veredicto viejo")
        self.assertIn("no cambio desde que se sello", r.stdout + r.stderr)

    def test_review_y_verify_nuevos_destraban_el_cierre(self):
        self.review.write_text("# Review sobre el spec enmendado (E-1)\n\n" + CITAS,
                               encoding="utf-8")
        self.ok("revision", "--feature", "1", "--veredicto", "approved")
        self.ok("verify", "--feature", "1")
        self.commit("docs: re-review y verify")
        r = self.close()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.estado(), "done")


if __name__ == "__main__":
    unittest.main()
