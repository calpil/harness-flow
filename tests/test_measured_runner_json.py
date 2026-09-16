"""Contrato del runner Go JSON; las muestras son fixtures, no corridas Go."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import postmerge_medido as postmerge


def eventos(paquete="example.com/pkg", tests=None):
    tests = tests if tests is not None else {"TestReal": "pass"}
    out = [{"Action": "start", "Package": paquete}]
    for nombre, estado in tests.items():
        out += [{"Action": "run", "Package": paquete, "Test": nombre},
                {"Action": estado, "Package": paquete, "Test": nombre}]
    out.append({"Action": "fail" if "fail" in tests.values() else "pass",
                "Package": paquete})
    return out


class EventosTests(unittest.TestCase):
    def correr(self, lista, rc=0, stderr=""):
        out = "".join(json.dumps(e) + "\n" for e in lista)
        result = subprocess.CompletedProcess("fixture", rc, out, stderr)
        # Se prueba el parser puro, no se presenta el fixture como una medicion.
        with contextlib.redirect_stdout(io.StringIO()):
            return postmerge.parsear_eventos(result)

    def test_json_valido_conserva_identidad_y_resultado(self):
        try:
            resultados, paquetes = self.correr(eventos())
        except SystemExit as error:
            self.fail(f"Go JSON valido fue rechazado: {error}")
        self.assertEqual(resultados, {("example.com/pkg", "TestReal"): "pass"})
        self.assertEqual(paquetes, {"example.com/pkg": "pass"})

    def test_solo_acepta_mediciones_completas_y_exit_coherente(self):
        sanos = eventos()
        rojos = eventos(tests={"TestReal": "fail"})
        casos = [
            ("exit23", sanos, 23),
            ("exit1_sin_fallos", sanos, 1),
            ("exit0_oculta_fallo", rojos, 0),
            ("build_roto", sanos + [{"Action": "build-fail", "ImportPath": "otro"}], 1),
            ("build_roto_entre_rojos", rojos + [{"Action": "build-fail", "ImportPath": "otro"}], 1),
            ("paquete_roto_sin_test_rojo", sanos + [
                {"Action": "start", "Package": "otro"},
                {"Action": "fail", "Package": "otro"}], 1),
            ("paquete_incompleto", sanos[:-1], 0),
            ("test_incompleto", sanos[:-1] + [
                {"Action": "run", "Package": "example.com/pkg", "Test": "TestOtro"}, sanos[-1]], 0),
            ("skip_total", eventos(tests={"TestReal": "skip"}), 0),
            ("sin_tests", eventos(tests={}), 0),
            ("vacio", [], 0),
            ("tipo_incorrecto", [[]], 0),
            ("test_sin_run", [sanos[0], *sanos[2:]], 0),
            ("sin_package_start", sanos[1:], 0),
            ("paquete_sin_identidad", [{"Action": "start", "Package": None}, *sanos], 0),
            ("test_sin_identidad", [sanos[0], {"Action": "run", "Package": "example.com/pkg", "Test": None}, *sanos[1:]], 0),
            ("accion_desconocida", sanos + [{"Action": "desconocida", "Package": "example.com/pkg"}], 0),
            ("final_duplicado", [*sanos[:-1], sanos[-2], sanos[-1]], 0),
            ("paquete_duplicado", sanos + sanos, 0),
            ("paquete_contradice_test", [*rojos[:-1], sanos[-1]], 1),
        ]
        for nombre, lista, rc in casos:
            with self.subTest(nombre=nombre):
                with self.assertRaises(SystemExit) as error:
                    self.correr(lista, rc)
                self.assertEqual(error.exception.code, 2)

    def test_no_interpreta_el_texto_del_test_como_estado(self):
        lista = eventos(tests={"TestReal": "fail"})
        lista.insert(2, {"Action": "output", "Package": "example.com/pkg",
                         "Test": "TestReal", "Output": "build failed; no tests to run\n"})
        resultados, _ = self.correr(lista, 1)
        self.assertEqual(resultados, {("example.com/pkg", "TestReal"): "fail"})

    def test_no_acepta_eventos_de_stderr_como_evidencia(self):
        with self.assertRaises(SystemExit) as error:
            self.correr([], stderr="\n".join(json.dumps(e) for e in eventos()))
        self.assertEqual(error.exception.code, 2)


    def test_error_de_proceso_o_codificacion_es_no_medicion(self):
        for fallo in (OSError("fixture"), UnicodeDecodeError("utf-8", b"\xff", 0, 1, "fixture")):
            with self.subTest(fallo=type(fallo).__name__):
                with mock.patch.object(postmerge.subprocess, "run", side_effect=fallo), \
                        contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as error:
                    postmerge.correr("/fixture", "fixture")
                self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
