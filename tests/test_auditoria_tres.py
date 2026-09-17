"""Tres falsos verdes de la auditoria: contexto a medias, rollback mocho, DSN.

Cada test reproduce el defecto concreto, no la feliz. Validados contra el
codigo anterior con `git stash`: sin los arreglos, fallan.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cierre_local  # noqa: E402
import contexto  # noqa: E402


class GrafoUtilizableTests(unittest.TestCase):
    """graphify puede salir 0 y no dejar nada servible."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_grafo_ausente_no_es_exito(self):
        ok, motivo = contexto._grafo_utilizable(self.dir / "no-esta.json")
        self.assertFalse(ok)
        self.assertIn("no dejo el grafo", motivo)

    def test_grafo_truncado_no_es_exito(self):
        g = self.dir / "g.json"
        g.write_text('{"nodes": [', encoding="utf-8")
        ok, motivo = contexto._grafo_utilizable(g)
        self.assertFalse(ok)
        self.assertIn("JSON valido", motivo)

    def test_grafo_sin_nodos_no_es_exito(self):
        g = self.dir / "g.json"
        g.write_text('{"nodes": []}', encoding="utf-8")
        ok, motivo = contexto._grafo_utilizable(g)
        self.assertFalse(ok)
        self.assertIn("sin nodos", motivo)

    def test_grafo_con_nodos_si_es_exito(self):
        g = self.dir / "g.json"
        g.write_text(json.dumps({"nodes": [{"id": "a"}]}), encoding="utf-8")
        ok, motivo = contexto._grafo_utilizable(g)
        self.assertTrue(ok, motivo)


class RollbackTests(unittest.TestCase):
    """El rollback debe limpiar docs/ y no tapar la causa raiz."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        docs = root / "docs"
        progress = root / "harness" / "progress"
        (docs / "prd").mkdir(parents=True)
        progress.mkdir(parents=True)
        (root / "harness" / "outbox").mkdir(parents=True)
        (progress / "archive").mkdir(parents=True)
        (docs / "sdd.md").write_text("sdd original\n", encoding="utf-8")
        (docs / "prd" / "PRD-master.md").write_text("prd\n", encoding="utf-8")
        (progress / "history.md").write_text("hist\n", encoding="utf-8")
        (root / "harness" / "feature_list.json").write_text("{}", encoding="utf-8")
        self.root, self.docs = root, docs
        self.p = {"root": root, "docs": docs, "progress": progress,
                  "harness": root / "harness",
                  "backlog": root / "harness" / "feature_list.json"}

    def test_borra_documentos_nuevos_en_docs(self):
        """Un doc de nombre variable creado durante el cierre no debe quedar."""
        nuevo = self.docs / "revision-9.md"
        with self.assertRaises(RuntimeError):
            with cierre_local.transaction(self.p, "9"):
                nuevo.write_text("basura de un cierre fallido\n", encoding="utf-8")
                raise RuntimeError("fallo real del cierre")
        self.assertFalse(nuevo.exists(),
                         "el rollback dejo un documento del cierre fallido")

    def test_respeta_los_documentos_preexistentes(self):
        previo = self.docs / "ya-estaba.md"
        previo.write_text("contenido previo\n", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            with cierre_local.transaction(self.p, "9"):
                raise RuntimeError("fallo real del cierre")
        self.assertEqual(previo.read_text(encoding="utf-8"), "contenido previo\n")

    def test_un_fallo_de_rollback_no_tapa_la_causa_raiz(self):
        """Antes, un PermissionError del rollback reemplazaba la excepcion."""
        real = RuntimeError("fallo real del cierre (causa raiz)")
        original = Path.write_bytes

        def explota(self, *a, **k):
            # solo revienta al restaurar, que es lo que hace el rollback
            raise PermissionError(13, "Permission denied", str(self))

        # El parche debe seguir en pie MIENTRAS corre el rollback, o sea al
        # salir del with de transaction: por eso envuelve al with, no al body.
        with mock.patch.object(Path, "write_bytes", explota):
            with self.assertRaises(RuntimeError) as capt:
                with cierre_local.transaction(self.p, "9"):
                    original(self.docs / "sdd.md", b"modificado\n")
                    raise real
        self.assertIs(capt.exception, real,
                      "el rollback tapo la causa raiz con su propio error")


class DsnTests(unittest.TestCase):
    """La password no puede romper la cadena de conexion."""

    def test_password_con_espacios_no_parte_la_conexion(self):
        capturado = {}

        class FakePsycopg:
            @staticmethod
            def connect(*args, **kwargs):
                capturado.update(kwargs)
                capturado["posicionales"] = args
                raise SystemExit("corta aca: solo interesa como se conecta")

        entorno = {"DB_HOST": "h", "DB_PORT": "5432", "DB_NAME": "n",
                   "DB_USER": "u", "DB_PASSWORD": "pa ss 'x'\\y",
                   "DB_SSL_MODE": "require"}
        import hub
        with mock.patch.dict(sys.modules, {"psycopg": FakePsycopg}), \
             mock.patch.object(hub, "hub_env", lambda: entorno):
            with self.assertRaises(SystemExit):
                hub.conectar()
        self.assertEqual(capturado.get("posicionales"), (),
                         "sigue pasando un DSN concatenado")
        self.assertEqual(capturado.get("password"), "pa ss 'x'\\y")
        self.assertEqual(capturado.get("host"), "h")


if __name__ == "__main__":
    unittest.main()
