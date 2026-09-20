"""Una cita es `archivo.ext:linea`, no cualquier cosa con dos puntos y un numero.

Bug: `CITA_RE = r"[\\w./\\\\-]+\\.\\w+:\\d+"` casaba dentro de una URL
(`https://jira.empresa.com:8080/browse/ABC-1` -> `//jira.empresa.com:8080`) y
dentro de una version (`1.2:34`). Un review cuyas filas citaran el ticket de
Jira pasaba `cubre_acs`, o sea `gate.py revision` y `gate.py close`: el falso
verde exacto que este gate existe para impedir, y con atlassian.py en el flujo
pegar URLs de Jira en las actas es lo natural.

Dos defensas: se borran las URL antes de buscar, y la extension tiene que
empezar por letra.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from comun import cubre_acs, hay_cita  # noqa: E402


class CitaRealTests(unittest.TestCase):
    def test_la_url_del_ticket_no_es_una_cita(self):
        rev = "| AC-1 | ok | ver https://jira.empresa.com:8080/browse/ABC-1 |\n"
        _, faltan = cubre_acs(rev, ["AC-1"])
        self.assertEqual(faltan, ["AC-1"], "una URL de Jira no prueba nada del codigo")

    def test_una_version_no_es_una_cita(self):
        rev = "| AC-1 | ok | validado con la version 1.2:34 |\n"
        _, faltan = cubre_acs(rev, ["AC-1"])
        self.assertEqual(faltan, ["AC-1"])

    def test_urls_sin_esquema_conocido_tampoco(self):
        for falsa in ("ftp://host.io:21/x", "git+ssh://repo.dev:22/a",
                      "http://localhost.dev:3000/app"):
            with self.subTest(falsa=falsa):
                _, faltan = cubre_acs(f"## AC-1\n{falsa}\n", ["AC-1"])
                self.assertEqual(faltan, ["AC-1"], f"{falsa} no es archivo:linea")

    def test_la_cita_de_verdad_sigue_valiendo(self):
        for buena in ("src/a.ts:1", "(src/a.ts:42)", "scripts/comun.py:191",
                      "projects/app/src/main.ts:120", "a.go:7",
                      "docs/spec-feature-9.md:14"):
            with self.subTest(buena=buena):
                cub, _ = cubre_acs(f"## AC-1\n{buena}\n", ["AC-1"])
                self.assertEqual(cub, ["AC-1"], f"{buena} si es una cita")

    def test_una_cita_real_en_la_misma_linea_que_una_url_vale(self):
        # Borrar la URL no puede llevarse por delante la cita que si esta.
        rev = "| AC-1 | ok | src/pago.ts:88 (ticket https://jira.io:8080/X-1) |\n"
        cub, _ = cubre_acs(rev, ["AC-1"])
        self.assertEqual(cub, ["AC-1"])

    def test_la_url_sin_esquema_tampoco_es_una_cita(self):
        """URL_RE solo neutraliza lo que lleva '://'.

        Pegado sin esquema -- como lo pega cualquiera -- 'host.dominio:puerto'
        tiene la forma '.ext:numero' y pasaba igual: el mismo contenido
        bloqueaba con 'https://' delante y pasaba sin el.
        """
        for falsa in ("jira.empresa.com:8080/browse/ABC-1",
                      "confluence.io:443/wiki/x", "pagos.svc:8443",
                      "www.ejemplo.com:443", "registry.empresa.com:5000/pago"):
            with self.subTest(falsa=falsa):
                _, faltan = cubre_acs(f"## AC-1\n{falsa}\n", ["AC-1"])
                self.assertEqual(faltan, ["AC-1"], f"{falsa} no es archivo:linea")

    def test_un_archivo_con_esa_extension_dentro_de_una_ruta_si_vale(self):
        # El sufijo de red solo descalifica al token pelado: 'src/schema.io:12'
        # es un archivo de verdad y no puede volverse falso rojo.
        for buena in ("src/schema.io:12", "packages/core.dev:7"):
            with self.subTest(buena=buena):
                cub, _ = cubre_acs(f"## AC-1\n{buena}\n", ["AC-1"])
                self.assertEqual(cub, ["AC-1"])

    def test_un_dotfile_tambien_se_puede_citar(self):
        # .env esta en rutas_protegidas: citarlo es lo natural al justificar
        # un AC sobre configuracion. El regex exigia un caracter antes del
        # punto de la extension y lo dejaba fuera.
        for buena in ("src/.env:3", ".env:12", "config/.eslintrc.json:4",
                      "infra/stack.cloudformation:12"):
            with self.subTest(buena=buena):
                self.assertTrue(hay_cita(buena), f"{buena} es una cita legitima")

    def test_la_cita_pegada_a_una_URL_no_se_borra_con_ella(self):
        """Borrar la URL no puede llevarse por delante la cita que si esta.

        Con `\\S+` la URL se comia todo lo que viniera sin espacio detras
        -- markdown `[ABC-1](url)<br>src/pago.ts:88`, o una tabla sin espacios
        alrededor de los pipes -- y el gate bloqueaba un review correcto.
        """
        casos = [
            "| AC-1 | ok | [ABC-1](https://jira.io/browse/ABC-1)<br>src/pago.ts:88 |",
            "|AC-1|https://jira.io/ABC-1|src/pago.ts:88|",
            "AC-1: ver <https://jira.io/ABC-1>src/pago.ts:88",
            "- AC-1: (https://jira.io/ABC-1)src/pago.ts:88",
        ]
        for linea in casos:
            with self.subTest(linea=linea):
                self.assertTrue(hay_cita(linea), "se perdio la cita real")

    def test_hay_cita_no_revienta_con_entrada_vacia(self):
        for vacio in ("", None):
            self.assertFalse(hay_cita(vacio))


if __name__ == "__main__":
    unittest.main()
