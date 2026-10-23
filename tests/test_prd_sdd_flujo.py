"""El PRD/SDD a lo largo del flujo, no solo al principio (rol producto) y al final (sync).

Los modos de fallo que cubren, todos con repro antes del arreglo:
- add.py copiaba la guia entera de templates/spec.md como spec y perdia --prd;
- docs/sdd.md no era ruta protegida: un agente lo editaba y gate.py check salia verde;
- require_docs_al_dia salia como regla activa y ningun gate la miraba;
- el spec, el brief y estado no sabian de que PRD/SDD salia la feature, ni si
  el documento cambio despues de aprobar el spec.
"""
from __future__ import annotations

import json
import sys
import unittest

import test_producto as fx
from test_producto import PRD_COMPLETO, SDD_COMPLETO, SCRIPTS

sys.path.insert(0, str(SCRIPTS))
import bloques  # noqa: E402
import multirepo  # noqa: E402

SPEC_CITADO = """# Spec - Feature #1: Cobro idempotente

Estado: draft

## Contexto

PRD: `docs/prd/PRD-master.md` · candidata: F-1 · cumple: O1
SDD: `docs/sdd.md` · decisiones que aplica: D1

## Criterios de aceptacion

- AC-1: dado un pago repetido, cuando llega, entonces devuelve el mismo pedido.
"""


class FlujoPrdSddTests(unittest.TestCase):
    # Los helpers de ProductoTests sin heredar sus tests (correrian dos veces).
    setUp = fx.ProductoTests.setUp
    cli, ok, falla, datos, git = fx.ProductoTests.cli, fx.ProductoTests.ok, fx.ProductoTests.falla, \
        fx.ProductoTests.datos, fx.ProductoTests.git
    repo_git, aprobar_prd = fx.ProductoTests.repo_git, fx.ProductoTests.aprobar_prd

    def aprobar_sdd(self):
        self.borrador_sdd.write_text(SDD_COMPLETO, encoding="utf-8")
        return self.ok("producto.py", "aprobar", "--doc", "sdd", "--yes", "--por", "Fixture")

    def reglas(self, **rules):
        data = self.datos()
        data["rules"].update(rules)
        self.backlog.write_text(json.dumps(data), encoding="utf-8")

    def spec(self, texto=SPEC_CITADO):
        path = self.root / "docs" / "spec-feature-1-cobro-idempotente.md"
        path.write_text(texto, encoding="utf-8")
        return path

    def feature(self, **campos):
        data = self.datos()
        data["features"] = [{"id": 1, "name": "Cobro idempotente", "status": "in_progress", **campos}]
        self.backlog.write_text(json.dumps(data), encoding="utf-8")

    # --- add.py --------------------------------------------------------------

    def test_add_crea_el_spec_desde_el_bloque_y_enlaza_prd_y_candidata(self):
        self.aprobar_prd()
        self.ok("add.py", "--name", "Cobro idempotente", "--candidata", "F-1")
        spec = (self.root / "docs" / "spec-feature-1-cobro-idempotente.md").read_text(encoding="utf-8")
        self.assertTrue(spec.startswith("# Spec - Feature #1: Cobro idempotente\n\nEstado: draft\n"), spec[:80])
        self.assertNotIn("Plantilla de spec", spec)
        self.assertNotIn("```", spec)
        self.assertNotIn("{{", spec)
        self.assertIn("PRD: `docs/prd/PRD-master.md`", spec)
        self.assertIn("candidata: F-1: Cobro idempotente: un reintento no crea un segundo pedido", spec)
        f = self.datos()["features"][0]
        self.assertEqual((f["prd"], f["prd_candidata"]), ("docs/prd/PRD-master.md", "F-1"))

    def test_add_sin_candidata_deja_el_hueco_explicito(self):
        self.ok("add.py", "--name", "Arreglo", "--kind", "bug")
        spec = (self.root / "docs" / "spec-feature-1-arreglo.md").read_text(encoding="utf-8")
        self.assertIn("candidata: ninguna declarada", spec)
        self.assertNotIn("prd", self.datos()["features"][0])

    def test_add_candidata_que_el_prd_no_declara_o_sin_prd_se_niega(self):
        r = self.falla("add.py", "--name", "X", "--candidata", "F-1")
        self.assertIn("sin PRD con cuerpo", r.stderr)
        self.aprobar_prd()
        r = self.falla("add.py", "--name", "X", "--candidata", "F-9")
        self.assertIn("F-9 no esta en '## Features candidatas'", r.stderr)
        r = self.falla("add.py", "--name", "X", "--candidata", "uno")
        self.assertIn("F-1", r.stderr)
        self.assertEqual(self.datos()["features"], [])

    def test_add_rechaza_un_prd_que_no_es_el_que_sella_el_ritual(self):
        self.aprobar_prd()
        otro = self.root / "docs" / "prd" / "otro.md"
        otro.write_text(PRD_COMPLETO, encoding="utf-8")
        r = self.falla("add.py", "--name", "X", "--prd", "docs/prd/otro.md", "--candidata", "F-1")
        self.assertIn("docs/prd/PRD-master.md", r.stderr)
        self.assertEqual(self.datos()["features"], [])
        self.ok("add.py", "--name", "Cobro idempotente", "--prd", "docs/prd/PRD-master.md", "--candidata", "F-1")

    def test_add_avisa_que_approve_spec_se_va_a_negar_sin_documentos(self):
        r = self.ok("add.py", "--name", "Cobro idempotente")
        self.assertIn("approve-spec se va a negar", r.stdout)
        self.assertIn("prd: sin documento", r.stdout)

    # --- require_docs_al_dia en approve-spec ---------------------------------

    def test_approve_spec_se_niega_sin_prd_ni_sdd_con_la_regla_por_defecto(self):
        self.feature()
        sp = self.spec()
        r = self.falla("gate.py", "approve-spec", "--feature", "1", "--yes")
        self.assertIn("require_docs_al_dia", r.stderr)
        self.assertIn("prd: sin documento", r.stderr)
        self.assertIn("sdd: sin documento", r.stderr)
        self.assertIn("Estado: draft", sp.read_text(encoding="utf-8"))
        self.assertNotIn("last_spec_sig", self.datos()["features"][0])

        self.aprobar_prd()
        r = self.falla("gate.py", "approve-spec", "--feature", "1", "--yes")
        self.assertNotIn("prd:", r.stderr)
        self.assertIn("sdd: sin documento", r.stderr)
        self.aprobar_sdd()
        self.ok("gate.py", "approve-spec", "--feature", "1", "--yes")

    def test_true_de_los_backlogs_viejos_exige_solo_el_prd(self):
        self.reglas(require_docs_al_dia=True)
        self.feature()
        self.spec()
        r = self.falla("gate.py", "approve-spec", "--feature", "1", "--yes")
        self.assertNotIn("sdd:", r.stderr)
        self.aprobar_prd()
        self.ok("gate.py", "approve-spec", "--feature", "1", "--yes")

    def test_regla_apagada_o_kind_bug_no_exigen_documentos(self):
        self.feature(kind="bug")
        self.spec()
        self.ok("gate.py", "approve-spec", "--feature", "1", "--yes")
        self.reglas(require_docs_al_dia=False)
        self.feature()
        self.spec()
        self.ok("gate.py", "approve-spec", "--feature", "1", "--yes")

    def test_un_valor_invalido_de_la_regla_falla_en_vez_de_apagarse(self):
        self.reglas(require_docs_al_dia=["prd", "constitution"])
        self.feature()
        self.spec()
        r = self.falla("gate.py", "approve-spec", "--feature", "1", "--yes")
        self.assertIn("require_docs_al_dia invalido", r.stderr)
        r = self.falla("gate.py", "check")
        self.assertIn("require_docs_al_dia invalido", r.stdout)

    def test_un_cuerpo_sin_sello_ni_commit_no_cuenta_y_uno_commiteado_si(self):
        self.reglas(require_docs_al_dia=["prd"])
        self.repo_git()
        self.feature()
        self.spec()
        self.prd.parent.mkdir()
        self.prd.write_text(PRD_COMPLETO, encoding="utf-8")  # un agente, sin el ritual
        r = self.falla("gate.py", "approve-spec", "--feature", "1", "--yes")
        self.assertIn("sin sello de producto.py aprobar ni commit del usuario", r.stderr)
        self.git("add", "docs/prd/PRD-master.md")
        self.git("commit", "-m", "usuario: PRD a mano")
        self.ok("gate.py", "approve-spec", "--feature", "1", "--yes")

    def test_sin_repo_git_el_cuerpo_sin_sello_no_cuenta_y_el_sellado_si(self):
        self.reglas(require_docs_al_dia=["prd"])
        self.feature()
        self.spec()
        self.prd.parent.mkdir()
        self.prd.write_text(PRD_COMPLETO, encoding="utf-8")  # un agente, y no hay commit que medir
        r = self.falla("gate.py", "approve-spec", "--feature", "1", "--yes")
        self.assertIn("sin sello vigente", r.stderr)
        self.assertIn("repo git", r.stderr)
        self.assertNotIn("last_spec_sig", self.datos()["features"][0])
        self.aprobar_prd()
        self.ok("gate.py", "approve-spec", "--feature", "1", "--yes")

    def test_sin_repo_git_check_rechaza_el_cuerpo_sin_sello_y_acepta_el_sellado(self):
        self.prd.parent.mkdir()
        self.prd.write_text(PRD_COMPLETO, encoding="utf-8")
        r = self.falla("gate.py", "check")
        self.assertIn("docs/prd/PRD-master.md", r.stdout)
        self.assertIn("sin sello", r.stdout)
        self.aprobar_prd()
        r = self.ok("gate.py", "check")
        self.assertIn("ruta(s) protegida(s) intactas", r.stdout)
        (self.root / "docs" / "prd" / "otro.md").write_text("colado", encoding="utf-8")
        r = self.falla("gate.py", "check")
        self.assertIn("docs/prd/otro.md", r.stdout)

    def test_sin_repo_git_el_encabezado_que_inventa_el_generador_no_es_violacion(self):
        self.ok("documentacion.py", "sync")
        r = self.ok("gate.py", "check")
        self.assertIn("ruta(s) protegida(s) intactas", r.stdout)

    def test_sin_repo_git_estado_y_add_no_dan_por_listo_un_cuerpo_sin_sello(self):
        self.reglas(require_docs_al_dia=["prd"])
        self.prd.parent.mkdir()
        self.prd.write_text(PRD_COMPLETO, encoding="utf-8")
        out = self.ok("estado.py").stdout
        self.assertIn("manual del usuario sin sello", out)
        self.assertIn("Primero el rol producto", out)
        self.assertNotIn("Para arrancar: add.py", out)
        r = self.ok("add.py", "--name", "Cobro idempotente")
        self.assertIn("approve-spec se va a negar", r.stdout)
        self.assertIn("sin sello vigente", r.stdout)

    # --- citas al PRD/SDD -------------------------------------------------------

    def test_approve_spec_avisa_lo_que_el_spec_no_cita(self):
        self.aprobar_prd()
        self.aprobar_sdd()
        self.feature(prd_candidata="F-1")
        self.spec(SPEC_CITADO.replace("cumple: O1", "cumple: O7").replace("aplica: D1", "aplica: lo de siempre"))
        r = self.ok("gate.py", "approve-spec", "--feature", "1", "--yes")
        self.assertIn("aprobado y sellado", r.stdout)
        self.assertIn("cita O7, que el PRD no declara", r.stdout)
        self.assertIn("no cita ninguna decision del SDD (D1)", r.stdout)

        self.feature(prd_candidata="F-1")
        self.spec()
        r = self.ok("gate.py", "approve-spec", "--feature", "1", "--yes")
        self.assertNotIn("[!]", r.stdout)

        self.feature(prd_candidata="F-1")
        self.spec(SPEC_CITADO.replace("cumple: O1", "cumple: ninguno")
                  .replace("aplica: D1", "aplica: ninguna"))
        r = self.ok("gate.py", "approve-spec", "--feature", "1", "--yes")
        self.assertNotIn("[!]", r.stdout)

    # --- el documento cambia despues del spec --------------------------------

    def test_reaprobar_el_prd_marca_los_specs_abiertos_hasta_re_aprobarlos(self):
        self.aprobar_prd()
        self.aprobar_sdd()
        self.feature(prd_candidata="F-1")
        self.spec()
        self.ok("gate.py", "approve-spec", "--feature", "1", "--yes")
        self.assertEqual(set(self.datos()["features"][0]["docs_base"]), {"prd", "sdd"})
        self.assertNotIn("cambio desde", self.ok("estado.py").stdout)

        self.borrador_prd.write_text(self.borrador_prd.read_text(encoding="utf-8")
                                     .replace("flujo de devoluciones", "flujo de reembolsos"), encoding="utf-8")
        r = self.ok("producto.py", "aprobar", "--doc", "prd", "--yes")
        self.assertIn("specs aprobados contra la version anterior del PRD maestro: #1", r.stdout)
        self.assertIn("PRD cambio desde el spec", self.ok("estado.py").stdout)
        r = self.ok("gate.py", "check")
        self.assertIn("#1 el PRD maestro cambio desde que se aprobo el spec", r.stdout)
        self.assertIn("cambio desde que se aprobo este spec", self.ok("contexto.py", "brief", "--feature", "1").stdout)

        self.ok("gate.py", "approve-spec", "--feature", "1", "--yes")  # el leader lo revisa y sigue valiendo
        self.assertNotIn("cambio desde", self.ok("estado.py").stdout)

    def test_re_aprobar_el_mismo_texto_o_sincronizar_el_bloque_no_es_un_cambio(self):
        self.aprobar_prd()
        self.aprobar_sdd()
        self.feature(status="done", closed_at="2026-09-19", prd_candidata="F-1")
        data = self.datos()
        data["features"].append({"id": 2, "name": "Alerta de duplicados", "status": "in_progress"})
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        (self.root / "docs" / "spec-feature-2-alerta-de-duplicados.md").write_text(
            SPEC_CITADO.replace("#1: Cobro idempotente", "#2: Alerta de duplicados"), encoding="utf-8")
        self.ok("gate.py", "approve-spec", "--feature", "2", "--yes")
        self.ok("documentacion.py", "sync")  # el cierre de #1 agrega el bloque generado
        self.assertIn(b"Candidata del PRD: F-1", self.prd.read_bytes())
        r = self.ok("producto.py", "aprobar", "--doc", "prd", "--yes", "--por", "Otra persona")
        self.assertNotIn("version anterior", r.stdout)
        self.assertNotIn("cambio desde", self.ok("estado.py").stdout)

    # --- brief, revisor y estado -----------------------------------------------

    def test_el_brief_del_leader_trae_el_prd_sdd_y_el_del_revisor_no(self):
        self.aprobar_prd()
        self.aprobar_sdd()
        self.feature(prd_candidata="F-1", prd="docs/prd/PRD-master.md")
        self.spec()
        brief = self.ok("contexto.py", "brief", "--feature", "1").stdout
        self.assertIn("producto (leelo antes de disenar", brief)
        self.assertIn("F-1: Cobro idempotente: un reintento no crea un segundo pedido (cumple O1)", brief)
        self.assertIn("objetivos: O1, O2 · no-objetivos: NO1", brief)
        self.assertIn("decisiones: D1", brief)
        self.assertNotIn("producto (", self.ok("contexto.py", "brief", "--feature", "1", "--sin-producto").stdout)
        self.repo_git()
        briefing = self.ok("revision.py", "--feature", "1", "--briefing").stdout
        self.assertIn("BRIEF #1", briefing)
        self.assertNotIn("producto (", briefing)

    def test_estado_manda_al_rol_producto_y_cuenta_las_candidatas(self):
        out = self.ok("estado.py").stdout
        self.assertIn("Primero el rol producto antes de cualquier spec: producto.py borrador --doc prd", out)
        self.assertNotIn("Para arrancar: add.py", out)
        self.aprobar_prd()
        self.aprobar_sdd()
        self.ok("add.py", "--name", "Cobro idempotente", "--candidata", "F-1")
        out = self.ok("estado.py").stdout
        self.assertIn("candidatas: F-1 #1 todo · F-2 sin feature", out)
        self.assertIn("arranca la #1", out)


class SddProtegidoTests(unittest.TestCase):
    setUp = fx.ProductoTests.setUp
    cli, ok, falla, datos, git = fx.ProductoTests.cli, fx.ProductoTests.ok, fx.ProductoTests.falla, \
        fx.ProductoTests.datos, fx.ProductoTests.git
    repo_git = fx.ProductoTests.repo_git

    def aprobar_sdd(self):
        self.borrador_sdd.write_text(SDD_COMPLETO, encoding="utf-8")
        return self.ok("producto.py", "aprobar", "--doc", "sdd", "--yes", "--por", "Fixture")

    def test_gate_check_protege_docs_sdd_como_el_prd(self):
        self.repo_git()
        self.aprobar_sdd()
        self.ok("gate.py", "check")  # sellado y sin commitear
        self.ok("documentacion.py", "sync")  # primera insercion del bloque
        self.assertIn(bloques.START, self.sdd.read_bytes())
        self.ok("gate.py", "check")
        self.sdd.write_text(self.sdd.read_text(encoding="utf-8")
                            .replace("no sobrevive un reinicio", "sobrevive todo"), encoding="utf-8")
        r = self.falla("gate.py", "check")
        self.assertIn("rutas protegidas modificadas: docs/sdd.md", r.stdout)

    def test_el_sdd_que_solo_tiene_bloque_generado_es_primera_insercion_valida(self):
        self.repo_git()
        self.ok("documentacion.py", "sync")  # sin cuerpo: inventa el encabezado del SDD
        self.assertTrue(self.sdd.read_bytes().startswith(bloques.SDD_PREFIX))
        r = self.ok("gate.py", "check")
        self.assertIn("ruta(s) protegida(s) intactas", r.stdout)

    def test_un_backlog_viejo_que_no_protege_el_sdd_lo_avisa(self):
        data = self.datos()
        data["rules"]["rutas_protegidas"] = ["docs/prd/**", "docs/constitution.md", ".env"]
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        self.repo_git()
        r = self.ok("gate.py", "check")
        self.assertIn("docs/sdd.md no esta en rules.rutas_protegidas", r.stdout)

    def test_aprobar_sdd_se_niega_si_un_registro_multirepo_abierto_lo_fijo(self):
        data = self.datos()
        data["features"] = [{"id": 7, "name": "Registrada", "status": "in_progress",
                             "multi_repo_protected": {"/x": {"docs/sdd.md": {"kind": "missing"}}}}]
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        self.borrador_sdd.write_text(SDD_COMPLETO, encoding="utf-8")
        r = self.falla("producto.py", "aprobar", "--doc", "sdd", "--yes")
        self.assertIn("#7", r.stderr)
        self.assertIn("docs/sdd.md", r.stderr)
        self.assertFalse(self.sdd.exists())
        # el mismo registro no fijo el PRD: aprobarlo no lo rompe
        self.borrador_prd.write_text(PRD_COMPLETO, encoding="utf-8")
        self.ok("producto.py", "aprobar", "--doc", "prd", "--yes")

    def test_el_registro_multirepo_trata_el_sdd_como_el_prd(self):
        rel = "docs/sdd.md"
        manual = b"# SDD del usuario\r\n"
        generado = manual + bloques.START + b"\nx\n" + bloques.END + b"\n"
        antes = {"/fixture": {rel: bloques.fingerprint(manual, bloques.SDD_PREFIX)}}
        despues = {"/fixture": {rel: bloques.fingerprint(generado, bloques.SDD_PREFIX)}}
        self.assertTrue(multirepo.snapshot_matches(antes, despues))
        self.assertEqual(multirepo.protected_context(antes), multirepo.protected_context(despues))
        self.assertFalse(multirepo.snapshot_matches(despues, antes))
        ausente = {"/fixture": {rel: bloques.fingerprint(None, bloques.SDD_PREFIX)}}
        inventado = {"/fixture": {rel: bloques.fingerprint(
            bloques.SDD_PREFIX + bloques.START + b"\nx\n" + bloques.END + b"\n", bloques.SDD_PREFIX)}}
        self.assertTrue(multirepo.snapshot_matches(ausente, inventado))
        self.assertTrue(bloques.allowed(None, bloques.SDD_PREFIX + bloques.START + b"\nx\n" + bloques.END + b"\n",
                                        bloques.SDD_PREFIX))
        self.assertFalse(bloques.allowed(None, bloques.PRD_PREFIX + bloques.START + b"\nx\n" + bloques.END + b"\n",
                                         bloques.SDD_PREFIX))


if __name__ == "__main__":
    unittest.main()
