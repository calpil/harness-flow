"""Contexto: grafo multi-raiz, frescura y brief compacto.

Lo que se prueba es lo que fallo de verdad: con los micros en OTRA raiz del
disco, el arnes consultaba solo el grafo del front y las consultas volvian
vacias. Y nada refrescaba el grafo, asi que envejecia indefinidamente.
"""
from __future__ import annotations

import io
import json
import contextlib
import os
import sys
import tempfile
import time
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import comun  # noqa: E402
import contexto  # noqa: E402


def _grafo(nodes, links, directed=True):
    return {"directed": directed, "multigraph": False, "graph": {},
            "nodes": nodes, "links": links}


class ContextoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "front"
        (self.root / "harness" / "progress").mkdir(parents=True)
        (self.root / "docs").mkdir()
        self.otra = Path(self.tmp.name) / "micros"
        (self.otra / "graphify-out").mkdir(parents=True)
        self.prev = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(lambda: os.chdir(self.prev))
        (self.root / "harness" / "feature_list.json").write_text(json.dumps({
            "project": "demo",
            "rules": {"require_spec_approved": False, "require_review": False,
                      "require_leccion": False, "require_verify_green": False,
                      "require_docs_al_dia": False},
            "features": [{"id": 1, "name": "Deuda tenant", "status": "in_progress",
                          "microservicios": ["ms-tenant-service"]}],
        }), encoding="utf-8")
        (self.root / "docs" / "spec-feature-1-deuda-tenant.md").write_text(
            "Estado: approved\n\n- AC-1: cobra la deuda `verificar: go test ./...`\n",
            encoding="utf-8")

    def _declarar(self, max_horas=12):
        (self.root / "harness" / "grafos.json").write_text(json.dumps({
            "max_horas": max_horas,
            "raices": [{"nombre": "front", "path": "."},
                       {"nombre": "micros", "path": str(self.otra)}],
        }), encoding="utf-8")

    # --- multi-raiz --------------------------------------------------------

    def test_sin_config_usa_la_raiz_del_arnes(self):
        p = comun.paths(self.root)
        self.assertEqual(p["graph"], self.root / "graphify-out" / "graph.json")
        self.assertEqual([r["nombre"] for r in comun.raices_grafo(p)],
                         [self.root.name])

    def test_varias_raices_apuntan_al_combinado(self):
        self._declarar()
        p = comun.paths(self.root)
        self.assertEqual(p["graph"],
                         self.root / "graphify-out" / "merged-graph.json")
        nombres = [r["nombre"] for r in comun.raices_grafo(p)]
        self.assertEqual(nombres, ["front", "micros"])

    def test_raiz_inexistente_es_error_y_no_se_ignora(self):
        (self.root / "harness" / "grafos.json").write_text(json.dumps({
            "raices": [{"nombre": "fantasma", "path": "/no/existe/jamas"}],
        }), encoding="utf-8")
        with self.assertRaises(SystemExit):
            comun.raices_grafo(comun.paths(self.root))

    # --- frescura ----------------------------------------------------------

    def test_grafo_ausente_marca_contexto_vencido(self):
        self._declarar()
        e = contexto.estado_contexto(comun.paths(self.root))
        self.assertFalse(e["fresco"])
        self.assertIn("micros", e["vencidas"])

    def test_combinado_mas_viejo_que_una_raiz_esta_vencido(self):
        self._declarar()
        (self.root / "graphify-out").mkdir(parents=True, exist_ok=True)
        comb = self.root / "graphify-out" / "merged-graph.json"
        for f in (self.root / "graphify-out" / "graph.json",
                  self.otra / "graphify-out" / "graph.json", comb):
            f.write_text("{}", encoding="utf-8")
        viejo = time.time() - 3600
        os.utime(comb, (viejo, viejo))
        e = contexto.estado_contexto(comun.paths(self.root))
        self.assertIn("(combinado)", e["vencidas"])
        self.assertFalse(e["fresco"])

    def test_todo_reciente_es_fresco(self):
        self._declarar()
        (self.root / "graphify-out").mkdir(parents=True, exist_ok=True)
        for f in (self.root / "graphify-out" / "graph.json",
                  self.otra / "graphify-out" / "graph.json",
                  self.root / "graphify-out" / "merged-graph.json"):
            f.write_text("{}", encoding="utf-8")
        with mock.patch.object(contexto.shutil, "which", return_value="/bin/graphify"):
            e = contexto.estado_contexto(comun.paths(self.root))
        self.assertTrue(e["fresco"], e["vencidas"])

    def test_refrescar_sin_graphify_reporta_fallo_no_exito(self):
        self._declarar()
        with mock.patch.object(contexto.shutil, "which", return_value=None):
            parte = contexto.refrescar(comun.paths(self.root), verboso=False)
        self.assertTrue(parte["fallos"])
        self.assertEqual(parte["actualizadas"], [])

    def test_refrescar_combina_las_raices_con_rutas_absolutas(self):
        self._declarar()
        (self.root / "graphify-out").mkdir(parents=True, exist_ok=True)
        (self.root / "graphify-out" / "graph.json").write_text("{}", encoding="utf-8")
        (self.otra / "graphify-out" / "graph.json").write_text("{}", encoding="utf-8")
        llamadas = []

        def fake_run(cmd, cwd):
            llamadas.append(cmd)
            return 0, "ok"

        with mock.patch.object(contexto.shutil, "which", return_value="/bin/graphify"), \
                mock.patch.object(contexto, "_run", side_effect=fake_run):
            parte = contexto.refrescar(comun.paths(self.root), forzar=True,
                                       verboso=False)
        merge = [c for c in llamadas if "merge-graphs" in c]
        self.assertEqual(len(merge), 1, llamadas)
        idx = merge[0].index("--out")
        grafos = merge[0][1:idx]  # tras 'merge-graphs', antes de --out
        grafos = [x for x in grafos if x != "merge-graphs"]
        self.assertEqual(len(grafos), 2, grafos)
        self.assertTrue(Path(merge[0][idx + 1]).is_absolute())
        for g in grafos:
            self.assertTrue(Path(g).is_absolute(), g)
        self.assertEqual(parte["fallos"], [])

    # --- brief -------------------------------------------------------------

    def test_superficie_ordena_por_acoplamiento_y_excluye_estructura(self):
        nodes = [
            {"id": "a", "source_file": "ms-tenant-service/handlers/deuda.go"},
            {"id": "b", "source_file": "ms-tenant-service/repo/deuda.go"},
            {"id": "c", "source_file": "ms-client-service/api/client.go"},
            {"id": "d", "source_file": "ms-tenant-service/handlers/deuda.go"},
        ]
        links = [
            {"source": "a", "target": "b", "relation": "calls"},
            {"source": "a", "target": "b", "relation": "calls"},
            {"source": "a", "target": "c", "relation": "imports"},
            # 'contains' es estructura interna: no debe contar
            {"source": "a", "target": "d", "relation": "contains"},
        ]
        s = contexto.superficie(_grafo(nodes, links), ["ms-tenant-service"])
        top = dict(s["archivos"])
        self.assertEqual(top["ms-tenant-service/handlers/deuda.go"], 3)
        cruces = {(fs, ft, rel): n for (fs, ft, rel), n in s["cruces"]}
        self.assertIn(("ms-tenant-service/handlers/deuda.go",
                       "ms-client-service/api/client.go", "imports"), cruces)
        self.assertNotIn("contains", [r for (_f, _t, r) in cruces])

    def test_brief_incluye_ac_comando_y_avisa_grafo_vencido(self):
        self._declarar()
        buf = io.StringIO()
        with mock.patch.object(contexto, "_lecciones", return_value=[]), \
                mock.patch.object(contexto, "_impacto_hub", return_value=["x"]), \
                contextlib.redirect_stdout(buf):
            contexto.cmd_brief(Namespace(feature="1", max_lineas=200,
                                         max_archivos=5, max_lecciones=5))
        out = buf.getvalue()
        self.assertIn("AC-1", out)
        self.assertIn("go test ./...", out)
        self.assertIn("contexto VENCIDO", out)
        self.assertIn("sin grafo", out)

    def test_brief_recorta_por_el_medio_y_conserva_las_rutas(self):
        """El pie (spec/evidencia) es lo unico accionable: no puede recortarse.

        Antes se truncaba por el final, asi que un brief largo perdia justo las
        rutas que el agente tiene que abrir y quedaba en puro indice.
        """
        self._declarar()
        buf = io.StringIO()
        with mock.patch.object(contexto, "_lecciones", return_value=[]), \
                mock.patch.object(contexto, "_impacto_hub", return_value=["x"] * 40), \
                contextlib.redirect_stdout(buf):
            contexto.cmd_brief(Namespace(feature="1", max_lineas=12,
                                         max_archivos=5, max_lecciones=5))
        lineas = buf.getvalue().rstrip("\n").splitlines()
        self.assertLessEqual(len(lineas), 12)
        self.assertTrue(any("recortadas" in l for l in lineas), lineas)
        self.assertTrue(any(l.startswith("spec:") for l in lineas), lineas)
        self.assertTrue(any(l.startswith("evidencia:") for l in lineas), lineas)

    # --- ruido que hacia caro el brief -------------------------------------

    def test_micros_declarados_parte_una_cadena_con_comas(self):
        """El backlog real trae 'a, b (comentario)' en un solo elemento."""
        f = {"microservicios": ["ms-tenant-service, landing (solo el alta)"]}
        self.assertEqual(contexto._micros_declarados(f),
                         ["ms-tenant-service", "landing"])

    def test_micros_sin_nodos_se_reportan_en_vez_de_callarse(self):
        nodes = [{"id": "a", "source_file": "ms-otro/api.go"}]
        s = contexto.superficie(_grafo(nodes, []), ["ms-fantasma"])
        self.assertEqual(s["sin_match"], ["ms-fantasma"])

    def test_cruces_ignoran_nodos_sin_archivo(self):
        """Un nodo sin source_file generaba filas 'a --calls--> ' inutiles."""
        nodes = [{"id": "a", "source_file": "ms-tenant-service/h.go"},
                 {"id": "b"}]
        links = [{"source": "a", "target": "b", "relation": "calls"}]
        s = contexto.superficie(_grafo(nodes, links), ["ms-tenant-service"])
        self.assertEqual(s["cruces"], [])

    def test_lecciones_solo_las_usadas_por_el_proyecto(self):
        """leccion.py list enumera >100 skills del perfil: pegarlas es ruido."""
        data = {"features": [{"id": 1, "leccion": "gates-que-no-mienten"},
                             {"id": 2, "leccion": "ninguna"},
                             {"id": 3}]}
        salida = ("   software-development/gates-que-no-mienten  306 lineas\n"
                  "   otra-cosa/no-usada  10 lineas\n")
        with mock.patch.object(contexto, "_run", return_value=(0, salida)):
            filas = contexto._lecciones(data)
        self.assertEqual(len(filas), 1)
        self.assertIn("gates-que-no-mienten", filas[0])

    def test_leccion_declarada_sin_skill_instalada_se_marca(self):
        data = {"features": [{"id": 1, "leccion": "nunca-se-escribio"}]}
        with mock.patch.object(contexto, "_run", return_value=(0, "")):
            filas = contexto._lecciones(data)
        self.assertIn("FALTA", filas[0])

    def test_impacto_compacto_resume_en_una_linea(self):
        reporte = ["== Impacto de demo/ms-tenant-service ==",
                   "Si tocas esto, se puede romper (2):",
                   "   <- demo/ms-auth-service  [DEPENDE_DE]",
                   "   <- demo/ms-media-service  [DEPENDE_DE]",
                   "Depende de (1):",
                   "   -> demo/ms-client-service  [DEPENDE_DE]"]
        with mock.patch.object(contexto, "_impacto_hub", return_value=reporte):
            filas = contexto._impacto_compacto("demo", "ms-tenant-service")
        self.assertEqual(len(filas), 1)
        self.assertIn("ms-auth-service, ms-media-service", filas[0])
        self.assertIn("usa: ms-client-service", filas[0])

    # --- escape para CI y para los tests del propio arnes -------------------

    def test_variable_de_entorno_apaga_el_refresco(self):
        with mock.patch.dict(os.environ, {"HARNESS_SIN_CONTEXTO": "1"}):
            self.assertTrue(contexto._desactivado())
        with mock.patch.dict(os.environ, {"HARNESS_SIN_CONTEXTO": "0"}):
            self.assertFalse(contexto._desactivado())

    def test_la_variable_apaga_el_automatico_pero_no_el_explicito(self):
        """Si apagara `refrescar()`, el comando explicito mentiria en CI.

        HARNESS_SIN_CONTEXTO existe para que start/close no lancen graphify,
        no para que `contexto.py refrescar` devuelva un parte vacio y en verde.
        """
        self._declarar()
        with mock.patch.dict(os.environ, {"HARNESS_SIN_CONTEXTO": "1"}):
            p = comun.paths(self.root)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertIsNone(
                    contexto.refrescar_si_vencido(p, etiqueta="arrancar #1"))
            with mock.patch.object(contexto.shutil, "which", return_value=None):
                parte = contexto.refrescar(p, verboso=False)
        self.assertTrue(parte["fallos"])


if __name__ == "__main__":
    unittest.main()
