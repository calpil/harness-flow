"""Un hallazgo del codigo no abre una ficha.

Caso medido (ADR, 2026-11-12): en cuatro horas y media el agente dio de alta 16
fichas desde hallazgos de specs y reviews: una constante repetida, un tipo sin
un valor, un test lento, los "cortes" de una feature sin arrancar. Pregunto por
formulario, pero cada pregunta ofrecia solo "ficha aparte" y la recomendaba.
Cada ficha paga spec, lista de tests, review, verify y cierre. El usuario
retiro siete a mano: eran enmiendas de features abiertas.

Lo que fallaba en el arnes:
  1. nada decia que hacer con un hallazgo: enmienda, AC o ficha;
  2. no habia donde dejar un hallazgo que no fuera una ficha;
  3. add.py creaba la ficha sin pedir el SI ni el motivo: era el unico ritual sin --yes.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

PRD = """# PRD - demo

Estado: approved

## Features candidatas

- F-1: Cobro idempotente: un reintento no crea un segundo pedido (cumple O1)
"""

SPEC = ("# Spec - Feature #{id}: demo\n\nEstado: {estado}\n\n"
        "## Criterios de aceptacion\n\n- AC-1: dado un carro, cuando pago, entonces cobra.\n")

PESO = "comportamiento nuevo que pidio el usuario"

SIN_GATES = {"require_spec_approved": False, "require_review": False, "require_leccion": False,
             "require_verify_green": False, "require_docs_al_dia": False}


class Base(unittest.TestCase):
    features: list[dict] = []

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="hallazgos-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        (self.root / "harness" / "progress").mkdir(parents=True)
        (self.root / "docs" / "prd").mkdir(parents=True)
        self.backlog = self.root / "harness" / "feature_list.json"
        self.backlog.write_text(json.dumps({"project": "demo", "rules": dict(SIN_GATES),
                                            "features": [dict(f) for f in self.features]}),
                                encoding="utf-8")
        self.env = dict(os.environ, HARNESS_SIN_CONTEXTO="1", HARNESS_SIN_HUB="1",
                        PYTHONDONTWRITEBYTECODE="1")

    def cli(self, script, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=self.root,
                              env=self.env, capture_output=True, text=True, timeout=120)

    def ok(self, script, *args):
        r = self.cli(script, *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout + r.stderr

    def falla(self, script, *args):
        r = self.cli(script, *args)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        return r.stdout + r.stderr

    def datos(self):
        return json.loads(self.backlog.read_text(encoding="utf-8"))

    def hallazgos(self):
        return self.datos().get("hallazgos", [])

    def spec(self, fid, slug, estado="draft"):
        path = self.root / "docs" / f"spec-feature-{fid}-{slug}.md"
        path.write_text(SPEC.format(id=fid, estado=estado), encoding="utf-8")
        return path


class AltaDeFichasTests(Base):
    features = [
        {"id": 1, "name": "modulo cuentas", "status": "todo", "microservicios": ["ms-order-service"]},
        {"id": 2, "name": "cobro viejo", "status": "done", "microservicios": ["ms-order-service"]},
        {"id": 3, "name": "catalogo", "status": "in_progress", "microservicios": ["ms-catalog-service"]},
    ]

    def test_una_ficha_que_el_usuario_no_aprobo_no_entra(self):
        for kind in ("feature", "bug", "task"):
            with self.subTest(kind=kind):
                out = self.falla("add.py", "--name", f"una sola constante {kind}", "--kind", kind)
                self.assertIn("requiere --yes", out)
                self.assertEqual(len(self.datos()["features"]), 3)
                self.assertEqual(list((self.root / "docs").glob("spec-feature-4-*")), [])

    def test_la_negativa_dice_a_donde_va_un_hallazgo(self):
        out = self.falla("add.py", "--name", "una sola constante", "--kind", "task")
        self.assertIn("enmienda", out)
        self.assertIn("hallazgo.py", out)
        self.assertIn("anotar", out)

    def test_la_negativa_nombra_las_features_abiertas_del_mismo_repo(self):
        out = self.falla("add.py", "--name", "personas fusionadas", "--microservicio", "ms-order-service")
        self.assertIn("#1 [todo] modulo cuentas", out)
        self.assertNotIn("cobro viejo", out)      # cerrada: no recibe trabajo
        self.assertNotIn("catalogo", out)         # otro repo

    def test_la_negativa_nombra_la_feature_de_la_que_depende(self):
        out = self.falla("add.py", "--name", "corte dos del catalogo", "--requiere", "3")
        self.assertIn("#3 [in_progress] catalogo", out)
        self.assertNotIn("modulo cuentas", out)

    def test_la_feature_de_la_que_depende_va_primero(self):
        out = self.falla("add.py", "--name", "corte dos", "--requiere", "3",
                         "--microservicio", "ms-order-service")
        self.assertLess(out.index("#3 [in_progress] catalogo"), out.index("#1 [todo] modulo cuentas"))

    def test_sin_repo_ni_dependencia_nombra_todas_las_abiertas(self):
        out = self.falla("add.py", "--name", "algo suelto")
        self.assertIn("#1 [todo] modulo cuentas", out)
        self.assertIn("#3 [in_progress] catalogo", out)
        self.assertNotIn("cobro viejo", out)

    def test_la_negativa_pide_ofrecer_la_enmienda_antes_que_la_ficha(self):
        out = self.falla("add.py", "--name", "bug aparte", "--kind", "bug")
        self.assertIn("la primera opcion es el destino sin ficha", out)

    def test_con_el_si_del_usuario_y_el_motivo_la_ficha_entra(self):
        self.ok("add.py", "--name", "exportar el estado de cuenta", "--yes", "--peso", PESO)
        nueva = self.datos()["features"][-1]
        self.assertEqual((nueva["id"], nueva["status"], nueva["peso"]), (4, "todo", PESO))

    def test_el_si_sin_decir_por_que_es_ficha_no_alcanza(self):
        for peso in ((), ("--peso", ""), ("--peso", "porque si"), ("--peso", "una linea\ny otra mas larga")):
            with self.subTest(peso=peso):
                out = self.falla("add.py", "--name", "una sola constante", "--kind", "task", "--yes", *peso)
                self.assertIn("--peso", out)
                self.assertEqual(len(self.datos()["features"]), 3)

    def test_la_primera_ficha_de_una_candidata_del_prd_entra_sin_yes(self):
        (self.root / "docs" / "prd" / "PRD-master.md").write_text(PRD, encoding="utf-8")
        self.ok("add.py", "--name", "Cobro idempotente", "--candidata", "F-1")
        nueva = self.datos()["features"][-1]
        self.assertEqual(nueva["prd_candidata"], "F-1")
        self.assertNotIn("peso", nueva)

    def test_otra_ficha_de_la_misma_candidata_es_partir_y_pide_el_si(self):
        (self.root / "docs" / "prd" / "PRD-master.md").write_text(PRD, encoding="utf-8")
        self.ok("add.py", "--name", "Cobro idempotente", "--candidata", "F-1")
        out = self.falla("add.py", "--name", "Cobro idempotente corte dos", "--candidata", "F-1")
        self.assertIn("requiere --yes", out)
        self.ok("add.py", "--name", "Cobro idempotente corte dos", "--candidata", "F-1", "--yes", "--peso", PESO)

    def test_una_normalizacion_entra_sin_yes_solo_con_el_trinquete_adoptado(self):
        out = self.falla("add.py", "--name", "normalizar pedidos", "--kind", "normalizacion")
        self.assertIn("requiere --yes", out)
        (self.root / "harness" / "arquitectura-base.json").write_text("{}", encoding="utf-8")
        self.ok("add.py", "--name", "normalizar pedidos", "--kind", "normalizacion")

    def test_el_nombre_repetido_se_dice_antes_que_pedir_el_si(self):
        out = self.falla("add.py", "--name", "modulo cuentas")
        self.assertIn("ya existe la feature #1", out)


class AnotarTests(Base):
    features = [
        {"id": 1, "name": "modulo cuentas", "status": "todo", "microservicios": ["ms-order-service"]},
        {"id": 2, "name": "cobro viejo", "status": "done", "microservicios": ["ms-order-service"]},
        {"id": 3, "name": "retirada", "status": "superseded"},
    ]

    def test_un_hallazgo_se_anota_en_una_feature_abierta_sin_crear_ficha(self):
        out = self.ok("hallazgo.py", "anotar", "--feature", "1", "--texto",
                      "contract sin email_normalizado", "--origen", "review de la #179")
        self.assertIn("H-1 anotado en la #1", out)
        h, = self.hallazgos()
        self.assertEqual((h["id"], h["feature"], h["estado"], h["origen"]),
                         ("H-1", 1, "abierto", "review de la #179"))
        self.assertEqual(len(self.datos()["features"]), 3)
        self.assertEqual(list((self.root / "docs").glob("spec-feature-*")), [])

    def test_una_feature_cerrada_no_recibe_hallazgos(self):
        for fid, estado in (("2", "done"), ("3", "superseded")):
            with self.subTest(estado=estado):
                out = self.falla("hallazgo.py", "anotar", "--feature", fid, "--texto", "algo")
                self.assertIn(estado, out)
                self.assertEqual(self.hallazgos(), [])

    def test_una_feature_que_no_existe_no_recibe_hallazgos(self):
        self.falla("hallazgo.py", "anotar", "--feature", "99", "--texto", "algo")
        self.assertEqual(self.hallazgos(), [])

    def test_sin_feature_queda_en_el_proyecto_con_su_repo(self):
        out = self.ok("hallazgo.py", "anotar", "--texto", "el tipo MedioPago no trae banchile",
                      "--microservicio", "ms-order-service")
        self.assertIn("el proyecto", out)
        h, = self.hallazgos()
        self.assertEqual((h["feature"], h["microservicios"]), (None, ["ms-order-service"]))

    def test_el_mismo_hallazgo_no_se_anota_dos_veces(self):
        self.ok("hallazgo.py", "anotar", "--feature", "1", "--texto", "Una sola constante para el medio")
        out = self.falla("hallazgo.py", "anotar", "--texto", "una sola constante, para el medio")
        self.assertIn("H-1", out)
        self.assertEqual(len(self.hallazgos()), 1)

    def test_el_texto_va_en_una_linea_y_no_vacio(self):
        for texto in ("", "   ", "uno\ndos", "x" * 401):
            with self.subTest(texto=texto[:10]):
                self.falla("hallazgo.py", "anotar", "--feature", "1", "--texto", texto)
        self.assertEqual(self.hallazgos(), [])

    def test_los_ids_no_se_reusan_al_resolver(self):
        self.ok("hallazgo.py", "anotar", "--feature", "1", "--texto", "uno")
        self.ok("hallazgo.py", "resolver", "--id", "H-1", "--como", "AC-2")
        self.ok("hallazgo.py", "anotar", "--feature", "1", "--texto", "dos")
        self.assertEqual([h["id"] for h in self.hallazgos()], ["H-1", "H-2"])

    def test_resolver_dice_donde_quedo_y_no_se_resuelve_dos_veces(self):
        self.ok("hallazgo.py", "anotar", "--feature", "1", "--texto", "uno")
        self.falla("hallazgo.py", "resolver", "--id", "H-1", "--como", "  ")
        self.ok("hallazgo.py", "resolver", "--id", "h-1", "--como", "E-1 de la #1")
        h, = self.hallazgos()
        self.assertEqual((h["estado"], h["como"]), ("resuelto", "E-1 de la #1"))
        self.falla("hallazgo.py", "resolver", "--id", "H-1", "--como", "otra vez")
        self.falla("hallazgo.py", "resolver", "--id", "H-9", "--como", "no existe")

    def test_mover_solo_a_una_feature_abierta_o_al_proyecto(self):
        self.ok("hallazgo.py", "anotar", "--texto", "uno")
        self.falla("hallazgo.py", "mover", "--id", "H-1", "--feature", "2")
        self.assertIsNone(self.hallazgos()[0]["feature"])
        self.ok("hallazgo.py", "mover", "--id", "H-1", "--feature", "1")
        self.assertEqual(self.hallazgos()[0]["feature"], 1)
        self.ok("hallazgo.py", "mover", "--id", "H-1", "--sin-feature")
        self.assertIsNone(self.hallazgos()[0]["feature"])

    def test_list_muestra_los_abiertos_por_feature(self):
        self.ok("hallazgo.py", "anotar", "--feature", "1", "--texto", "uno")
        self.ok("hallazgo.py", "anotar", "--texto", "dos")
        self.ok("hallazgo.py", "anotar", "--feature", "1", "--texto", "tres")
        self.ok("hallazgo.py", "resolver", "--id", "H-3", "--como", "descartado: no aplica")
        out = self.ok("hallazgo.py", "list")
        self.assertIn("#1 modulo cuentas", out)
        self.assertIn("sin feature", out)
        self.assertNotIn("tres", out)
        self.assertIn("descartado: no aplica", self.ok("hallazgo.py", "list", "--todos"))
        self.assertNotIn("dos", self.ok("hallazgo.py", "list", "--feature", "1"))

    def test_la_bitacora_guarda_el_hallazgo(self):
        self.ok("hallazgo.py", "anotar", "--feature", "1", "--texto", "uno")
        historia = (self.root / "harness" / "progress" / "history.md").read_text(encoding="utf-8")
        self.assertIn("hallazgo H-1 anotado en la #1", historia)


class NadieLosPierdeTests(Base):
    features = [
        {"id": 1, "name": "modulo cuentas", "status": "in_progress", "branch": "feature/1",
         "microservicios": ["ms-order-service"]},
        {"id": 2, "name": "catalogo", "status": "todo", "microservicios": ["ms-catalog-service"]},
    ]

    def setUp(self):
        super().setUp()
        self.spec(1, "modulo-cuentas", "approved")
        self.spec(2, "catalogo")
        (self.root / "docs" / "impl-1.md").write_text("## AC-1\nsrc/a.go:1\n", encoding="utf-8")
        self.ok("hallazgo.py", "anotar", "--feature", "1", "--texto", "contract sin cliente_sub")
        self.ok("hallazgo.py", "anotar", "--texto", "constante repetida en order",
                "--microservicio", "ms-order-service")
        self.ok("hallazgo.py", "anotar", "--texto", "indice que falta en catalog",
                "--microservicio", "ms-catalog-service")
        self.ok("hallazgo.py", "anotar", "--texto", "nota sin repo declarado")

    def test_el_brief_muestra_los_de_la_feature_y_los_del_proyecto_que_tocan_sus_repos(self):
        out = self.ok("contexto.py", "brief", "--feature", "1")
        self.assertIn("HALLAZGOS ANOTADOS EN ESTA FEATURE (1 abiertos)", out)
        self.assertIn("H-1 contract sin cliente_sub", out)
        self.assertIn("H-2 [ms-order-service] constante repetida en order", out)
        self.assertIn("H-4 nota sin repo declarado", out)
        self.assertNotIn("indice que falta en catalog", out)
        self.assertIn("hallazgo.py resolver --id", out)
        self.assertIn("hallazgo.py mover --id", out)

    def test_el_brief_dice_enmienda_solo_cuando_el_spec_ya_esta_sellado(self):
        self.assertIn("spec sin sellar", self.ok("contexto.py", "brief", "--feature", "1"))
        data = self.datos()
        data["features"][0]["last_spec_sig"] = {"size": 1, "hash": "x"}
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        out = self.ok("contexto.py", "brief", "--feature", "1")
        self.assertIn("enmienda", out)
        self.assertNotIn("spec sin sellar", out)

    def test_el_brief_no_muestra_un_hallazgo_resuelto(self):
        self.ok("hallazgo.py", "resolver", "--id", "H-1", "--como", "AC-2")
        out = self.ok("contexto.py", "brief", "--feature", "1")
        self.assertNotIn("HALLAZGOS ANOTADOS EN ESTA FEATURE", out)
        self.assertNotIn("contract sin cliente_sub", out)

    def test_el_revisor_no_los_recibe(self):
        import argparse
        import contextlib
        import io
        sys.path.insert(0, str(SCRIPTS))
        import contexto
        previo = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(lambda: os.chdir(previo))
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            contexto.cmd_brief(argparse.Namespace(
                feature="1", max_lineas=70, max_archivos=10, max_lecciones=10, max_relacionados=0,
                con_producto=False, con_hallazgos=False, con_reglas=False))
        self.assertNotIn("contract sin cliente_sub", salida.getvalue())
        self.assertIn("con_hallazgos=False", (SCRIPTS / "revision.py").read_text(encoding="utf-8"))

    def test_el_arranque_de_sesion_los_cuenta(self):
        out = self.ok("estado.py")
        self.assertIn("hallazgos: 4 abiertos: #1 (1), sin feature (3)", out)

    def test_el_arranque_de_sesion_calla_si_no_hay(self):
        for hid in ("H-1", "H-2", "H-3", "H-4"):
            self.ok("hallazgo.py", "resolver", "--id", hid, "--como", "descartado: prueba")
        self.assertNotIn("hallazgos:", self.ok("estado.py"))

    def test_approve_spec_avisa_los_que_la_feature_tiene_anotados(self):
        self.ok("hallazgo.py", "anotar", "--feature", "2", "--texto", "falta el filtro por marca")
        out = self.ok("gate.py", "approve-spec", "--feature", "2", "--yes", "--por", "Fixture")
        self.assertIn("hallazgos anotados en esta feature sin resolver (H-5)", out)

    def test_close_se_niega_con_un_hallazgo_de_la_feature_sin_resolver(self):
        out = self.falla("gate.py", "close", "--feature", "1", "--status", "done", "--to", "develop")
        self.assertIn("hallazgos anotados sin resolver (H-1)", out)
        self.assertEqual(self.datos()["features"][0]["status"], "in_progress")

    def test_close_no_se_niega_por_hallazgos_resueltos_movidos_o_del_proyecto(self):
        for accion in (("resolver", "--id", "H-1", "--como", "E-1 de la #1"),
                       ("mover", "--id", "H-1", "--sin-feature")):
            with self.subTest(accion=accion[0]):
                self.setUp()
                self.ok("hallazgo.py", *accion)
                r = self.cli("gate.py", "close", "--feature", "1", "--status", "done", "--to", "develop")
                self.assertNotIn("hallazgos anotados sin resolver", r.stdout + r.stderr)

    def test_un_bloqueo_no_exige_resolverlos(self):
        r = self.cli("gate.py", "close", "--feature", "1", "--status", "blocked")
        self.assertNotIn("hallazgos anotados sin resolver", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
