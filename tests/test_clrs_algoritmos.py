"""Tests para algoritmos y estructuras de datos (CLRS) en harness-flow:
- Deteccion de ciclos mediante DFS de 3 colores (detectar_ciclos_dependencias).
- Ordenamiento topologico de features mediante algoritmo de Kahn (orden_topologico_features).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from comun import detectar_ciclos_dependencias, orden_topologico_features  # noqa: E402


class ClrsAlgoritmosTests(unittest.TestCase):
    def test_dag_sin_ciclos_retorna_vacio(self):
        data = {
            "features": [
                {"id": 0, "name": "normalizar"},
                {"id": 1, "name": "base", "requiere": [0]},
                {"id": 2, "name": "auth", "requiere": ["#1"]},
                {"id": 3, "name": "billing", "requiere": ["#2"]},
            ]
        }
        ciclos = detectar_ciclos_dependencias(data)
        self.assertEqual(ciclos, [])

    def test_ciclo_directo_detectado(self):
        data = {
            "features": [
                {"id": 1, "name": "feat-1", "requiere": ["#2"]},
                {"id": 2, "name": "feat-2", "requiere": ["#1"]},
            ]
        }
        ciclos = detectar_ciclos_dependencias(data)
        self.assertTrue(len(ciclos) > 0)
        self.assertEqual(ciclos[0][0], ciclos[0][-1])

    def test_ciclo_triangular_detectado(self):
        data = {
            "features": [
                {"id": 1, "name": "feat-1", "requiere": ["#2"]},
                {"id": 2, "name": "feat-2", "requiere": ["#3"]},
                {"id": 3, "name": "feat-3", "requiere": ["#1"]},
            ]
        }
        ciclos = detectar_ciclos_dependencias(data)
        self.assertTrue(len(ciclos) > 0)
        self.assertEqual(ciclos[0][0], ciclos[0][-1])
        self.assertEqual(set(ciclos[0]), {"1", "2", "3"})

    def test_auto_ciclo_detectado(self):
        data = {
            "features": [
                {"id": 1, "name": "feat-1", "requiere": ["#1"]},
            ]
        }
        ciclos = detectar_ciclos_dependencias(data)
        self.assertEqual(ciclos, [["1", "1"]])

    def test_ciclo_con_candidatas_prd(self):
        data = {
            "features": [
                {"id": 1, "prd_candidata": "F-1", "requiere": ["F-2"]},
                {"id": 2, "prd_candidata": "F-2", "requiere": ["F-1"]},
            ]
        }
        ciclos = detectar_ciclos_dependencias(data)
        self.assertTrue(len(ciclos) > 0)
        self.assertEqual(ciclos[0][0], ciclos[0][-1])

    def test_orden_topologico_kahn_valido(self):
        data = {
            "features": [
                {"id": 2, "name": "billing", "requiere": ["#1"]},
                {"id": 0, "name": "setup"},
                {"id": 1, "name": "auth", "requiere": [0]},
                {"id": 3, "name": "reports", "requiere": ["#1"]},
            ]
        }
        orden = orden_topologico_features(data)
        self.assertEqual(len(orden), 4)
        pos = {fid: idx for idx, fid in enumerate(orden)}

        # 0 debe preceder a 1
        self.assertLess(pos["0"], pos["1"])
        # 1 debe preceder a 2 y a 3
        self.assertLess(pos["1"], pos["2"])
        self.assertLess(pos["1"], pos["3"])

    def test_orden_topologico_lanza_error_si_hay_ciclo(self):
        data = {
            "features": [
                {"id": 1, "name": "feat-1", "requiere": ["#2"]},
                {"id": 2, "name": "feat-2", "requiere": ["#1"]},
            ]
        }
        with self.assertRaises(ValueError) as ctx:
            orden_topologico_features(data)
        self.assertIn("Ciclo de dependencias detectado", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
