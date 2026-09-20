"""Rol producto: PRD inicial y SDD de arquitectura sin que un agente toque docs/prd/** a mano.

El modo de fallo que cubren: el rol redacta el cuerpo manual del PRD, el usuario
lo aprueba en el chat, y aun asi `gate.py check` sale rojo por rutas protegidas
(o peor: el sello reautoriza ediciones que el usuario nunca vio).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import bloques  # noqa: E402
import documentacion  # noqa: E402
import producto  # noqa: E402

PRD_COMPLETO = """# PRD - demo

Estado: draft
Dueño: Fixture
Creado: 2026-09-19
Alcance: cobro idempotente al reintentar el pago; NO toca devoluciones

## Resumen

Hoy: un reintento de pago crea un segundo pedido y alguien lo anula a mano.
Despues: el reintento devuelve el mismo pedido y nadie tiene que mirar.

## La historia

Antes: Marta paga un viernes a las 6, la app se cuelga y vuelve a tocar "pagar".
El lunes tiene dos pedidos y un cargo doble que reclamar.

Despues: Marta toca "pagar" dos veces y ve un solo pedido confirmado. No hay nada
que reclamar.

## Objetivos y no-objetivos

- O1: un reintento con la misma clave devuelve el pedido original
- O2: operaciones ve cuantos reintentos hubo
- NO1: no cambia el flujo de devoluciones

## Como funciona hoy y como va a funcionar

Hoy:     pagar -> crear pedido -> cobrar
Despues: pagar -> buscar la clave -> si existe, devolver el pedido; si no, crear y cobrar

## Los datos

disparador   llega un pago con clave de idempotencia
por pedido   idempotency_key unica   <- candado

## Pseudo-codigo: el acuerdo

CUANDO llega un pago
  ya existe un pedido con esa clave?   -> si si, devolverlo y no cobrar
ENTONCES crear el pedido y cobrar una sola vez
Promesas: un solo cargo por clave.

## Features candidatas

- F-1: Cobro idempotente: un reintento no crea un segundo pedido (cumple O1)
- F-2: Alerta de duplicados: operaciones ve los intentos repetidos (cumple O2)
"""

SDD_COMPLETO = """# SDD - demo

Estado: draft

## Contexto

Monorepo Go con dos servicios y Postgres.

## Componentes

- orders: recibe el pedido y lo persiste.
- payments: habla con la pasarela.

## Datos e integraciones

Tabla `payments.attempts` con clave unica por `idempotency_key`.

## Decisiones

Clave de idempotencia en base de datos y no en cache: sobrevive reinicios.

## Riesgos

Una clave reutilizada entre clientes distintos mezclaria pedidos.
"""


class ProductoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root / "harness" / "progress").mkdir(parents=True)
        (self.root / "docs").mkdir()
        self.backlog = self.root / "harness" / "feature_list.json"
        self.backlog.write_text(json.dumps({"project": "demo", "rules": {}, "features": []}),
                                encoding="utf-8")
        self.prev_cwd = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(lambda: os.chdir(self.prev_cwd))
        self.env = {"PATH": os.environ["PATH"], "HOME": str(self.root), "USERPROFILE": str(self.root),
                    "PYTHONDONTWRITEBYTECODE": "1", "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                    "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid"}
        self.prd = self.root / "docs" / "prd" / "PRD-master.md"
        self.sdd = self.root / "docs" / "sdd.md"
        self.borrador_prd = self.root / "docs" / "borrador-prd.md"
        self.borrador_sdd = self.root / "docs" / "borrador-sdd.md"

    # --- helpers ---------------------------------------------------------

    def cli(self, script, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=self.root,
                              env=self.env, capture_output=True, text=True, timeout=60)

    def ok(self, script, *args):
        r = self.cli(script, *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        return r

    def falla(self, script, *args):
        r = self.cli(script, *args)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        return r

    def datos(self):
        return json.loads(self.backlog.read_text(encoding="utf-8"))

    def git(self, *args):
        r = subprocess.run(["git", "-C", str(self.root), *args], env=self.env,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout.strip()

    def repo_git(self):
        """Raiz versionada con lo que haya en docs/ y harness/ como baseline.

        docs/ queda trackeado aunque este vacio, para que el PRD nuevo salga en
        porcelain como `?? docs/prd/PRD-master.md` y los tests midan el sello y
        no el arreglo de `-uall` (ese tiene su propia regresion en
        test_documentacion).
        """
        (self.root / "docs" / ".keep").write_text("", encoding="utf-8")
        self.git("init", "-b", "develop")
        self.git("add", "-A")
        self.git("commit", "-m", "fixture: baseline")

    def aprobar_prd(self):
        self.borrador_prd.write_text(PRD_COMPLETO, encoding="utf-8")
        return self.ok("producto.py", "aprobar", "--doc", "prd", "--yes", "--por", "Fixture")

    # --- borrador ----------------------------------------------------------

    def test_borrador_nace_de_la_plantilla_en_draft_y_no_se_pisa(self):
        for doc, path, seccion in (("prd", self.borrador_prd, "## Pseudo-codigo: el acuerdo"),
                                   ("sdd", self.borrador_sdd, "## Decisiones")):
            with self.subTest(doc=doc):
                r = self.ok("producto.py", "borrador", "--doc", doc)
                self.assertIn(f"templates/{doc}.md", r.stdout)
                texto = path.read_text(encoding="utf-8")
                self.assertTrue(texto.startswith(f"# {doc.upper()} - demo\n"), texto[:40])
                self.assertIn("Estado: draft", texto)
                self.assertIn(seccion, texto)
                self.assertNotIn("{{PROYECTO}}", texto)
                self.assertNotIn("{{DUENO}}", texto)
                self.assertNotIn("{{FECHA}}", texto)
                self.assertNotIn("harness-flow:features", texto)
                path.write_text(texto + "\nmi trabajo\n", encoding="utf-8")
                r = self.ok("producto.py", "borrador", "--doc", doc)
                self.assertIn("ya existe", r.stdout)
                self.assertTrue(path.read_text(encoding="utf-8").endswith("mi trabajo\n"))
        historia = (self.root / "harness" / "progress" / "history.md").read_text(encoding="utf-8")
        self.assertIn("borrador de PRD maestro creado", historia)

    def test_borrador_se_siembra_del_cuerpo_manual_existente_sin_el_bloque(self):
        self.prd.parent.mkdir()
        self.prd.write_bytes(b"# PRD del usuario\n\nEstado: approved\nAprobado: alguien\n\n## Problema\n\nreal\n\n"
                             + bloques.START + b"\nviejo\n" + bloques.END + b"\n")
        r = self.ok("producto.py", "borrador", "--doc", "prd")
        self.assertIn("cuerpo manual de docs/prd/PRD-master.md", r.stdout)
        texto = self.borrador_prd.read_text(encoding="utf-8")
        self.assertTrue(texto.startswith("# PRD del usuario\n"))
        self.assertIn("Estado: draft", texto)
        self.assertNotIn("Aprobado:", texto)
        self.assertNotIn("harness-flow:features", texto)
        self.assertNotIn("viejo", texto)

    def test_borrador_ignora_el_encabezado_que_inventa_el_generador(self):
        documentacion.sync()  # PRD-master = prefijo por defecto + bloque vacio
        self.assertTrue(self.prd.read_bytes().startswith(bloques.PRD_PREFIX))
        r = self.ok("producto.py", "borrador", "--doc", "prd")
        self.assertIn("templates/prd.md", r.stdout)
        self.assertIn("## La historia", self.borrador_prd.read_text(encoding="utf-8"))

    def test_borrador_se_niega_con_marcadores_malformados_en_el_destino(self):
        self.prd.parent.mkdir()
        self.prd.write_bytes(b"# x\n" + bloques.START + b"\nsin cierre\n")
        r = self.falla("producto.py", "borrador", "--doc", "prd")
        self.assertIn("malformados", r.stderr)
        self.assertFalse(self.borrador_prd.exists())

    # --- aprobar: negativas ------------------------------------------------

    def test_aprobar_se_niega_sin_yes_y_no_toca_nada(self):
        self.borrador_prd.write_text(PRD_COMPLETO, encoding="utf-8")
        antes = self.backlog.read_bytes()
        r = self.falla("producto.py", "aprobar", "--doc", "prd")
        self.assertIn("--yes", r.stderr)
        self.assertFalse(self.prd.exists())
        self.assertEqual(self.backlog.read_bytes(), antes)
        self.assertEqual(self.borrador_prd.read_text(encoding="utf-8"), PRD_COMPLETO)

    def test_aprobar_se_niega_sin_borrador(self):
        r = self.falla("producto.py", "aprobar", "--doc", "sdd", "--yes")
        self.assertIn("borrador-sdd.md", r.stderr)
        self.assertFalse(self.sdd.exists())

    def test_aprobar_se_niega_con_la_plantilla_sin_rellenar_y_nombra_las_secciones(self):
        for doc, path, seccion in (("prd", self.borrador_prd, "Objetivos y no-objetivos"),
                                   ("sdd", self.borrador_sdd, "Decisiones")):
            with self.subTest(doc=doc):
                self.ok("producto.py", "borrador", "--doc", doc)
                r = self.falla("producto.py", "aprobar", "--doc", doc, "--yes")
                self.assertIn(f"'## {seccion}' esta vacia", r.stderr)
                self.assertIn("Estado: draft", path.read_text(encoding="utf-8"))
        self.assertFalse(self.prd.exists())
        self.assertFalse(self.sdd.exists())
        self.assertNotIn("documentos", self.datos())

    def test_aprobar_se_niega_si_falta_una_seccion_o_las_candidatas(self):
        sin_seccion = PRD_COMPLETO.replace("## Los datos\n\ndisparador   llega un pago con clave de idempotencia\npor pedido   idempotency_key unica   <- candado\n\n", "")
        self.borrador_prd.write_text(sin_seccion, encoding="utf-8")
        r = self.falla("producto.py", "aprobar", "--doc", "prd", "--yes")
        self.assertIn("falta la seccion '## Los datos'", r.stderr)

        sin_candidatas = PRD_COMPLETO.replace("- F-1: Cobro idempotente: un reintento no crea un segundo pedido (cumple O1)\n", "Cobro idempotente.\n") \
                                     .replace("- F-2: Alerta de duplicados: operaciones ve los intentos repetidos (cumple O2)\n", "")
        self.borrador_prd.write_text(sin_candidatas, encoding="utf-8")
        r = self.falla("producto.py", "aprobar", "--doc", "prd", "--yes")
        self.assertIn("F-n", r.stderr)
        self.assertFalse(self.prd.exists())

    def test_aprobar_se_niega_si_el_borrador_trae_el_bloque_generado(self):
        self.borrador_prd.write_text(
            PRD_COMPLETO + "\n" + documentacion.INICIO + "\nx\n" + documentacion.FIN + "\n", encoding="utf-8")
        r = self.falla("producto.py", "aprobar", "--doc", "prd", "--yes")
        self.assertIn("harness-flow:features", r.stderr)
        self.assertFalse(self.prd.exists())

    def test_aprobar_prd_se_niega_con_features_multirepo_registradas_abiertas(self):
        data = self.datos()
        data["features"] = [{"id": 7, "name": "Registrada", "status": "in_progress",
                             "multi_repo_protected": {"/x": {"docs/prd/PRD-master.md": {"kind": "missing"}}}},
                            {"id": 8, "name": "Cerrada", "status": "done",
                             "multi_repo_protected": {"/x": {}}}]
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        self.borrador_prd.write_text(PRD_COMPLETO, encoding="utf-8")
        r = self.falla("producto.py", "aprobar", "--doc", "prd", "--yes")
        self.assertIn("#7", r.stderr)
        self.assertNotIn("#8", r.stderr)
        self.assertIn("multi-repo", r.stderr)
        self.assertFalse(self.prd.exists())
        self.assertIn("Estado: draft", self.borrador_prd.read_text(encoding="utf-8"))

    def test_aprobar_se_niega_con_marcadores_malformados_en_el_destino(self):
        self.prd.parent.mkdir()
        roto = b"# x\n" + bloques.START + b"\n" + bloques.START + b"\n" + bloques.END + b"\n"
        self.prd.write_bytes(roto)
        self.borrador_prd.write_text(PRD_COMPLETO, encoding="utf-8")
        r = self.falla("producto.py", "aprobar", "--doc", "prd", "--yes")
        self.assertIn("malformados", r.stderr)
        self.assertEqual(self.prd.read_bytes(), roto)
        self.assertNotIn("documentos", self.datos())

    # --- aprobar: sello ----------------------------------------------------

    def test_aprobar_prd_copia_el_cuerpo_sella_el_backlog_y_lista_las_candidatas(self):
        r = self.aprobar_prd()
        cuerpo = self.prd.read_text(encoding="utf-8")
        self.assertTrue(cuerpo.startswith("# PRD - demo\n\nEstado: approved\nAprobado: Fixture · "))
        self.assertIn("sellado por producto.py aprobar --yes", cuerpo)
        self.assertIn("\nDueño: Fixture\n", cuerpo)
        self.assertIn("## Features candidatas", cuerpo)
        self.assertNotIn("harness-flow:features", cuerpo)
        self.assertEqual(self.borrador_prd.read_text(encoding="utf-8"), cuerpo)

        sello = self.datos()["documentos"]["prd"]
        self.assertEqual(sello["aprobado_por"], "Fixture")
        self.assertEqual(sello["destino"], "docs/prd/PRD-master.md")
        self.assertEqual(sello["fingerprint"], bloques.fingerprint(self.prd.read_bytes()))
        self.assertEqual(sello["borrador_sha256"], hashlib.sha256(self.borrador_prd.read_bytes()).hexdigest())

        historia = (self.root / "harness" / "progress" / "history.md").read_text(encoding="utf-8")
        self.assertIn("PRD maestro aprobado por Fixture -> docs/prd/PRD-master.md", historia)
        self.assertIn('add.py --name "Cobro idempotente" --prd docs/prd/PRD-master.md', r.stdout)
        self.assertIn('add.py --name "Alerta de duplicados" --prd docs/prd/PRD-master.md', r.stdout)

    def test_aprobar_conserva_el_bloque_generado_y_el_sync_conserva_el_cuerpo(self):
        data = self.datos()
        data["features"] = [{"id": 1, "name": "Cobro idempotente", "status": "done", "closed_at": "2026-09-19"}]
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        documentacion.sync()
        self.assertIn(b"Feature #1", self.prd.read_bytes())

        self.aprobar_prd()
        despues = self.prd.read_bytes()
        self.assertTrue(despues.startswith(b"# PRD - demo\n"))
        self.assertNotIn(bloques.PRD_PREFIX, despues)
        self.assertIn(b"Feature #1", despues)
        self.assertEqual(despues.count(bloques.START), 1)
        self.assertEqual(despues.count(bloques.END), 1)

        self.assertEqual(documentacion.sync(), [], "sync no tenia nada que cambiar")
        data = self.datos()
        data["features"].append({"id": 2, "name": "Alerta de duplicados", "status": "done", "closed_at": "2026-09-20"})
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        documentacion.sync()
        final = self.prd.read_bytes()
        self.assertTrue(final.startswith(b"# PRD - demo\n"))
        self.assertIn(b"## Pseudo-codigo: el acuerdo", final)
        self.assertIn(b"Feature #2", final)
        sello = self.datos()["documentos"]["prd"]
        self.assertTrue(bloques.compatible(sello["fingerprint"], bloques.fingerprint(final)),
                        "el sync solo toca el bloque: el sello sigue vigente")

    def test_aprobar_sdd_escribe_docs_sdd_y_deja_lugar_al_bloque(self):
        self.borrador_sdd.write_text(SDD_COMPLETO, encoding="utf-8")
        self.ok("producto.py", "aprobar", "--doc", "sdd", "--yes", "--por", "Fixture")
        self.assertTrue(self.sdd.read_text(encoding="utf-8").startswith("# SDD - demo\n\nEstado: approved\n"))
        self.assertEqual(self.datos()["documentos"]["sdd"]["destino"], "docs/sdd.md")
        data = self.datos()
        data["features"] = [{"id": 1, "name": "Cobro idempotente", "status": "done", "microservicios": ["payments"]}]
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        documentacion.sync()
        sdd = self.sdd.read_text(encoding="utf-8")
        self.assertTrue(sdd.startswith("# SDD - demo\n"))
        self.assertIn("## Decisiones", sdd)
        self.assertIn("Feature #1", sdd)

    def test_reaprobar_reemplaza_el_sello_y_no_duplica_lineas(self):
        self.aprobar_prd()
        self.borrador_prd.write_text(self.borrador_prd.read_text(encoding="utf-8").replace("flujo de devoluciones", "flujo de devoluciones ni reembolsos"),
                                     encoding="utf-8")
        self.ok("producto.py", "aprobar", "--doc", "prd", "--yes", "--por", "Fixture2")
        cuerpo = self.prd.read_text(encoding="utf-8")
        self.assertEqual(cuerpo.count("Estado:"), 1)
        self.assertEqual(cuerpo.count("Aprobado:"), 1)
        self.assertIn("Aprobado: Fixture2", cuerpo)
        self.assertIn("devoluciones ni reembolsos", cuerpo)
        self.assertEqual(self.datos()["documentos"]["prd"]["aprobado_por"], "Fixture2")

    # --- gate ---------------------------------------------------------------

    def test_gate_check_acepta_el_prd_sellado_sin_commit_y_su_primer_sync(self):
        self.repo_git()  # baseline sin docs/prd
        self.aprobar_prd()
        r = self.ok("gate.py", "check")
        self.assertIn("ruta(s) protegida(s) intactas", r.stdout)

        self.ok("documentacion.py", "sync")  # primera insercion del bloque debajo del cuerpo sellado
        self.assertIn(bloques.START, self.prd.read_bytes())
        r = self.ok("gate.py", "check")
        self.assertIn("ruta(s) protegida(s) intactas", r.stdout)

    def test_gate_check_acepta_el_prd_reaprobado_sobre_uno_commiteado(self):
        data = self.datos()
        data["features"] = [{"id": 1, "name": "Cobro idempotente", "status": "done", "closed_at": "2026-09-19"}]
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        documentacion.sync()
        self.repo_git()  # baseline: PRD generado y commiteado
        self.aprobar_prd()  # el cuerpo manual ahora difiere de HEAD
        r = self.ok("gate.py", "check")
        self.assertIn("ruta(s) protegida(s) intactas", r.stdout)

    def test_gate_check_rechaza_editar_el_cuerpo_sellado_a_mano(self):
        self.repo_git()
        self.aprobar_prd()
        self.prd.write_text(self.prd.read_text(encoding="utf-8").replace("flujo de devoluciones", "flujo de devoluciones (editado)"),
                            encoding="utf-8")
        r = self.falla("gate.py", "check")
        self.assertIn("rutas protegidas modificadas", r.stdout)
        self.assertIn("docs/prd/PRD-master.md", r.stdout)

    def test_gate_check_rechaza_un_sello_que_no_corresponde_al_cuerpo(self):
        self.repo_git()
        self.aprobar_prd()
        data = self.datos()
        data["documentos"]["prd"]["fingerprint"] = bloques.fingerprint(b"# otro cuerpo\n")
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        r = self.falla("gate.py", "check")
        self.assertIn("rutas protegidas modificadas", r.stdout)

    def test_el_sello_del_prd_no_autoriza_otros_archivos_bajo_docs_prd(self):
        self.repo_git()
        self.aprobar_prd()
        (self.root / "docs" / "prd" / "otro.md").write_text("colado", encoding="utf-8")
        r = self.falla("gate.py", "check")
        self.assertIn("docs/prd/otro.md", r.stdout)

    def test_gate_check_tras_commitear_el_prd_sellado_sigue_verde_sin_el_sello(self):
        self.repo_git()
        self.aprobar_prd()
        self.git("add", "-A")
        self.git("commit", "-m", "usuario: PRD aprobado")
        data = self.datos()
        data.pop("documentos")
        self.backlog.write_text(json.dumps(data), encoding="utf-8")
        self.ok("gate.py", "check")

    # --- estado ---------------------------------------------------------------

    def test_estado_muestra_en_que_paso_esta_cada_documento(self):
        out = self.ok("estado.py").stdout
        self.assertIn("prd:   sin documento (producto.py borrador --doc prd)", out)
        self.assertIn("sdd:   sin documento (producto.py borrador --doc sdd)", out)

        self.ok("producto.py", "borrador", "--doc", "prd")
        self.assertIn("prd:   borrador sin aprobar (docs/borrador-prd.md)", self.ok("estado.py").stdout)

        self.aprobar_prd()
        out = self.ok("estado.py").stdout
        self.assertIn("prd:   aprobado por Fixture ·", out)
        self.assertNotIn("cambiado", out)

        self.borrador_prd.write_text(self.borrador_prd.read_text(encoding="utf-8") + "\nmas\n", encoding="utf-8")
        self.assertIn("borrador cambiado despues (re-aprobar)", self.ok("estado.py").stdout)

        self.prd.write_text(self.prd.read_text(encoding="utf-8") + "\nedicion del usuario\n", encoding="utf-8")
        self.assertIn("docs/prd/PRD-master.md cambio despues del sello", self.ok("estado.py").stdout)

    def test_estado_distingue_un_prd_manual_del_usuario_sin_sello(self):
        self.prd.parent.mkdir()
        self.prd.write_text("# PRD escrito a mano\n\nrequisitos\n", encoding="utf-8")
        self.assertIn("prd:   manual del usuario sin sello (docs/prd/PRD-master.md)", self.ok("estado.py").stdout)


class ValidacionTests(unittest.TestCase):
    """El validador decide si el ritual puede sellar: sus falsos verdes son los del rol."""

    DATOS = "disparador   llega un pago con clave de idempotencia\npor pedido   idempotency_key unica   <- candado\n"

    def test_una_guia_no_cuenta_como_contenido(self):
        texto = PRD_COMPLETO.replace(self.DATOS, "<!-- el plano de los datos -->\n")
        self.assertIn("la seccion '## Los datos' esta vacia (solo guia)", producto.validar(texto, "prd"))

    def test_una_guia_multilinea_tampoco(self):
        texto = PRD_COMPLETO.replace(self.DATOS, "<!-- linea uno\n     linea dos -->\n")
        self.assertIn("la seccion '## Los datos' esta vacia (solo guia)", producto.validar(texto, "prd"))

    def test_la_plantilla_recien_creada_no_es_aprobable_y_nombra_cada_parte(self):
        plantilla = (Path(__file__).resolve().parents[1] / "templates" / "prd.md").read_text(encoding="utf-8")
        problemas = producto.validar(plantilla, "prd")
        self.assertIn("falta 'Alcance:' en el encabezado (una linea: que toca y que NO toca)", problemas)
        self.assertTrue(any(p.startswith("'## Resumen' necesita 'Hoy:' y 'Despues:'") for p in problemas), problemas)
        self.assertTrue(any(p.startswith("'## La historia' necesita 'Antes:' y 'Despues:'") for p in problemas), problemas)
        self.assertIn("la seccion '## Objetivos y no-objetivos' esta vacia (solo guia)", problemas)
        self.assertIn("la seccion '## Pseudo-codigo: el acuerdo' esta vacia (solo guia)", problemas)
        self.assertFalse(any("codigo final" in p for p in problemas), "los ```go de la guia no cuentan como codigo")

    def test_el_alcance_va_en_el_encabezado(self):
        texto = PRD_COMPLETO.replace("Alcance: cobro idempotente al reintentar el pago; NO toca devoluciones\n", "Alcance:\n")
        self.assertIn("falta 'Alcance:' en el encabezado (una linea: que toca y que NO toca)", producto.validar(texto, "prd"))
        texto = PRD_COMPLETO.replace("Alcance: cobro idempotente al reintentar el pago; NO toca devoluciones\n", "")
        self.assertIn("falta 'Alcance:' en el encabezado (una linea: que toca y que NO toca)", producto.validar(texto, "prd"))

    def test_resumen_e_historia_van_en_dos_tiempos(self):
        sin_despues = PRD_COMPLETO.replace("Despues: el reintento devuelve el mismo pedido y nadie tiene que mirar.\n", "")
        self.assertIn("'## Resumen' necesita 'Hoy:' y 'Despues:' con contenido (falta Despues)", producto.validar(sin_despues, "prd"))
        antes_vacio = PRD_COMPLETO.replace(
            'Antes: Marta paga un viernes a las 6, la app se cuelga y vuelve a tocar "pagar".\nEl lunes tiene dos pedidos y un cargo doble que reclamar.\n',
            "Antes:\n")
        self.assertIn("'## La historia' necesita 'Antes:' y 'Despues:' con contenido (falta Antes)", producto.validar(antes_vacio, "prd"))
        # La etiqueta sola y el parrafo debajo tambien cuenta; con tilde y en negrita, igual.
        parrafo_debajo = PRD_COMPLETO.replace(
            'Antes: Marta paga un viernes a las 6, la app se cuelga y vuelve a tocar "pagar".\n',
            "**Antes:**\nMarta paga un viernes a las 6 y la app se cuelga.\n")
        parrafo_debajo = parrafo_debajo.replace("Despues: Marta toca", "Después: Marta toca")
        self.assertEqual(producto.validar(parrafo_debajo, "prd"), [])

    def test_objetivos_y_no_objetivos_llevan_nombre(self):
        sin_no = PRD_COMPLETO.replace("- NO1: no cambia el flujo de devoluciones\n", "no cambia el flujo de devoluciones\n")
        self.assertIn("'## Objetivos y no-objetivos' no declara ningun '- NO1: ...' (frenan el 'ya que estamos')",
                      producto.validar(sin_no, "prd"))
        sin_o = PRD_COMPLETO.replace("- O1: un reintento con la misma clave devuelve el pedido original\n", "") \
                            .replace("- O2: operaciones ve cuantos reintentos hubo\n", "")
        self.assertIn("'## Objetivos y no-objetivos' no declara ningun '- O1: ...' (con nombre, para citarlo)",
                      producto.validar(sin_o, "prd"))
        con_guion = PRD_COMPLETO.replace("- O1:", "- O-1:").replace("- NO1:", "* NO-1:")
        self.assertEqual(producto.validar(con_guion, "prd"), [])

    def test_codigo_final_se_niega_y_el_pseudocodigo_pasa(self):
        base = PRD_COMPLETO.replace("Promesas: un solo cargo por clave.\n", "Promesas: un solo cargo por clave.\n{bloque}")
        con_go = base.replace("{bloque}", "```go\nfunc cobrar() {}\n```\n")
        self.assertIn("trae codigo final (bloque ```go): el PRD lleva pseudo-codigo; el codigo se escribe despues, en otra parte",
                      producto.validar(con_go, "prd"))
        dos = base.replace("{bloque}", "```sql\nselect 1\n```\n\n```TS\nx\n```\n")
        self.assertTrue(any("```sql, ```ts" in p for p in producto.validar(dos, "prd")))
        for permitido in ("```\nCUANDO llega un pago\n```\n", "```text\nCUANDO llega un pago\n```\n",
                          "```pseudo\nENTONCES cobrar\n```\n"):
            with self.subTest(bloque=permitido[:10]):
                self.assertEqual(producto.validar(base.replace("{bloque}", permitido), "prd"), [])
        self.assertEqual(producto.validar(base.replace("{bloque}", "<!-- ```go en una guia no cuenta -->\n"), "prd"), [])

    def test_las_candidatas_se_leen_en_una_linea_y_con_el_nombre_antes_de_los_dos_puntos(self):
        self.assertEqual(producto.candidatas(PRD_COMPLETO),
                         [("1", "Cobro idempotente"), ("2", "Alerta de duplicados")])
        self.assertEqual(producto.candidatas("- F-3: Solo nombre\n* F-4 : Con asterisco: y resultado\n"),
                         [("3", "Solo nombre"), ("4", "Con asterisco")])
        self.assertEqual(producto.candidatas("F-5 suelta sin dos puntos\n- F-6\n: tarde\n"), [])

    def test_las_candidatas_dentro_de_una_guia_no_cuentan(self):
        self.assertEqual(producto.candidatas("<!-- - F-1: ejemplo: guia -->\n"), [])

    def test_el_borrador_completo_de_las_fixtures_es_aprobable(self):
        self.assertEqual(producto.validar(PRD_COMPLETO, "prd"), [])
        self.assertEqual(producto.validar(SDD_COMPLETO, "sdd"), [])

    def test_sellar_pone_estado_y_aprobado_una_sola_vez(self):
        una = producto.sellar(PRD_COMPLETO, "quien", "2026-09-19T00:00:00Z")
        self.assertIn("\nEstado: approved\nAprobado: quien · 2026-09-19T00:00:00Z · sellado por producto.py aprobar --yes\n", una)
        dos = producto.sellar(una, "otro", "2026-09-20T00:00:00Z")
        self.assertEqual(dos.count("Estado:"), 1)
        self.assertEqual(dos.count("Aprobado:"), 1)
        self.assertIn("Aprobado: otro", dos)
        sin_estado = producto.sellar("# T\n\n## Problema\n\nx\n", "q", "c")
        self.assertTrue(sin_estado.startswith("# T\n\nEstado: approved\nAprobado: q · c"))


if __name__ == "__main__":
    unittest.main()
