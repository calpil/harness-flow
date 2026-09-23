"""Brief: documentos de docs/ relacionados con la feature, solo rutas.

Buscar en docs/ por nombre de servicio a secas no sirve: en realestate
`ms-tenant-service` aparece en 539 archivos (~2,7M tokens). El brief da un
puñado de rutas ordenadas y el leader abre las que toquen su diseno.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import comun  # noqa: E402
import contexto  # noqa: E402


class RelacionadosTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "harness").mkdir()
        self.prev = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(lambda: os.chdir(self.prev))
        (self.root / "harness" / "feature_list.json").write_text(json.dumps({
            "project": "demo", "rules": {},
            "features": [
                {"id": 5, "name": "Cobro", "status": "in_progress",
                 "microservicios": ["ms-cobro-service, admin (solo lectura)"]},
                {"id": 3, "name": "Cobro viejo", "status": "done",
                 "closed_at": "2026-09-01T00:00:00Z",
                 "microservicios": ["demo/ms-cobro-service"]},
                {"id": 4, "name": "Otro servicio", "status": "done",
                 "closed_at": "2026-09-02T00:00:00Z",
                 "microservicios": ["ms-otro-service"]},
                {"id": 50, "name": "Cincuenta", "status": "todo"},
            ]}), encoding="utf-8")
        docs = self.root / "docs"
        for rel, texto in {
            "spec-feature-5-cobro.md": "Estado: approved\n- AC-1: x\n",  # en el pie
            "impl-5.md": "| AC-1 | a.go:1 |\n",                          # en el pie
            "review-5.md": "ronda 1\n",
            "decisiones-5.md": "se decidio X\n",
            "artefactos-5/a.md": "a\n", "artefactos-5/b.md": "b\n",
            "review-50-algo.md": "de la #50, no de la #5\n",
            "enmienda-pagos.md": "ms-cobro-service no reintenta\n",
            "acta-otra.md": "lo vio el administrador\n",
            "review-3.md": "Veredicto\n", "review-4.md": "Veredicto\n",
            "vault/notas/mia.md": "ojo con [[Feature-5]]\n",
            "vault/notas/otra.md": "de [[Feature-50]]\n",
            "vault/features/Feature-5.md": "generada: ms-cobro-service\n",
            ".obsidian/x.md": "ms-cobro-service\n",
        }.items():
            q = docs / rel
            q.parent.mkdir(parents=True, exist_ok=True)
            q.write_text(texto, encoding="utf-8")

    def _rel(self, tope=8):
        p = comun.paths(self.root)
        data = comun.load_backlog(p)
        f = comun.get_feature(data, 5)
        return contexto._relacionados(p, data, f, contexto._micros_declarados(f), tope)

    def _filas(self, lineas):
        """{tipo: [ruta, ...]} de las lineas del brief."""
        out: dict[str, list[str]] = {}
        for ln in lineas[2:]:
            partes = ln.split()
            if partes and not ln.lstrip().startswith("(+"):
                out.setdefault(partes[0], []).append(partes[1])
        return out

    def test_lista_lo_propio_decisiones_notas_y_previas(self):
        filas = self._filas(self._rel())
        self.assertEqual(filas.get("tuya"), ["docs/vault/notas/mia.md"])
        self.assertCountEqual(filas.get("feature"), [
            "docs/review-5.md", "docs/decisiones-5.md", "docs/artefactos-5/"])
        self.assertEqual(filas.get("decision"), ["docs/enmienda-pagos.md"])
        self.assertEqual(filas.get("previa"), ["docs/review-3.md"])

    def test_no_lista_ruido(self):
        """Pie, vault generado, .obsidian, otra feature y 'admin' sin borde."""
        todo = "\n".join(self._rel())
        for ruido in ("spec-feature-5-cobro", "impl-5", "review-50-algo",
                      "vault/features", ".obsidian", "acta-otra", "otra.md",
                      "review-4"):
            self.assertNotIn(ruido, todo)

    def test_el_tope_corta_por_prioridad_y_avisa(self):
        lineas = self._rel(tope=2)
        filas = self._filas(lineas)
        self.assertEqual(sum(len(v) for v in filas.values()), 2)
        self.assertIn("tuya", filas)            # lo tuyo va primero
        self.assertNotIn("previa", filas)       # las vecinas, al final
        self.assertIn("(+4 mas sin listar)", lineas[-1])

    def test_tope_cero_no_agrega_seccion(self):
        self.assertEqual([], self._rel(tope=0))

    def _brief(self, **extra):
        buf = io.StringIO()
        with mock.patch.object(contexto, "_lecciones", return_value=[]), \
                mock.patch.object(contexto, "_impacto_hub", return_value=["x"]), \
                contextlib.redirect_stdout(buf):
            contexto.cmd_brief(Namespace(feature="5", max_lineas=200,
                                         max_archivos=5, max_lecciones=5, **extra))
        return buf.getvalue()

    def test_brief_la_trae_por_defecto_y_el_revisor_no(self):
        """worktree.py start no pasa el argumento: le toca la seccion. El
        revisor (revision.py) pasa 0: juzga spec contra codigo, no la historia."""
        self.assertIn("documentos relacionados", self._brief())
        self.assertNotIn("documentos relacionados", self._brief(max_relacionados=0))
        src = (SCRIPTS / "revision.py").read_text(encoding="utf-8")
        self.assertIn("max_relacionados=0", src)


if __name__ == "__main__":
    unittest.main()
