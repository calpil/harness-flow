"""Trinquete de arquitectura: el codigo heredado solo puede achicarse.

El problema que cubre: un proyecto con mucho codigo escrito antes del arnes
tenia dos opciones malas. La Feature #0 bloqueaba todo el backlog hasta
reestructurar todo de una vez; la adopcion "progresiva" no bloqueaba nada y
tampoco media nada, asi que lo heredado no convergia y el codigo nuevo podia
nacer fuera de la norma sin que ningun verificador lo notara.

Los repos de estas pruebas son repos git reales en un directorio temporal: lo
que se mide es lo que la feature commiteo contra su commit base.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"
sys.path.insert(0, str(SCRIPTS))

import arquitectura  # noqa: E402
import stack  # noqa: E402
from comun import load_backlog, paths  # noqa: E402

GO = "golang-hexagonal"
SPEC = ("# Spec - Feature #{id}: {nombre}\n\nEstado: draft\n\n"
        "## Criterios de aceptacion\n\n"
        "- AC-1: dado un carro, cuando pago, entonces cobra. `verificar: true`\n\n"
        "## Fuera de alcance\n\nFacturas.\n")


def sh(*args, cwd):
    r = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)
    assert r.returncode == 0, f"{args}: {r.stdout}{r.stderr}"
    return r.stdout.strip()


def harness(script, *args, cwd):
    env = dict(os.environ, HARNESS_SIN_CONTEXTO="1")
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          cwd=str(cwd), capture_output=True, text=True, env=env)


def escribir(ruta: Path, texto: str = "package x\n") -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


class LayoutTests(unittest.TestCase):
    def test_go_lo_que_esta_fuera_de_cmd_e_internal_es_heredado(self):
        lay = arquitectura.layout_de(GO)
        self.assertTrue(lay.heredado("handlers/a.go"))
        self.assertTrue(lay.heredado("main.go"))
        self.assertEqual(".", lay.unidad("main.go"))
        self.assertEqual("gateway/fintoc", lay.unidad("gateway/fintoc/c.go"))

    def test_go_lo_que_sigue_la_norma_no_es_heredado(self):
        lay = arquitectura.layout_de(GO)
        for ruta in ("cmd/server/main.go", "internal/pagos/domain/pago.go",
                     "internal/pagos/adapter/out/pg/repo.go", "internal/platform/log.go"):
            with self.subTest(ruta=ruta):
                self.assertFalse(lay.heredado(ruta))

    def test_go_internal_sin_capa_sigue_siendo_heredado(self):
        """`*` no cruza directorios: internal/a/b/domain no es internal/<modulo>/domain."""
        lay = arquitectura.layout_de(GO)
        self.assertTrue(lay.heredado("internal/pagos/pago.go"))
        self.assertTrue(lay.heredado("internal/a/b/domain/x.go"))

    def test_go_los_tests_y_vendor_no_cuentan(self):
        lay = arquitectura.layout_de(GO)
        self.assertFalse(lay.en_alcance("handlers/a_test.go"))
        self.assertFalse(lay.en_alcance("vendor/x/y.go"))
        self.assertFalse(lay.en_alcance("README.md"))

    def test_angular_una_feature_sin_capas_es_una_unidad_heredada(self):
        lay = arquitectura.layout_de("angular-product")
        ruta = "projects/admin/src/app/features/pagos/lista/lista.component.ts"
        self.assertTrue(lay.heredado(ruta))
        self.assertEqual("projects/admin/src/app/features/pagos", lay.unidad(ruta))

    def test_angular_capas_rutas_core_y_raiz_estan_en_la_norma(self):
        lay = arquitectura.layout_de("angular-product")
        for ruta in ("projects/admin/src/app/features/pagos/ui/lista.component.ts",
                     "projects/admin/src/app/features/pagos/domain/pago.ts",
                     "projects/admin/src/app/features/pagos/pagos.routes.ts",
                     "projects/admin/src/app/core/auth.ts",
                     "src/app/app.routes.ts", "src/app/features/pagos/index.ts"):
            with self.subTest(ruta=ruta):
                self.assertTrue(lay.en_alcance(ruta))
                self.assertFalse(lay.heredado(ruta))

    def test_angular_specs_y_librerias_quedan_fuera_del_alcance(self):
        lay = arquitectura.layout_de("angular-product")
        self.assertFalse(lay.en_alcance("projects/admin/src/app/features/pagos/x.spec.ts"))
        self.assertFalse(lay.en_alcance("projects/shared-ui/src/lib/boton.ts"))

    def test_un_stack_sin_layout_no_se_puede_medir(self):
        self.assertIsNone(arquitectura.layout_de("python-dataproduct"))


class Proyecto(unittest.TestCase):
    """Un repo Go heredado: handlers/ (2), repos/ (1) y la composition root en regla."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve() / "proyecto"
        self.root.mkdir()
        escribir(self.root / "go.mod", "module example.com/proyecto\n")
        escribir(self.root / "cmd" / "server" / "main.go", "package main\nfunc main() {}\n")
        escribir(self.root / "handlers" / "a.go", "package handlers\n")
        escribir(self.root / "handlers" / "b.go", "package handlers\n")
        escribir(self.root / "repos" / "r.go", "package repos\n")
        (self.root / "docs").mkdir()
        self.backlog({"rules": {"rama_base": "main", "require_docs_al_dia": False}, "features": []})
        sh("git", "init", "-q", "-b", "main", cwd=self.root)
        sh("git", "config", "user.email", "t@example.com", cwd=self.root)
        sh("git", "config", "user.name", "T", cwd=self.root)
        self.commit("base")
        self.sha_base = sh("git", "rev-parse", "HEAD", cwd=self.root)

    def tearDown(self):
        shutil.rmtree(self.root.parent, ignore_errors=True)

    def backlog(self, data: dict) -> None:
        escribir(self.root / "harness" / "feature_list.json", json.dumps(data))

    def commit(self, mensaje: str) -> None:
        sh("git", "add", "-A", cwd=self.root)
        sh("git", "commit", "-q", "-m", mensaje, cwd=self.root)

    def sellar(self) -> dict:
        r = harness("arquitectura.py", "base", "--yes", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.commit("base de arquitectura")
        return self.base()

    def base(self) -> dict:
        return json.loads((self.root / "harness" / "arquitectura-base.json").read_text(encoding="utf-8"))

    def feature(self, fid=7, **extra) -> dict:
        """Abre la rama de la feature desde el commit actual y devuelve su fila."""
        base = sh("git", "rev-parse", "HEAD", cwd=self.root)
        sh("git", "checkout", "-q", "-b", f"feature/{fid}", cwd=self.root)
        return dict({"id": fid, "name": f"f{fid}", "status": "in_progress", "base_sha": base}, **extra)

    def evaluar(self, f: dict) -> dict:
        p = paths(self.root)
        return arquitectura.evaluar_feature(p, load_backlog(p), f, arquitectura.cargar_base(p))


class BaseTests(Proyecto):
    def test_sin_yes_no_sella_nada(self):
        r = harness("arquitectura.py", "base", cwd=self.root)
        self.assertNotEqual(0, r.returncode)
        self.assertFalse((self.root / "harness" / "arquitectura-base.json").exists())

    def test_la_base_cuenta_los_archivos_heredados_por_unidad(self):
        reg = self.sellar()["repos"]["."]
        self.assertEqual({"handlers": 2, "repos": 1}, reg["heredadas"])
        self.assertEqual(GO, reg["stack"])

    def test_re_sellar_no_puede_aflojar_la_base(self):
        self.sellar()
        escribir(self.root / "handlers" / "c.go")
        self.commit("crece")
        r = harness("arquitectura.py", "base", "--yes", cwd=self.root)
        self.assertNotEqual(0, r.returncode)
        self.assertIn("AFLOJARIA", r.stdout + r.stderr)
        self.assertEqual(2, self.base()["repos"]["."]["heredadas"]["handlers"])

    def test_ampliar_exige_motivo_y_entonces_si_sella(self):
        self.sellar()
        escribir(self.root / "handlers" / "c.go")
        self.commit("crece")
        sin = harness("arquitectura.py", "base", "--yes", "--ampliar", cwd=self.root)
        self.assertNotEqual(0, sin.returncode)
        con = harness("arquitectura.py", "base", "--yes", "--ampliar", "--motivo", "codigo de un proveedor",
                      cwd=self.root)
        self.assertEqual(0, con.returncode, con.stdout + con.stderr)
        self.assertEqual(3, self.base()["repos"]["."]["heredadas"]["handlers"])

    def test_check_global_falla_si_lo_heredado_crecio_fuera_del_proceso(self):
        self.sellar()
        self.assertEqual(0, harness("arquitectura.py", "check", cwd=self.root).returncode)
        escribir(self.root / "handlers" / "c.go")
        self.commit("crece por fuera")
        r = harness("arquitectura.py", "check", cwd=self.root)
        self.assertEqual(1, r.returncode)
        self.assertIn("handlers", r.stdout)

    def test_ajustar_aprieta_la_base_y_no_la_afloja(self):
        self.sellar()
        sh("git", "rm", "-q", "repos/r.go", cwd=self.root)
        self.commit("normaliza repos")
        r = harness("arquitectura.py", "check", "--ajustar", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertEqual({"handlers": 2}, self.base()["repos"]["."]["heredadas"])
        # Devolver el archivo ya no cabe: la base bajo y no vuelve a subir sola.
        escribir(self.root / "repos" / "r.go")
        self.commit("vuelve")
        self.assertEqual(1, harness("arquitectura.py", "check", "--ajustar", cwd=self.root).returncode)
        self.assertEqual({"handlers": 2}, self.base()["repos"]["."]["heredadas"])

    def test_eximir_saca_una_unidad_de_la_norma_solo_con_yes(self):
        self.sellar()
        sin = harness("arquitectura.py", "eximir", "--repo", ".", "--unidad", "repos",
                      "--motivo", "generado por sqlc", cwd=self.root)
        self.assertNotEqual(0, sin.returncode)
        con = harness("arquitectura.py", "eximir", "--repo", ".", "--unidad", "repos",
                      "--motivo", "generado por sqlc", "--yes", cwd=self.root)
        self.assertEqual(0, con.returncode, con.stdout + con.stderr)
        reg = self.base()["repos"]["."]
        self.assertEqual({"handlers": 2}, reg["heredadas"])
        self.assertEqual({"repos": "generado por sqlc"}, reg["exentas"])
        self.commit("exime")
        f = self.feature()
        escribir(self.root / "repos" / "otro.go")
        self.commit("crece lo exento")
        self.assertEqual([], self.evaluar(f)["fallos"])


class FeatureTests(Proyecto):
    def setUp(self):
        super().setUp()
        self.sellar()

    def test_agregar_un_archivo_a_una_unidad_heredada_falla(self):
        f = self.feature()
        escribir(self.root / "handlers" / "c.go")
        self.commit("handler nuevo en lo heredado")
        fallos = self.evaluar(f)["fallos"]
        self.assertEqual(1, len(fallos), fallos)
        self.assertIn("crecio", fallos[0])
        self.assertIn("handlers/c.go", fallos[0])

    def test_crear_una_unidad_fuera_de_la_norma_falla(self):
        f = self.feature()
        escribir(self.root / "pkg" / "nuevo" / "x.go")
        self.commit("paquete nuevo fuera de internal")
        fallos = self.evaluar(f)["fallos"]
        self.assertTrue(any("unidad heredada nueva" in x and "pkg/nuevo" in x for x in fallos), fallos)

    def test_el_codigo_nuevo_dentro_de_la_norma_pasa(self):
        f = self.feature()
        escribir(self.root / "internal" / "pagos" / "domain" / "pago.go", "package domain\n")
        self.commit("modulo nuevo en internal")
        self.assertEqual([], self.evaluar(f)["fallos"])

    def test_un_cambio_chico_en_lo_heredado_pasa(self):
        f = self.feature()
        escribir(self.root / "handlers" / "a.go", "package handlers\n" + "// x\n" * 10)
        self.commit("arreglo chico")
        self.assertEqual([], self.evaluar(f)["fallos"])

    def test_un_cambio_grande_en_un_archivo_heredado_obliga_a_normalizarlo(self):
        f = self.feature()
        escribir(self.root / "handlers" / "a.go", "package handlers\n" + "// x\n" * 60)
        self.commit("reescritura")
        fallos = self.evaluar(f)["fallos"]
        self.assertEqual(1, len(fallos), fallos)
        self.assertIn("handlers/a.go", fallos[0])
        self.assertIn("umbral 50", fallos[0])

    def test_el_umbral_es_una_regla_del_proyecto(self):
        self.backlog({"rules": {"rama_base": "main", "arquitectura_umbral_lineas": 100}, "features": []})
        self.commit("regla")
        f = self.feature()
        escribir(self.root / "handlers" / "a.go", "package handlers\n" + "// x\n" * 60)
        self.commit("reescritura")
        self.assertEqual([], self.evaluar(f)["fallos"])

    def test_un_archivo_muy_cambiado_que_se_muda_a_la_norma_pasa(self):
        f = self.feature()
        sh("git", "rm", "-q", "handlers/a.go", cwd=self.root)
        escribir(self.root / "internal" / "pagos" / "adapter" / "in" / "a.go",
                 "package in\n" + "// x\n" * 60)
        self.commit("mudanza")
        self.assertEqual([], self.evaluar(f)["fallos"])

    def test_vaciar_una_unidad_se_reporta(self):
        f = self.feature()
        sh("git", "mv", "repos/r.go", "internal_tmp.go", cwd=self.root)
        sh("git", "rm", "-q", "-f", "internal_tmp.go", cwd=self.root)
        escribir(self.root / "internal" / "pagos" / "adapter" / "out" / "r.go", "package out\n")
        self.commit("normaliza repos")
        res = self.evaluar(f)
        self.assertEqual([], res["fallos"])
        self.assertEqual([".:repos"], res["vaciadas"])

    def test_dos_features_paralelas_no_se_pisan(self):
        """Otra feature ya normalizo `repos` y la base bajo; esta rama aun lo trae intacto.

        Medir el arbol de la feature contra la base global daria "repos crecio":
        un rojo falso que obligaria a rebasar. Se mide contra SU commit base.
        """
        f = self.feature()
        escribir(self.root / "internal" / "pagos" / "domain" / "pago.go", "package domain\n")
        self.commit("trabajo propio")
        base = self.base()
        base["repos"]["."]["heredadas"].pop("repos")
        arquitectura.guardar_base(paths(self.root), base)
        self.assertEqual([], self.evaluar(f)["fallos"])

    def test_una_violacion_nueva_del_verificador_falla(self):
        f = self.feature()
        escribir(self.root / "internal" / "pagos" / "domain" / "pago.go",
                 'package domain\n\nimport "net/http"\n\nvar _ = http.StatusOK\n')
        self.commit("dominio impuro")
        fallos = self.evaluar(f)["fallos"]
        self.assertTrue(any("violacion nueva" in x and "net/http" in x for x in fallos), fallos)

    def test_sin_commit_base_legible_no_devuelve_verde(self):
        """Un gate que no puede medir no devuelve verdadero."""
        f = self.feature(base_sha="0" * 40)
        escribir(self.root / "handlers" / "c.go")
        self.commit("crece")
        fallos = self.evaluar(f)["fallos"]
        self.assertTrue(any("no se pudo leer" in x for x in fallos), fallos)


class CuotaTests(Proyecto):
    def setUp(self):
        super().setUp()
        self.sellar()
        self.p = paths(self.root)
        self.data = load_backlog(self.p)

    def aprobar(self, fid, kind="feature"):
        f = {"id": fid, "kind": kind}
        motivo = arquitectura.cuota_bloquea(self.p, self.data, f)
        if motivo is None:
            arquitectura.registrar_aprobacion(self.p, self.data, f)
        return motivo

    def test_la_cuarta_feature_de_negocio_queda_frenada(self):
        self.assertEqual([None, None, None], [self.aprobar(i) for i in (1, 2, 3)])
        motivo = self.aprobar(4)
        self.assertIn("cuota de normalizacion", motivo)
        self.assertIn("#1, #2, #3", motivo)

    def test_volver_a_aprobar_una_ya_contada_no_gasta_cuota(self):
        for i in (1, 2, 3):
            self.aprobar(i)
        self.assertIsNone(self.aprobar(2))

    def test_bugs_tareas_y_normalizaciones_no_se_frenan_ni_cuentan(self):
        for i in (1, 2, 3):
            self.aprobar(i)
        for kind in ("bug", "task", "normalizacion"):
            with self.subTest(kind=kind):
                self.assertIsNone(self.aprobar(9, kind))
        self.assertEqual([1, 2, 3], self.data["arquitectura"]["negocio_desde_normalizacion"])

    def test_cerrar_una_normalizacion_reinicia_la_cuota(self):
        for i in (1, 2, 3):
            self.aprobar(i)
        arquitectura.al_cerrar(self.p, self.data, {"id": 50, "kind": "normalizacion"})
        self.assertIsNone(self.aprobar(4))

    def test_cerrar_una_de_negocio_no_la_reinicia(self):
        for i in (1, 2, 3):
            self.aprobar(i)
        arquitectura.al_cerrar(self.p, self.data, {"id": 1, "kind": "feature"})
        self.assertIsNotNone(self.aprobar(4))

    def test_la_cuota_es_una_regla_del_proyecto_y_cero_la_apaga(self):
        self.data["rules"]["arquitectura_cuota"] = 1
        self.aprobar(1)
        self.assertIsNotNone(self.aprobar(2))
        self.data["rules"]["arquitectura_cuota"] = 0
        self.assertIsNone(self.aprobar(2))

    def test_sin_nada_heredado_la_cuota_deja_de_aplicar(self):
        for i in (1, 2, 3):
            self.aprobar(i)
        base = self.base()
        base["repos"]["."]["heredadas"] = {}
        arquitectura.guardar_base(self.p, base)
        self.assertIsNone(self.aprobar(4))

    def test_una_normalizacion_que_no_vacia_nada_no_cierra(self):
        f = self.feature(50, kind="normalizacion")
        escribir(self.root / "internal" / "pagos" / "domain" / "pago.go", "package domain\n")
        self.commit("no normaliza nada")
        fallos, _ = arquitectura.fallos_de_cierre(self.p, self.data, f)
        self.assertTrue(any("no vacio ninguna unidad" in x for x in fallos), fallos)

    def test_una_normalizacion_que_vacia_una_unidad_si_cierra(self):
        f = self.feature(50, kind="normalizacion")
        sh("git", "rm", "-q", "repos/r.go", cwd=self.root)
        escribir(self.root / "internal" / "pagos" / "adapter" / "out" / "r.go", "package out\n")
        self.commit("normaliza repos")
        self.assertEqual(([], []), arquitectura.fallos_de_cierre(self.p, self.data, f))


class GateTests(Proyecto):
    """El trinquete dentro de gate.py: reemplaza el muro de la #0 por la cuota."""

    def proyecto_con(self, n: int, con_f0: bool = True) -> None:
        feats = [{"id": i, "name": f"cobro {i}", "kind": "feature", "status": "todo",
                  "requiere": [0]} for i in range(1, n + 1)]
        if con_f0:
            feats.insert(0, {"id": 0, "name": "normalizacion-arquitectura", "status": "in_progress"})
        self.backlog({"rules": {"rama_base": "main", "require_docs_al_dia": False}, "features": feats})
        for f in feats[1 if con_f0 else 0:]:
            escribir(self.root / "docs" / f"spec-feature-{f['id']}-cobro-{f['id']}.md",
                     SPEC.format(id=f["id"], nombre=f["name"]))
        self.commit("backlog")

    def aprobar(self, fid):
        return harness("gate.py", "approve-spec", "--feature", str(fid), "--yes", "--por", "T",
                       cwd=self.root)

    def test_sin_trinquete_la_feature_0_sigue_siendo_un_muro(self):
        self.proyecto_con(1)
        r = self.aprobar(1)
        self.assertNotEqual(0, r.returncode)
        self.assertIn("require_stack_normativo", r.stdout + r.stderr)

    def test_adoptar_exige_yes(self):
        self.proyecto_con(1)
        self.assertNotEqual(0, harness("arquitectura.py", "adoptar", cwd=self.root).returncode)
        self.assertFalse((self.root / "harness" / "arquitectura-base.json").exists())

    def test_adoptar_libera_el_backlog_y_conserva_la_0_como_normalizacion(self):
        self.proyecto_con(2)
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        data["features"][2]["requiere"] = [0, 1]
        self.backlog(data)
        r = harness("arquitectura.py", "adoptar", "--yes", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        feats = {f["id"]: f for f in load_backlog(paths(self.root))["features"]}
        self.assertNotIn("requiere", feats[1])
        self.assertEqual([1], feats[2]["requiere"])
        self.assertEqual("normalizacion", feats[0]["kind"])
        self.assertEqual("in_progress", feats[0]["status"])
        self.assertEqual({"handlers": 2, "repos": 1}, self.base()["repos"]["."]["heredadas"])

    def test_con_el_trinquete_la_0_abierta_ya_no_frena_el_spec(self):
        self.proyecto_con(1)
        harness("arquitectura.py", "adoptar", "--yes", cwd=self.root)
        r = self.aprobar(1)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_approve_spec_aplica_la_cuota(self):
        self.proyecto_con(4, con_f0=False)
        harness("arquitectura.py", "adoptar", "--yes", cwd=self.root)
        for fid in (1, 2, 3):
            r = self.aprobar(fid)
            self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        r = self.aprobar(4)
        self.assertNotEqual(0, r.returncode)
        self.assertIn("cuota de normalizacion", r.stdout + r.stderr)
        spec4 = (self.root / "docs" / "spec-feature-4-cobro-4.md").read_text(encoding="utf-8")
        self.assertIn("Estado: draft", spec4, "un spec frenado no queda sellado")

    def cierre(self, kind: str, cambio) -> subprocess.CompletedProcess:
        """Feature 5 en su rama, con las demas reglas apagadas: solo decide el trinquete."""
        self.backlog({
            "rules": {"rama_base": "main", "require_docs_al_dia": False, "require_spec_approved": False,
                      "require_review": False, "require_leccion": False, "require_verify_green": False},
            "arquitectura": {"negocio_desde_normalizacion": [1, 2, 3]},
            "features": [{"id": 5, "name": "cobro 5", "kind": kind, "status": "in_progress",
                          "branch": "feature/5", "base_sha": self.sha_base}]})
        escribir(self.root / "docs" / "spec-feature-5-cobro-5.md", SPEC.format(id=5, nombre="cobro 5"))
        escribir(self.root / "docs" / "impl-5.md", "## AC-1\nhandlers/a.go:1\n")
        self.commit("backlog")
        harness("arquitectura.py", "base", "--yes", cwd=self.root)
        self.commit("base")
        data = json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        data["features"][0]["base_sha"] = sh("git", "rev-parse", "HEAD", cwd=self.root)
        self.backlog(data)
        self.commit("base de la feature")
        sh("git", "checkout", "-q", "-b", "feature/5", cwd=self.root)
        cambio()
        self.commit("trabajo de la feature")
        return harness("gate.py", "close", "--feature", "5", "--status", "done", "--to", "main",
                       cwd=self.root)

    def estado_backlog(self) -> dict:
        return json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))

    def test_close_se_niega_si_la_feature_hizo_crecer_lo_heredado(self):
        r = self.cierre("feature", lambda: escribir(self.root / "handlers" / "c.go"))
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)
        self.assertIn("arquitectura:", r.stdout)
        self.assertIn("handlers/c.go", r.stdout)
        self.assertEqual("in_progress", self.estado_backlog()["features"][0]["status"])

    def test_close_pasa_si_el_codigo_nuevo_nace_en_la_norma(self):
        """El control: con las demas reglas apagadas, lo unico que frenaba era el trinquete."""
        r = self.cierre("feature", lambda: escribir(
            self.root / "internal" / "pagos" / "domain" / "pago.go", "package domain\n"))
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        data = self.estado_backlog()
        self.assertEqual("done", data["features"][0]["status"])
        self.assertEqual([1, 2, 3], data["arquitectura"]["negocio_desde_normalizacion"],
                         "una feature de negocio no reinicia la cuota")

    def test_close_de_una_normalizacion_reinicia_la_cuota(self):
        def normaliza():
            sh("git", "rm", "-q", "repos/r.go", cwd=self.root)
            escribir(self.root / "internal" / "pagos" / "adapter" / "out" / "r.go", "package out\n")
        r = self.cierre("normalizacion", normaliza)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertEqual([], self.estado_backlog()["arquitectura"]["negocio_desde_normalizacion"])

    def test_close_de_una_normalizacion_que_no_normaliza_se_niega(self):
        r = self.cierre("normalizacion", lambda: escribir(
            self.root / "internal" / "pagos" / "domain" / "pago.go", "package domain\n"))
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)
        self.assertIn("no vacio ninguna unidad", r.stdout)

    def test_el_arranque_de_sesion_no_recrea_la_0_con_el_trinquete(self):
        (self.root / "cmd" / "server" / "main.go").unlink()  # violacion: sin composition root
        self.backlog({"rules": {"rama_base": "main"}, "features": [
            {"id": 1, "name": "cobro", "status": "todo"}]})
        self.commit("sin main")
        harness("arquitectura.py", "adoptar", "--yes", cwd=self.root)
        p = paths(self.root)
        data = load_backlog(p)
        res = stack.auto_normalizar_y_asegurar_cumplimiento(self.root, data)
        self.assertFalse(res["f0_creada"])
        self.assertEqual([1], [f["id"] for f in data["features"]])
        self.assertNotIn("requiere", data["features"][0])

    def test_sin_el_trinquete_el_arranque_de_sesion_si_crea_la_0(self):
        """El control del test anterior."""
        (self.root / "cmd" / "server" / "main.go").unlink()
        self.backlog({"rules": {"rama_base": "main"}, "features": [
            {"id": 1, "name": "cobro", "status": "todo"}]})
        self.commit("sin main")
        data = load_backlog(paths(self.root))
        res = stack.auto_normalizar_y_asegurar_cumplimiento(self.root, data)
        self.assertTrue(res["f0_creada"])

    def test_estado_muestra_el_avance(self):
        self.proyecto_con(1, con_f0=False)
        antes = arquitectura.resumen(paths(self.root), load_backlog(paths(self.root)))
        self.assertIn("sin adoptar", antes)
        harness("arquitectura.py", "adoptar", "--yes", cwd=self.root)
        p = paths(self.root)
        despues = arquitectura.resumen(p, load_backlog(p))
        self.assertIn("2 unidades heredadas (3 archivos)", despues)
        self.assertIn("cuota 0/3", despues)

    def test_siguiente_ordena_por_lo_mas_tocado(self):
        self.proyecto_con(1, con_f0=False)
        harness("arquitectura.py", "adoptar", "--yes", cwd=self.root)
        for i in range(3):
            escribir(self.root / "repos" / "r.go", f"package repos\n// {i}\n")
            self.commit(f"toca repos {i}")
        r = harness("arquitectura.py", "siguiente", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        lineas = [x for x in r.stdout.splitlines() if "cambios" in x]
        self.assertIn(".:repos", lineas[0])


class EnCursoYOtrosReposTests(Proyecto):
    """Lo que salio de un proyecto real: features ya abiertas y repos sin arbol registrado."""

    def setUp(self):
        super().setUp()
        # Un microservicio fuera de la raiz, declarado en grafos.json.
        self.ms = self.root.parent / "micros" / "ms-b"
        escribir(self.ms / "go.mod", "module example.com/ms-b\n")
        escribir(self.ms / "cmd" / "server" / "main.go", "package main\nfunc main() {}\n")
        escribir(self.ms / "handlers" / "h.go", "package handlers\n")
        sh("git", "init", "-q", "-b", "main", cwd=self.ms)
        sh("git", "config", "user.email", "t@example.com", cwd=self.ms)
        sh("git", "config", "user.name", "T", cwd=self.ms)
        self.commit_ms("base")
        escribir(self.root / "harness" / "grafos.json", json.dumps({"raices": [
            {"nombre": "front", "path": "."}, {"nombre": "micros", "path": str(self.ms.parent)}]}))
        self.backlog({"rules": {"rama_base": "main", "require_docs_al_dia": False}, "features": [
            {"id": 0, "name": "normalizacion-arquitectura", "kind": "refactor", "status": "in_progress"},
            {"id": 9, "name": "en curso", "kind": "feature", "status": "in_progress", "requiere": [0]},
            {"id": 10, "name": "por empezar", "kind": "feature", "status": "todo", "requiere": [0]}]})
        self.commit("proyecto")
        r = harness("arquitectura.py", "adoptar", "--yes", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.commit("adopta el trinquete")
        self.p = paths(self.root)

    def commit_ms(self, mensaje: str) -> None:
        sh("git", "add", "-A", cwd=self.ms)
        sh("git", "commit", "-q", "-m", mensaje, cwd=self.ms)

    def data(self) -> dict:
        return load_backlog(self.p)

    def test_la_base_incluye_el_repo_de_fuera_de_la_raiz(self):
        repos = self.base()["repos"]
        self.assertEqual({"handlers": 1}, repos[str(self.ms)]["heredadas"])
        self.assertEqual({"handlers": 2, "repos": 1}, repos["."]["heredadas"])

    def test_adoptar_exime_a_lo_que_ya_estaba_en_curso_y_no_a_la_0(self):
        arq = self.data()["arquitectura"]
        self.assertEqual([9], arq["exentas_en_curso"])

    def test_una_feature_en_curso_al_adoptar_cierra_aunque_agregue_heredado(self):
        data = self.data()
        f = self.feature(9)
        escribir(self.root / "handlers" / "c.go")
        self.commit("lo que ya venia haciendo")
        fallos, avisos = arquitectura.fallos_de_cierre(self.p, data, dict(f, id=9))
        self.assertEqual([], fallos)
        self.assertTrue(any("en curso al adoptar" in a for a in avisos), avisos)

    def test_al_cerrar_la_exenta_la_base_absorbe_lo_que_agrego_y_deja_de_estar_exenta(self):
        data = self.data()
        escribir(self.root / "handlers" / "c.go")
        self.commit("integrado en main")
        arquitectura.al_cerrar(self.p, data, {"id": 9, "kind": "feature"})
        self.assertEqual([], data["arquitectura"]["exentas_en_curso"])
        self.assertEqual(3, self.base()["repos"]["."]["heredadas"]["handlers"])
        historia = (self.root / "harness" / "progress" / "history.md").read_text(encoding="utf-8")
        self.assertIn("la base absorbe", historia)
        # Y la siguiente feature ya no esta exenta: vuelve a regir el trinquete.
        self.commit("cierre")
        f = self.feature(10)
        escribir(self.root / "handlers" / "d.go")
        self.commit("crece")
        fallos, _ = arquitectura.fallos_de_cierre(self.p, data, f)
        self.assertTrue(any("handlers/d.go" in x for x in fallos), fallos)

    def test_lo_que_crece_en_un_repo_sin_arbol_registrado_tambien_frena_el_cierre(self):
        """La feature solo registra el arbol de la raiz; el microservicio se mide por su checkout."""
        f = self.feature(10)
        escribir(self.root / "internal" / "pagos" / "domain" / "pago.go", "package domain\n")
        self.commit("la raiz queda en la norma")
        self.assertEqual([], arquitectura.fallos_de_cierre(self.p, self.data(), f)[0])
        escribir(self.ms / "handlers" / "nuevo.go")
        self.commit_ms("crece en el microservicio")
        fallos, avisos = arquitectura.fallos_de_cierre(self.p, self.data(), f)
        self.assertEqual(1, len(fallos), fallos)
        self.assertIn("handlers", fallos[0])
        self.assertIn("checkout", fallos[0])
        self.assertTrue(any("umbral" in a for a in avisos), avisos)

    def test_normalizar_un_repo_sin_arbol_registrado_cuenta_como_normalizacion(self):
        f = self.feature(50, kind="normalizacion")
        sin_mejora, _ = arquitectura.fallos_de_cierre(self.p, self.data(), f)
        self.assertTrue(any("no vacio ninguna unidad" in x for x in sin_mejora), sin_mejora)
        sh("git", "rm", "-q", "handlers/h.go", cwd=self.ms)
        escribir(self.ms / "internal" / "b" / "adapter" / "in" / "h.go", "package in\n")
        self.commit_ms("normaliza handlers")
        self.assertEqual([], arquitectura.fallos_de_cierre(self.p, self.data(), f)[0])

    def test_worktree_start_ya_no_choca_con_la_0_abierta(self):
        r = harness("worktree.py", "start", "--feature", "10", cwd=self.root)
        self.assertNotIn("require_stack_normativo", r.stdout + r.stderr)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)


class MuroSinTrinqueteTests(Proyecto):
    def test_sin_trinquete_worktree_start_sigue_frenado_por_la_0(self):
        """El control: el muro solo se levanta al adoptar."""
        self.backlog({"rules": {"rama_base": "main"}, "features": [
            {"id": 0, "name": "normalizacion-arquitectura", "status": "in_progress"},
            {"id": 10, "name": "por empezar", "kind": "feature", "status": "todo"}]})
        self.commit("proyecto")
        r = harness("worktree.py", "start", "--feature", "10", cwd=self.root)
        self.assertNotEqual(0, r.returncode)
        self.assertIn("require_stack_normativo", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
