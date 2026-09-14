"""Jira y Confluence se sincronizan juntos desde el binding Atlassian."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import atlassian  # noqa: E402


class AtlassianSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.prev_cwd = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(lambda: os.chdir(self.prev_cwd))
        (self.root / "harness").mkdir()
        (self.root / "docs").mkdir()
        (self.root / "harness" / "atlassian.json").write_text(json.dumps({
            "site": "example.atlassian.net",
            "jira_project": "ADR",
            "confluence_space": "ARQ",
            "issue_type": "Story",
        }), encoding="utf-8")
        (self.root / "harness" / "feature_list.json").write_text(json.dumps({
            "project": "demo",
            "features": [{"id": 3, "name": "Checkout con cupon", "kind": "feature", "status": "in_progress"}],
            "rules": {},
        }), encoding="utf-8")
        (self.root / "docs" / "spec-feature-3-checkout-con-cupon.md").write_text(
            "Estado: approved\n\n- AC-1: aplica descuento\n- AC-2: rechaza vencidos\n",
            encoding="utf-8")
        (self.root / "docs" / "impl-3.md").write_text("## AC-1\nsrc/a.py:10\n", encoding="utf-8")
        (self.root / "docs" / "review-3.md").write_text("Revisado: approved - ok\n", encoding="utf-8")

    def cli(self, *args):
        out = io.StringIO()
        err = io.StringIO()
        with mock.patch.object(sys, "argv", ["atlassian.py", *args]), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                atlassian.main()
                rc = 0
            except SystemExit as exc:
                if isinstance(exc.code, int):
                    rc = int(exc.code or 0)
                elif exc.code:
                    print(exc.code, file=err)
                    rc = 1
                else:
                    rc = 0
        return rc, out.getvalue(), err.getvalue()

    def test_push_con_token_crea_jira_y_confluence_automaticamente(self):
        os.environ["ATLASSIAN_EMAIL"] = "agent@example.com"
        os.environ["ATLASSIAN_API_TOKEN"] = "token"
        llamadas = []
        def fake_api(site, email, token, metodo, ruta, cuerpo=None):
            llamadas.append((metodo, ruta, cuerpo))
            if metodo == "POST" and ruta == "/rest/api/3/issue" and "parent" not in cuerpo["fields"]:
                return 201, {"key": "ADR-3"}
            if metodo == "POST" and ruta == "/rest/api/3/issue":
                return 201, {"key": "ADR-31" if "AC-1" in cuerpo["fields"]["summary"] else "ADR-32"}
            if metodo == "GET" and ruta == "/wiki/rest/api/space/ARQ":
                return 200, {"key": "ARQ"}
            if metodo == "GET" and ruta.startswith("/wiki/rest/api/content?"):
                return 200, {"results": []}
            if metodo == "POST" and ruta == "/wiki/rest/api/content":
                return 200, {"id": "999", "version": {"number": 1}}
            self.fail(f"llamada inesperada: {(metodo, ruta, cuerpo)}")

        with mock.patch.object(atlassian, "api", side_effect=fake_api):
            rc, out, err = self.cli("push", "--feature", "3")

        self.assertEqual(rc, 0, err)
        self.assertIn("creado ADR-3", out)
        self.assertIn("confluence", out.lower())
        rutas = [(m, r) for m, r, _ in llamadas]
        self.assertIn(("POST", "/rest/api/3/issue"), rutas)
        self.assertIn(("POST", "/wiki/rest/api/content"), rutas)
        page = next(c for m, r, c in llamadas if m == "POST" and r == "/wiki/rest/api/content")
        self.assertEqual(page["space"]["key"], "ARQ")
        self.assertEqual(page["title"], "Feature #3 - Checkout con cupon")
        self.assertIn("AC-1", page["body"]["storage"]["value"])
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        feature = data["features"][0]
        self.assertEqual(feature["jira_key"], "ADR-3")
        self.assertEqual(feature["confluence_page_id"], "999")

    def test_push_actualiza_pagina_confluence_existente(self):
        os.environ["ATLASSIAN_EMAIL"] = "agent@example.com"
        os.environ["ATLASSIAN_API_TOKEN"] = "token"
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        data["features"][0]["jira_key"] = "ADR-3"
        data["features"][0]["jira_ac_keys"] = {"AC-1": "ADR-31", "AC-2": "ADR-32"}
        (self.root / "harness" / "feature_list.json").write_text(json.dumps(data), encoding="utf-8")
        llamadas = []
        def fake_api(site, email, token, metodo, ruta, cuerpo=None):
            llamadas.append((metodo, ruta, cuerpo))
            if metodo == "PUT" and ruta == "/rest/api/3/issue/ADR-3":
                return 204, {}
            if metodo == "GET" and ruta == "/wiki/rest/api/space/ARQ":
                return 200, {"key": "ARQ"}
            if metodo == "GET" and ruta.startswith("/wiki/rest/api/content?"):
                return 200, {"results": [{"id": "999", "version": {"number": 4}}]}
            if metodo == "PUT" and ruta == "/wiki/rest/api/content/999":
                return 200, {"id": "999", "version": {"number": 5}}
            self.fail(f"llamada inesperada: {(metodo, ruta, cuerpo)}")

        with mock.patch.object(atlassian, "api", side_effect=fake_api):
            rc, out, err = self.cli("push", "--feature", "3")

        self.assertEqual(rc, 0, err)
        self.assertIn("actualizada", out)
        puts = [c for m, r, c in llamadas if m == "PUT" and r == "/wiki/rest/api/content/999"]
        self.assertEqual(len(puts), 1)
        self.assertEqual(puts[0]["version"]["number"], 5)
        self.assertFalse(any(m == "POST" and r == "/wiki/rest/api/content" for m, r, _ in llamadas))

    def test_sin_token_deja_intents_de_jira_y_confluence_en_outbox(self):
        os.environ.pop("ATLASSIAN_EMAIL", None)
        os.environ.pop("ATLASSIAN_API_TOKEN", None)

        rc, out, err = self.cli("push", "--feature", "3")

        self.assertEqual(rc, 0, err)
        self.assertIn("outbox", out.lower())
        intents = sorted((self.root / "harness" / "outbox").glob("*.json"))
        tipos = [json.loads(p.read_text(encoding="utf-8"))["tipo"] for p in intents]
        self.assertEqual(tipos, ["confluence-upsert", "jira-upsert"])
        confluence = json.loads(intents[0].read_text(encoding="utf-8"))
        self.assertEqual(confluence["space"], "ARQ")
        self.assertEqual(confluence["title"], "Feature #3 - Checkout con cupon")
        self.assertIn("AC-2", confluence["body"])

    def test_error_actualizando_jira_bloquea_confluence_y_sale_rojo(self):
        os.environ["ATLASSIAN_EMAIL"] = "agent@example.com"
        os.environ["ATLASSIAN_API_TOKEN"] = "token"
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        data["features"][0]["jira_key"] = "ADR-3"
        (self.root / "harness" / "feature_list.json").write_text(json.dumps(data), encoding="utf-8")
        llamadas = []
        def fake_api(site, email, token, metodo, ruta, cuerpo=None):
            llamadas.append((metodo, ruta, cuerpo))
            if metodo == "PUT" and ruta == "/rest/api/3/issue/ADR-3":
                return 400, {"error": "summary invalido"}
            self.fail(f"no debe seguir despues de fallar Jira: {(metodo, ruta, cuerpo)}")

        with mock.patch.object(atlassian, "api", side_effect=fake_api):
            rc, out, err = self.cli("push", "--feature", "3")

        self.assertNotEqual(rc, 0)
        self.assertIn("Jira rechazo", err)
        self.assertFalse(any(r.startswith("/wiki/") for _, r, _ in llamadas))

    def test_error_creando_subtask_jira_bloquea_confluence_y_sale_rojo(self):
        os.environ["ATLASSIAN_EMAIL"] = "agent@example.com"
        os.environ["ATLASSIAN_API_TOKEN"] = "token"
        llamadas = []
        def fake_api(site, email, token, metodo, ruta, cuerpo=None):
            llamadas.append((metodo, ruta, cuerpo))
            if metodo == "POST" and ruta == "/rest/api/3/issue" and "parent" not in cuerpo["fields"]:
                return 201, {"key": "ADR-3"}
            if metodo == "POST" and ruta == "/rest/api/3/issue" and "AC-1" in cuerpo["fields"]["summary"]:
                return 201, {"key": "ADR-31"}
            if metodo == "POST" and ruta == "/rest/api/3/issue":
                return 400, {"error": "subtask invalida"}
            self.fail(f"no debe llegar a Confluence despues de fallar subtask: {(metodo, ruta, cuerpo)}")

        with mock.patch.object(atlassian, "api", side_effect=fake_api):
            rc, out, err = self.cli("push", "--feature", "3")

        self.assertNotEqual(rc, 0)
        self.assertIn("subtask", err.lower())
        self.assertFalse(any(r.startswith("/wiki/") for _, r, _ in llamadas))
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        self.assertNotIn("confluence_page_id", data["features"][0])

    def test_confluence_page_id_guardado_se_actualiza_aunque_cambie_titulo(self):
        os.environ["ATLASSIAN_EMAIL"] = "agent@example.com"
        os.environ["ATLASSIAN_API_TOKEN"] = "token"
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        data["features"][0].update({
            "jira_key": "ADR-3",
            "jira_ac_keys": {"AC-1": "ADR-31", "AC-2": "ADR-32"},
            "confluence_page_id": "999",
            "confluence_page_title": "Feature #3 - Nombre viejo",
        })
        (self.root / "harness" / "feature_list.json").write_text(json.dumps(data), encoding="utf-8")
        llamadas = []
        def fake_api(site, email, token, metodo, ruta, cuerpo=None):
            llamadas.append((metodo, ruta, cuerpo))
            if metodo == "PUT" and ruta == "/rest/api/3/issue/ADR-3":
                return 204, {}
            if metodo == "GET" and ruta == "/wiki/rest/api/space/ARQ":
                return 200, {"key": "ARQ"}
            if metodo == "GET" and ruta == "/wiki/rest/api/content/999?expand=version":
                return 200, {"id": "999", "version": {"number": 7}}
            if metodo == "PUT" and ruta == "/wiki/rest/api/content/999":
                return 200, {"id": "999", "version": {"number": 8}}
            if metodo == "GET" and ruta.startswith("/wiki/rest/api/content?"):
                self.fail("si hay confluence_page_id no debe buscar por titulo primero")
            if metodo == "POST" and ruta == "/wiki/rest/api/content":
                self.fail("si hay confluence_page_id no debe crear otra pagina")
            self.fail(f"llamada inesperada: {(metodo, ruta, cuerpo)}")

        with mock.patch.object(atlassian, "api", side_effect=fake_api):
            rc, out, err = self.cli("push", "--feature", "3")

        self.assertEqual(rc, 0, err)
        self.assertIn("actualizada", out)
        put = next(c for m, r, c in llamadas if m == "PUT" and r == "/wiki/rest/api/content/999")
        self.assertEqual(put["version"]["number"], 8)
        self.assertEqual(put["title"], "Feature #3 - Checkout con cupon")
    def test_confluence_body_incluye_prd_y_sdd_si_existen(self):
        prd = self.root / "docs" / "prd" / "PRD-master.md"
        prd.parent.mkdir(parents=True)
        prd.write_text("# PRD maestro\n\nFeature #3 - Checkout con cupon\n", encoding="utf-8")
        (self.root / "docs" / "sdd.md").write_text(
            "# SDD\n\nDiseno implementado por feature\n", encoding="utf-8")
        p = atlassian.paths()
        data = atlassian.load_backlog(p)
        f = atlassian.get_feature(data, 3)

        body = atlassian.cuerpo_confluence(p, f, ["AC-1", "AC-2"])

        self.assertIn("PRD maestro", body)
        self.assertIn("SDD", body)
        self.assertIn("Diseno implementado por feature", body)


if __name__ == "__main__":
    unittest.main()
