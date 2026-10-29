"""El panorama cuenta el backlog real sin convertir pendientes en cierres."""
import contextlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "estado.py"


class EstadoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.backlog = self.root / "harness" / "feature_list.json"
        self.backlog.parent.mkdir()

    def panorama(self, features):
        self.backlog.write_text(json.dumps({
            "project": "prueba", "rules": {"require_docs_al_dia": False}, "features": features,
        }, ensure_ascii=False) + "\n", encoding="utf-8")
        antes = self.backlog.read_bytes()
        resultado = subprocess.run(
            [sys.executable, str(SCRIPT)], cwd=self.root,
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
        self.assertEqual(self.backlog.read_bytes(), antes, "el panorama no debe reescribir estados")
        self.assertEqual(resultado.stderr, "")
        return resultado.stdout

    def test_avisa_del_daemon_cbm_sin_socket_al_arrancar_la_sesion(self):
        """El aviso sale en el panorama de arranque aunque ningun cierre haya quedado
        pendiente: lo que se mide en ese momento, no lo guardado."""
        sys.path.insert(0, str(SCRIPT.parent))
        import contexto
        import estado
        self.backlog.write_text(json.dumps({
            "project": "prueba", "rules": {"require_docs_al_dia": False}, "features": [],
        }) + "\n", encoding="utf-8")
        antes = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, antes)
        salida = io.StringIO()
        with mock.patch.object(contexto, "_cbm_daemon_sin_socket", return_value=[4242]), \
                mock.patch.object(contexto.shutil, "which", return_value="/x"), \
                mock.patch.dict(os.environ, {"HARNESS_SIN_CBM": ""}), \
                contextlib.redirect_stdout(salida):
            estado.main()
        self.assertIn("El daemon cbm (pid 4242) esta vivo pero su socket ya no existe",
                      salida.getvalue())
        self.assertIn("limpiar-cbm --reiniciar-daemon", salida.getvalue())

    def test_pending_se_cuenta_y_se_lista_como_abierta(self):
        out = self.panorama([
            {"id": 1, "name": "En curso", "status": "in_progress"},
            {"id": 2, "name": "En review", "status": "review"},
            {"id": 3, "name": "Pendiente", "status": "pending"},
            {"id": 4, "name": "Terminada", "status": "done"},
        ])
        self.assertIn("features: 3 abiertas, 1 cerradas", out)
        filas = re.findall(r"^   #(\d+) \[([^\]]+)\]", out, re.MULTILINE)
        self.assertEqual(filas, [("1", "in_progress"), ("2", "review"), ("3", "pending")])
        self.assertIn("retoma la feature #1", out)

    def test_estado_desconocido_no_se_cuenta_como_cerrado(self):
        out = self.panorama([
            {"id": 1, "name": "Pendiente", "status": "pending"},
            {"id": 2, "name": "Estado nuevo", "status": "awaiting_approval"},
            {"id": 3, "name": "Terminada", "status": "done"},
        ])
        self.assertIn("features: 1 abiertas, 1 cerradas", out)
        self.assertIn("1 con estado desconocido", out)
        self.assertIn("#2 [awaiting_approval]", out)
        self.assertIn("estado desconocido", out)
        self.assertIn("arranca la #1", out)

    def test_solo_desconocidos_no_sugiere_que_el_backlog_esta_vacio(self):
        for valor in ("awaiting_approval", "", None):
            with self.subTest(status=valor):
                out = self.panorama([{"id": 9, "name": "Sin clasificar", "status": valor}])
                self.assertIn("features: 0 abiertas, 0 cerradas", out)
                self.assertIn("1 con estado desconocido", out)
                self.assertIn("#9", out)
                self.assertNotIn("Nada en curso", out)
                self.assertNotIn("arranca la", out)
                self.assertIn("revisa", out.lower())

    def test_cierres_distinguen_done_de_superseded(self):
        out = self.panorama([
            {"id": 1, "name": "Terminada", "status": "done"},
            {"id": 2, "name": "Reemplazada", "status": "superseded"},
            {"id": 3, "name": "Otra terminada", "status": "done"},
        ])
        self.assertIn("features: 0 abiertas, 3 cerradas (2 done, 1 superseded)", out)
        self.assertNotIn("estado desconocido", out)
        self.assertIn("Nada en curso", out)

    def test_cada_estado_abierto_sigue_visible_y_pending_se_puede_sugerir(self):
        for status in ("pending", "todo", "in_progress", "blocked", "review"):
            with self.subTest(status=status):
                out = self.panorama([{"id": 1, "name": "Abierta", "status": status}])
                self.assertIn("features: 1 abiertas, 0 cerradas", out)
                self.assertIn(f"#1 [{status}] Abierta", out)
                self.assertNotIn("Nada en curso", out)
                self.assertNotIn("estado desconocido", out)
                if status == "in_progress":
                    self.assertIn("retoma la feature #1", out)
                elif status in ("todo", "pending"):
                    self.assertIn("arranca la #1", out)
                else:
                    self.assertNotIn("arranca la", out)
                    self.assertIn("revisa", out.lower())

    def test_sugiere_pending_o_todo_antes_de_blocked_o_review(self):
        for activa in ("blocked", "review"):
            for pendiente in ("pending", "todo"):
                with self.subTest(activa=activa, pendiente=pendiente):
                    out = self.panorama([
                        {"id": 1, "name": "Ya iniciada", "status": activa},
                        {"id": 2, "name": "Por iniciar", "status": pendiente},
                    ])
                    self.assertIn("arranca la #2: worktree.py start --feature 2", out)
                    self.assertNotIn("arranca la #1", out)

    def test_in_progress_gana_a_pending_aunque_este_despues(self):
        out = self.panorama([
            {"id": 1, "name": "Por iniciar", "status": "pending"},
            {"id": 2, "name": "Ya iniciada", "status": "in_progress"},
        ])
        self.assertIn("retoma la feature #2", out)
        self.assertNotIn("arranca la", out)

    def test_status_ausente_se_reporta_sin_reescribirlo(self):
        out = self.panorama([{"id": 1, "name": "Falta status"}])
        self.assertIn("features: 0 abiertas, 0 cerradas", out)
        self.assertIn("1 con estado desconocido", out)
        self.assertIn("#1 [None]", out)
        self.assertNotIn("Nada en curso", out)

    def test_backlog_vacio_conserva_sugerencia_de_alta(self):
        out = self.panorama([])
        self.assertIn("features: 0 abiertas, 0 cerradas (0 done, 0 superseded)", out)
        self.assertIn("Nada en curso", out)
        self.assertIn("add.py --name", out)
        self.assertNotIn("estado desconocido", out)

    def test_frontera_prioriza_feature_sin_bloqueos_y_reporta_cuando_todas_estan_bloqueadas(self):
        out = self.panorama([
            {"id": 1, "name": "Depende de 2", "status": "todo", "requiere": [2]},
            {"id": 2, "name": "Walking skeleton", "status": "todo"},
        ])
        self.assertIn("#1 [todo] Depende de 2", out)
        self.assertIn("bloqueada por #2 (todo)", out)
        self.assertIn("arranca la #2: worktree.py start --feature 2", out)

        out_desbloqueada = self.panorama([
            {"id": 1, "name": "Depende de 2", "status": "todo", "requiere": [2]},
            {"id": 2, "name": "Walking skeleton", "status": "done"},
        ])
        self.assertIn("dependencias ok", out_desbloqueada)
        self.assertIn("arranca la #1: worktree.py start --feature 1", out_desbloqueada)

        out_todas_bloq = self.panorama([
            {"id": 1, "name": "Bloqueada A", "status": "todo", "requiere": ["F-9"]},
        ])
        self.assertIn("la #1 esta bloqueada por F-9 (sin feature): cierra primero su dependencia", out_todas_bloq)


if __name__ == "__main__":
    unittest.main()
