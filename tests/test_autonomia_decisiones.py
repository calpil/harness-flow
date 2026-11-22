#!/usr/bin/env python3
"""Lo que el usuario decidio sobre los tres mecanismos de autonomia (2026-11-22).

`test_mecanismos_autonomia.py` cubre el Feature Map, los evals y el motor de
guardrails. Este archivo fija cuatro decisiones del usuario y un limite:

1. Los AC de verificacion manual los comprueba PRIMERO el agente, con evidencia;
   al usuario le llegan solo los que el agente no pudo comprobar. Antes iban
   directo al usuario y `close` cerraba sin constancia de que alguien los mirara.
2. Un guardrail lo propone el agente y lo registra el SI del usuario. Antes
   `agregar` y `promover` registraban sin preguntar.
3. Los guardrails bloquean tambien la subida, con un hook `pre-push` que instala
   el usuario. Antes solo bloqueaban `verify` y `close`.
4. Un eval lleva un grupo de control sin la skill: prueba que el examen puede
   fallar. Antes un examen que cualquiera aprueba contaba como PASS.
5. La exigencia del Feature Map rige para los specs que se aprueben desde ahora.
   Antes `close` se la exigia tambien a las features que ya estaban en curso.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import evals

from test_mecanismos_autonomia import correr, crear_repo_base, escribir, sh

SPEC_UI = ("# Spec - Feature #1: registro\n\nEstado: draft\n\n## Criterios de aceptacion\n\n"
           "- AC-1 [costura: ui]: el formulario crea la cuenta. `verificar: true`\n")
SPEC_MANUAL = ("# Spec - Feature #1: recibo\n\nEstado: draft\n\n## Criterios de aceptacion\n\n"
               "- AC-1 [costura: servicio]: calcula el total. `verificar: true`\n"
               "- AC-2 [costura: manual]: el recibo impreso muestra el total.\n")
LISTA_MANUAL = ("# Lista de tests - Feature #1\n\nEstado: draft\n\n"
                "- AC-1: calcula_el_total [costura: servicio]\n"
                "- AC-2: verificacion manual: el recibo impreso muestra el total\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="harness-decisiones-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def feature(self) -> dict:
        return json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))["features"][0]

    def guardar_feature(self, f: dict) -> None:
        ruta = self.root / "harness" / "feature_list.json"
        data = json.loads(ruta.read_text(encoding="utf-8"))
        data["features"][0] = f
        ruta.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def en_curso(self, spec: str, nombre: str, lista: str | None = None) -> Path:
        """Feature #1 aprobada, en su worktree, con un commit de trabajo. Devuelve el worktree."""
        self.root = crear_repo_base(self.tmp, feature={"id": 1, "name": nombre, "kind": "feature",
                                                       "status": "todo"}, spec_text=spec)
        self.ok("gate.py", "approve-spec", "--feature", "1", "--yes", "--por", "T")
        self.ok("worktree.py", "start", "--feature", "1", *([] if lista else ["--delegado", "--yes"]))
        wt = Path(self.feature()["worktree"])
        escribir(wt / "src/app.ts", "export const ok = true;\nexport const nuevo = 1;\n")
        sh("git", "add", "src/app.ts", cwd=wt)
        sh("git", "commit", "-q", "-m", "feat: trabajo", cwd=wt)
        escribir(self.root / "docs" / "impl-1.md", "## AC-1\n\nsrc/app.ts:2\n\n## AC-2\n\nsrc/app.ts:2\n")
        if lista:
            escribir(self.root / "docs" / "tests-1.md", lista)
            self.ok("gate.py", "sellar-tests", "--feature", "1", "--por", "T")
        self.commit("docs")
        return wt

    def ok(self, script, *args, **kw):
        r = correr(script, *args, cwd=self.root, **kw)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        return r

    def commit(self, mensaje: str) -> None:
        sh("git", "add", "-A", cwd=self.root)
        subprocess.run(["git", "commit", "-q", "-m", mensaje], cwd=str(self.root), capture_output=True)

    def cerrar(self):
        self.commit("antes de cerrar")
        return correr("gate.py", "close", "--feature", "1", "--status", "done", "--to", "develop", cwd=self.root)


class SoloSpecsNuevosTests(Base):
    def test_la_primera_aprobacion_del_spec_deja_la_marca(self):
        self.en_curso(SPEC_UI, "registro")
        self.assertTrue(self.feature()["autocomprobacion"])

    def test_una_feature_aprobada_antes_de_la_regla_cierra_sin_feature_map_y_lo_avisa(self):
        self.en_curso(SPEC_UI, "registro")
        f = self.feature()
        del f["autocomprobacion"]
        self.guardar_feature(f)
        r = self.cerrar()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("feature-map:", r.stdout)
        self.assertEqual("done", self.feature()["status"])

    def test_una_feature_aprobada_con_la_regla_sigue_bloqueada_sin_feature_map(self):
        """El control: la marca no apaga el gate para los specs nuevos."""
        self.en_curso(SPEC_UI, "registro")
        r = self.cerrar()
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)
        self.assertIn("feature-map:", r.stdout)


class AcManualesTests(Base):
    def setUp(self):
        super().setUp()
        self.en_curso(SPEC_MANUAL, "recibo", LISTA_MANUAL)
        self.evidencia = self.tmp / "recibo.txt"
        self.evidencia.write_text("TOTAL 1.500\n", encoding="utf-8")

    def registrar(self, *args, ac="AC-2"):
        return correr("comprobacion.py", "registrar", "--feature", "1", "--ac", ac, *args, cwd=self.root)

    def ok_del_agente(self):
        return self.registrar("--resultado", "ok", "--como", "imprimi el recibo del cobro 1",
                              "--observado", "muestra TOTAL 1.500", "--evidencia", str(self.evidencia))

    def test_un_ac_manual_que_nadie_comprobo_no_cierra(self):
        r = self.cerrar()
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)
        self.assertIn("AC-2 es de verificacion manual y nadie lo comprobo", r.stdout)
        self.assertIn("compruebalo TU", r.stdout)

    def test_cierra_con_la_comprobacion_del_agente_y_su_evidencia(self):
        self.assertEqual(0, self.ok_del_agente().returncode)
        c = self.feature()["comprobaciones"]["AC-2"]
        self.assertEqual(("ok", "agente", len("TOTAL 1.500\n")), (c["resultado"], c["quien"], c["evidencia"][0]["size"]))
        r = self.cerrar()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_la_comprobacion_del_agente_exige_que_hizo_que_vio_y_evidencia(self):
        casos = {"--como": ["--observado", "x", "--evidencia", str(self.evidencia)],
                 "--observado": ["--como", "x", "--evidencia", str(self.evidencia)],
                 "--evidencia": ["--como", "x", "--observado", "y"],
                 "evidencia no existe": ["--como", "x", "--observado", "y", "--evidencia", str(self.tmp / "nada.png")]}
        for falta, args in casos.items():
            with self.subTest(falta=falta):
                r = self.registrar("--resultado", "ok", *args)
                self.assertNotEqual(0, r.returncode)
                self.assertIn(falta, r.stdout + r.stderr)
        self.assertNotIn("comprobaciones", self.feature())

    def test_una_comprobacion_que_fallo_no_cierra(self):
        self.registrar("--resultado", "falla", "--como", "imprimi el recibo", "--observado", "total en blanco",
                       "--evidencia", str(self.evidencia))
        r = self.cerrar()
        self.assertEqual(1, r.returncode)
        self.assertIn("FALLO: total en blanco", r.stdout)

    def test_lo_que_el_agente_no_pudo_comprobar_espera_al_usuario(self):
        r = self.registrar("--resultado", "no-pude", "--como", "no hay impresora en este entorno")
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("UN formulario", r.stdout)
        r = self.cerrar()
        self.assertEqual(1, r.returncode)
        self.assertIn("Pidele al usuario", r.stdout)
        self.assertEqual(0, self.registrar("--resultado", "ok", "--usuario", "--yes", "--por", "Alan").returncode)
        r = self.cerrar()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_el_agente_no_registra_por_el_usuario(self):
        r = self.registrar("--resultado", "ok", "--como", "x", "--observado", "y",
                           "--evidencia", str(self.evidencia), "--yes", "--por", "Alan")
        self.assertNotEqual(0, r.returncode)
        self.assertNotEqual(0, self.registrar("--resultado", "ok", "--usuario").returncode)
        self.assertNotEqual(0, self.registrar("--resultado", "ok", "--usuario", "--yes").returncode)
        self.assertNotIn("comprobaciones", self.feature())

    def test_una_comprobacion_anterior_a_una_enmienda_ya_no_vale(self):
        self.ok_del_agente()
        f = self.feature()
        f["enmiendas"] = [{"id": "E1"}]
        self.guardar_feature(f)
        r = correr("comprobacion.py", "pendientes", "--feature", "1", cwd=self.root)
        self.assertIn("antes de la ultima enmienda", r.stdout)

    def test_una_feature_aprobada_antes_de_la_regla_no_la_exige(self):
        f = self.feature()
        del f["autocomprobacion"]
        self.guardar_feature(f)
        r = self.cerrar()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_el_brief_manda_a_comprobar_antes_de_pedir_al_usuario(self):
        r = self.ok("contexto.py", "brief", "--feature", "1")
        self.assertIn("AC de verificacion manual (AC-2): compruebalos TU primero", r.stdout)
        self.assertIn("solo los que no pudiste comprobar", r.stdout)


class GuardrailConElSiDelUsuarioTests(Base):
    def setUp(self):
        super().setUp()
        self.root = crear_repo_base(self.tmp, feature={"id": 1, "name": "x", "kind": "feature", "status": "todo"},
                                    spec_text=SPEC_UI)

    def reglas(self) -> list[str]:
        ruta = self.root / "harness" / "guardrails.json"
        return [r["id"] for r in json.loads(ruta.read_text(encoding="utf-8"))["reglas"]] if ruta.is_file() else []

    def agregar(self, *extra):
        return correr("guardrails.py", "agregar", "--id", "sin-atajo", "--patron", r"ATAJO_PROHIBIDO\(",
                      "--glob", "**/*.ts", "--mensaje", "usa el servicio", *extra, cwd=self.root)

    def test_sin_el_si_muestra_la_propuesta_y_no_registra(self):
        r = self.agregar()
        self.assertEqual(1, r.returncode)
        self.assertIn("guardrail propuesto: sin-atajo", r.stdout)
        self.assertIn("USUARIO", r.stdout + r.stderr)
        self.assertIn("formulario", r.stdout + r.stderr)
        self.assertEqual([], self.reglas())

    def test_el_si_sin_nombre_no_alcanza(self):
        self.assertEqual(1, self.agregar("--yes").returncode)
        self.assertEqual([], self.reglas())

    def test_con_el_si_registra_y_deja_constancia(self):
        r = self.agregar("--yes", "--por", "Alan")
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertEqual(["sin-atajo"], self.reglas())
        historia = (self.root / "harness" / "progress" / "history.md").read_text(encoding="utf-8")
        self.assertIn("guardrail agregado con el si de Alan: sin-atajo", historia)

    def test_promover_una_skill_tambien_lo_exige(self):
        skills = self.tmp / "skills"
        escribir(skills / "sin-atajos" / "SKILL.md", "---\nname: sin-atajos\ndescription: Use when x.\n---\n\nNo uses atajos.\n")
        args = ("guardrails.py", "promover", "--desde-skill", "sin-atajos", "--id", "sin-atajo",
                "--patron", r"ATAJO_PROHIBIDO\(", "--mensaje", "usa el servicio")
        env = {"HARNESS_SKILLS_DIR": str(skills)}
        self.assertEqual(1, correr(*args, cwd=self.root, env_extra=env).returncode)
        self.assertEqual([], self.reglas())
        self.assertEqual(0, correr(*args, "--yes", "--por", "Alan", cwd=self.root, env_extra=env).returncode)
        self.assertEqual(["sin-atajo"], self.reglas())


class HookPrePushTests(Base):
    MALA = "export const x = ATAJO_PROHIBIDO(1);\n"
    BUENA = "export const x = servicio(1);\n"

    def setUp(self):
        super().setUp()
        self.root = crear_repo_base(self.tmp, feature={"id": 1, "name": "x", "kind": "feature", "status": "todo"},
                                    spec_text=SPEC_UI)
        self.remoto = self.tmp / "remoto.git"
        sh("git", "init", "-q", "--bare", str(self.remoto), cwd=self.tmp)
        sh("git", "remote", "add", "origin", str(self.remoto), cwd=self.root)
        self.ok("guardrails.py", "agregar", "--id", "sin-atajo", "--patron", r"ATAJO_PROHIBIDO\(",
                "--glob", "**/*.ts", "--mensaje", "usa el servicio", "--yes", "--por", "T")
        self.commit("guardrail")
        sh("git", "push", "-q", "origin", "develop", cwd=self.root)
        self.hook = self.root / ".git" / "hooks" / "pre-push"

    def rama(self, texto: str):
        sh("git", "checkout", "-q", "-b", "feature/1", cwd=self.root)
        escribir(self.root / "src" / "nuevo.ts", texto)
        self.commit("trabajo")

    def subir(self):
        return subprocess.run(["git", "push", "origin", "feature/1"], cwd=str(self.root),
                              capture_output=True, text=True)

    def test_instalarlo_exige_el_si_y_nombra_los_repos(self):
        r = correr("guardrails.py", "instalar-hook", cwd=self.root)
        self.assertEqual(1, r.returncode)
        self.assertIn(str(self.root), r.stdout)
        self.assertFalse(self.hook.exists())

    def test_bloquea_la_subida_de_una_linea_que_infringe_y_no_la_imprime(self):
        self.ok("guardrails.py", "instalar-hook", "--yes")
        self.rama(self.MALA)
        r = self.subir()
        self.assertNotEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("subida BLOQUEADA", r.stderr)
        self.assertIn("[sin-atajo] src/nuevo.ts:1: usa el servicio", r.stderr)
        self.assertNotIn("ATAJO_PROHIBIDO", r.stderr)
        self.assertNotIn("feature/1", sh("git", "ls-remote", "--heads", "origin", cwd=self.root))

    def test_deja_subir_lo_que_cumple(self):
        self.ok("guardrails.py", "instalar-hook", "--yes")
        self.rama(self.BUENA)
        r = self.subir()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_lo_commiteado_antes_de_la_regla_no_bloquea_la_subida(self):
        """Promover trabajo viejo: esas lineas ya estaban cuando el usuario aprobo el guardrail."""
        self.ok("guardrails.py", "instalar-hook", "--yes")
        self.rama(self.MALA)
        ruta = self.root / "harness" / "guardrails.json"
        cfg = json.loads(ruta.read_text(encoding="utf-8"))
        cfg["reglas"][0]["added_at"] = "2099-01-01T00:00:00Z"
        ruta.write_text(json.dumps(cfg), encoding="utf-8")
        r = self.subir()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_un_pre_push_ajeno_no_se_reemplaza(self):
        escribir(self.hook, "#!/bin/sh\nexit 0\n")
        r = correr("guardrails.py", "instalar-hook", "--yes", cwd=self.root)
        self.assertIn("ya tiene un pre-push propio", r.stdout)
        self.assertEqual("#!/bin/sh\nexit 0\n", self.hook.read_text(encoding="utf-8"))

    def test_con_core_hooks_path_no_se_toca(self):
        sh("git", "config", "core.hooksPath", ".githooks", cwd=self.root)
        r = correr("guardrails.py", "instalar-hook", "--yes", cwd=self.root)
        self.assertIn("core.hooksPath", r.stdout)
        self.assertFalse((self.root / ".githooks" / "pre-push").exists())

    def test_quitar_el_hook_solo_quita_el_propio(self):
        self.ok("guardrails.py", "instalar-hook", "--yes")
        self.assertIn("hook pre-push quitado", correr("guardrails.py", "quitar-hook", cwd=self.root).stdout)
        self.assertFalse(self.hook.exists())
        escribir(self.hook, "#!/bin/sh\nexit 0\n")
        self.assertIn("sin hook de guardrails", correr("guardrails.py", "quitar-hook", cwd=self.root).stdout)
        self.assertTrue(self.hook.exists())

    def test_si_el_arnes_ya_no_esta_el_hook_no_deja_pasar(self):
        """Un chequeo que no puede medir no devuelve verdadero."""
        self.ok("guardrails.py", "instalar-hook", "--yes")
        self.rama(self.BUENA)
        self.hook.write_text(self.hook.read_text(encoding="utf-8").replace(f"--raiz {self.root}", f"--raiz {self.tmp / 'no-existe'}"),
                             encoding="utf-8")
        r = self.subir()
        self.assertNotEqual(0, r.returncode)
        self.assertIn("no se encuentra el arnes", r.stderr)

    def test_el_arranque_de_sesion_dice_en_cuantos_repos_esta_el_hook(self):
        self.assertIn("hook pre-push en 0/1 repo(s)", self.ok("estado.py", "--offline").stdout)
        self.ok("guardrails.py", "instalar-hook", "--yes")
        self.assertIn("hook pre-push en 1/1 repo(s)", self.ok("estado.py", "--offline").stdout)


def corrida(n: int, cumple: bool) -> dict:
    return {"caso_id": "E-1", "corrida": n, "senales_prohibidas_detectadas": [],
            "criterios": [{"id": "C-1", "cumplido": cumple, "evidencia": "handler.go:10 valida la clave"}]}


def suite(control: int = 0) -> dict:
    return {"umbral": 0.85, "corridas_por_caso": 2, "corridas_control": control,
            "casos": [{"id": "E-1", "tarea": "Escribe un cobro con reintentos.",
                       "criterios": [{"id": "C-1", "descripcion": "valida la clave de idempotencia", "peso": 1.0}]}]}


class ControlEnLosEvalsTests(unittest.TestCase):
    def test_las_corridas_de_control_no_entran_al_score(self):
        ev = evals.evaluar_ronda(suite(1), {"corridas": [corrida(1, True), corrida(2, True), corrida(3, False)]},
                                 {("E-1", 3)})
        self.assertEqual(1.0, ev["score"])
        self.assertEqual({"score": 0.0, "corridas": 1, "margen": 1.0, "distingue": True}, ev["control"])
        self.assertTrue(ev["aprobado"])

    def test_si_sin_la_skill_sacan_lo_mismo_el_examen_no_aprueba(self):
        """El control: un examen que no puede fallar no dice nada de la skill."""
        ev = evals.evaluar_ronda(suite(1), {"corridas": [corrida(1, True), corrida(2, True), corrida(3, True)]},
                                 {("E-1", 3)})
        self.assertEqual(1.0, ev["score"])
        self.assertFalse(ev["control"]["distingue"])
        self.assertFalse(ev["aprobado"])

    def test_la_suite_que_pide_control_no_acepta_un_resultado_sin_el(self):
        with self.assertRaisesRegex(ValueError, "corrida\\(s\\) de control"):
            evals.evaluar_ronda(suite(1), {"corridas": [corrida(1, True), corrida(2, True)]})

    def test_una_corrida_de_control_no_cuenta_para_el_minimo_con_la_skill(self):
        with self.assertRaisesRegex(ValueError, "con la skill"):
            evals.evaluar_ronda(suite(1), {"corridas": [corrida(1, True), corrida(2, False)]}, {("E-1", 2)})

    def test_nombrar_como_control_una_corrida_que_el_juez_no_evaluo_se_rechaza(self):
        with self.assertRaisesRegex(ValueError, "--control E-1:9"):
            evals.evaluar_ronda(suite(), {"corridas": [corrida(1, True), corrida(2, True)]}, {("E-1", 9)})

    def test_sin_control_el_resultado_lo_dice(self):
        ev = evals.evaluar_ronda(suite(), {"corridas": [corrida(1, True), corrida(2, True)]})
        self.assertIsNone(ev["control"])
        self.assertTrue(ev["aprobado"])

    def test_corridas_control_invalido_no_valida(self):
        mala = suite()
        mala["corridas_control"] = -1
        self.assertTrue(any("corridas_control" in x for x in evals.validar_suite(mala)))


class ControlPorLineaDeComandosTests(Base):
    def setUp(self):
        super().setUp()
        self.root = crear_repo_base(self.tmp, feature={"id": 1, "name": "x", "kind": "feature", "status": "todo"},
                                    spec_text=SPEC_UI)
        skills = self.tmp / "skills"
        escribir(skills / "cobros" / "SKILL.md", "---\nname: cobros\ndescription: Use when charging.\n---\n\n"
                                                 "# cobros\n\n## Reglas\n\n- Validar la clave de idempotencia.\n")
        self.env = {"HARNESS_SKILLS_DIR": str(skills)}
        self.ok("evals.py", "init", "cobros", "--corridas", "2", "--control", "1", env_extra=self.env)
        self.suite_p = self.root / "harness" / "evals" / "cobros.json"
        s = json.loads(self.suite_p.read_text(encoding="utf-8"))
        s["casos"][0]["tarea"] = "Escribe un cobro con reintentos."
        self.suite_p.write_text(json.dumps(s), encoding="utf-8")

    def registrar(self, corridas, *extra):
        resultado = self.tmp / "veredicto.json"
        resultado.write_text(json.dumps({"juez": "otro-modelo", "corridas": corridas}), encoding="utf-8")
        return correr("evals.py", "registrar", "cobros", "--resultado", str(resultado), *extra,
                      cwd=self.root, env_extra=self.env)

    def test_init_deja_el_control_en_la_suite_y_el_briefing_lo_pide_sin_avisarle_al_juez(self):
        self.assertEqual(1, json.loads(self.suite_p.read_text(encoding="utf-8"))["corridas_control"])
        r = self.ok("evals.py", "briefing", "cobros", "--fase", "ejecutar", env_extra=self.env)
        self.assertIn("GRUPO DE CONTROL", r.stdout)
        self.assertIn("SIN la skill", r.stdout)
        self.assertIn("corridas 3..3", r.stdout)
        juez = self.ok("evals.py", "briefing", "cobros", "--fase", "juez", env_extra=self.env)
        self.assertNotIn("control", juez.stdout.lower())

    def test_registrar_con_control_aprueba_y_dice_cuanto_sube_la_skill(self):
        r = self.registrar([corrida(1, True), corrida(2, True), corrida(3, False)], "--control", "E-1:3")
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("La skill sube el score 100%", r.stdout)
        ronda = json.loads((self.root / "harness" / "evals" / "cobros-resultados.json").read_text(encoding="utf-8"))["rondas"][-1]
        self.assertTrue(ronda["control"]["distingue"])

    def test_registrar_un_examen_que_no_distingue_reprueba(self):
        r = self.registrar([corrida(1, True), corrida(2, True), corrida(3, True)], "--control", "E-1:3")
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)
        self.assertIn("El examen no mide lo que la skill aporta", r.stdout)

    def test_un_control_mal_escrito_se_rechaza(self):
        r = self.registrar([corrida(1, True), corrida(2, True), corrida(3, False)], "--control", "tres")
        self.assertNotEqual(0, r.returncode)
        self.assertIn("--control invalido", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
