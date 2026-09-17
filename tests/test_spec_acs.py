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

from comun import ac_comandos, spec_acs  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
