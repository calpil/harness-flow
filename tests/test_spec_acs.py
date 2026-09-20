"""spec_acs: reconocer los AC aunque el titulo lleve un parentesis.

Caso real: docs/spec-feature-9-admin-pedidos.md declara catorce AC con la
forma "- AC-1 (cola por estado): ..." y el gate los contaba como cero, de
modo que una feature con sus AC escritos quedaba bloqueada por "no declara
ningun AC-n". El parentesis describe el AC; no cambia que el AC exista.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from comun import (acs_faltantes, acs_no_reconocidos, ac_comandos,  # noqa: E402
                   spec_ac_lineas, spec_acs)


class SpecAcsTests(unittest.TestCase):
    def test_ac_con_titulo_entre_parentesis(self):
        texto = (
            "- AC-1 (cola por estado): Given pedidos, When se abre, Then se listan.\n"
            "- AC-2 (detalle del pedido): Given un pedido, Then se ve el detalle.\n"
        )
        self.assertEqual(spec_acs(texto), ["AC-1", "AC-2"])

    def test_formato_simple_sigue_valido(self):
        texto = "- AC-1: el padron acepta limit y offset\n- AC-2: el total es global\n"
        self.assertEqual(spec_acs(texto), ["AC-1", "AC-2"])

    def test_sin_duplicados_y_en_orden(self):
        texto = "- AC-2 (b): x\n- AC-1 (a): y\n- AC-2 (b otra vez): z\n"
        self.assertEqual(spec_acs(texto), ["AC-2", "AC-1"])

    def test_no_confunde_texto_que_solo_menciona_un_ac(self):
        # Una mencion en prosa no declara el AC: sin ':' tras el id no hay AC.
        texto = "El AC-9 quedo pendiente y se explica mas abajo.\n"
        self.assertEqual(spec_acs(texto), [])

    def test_parentesis_no_se_come_el_resto_del_documento(self):
        # El titulo entre parentesis es de UNA linea: no puede saltar lineas.
        texto = "- AC-1 (sin cerrar\n- AC-2: este si declara\n"
        self.assertEqual(spec_acs(texto), ["AC-2"])

    def test_el_titulo_no_devora_hasta_un_parentesis_lejano(self):
        # Un titulo con parentesis anidado en la prosa no parte el AC en dos.
        texto = "- AC-1 (cola): pedidos (ver anexo) y mas: detalle\n"
        self.assertEqual(spec_acs(texto), ["AC-1"])
        # Y la linea sin parentesis de cierre no puede declarar nada.
        self.assertEqual(spec_acs("- AC-3 (abierto: texto sin cierre\n"), [])

    def test_comando_bajo_un_ac_con_parentesis(self):
        texto = (
            "- AC-1 (cola por estado): Given pedidos, Then se listan.\n"
            "  `verificar: go test ./cola/`\n"
        )
        self.assertEqual(spec_acs(texto), ["AC-1"])
        self.assertEqual(ac_comandos(texto), {"AC-1": "go test ./cola/"})


class ParentesisAnidadoTests(unittest.TestCase):
    """Un AC que el parser no ve es un AC que NADIE verifica, en verde.

    "- AC-1 (cobro (auth + capture)): ..." no casaba con `\\([^()\\n]*\\)`:
    spec_acs devolvia solo ['AC-2'], approve-spec sellaba "AC: AC-2", el review
    solo respondia por AC-2 y `gate.py check` salia "[ok] check limpio".
    """

    def test_titulo_con_parentesis_anidado_declara_el_ac(self):
        texto = "- AC-1 (cobro (auth + capture)): dado x.\n- AC-2: dado z.\n"
        self.assertEqual(spec_acs(texto), ["AC-1", "AC-2"])
        self.assertIn("auth + capture", spec_ac_lineas(texto)["AC-1"])

    def test_sigue_sin_cruzar_lineas(self):
        # El titulo es de UNA linea: un parentesis sin cerrar no declara nada
        # ni se come el documento.
        self.assertEqual(spec_acs("- AC-1 (abierto (sin cerrar\n- AC-2: si\n"), ["AC-2"])

    def test_el_hueco_en_la_numeracion_se_detecta(self):
        # El sintoma tipico de un AC que el parser se comio.
        self.assertEqual(acs_faltantes(["AC-2", "AC-4"]), ["AC-1", "AC-3"])
        self.assertEqual(acs_faltantes(["AC-1", "AC-2", "AC-3"]), [])
        self.assertEqual(acs_faltantes([]), [])


class AcQueElParserNoVeTests(unittest.TestCase):
    """Un AC mal escrito desaparece del flujo entero y el check sale verde.

    El hueco en la numeracion no alcanza como senal: si el AC que el parser se
    comio es el de numero MAS ALTO, no hay hueco que detectar. Se compara contra
    la gramatica laxa de declara_ac, que si reconoce la linea como declaracion.
    """

    def test_detecta_el_ac_mal_escrito_aunque_sea_el_ultimo(self):
        spec = ("- AC-1: bien\n- AC-2: bien\n"
                "- AC-3 (cobro (auth)) sin dos puntos, mal escrito\n")
        self.assertEqual(spec_acs(spec), ["AC-1", "AC-2"])
        self.assertEqual(acs_faltantes(spec_acs(spec)), [], "no hay hueco que ver")
        self.assertEqual(acs_no_reconocidos(spec), ["AC-3"], "y aun asi hay que verlo")

    def test_no_marca_los_ac_bien_escritos(self):
        spec = "- AC-1: bien\n- AC-2 (titulo): tambien\n## AC-3: y este\n"
        self.assertEqual(acs_no_reconocidos(spec), [],
                         "solo los que el parser NO reconoce")

    def test_el_spec_admite_el_mismo_adorno_que_la_evidencia(self):
        """Una sola gramatica: lo que declara_ac reconoce, spec_acs lo declara.

        Eran dos: '## AC-3: ...' abria seccion para la evidencia pero NO
        declaraba el AC en el spec, asi que ese criterio desaparecia del flujo
        entero -- sellado, review, PRD -- con el check en verde.
        """
        for linea in ("## AC-1: encabezado", "| AC-1: en tabla |",
                      "1. AC-1: numerada", "**AC-1**: enfasis",
                      "> AC-1: citada", "* AC-1: bullet", "- AC-1: guion"):
            with self.subTest(linea=linea):
                self.assertEqual(spec_acs(linea), ["AC-1"], f"no declaro {linea!r}")
                self.assertEqual(acs_no_reconocidos(linea), [])

    def test_el_titulo_admite_varios_grupos_y_corchetes(self):
        for linea in ("- AC-1 (UI) (opcional): x", "- AC-1 [export CSV]: x",
                      "- AC-1 (cobro (auth + capture)): x"):
            with self.subTest(linea=linea):
                self.assertEqual(spec_acs(linea), ["AC-1"])

    def test_lo_que_el_parser_no_entiende_se_denuncia(self):
        # Tres niveles, parentesis sin cerrar o de mas: no se declara el AC,
        # pero NO puede pasar en silencio.
        for linea in ("- AC-3 (cobro (Visa (credito))): x", "- AC-3 (cobro: x",
                      "- AC-3 (cobro)): x"):
            with self.subTest(linea=linea):
                self.assertEqual(spec_acs(linea), [])
                self.assertEqual(acs_no_reconocidos(linea), ["AC-3"])

    def test_el_titulo_no_puede_devorar_una_prosa_con_dos_puntos(self):
        # El titulo son grupos delimitados, no "cualquier cosa antes del :".
        self.assertEqual(spec_acs("El AC-9 se pospuso porque: faltaba el back."), [])

    def test_una_mencion_en_prosa_sigue_sin_declarar(self):
        self.assertEqual(spec_acs("El AC-9 quedo pendiente y se explica abajo."), [])

    def test_el_ac_no_puede_partirse_en_dos_lineas(self):
        # El 'AC-9' suelto y los dos puntos en la linea siguiente no declaran
        # nada, pero si se avisa de que esa linea parece un AC.
        spec = "- AC-9\n  : texto\n"
        self.assertEqual(spec_acs(spec), [])
        self.assertEqual(acs_no_reconocidos(spec), ["AC-9"])


class UnSoloParserTests(unittest.TestCase):
    """documentacion.py y el brief tenian su propio regex de AC.

    El del PRD exigia `AC-n:` pegado: un spec con "- AC-1 (cola por estado): ..."
    salia en el PRD con menos AC de los que tiene, o directamente como
    "sin AC en spec". El del brief casaba con startswith, de modo que 'AC-1'
    enganchaba la linea de 'AC-10'.
    """

    TEXTO = ("- AC-10 (padron): Given lista, Then pagina.\n"
             "- AC-1 (cola por estado): Given pedidos, Then se listan.\n"
             "* AC-2: Given un pedido, Then se ve el detalle.\n")

    def test_devuelve_la_linea_de_cada_ac_sin_adorno(self):
        lineas = spec_ac_lineas(self.TEXTO)
        self.assertEqual(list(lineas), ["AC-10", "AC-1", "AC-2"])
        self.assertTrue(lineas["AC-1"].startswith("AC-1 (cola por estado):"))
        self.assertTrue(lineas["AC-2"].startswith("AC-2:"))

    def test_ac_1_no_se_queda_con_la_linea_de_ac_10(self):
        # AC-10 aparece ANTES: con startswith, AC-1 heredaba su texto.
        self.assertIn("cola por estado", spec_ac_lineas(self.TEXTO)["AC-1"])

    def test_una_linea_en_blanco_antes_del_ac_no_roba_la_linea(self):
        """AC_RE arranca con ^\\s* y \\s casa el salto de linea.

        Tomando m.start() el match podia empezar en la linea ANTERIOR (vacia)
        y el consumidor recibia "" en vez del texto del AC: el PRD listaba un
        criterio vacio. Se ancla al id, que no miente.
        """
        texto = "## Criterios\n\n- AC-1: conserva historial\n\n- AC-2: y el resto\n"
        lineas = spec_ac_lineas(texto)
        self.assertEqual(lineas["AC-1"], "AC-1: conserva historial")
        self.assertEqual(lineas["AC-2"], "AC-2: y el resto")
        self.assertTrue(all(v.strip() for v in lineas.values()), "ninguna linea vacia")

    def test_el_prd_ve_los_mismos_ac_que_el_gate(self):
        import tempfile
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        import documentacion
        spec = Path(tempfile.mkdtemp()) / "spec.md"
        spec.write_text(self.TEXTO, encoding="utf-8")
        del_prd = documentacion._acs_desde_spec(spec)
        self.assertEqual(len(del_prd), len(spec_acs(self.TEXTO)),
                         "el PRD listaba menos AC que el spec")
        self.assertTrue(any("cola por estado" in x for x in del_prd))


if __name__ == "__main__":
    unittest.main()
