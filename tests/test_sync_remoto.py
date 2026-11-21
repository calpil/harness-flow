"""Sincronizacion multi-desarrollador: commit/push en rama base + espejo Memory Hub Postgres.

Cubre el contrato completo de `scripts/sync_remoto.py` y su integracion en
`estado.py`, `worktree.py`, `gate.py` y `hub.py`:

  1. `worktree.py start` valida primero remoto + Hub, marca `in_progress` con
     `desarrollo.estado = 'desarrollando'` (dueno, email, host, rama, fecha) y
     hace commit+push atomico en `origin/<rama_base>` sin ensuciar el arbol.
  2. Un segundo desarrollador no puede iniciar, aprobar spec ni verificar spec
     de una feature ya tomada; `estado.py` la muestra y sugiere otra libre.
  3. Dos devs en features distintas trabajan sin pisarse y `gate.py check`
     delega la validacion local de features ajenas a su dueno.
  4. Fallos de red/push bloquean con rollback del worktree; `--offline` permite
     emergencias sin pisar reclamos ajenos ya conocidos; `worktree.py sync`
     publica al volver la red.
  5. `worktree.py liberar` libera features propias y exige `--forzar --yes`
     para liberar una feature ajena.
  6. Espejo en Memory Hub Postgres (lectura sin DDL, escritura de nodos/aristas
     `DESARROLLANDO`, bloqueo por conflicto desde Hub y liberacion en close/liberar).
"""
import contextlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"
sys.path.insert(0, str(SCRIPTS))

try:
    import psycopg  # noqa: F401
except ImportError:
    falso = types.ModuleType("psycopg")
    falso.Error = type("Error", (Exception,), {})
    tipos, js = types.ModuleType("psycopg.types"), types.ModuleType("psycopg.types.json")
    js.Jsonb = type("Jsonb", (), {"__init__": lambda self, obj: setattr(self, "obj", obj)})
    sys.modules.update({"psycopg": falso, "psycopg.types": tipos, "psycopg.types.json": js})

import comun  # noqa: E402
import hub  # noqa: E402
import sync_remoto  # noqa: E402


def sh(*args, cwd, check=True):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, check=check)


def harness(script, *args, cwd, env_extra=None):
    env = dict(
        os.environ,
        HARNESS_SIN_CONTEXTO="1",
        HARNESS_SIN_CBM="1",
        HARNESS_SIN_HUB="1",
        HARNESS_SIN_SYNC_REMOTO="",
        HARNESS_DEV="",
    )
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=str(cwd), capture_output=True, text=True, env=env,
    )


class EquipoRemotoFixture(unittest.TestCase):
    """Un remoto bare `origin` y dos clones locales independientes: Alan y Maria."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="harness-sync-")
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name).resolve()
        self.bare = base / "origin.git"
        self.bare.mkdir()
        sh("git", "init", "--bare", "-q", "-b", "develop", ".", cwd=self.bare)

        self.alan = base / "dev-alan" / "app"
        self.maria = base / "dev-maria" / "app"
        self.alan.parent.mkdir(parents=True)
        self.maria.parent.mkdir(parents=True)

        # Repo semilla en dev-alan, subido a origin/develop
        self.alan.mkdir()
        sh("git", "init", "-q", "-b", "develop", ".", cwd=self.alan)
        sh("git", "config", "user.name", "Alan", cwd=self.alan)
        sh("git", "config", "user.email", "alan@equipo.test", cwd=self.alan)
        (self.alan / "harness" / "progress").mkdir(parents=True)
        (self.alan / "docs").mkdir(parents=True)
        backlog = {
            "project": "tienda",
            "rules": {
                "rama_base": "develop",
                "require_docs_al_dia": False,
                "require_spec_approved": True,
                "require_review": False,
                "require_verify_green": False,
                "require_leccion": False,
            },
            "features": [
                {"id": 1, "name": "Pagos", "kind": "feature", "status": "todo"},
                {"id": 2, "name": "Envios", "kind": "feature", "status": "todo"},
            ],
        }
        (self.alan / "harness" / "feature_list.json").write_text(
            json.dumps(backlog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        for fid, nombre in ((1, "pagos"), (2, "envios")):
            (self.alan / "docs" / f"spec-feature-{fid}-{nombre}.md").write_text(
                f"# Spec - Feature #{fid}: {nombre}\n\nEstado: draft\n\n"
                "## Criterios de aceptacion\n\n"
                "- AC-1 [costura: servicio]: dado x, cuando y, entonces z. `verificar: true`\n",
                encoding="utf-8",
            )
        (self.alan / "README.md").write_text("# Tienda\n", encoding="utf-8")
        sh("git", "add", "-A", cwd=self.alan)
        sh("git", "commit", "-qm", "init proyecto", cwd=self.alan)
        sh("git", "remote", "add", "origin", str(self.bare), cwd=self.alan)
        sh("git", "push", "-q", "-u", "origin", "develop", cwd=self.alan)

        # Clonar para Maria
        sh("git", "clone", "-q", "-b", "develop", str(self.bare), str(self.maria), cwd=self.maria.parent)
        sh("git", "config", "user.name", "Maria", cwd=self.maria)
        sh("git", "config", "user.email", "maria@equipo.test", cwd=self.maria)

    def env_alan(self, **extra):
        return {"HARNESS_HOST_NAME": "mac-alan", **extra}

    def env_maria(self, **extra):
        return {"HARNESS_HOST_NAME": "laptop-maria", **extra}

    def remoto_backlog(self) -> dict:
        out = sh("git", "show", "develop:harness/feature_list.json", cwd=self.bare).stdout
        return json.loads(out)

    def remoto_feature(self, fid: int) -> dict:
        for f in self.remoto_backlog()["features"]:
            if int(f["id"]) == fid:
                return f
        raise AssertionError(f"feature #{fid} no encontrada en origin")

    def local_backlog(self, repo: Path) -> dict:
        return json.loads((repo / "harness" / "feature_list.json").read_text(encoding="utf-8"))


class SyncRemotoGitTests(EquipoRemotoFixture):
    def test_start_publica_estado_desarrollando_en_origin_y_mantiene_arbol_limpio(self):
        r = harness("worktree.py", "start", "--feature", "1", cwd=self.alan, env_extra=self.env_alan())
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("estado 'desarrollando' publicado en origin/develop", r.stdout)

        rem = self.remoto_feature(1)
        self.assertEqual("in_progress", rem["status"])
        self.assertEqual("desarrollando", rem["desarrollo"]["estado"])
        self.assertEqual("Alan", rem["desarrollo"]["por"])
        self.assertEqual("alan@equipo.test", rem["desarrollo"]["email"])
        self.assertEqual("mac-alan", rem["desarrollo"]["host"])
        self.assertEqual("feature/1-pagos", rem["desarrollo"]["branch"])

        # Fast-forward limpio: HEAD de Alan == origin/develop y feature_list.json sin diff sucio.
        head_alan = sh("git", "rev-parse", "HEAD", cwd=self.alan).stdout.strip()
        head_origin = sh("git", "rev-parse", "develop", cwd=self.bare).stdout.strip()
        self.assertEqual(head_origin, head_alan)
        dirty = sh("git", "status", "--porcelain", "--", "harness/feature_list.json", cwd=self.alan).stdout
        self.assertEqual("", dirty.strip())

    def test_segundo_dev_no_puede_iniciar_misma_feature_y_no_deja_worktree(self):
        r1 = harness("worktree.py", "start", "--feature", "1", cwd=self.alan, env_extra=self.env_alan())
        self.assertEqual(0, r1.returncode, r1.stdout + r1.stderr)

        # Maria NO hizo git pull; el arnes debe consultar origin primero y bloquear.
        r2 = harness("worktree.py", "start", "--feature", "1", cwd=self.maria, env_extra=self.env_maria())
        self.assertNotEqual(0, r2.returncode)
        salida = r2.stdout + r2.stderr
        self.assertIn("Alan", salida)
        self.assertIn("mac-alan", salida)
        self.assertIn("origin/develop", salida)
        self.assertIn("worktree.py liberar --feature 1 --forzar --yes", salida)
        self.assertFalse((self.maria.parent / "app-wt" / "1-pagos").exists())
        self.assertEqual("todo", self.local_backlog(self.maria)["features"][0]["status"])

    def test_segundo_dev_no_puede_aprobar_ni_verificar_spec_de_feature_ajena(self):
        r1 = harness("worktree.py", "start", "--feature", "1", cwd=self.alan, env_extra=self.env_alan())
        self.assertEqual(0, r1.returncode, r1.stdout + r1.stderr)

        spec_maria = self.maria / "docs" / "spec-feature-1-pagos.md"
        antes = spec_maria.read_text(encoding="utf-8")

        ra = harness("gate.py", "approve-spec", "--feature", "1", "--yes",
                     cwd=self.maria, env_extra=self.env_maria())
        self.assertNotEqual(0, ra.returncode)
        self.assertIn("Alan", ra.stdout + ra.stderr)
        self.assertEqual(antes, spec_maria.read_text(encoding="utf-8"), "no debe sellar el spec al bloquear")

        rc = harness("gate.py", "check-spec", "--feature", "1",
                     cwd=self.maria, env_extra=self.env_maria())
        self.assertNotEqual(0, rc.returncode)
        self.assertIn("Alan", rc.stdout + rc.stderr)

    def test_estado_valida_remoto_primero_y_no_sugiere_feature_ajena(self):
        r1 = harness("worktree.py", "start", "--feature", "1", cwd=self.alan, env_extra=self.env_alan())
        self.assertEqual(0, r1.returncode, r1.stdout + r1.stderr)

        antes = (self.maria / "harness" / "feature_list.json").read_bytes()
        re_m = harness("estado.py", cwd=self.maria, env_extra=self.env_maria())
        self.assertEqual(0, re_m.returncode, re_m.stdout + re_m.stderr)
        self.assertEqual(antes, (self.maria / "harness" / "feature_list.json").read_bytes(),
                         "estado.py no debe ensuciar feature_list.json en disco")
        self.assertIn("sync remoto: ok", re_m.stdout)
        self.assertIn("atrasada 1 commit(s)", re_m.stdout)
        self.assertIn("#1 [in_progress] Pagos", re_m.stdout)
        self.assertIn("desarrollando por Alan (mac-alan)", re_m.stdout)
        self.assertNotIn("retoma la feature #1", re_m.stdout)
        self.assertIn("arranca la #2: worktree.py start --feature 2", re_m.stdout)

    def test_dos_devs_trabajan_en_features_distintas_y_gate_check_pasa(self):
        # Alan aprueba spec #1 y arranca #1
        self.assertEqual(0, harness("gate.py", "approve-spec", "--feature", "1", "--yes",
                                    cwd=self.alan, env_extra=self.env_alan()).returncode)
        r1 = harness("worktree.py", "start", "--feature", "1", cwd=self.alan, env_extra=self.env_alan())
        self.assertEqual(0, r1.returncode, r1.stdout + r1.stderr)

        # Maria (sin git pull previo) aprueba spec #2 y arranca #2
        self.assertEqual(0, harness("gate.py", "approve-spec", "--feature", "2", "--yes",
                                    cwd=self.maria, env_extra=self.env_maria()).returncode)
        r2 = harness("worktree.py", "start", "--feature", "2", cwd=self.maria, env_extra=self.env_maria())
        self.assertEqual(0, r2.returncode, r2.stdout + r2.stderr)

        # En origin/develop coexisten ambos desarrollos intactos.
        self.assertEqual("Alan", self.remoto_feature(1)["desarrollo"]["por"])
        self.assertEqual("Maria", self.remoto_feature(2)["desarrollo"]["por"])

        # gate.py check en Maria NO falla por la ruta de worktree de Alan ni por la evidencia de #1.
        chk = harness("gate.py", "check", cwd=self.maria, env_extra=self.env_maria())
        self.assertEqual(0, chk.returncode, chk.stdout + chk.stderr)
        self.assertIn("validacion local delegada a su dueno", chk.stdout)
        self.assertIn("check limpio", chk.stdout)

    def test_mismo_dev_en_otro_equipo_puede_retomar_su_propia_feature(self):
        r1 = harness("worktree.py", "start", "--feature", "1", cwd=self.alan, env_extra=self.env_alan())
        self.assertEqual(0, r1.returncode, r1.stdout + r1.stderr)

        # Misma persona (alan@equipo.test) en otro clon / equipo
        sh("git", "config", "user.name", "Alan", cwd=self.maria)
        sh("git", "config", "user.email", "alan@equipo.test", cwd=self.maria)
        r2 = harness("gate.py", "approve-spec", "--feature", "1", "--yes",
                     cwd=self.maria, env_extra={"HARNESS_HOST_NAME": "linux-alan"})
        self.assertEqual(0, r2.returncode, r2.stdout + r2.stderr)

    def test_fallo_de_red_bloquea_comandos_y_offline_permite_emergencia_y_sync_posterior(self):
        # Apuntamos origin a una ruta inexistente para simular falta de red.
        sh("git", "remote", "set-url", "origin", str(self.bare.parent / "roto.git"), cwd=self.alan)

        for cmd in (
            ("estado.py",),
            ("worktree.py", "start", "--feature", "1"),
            ("gate.py", "approve-spec", "--feature", "1", "--yes"),
            ("gate.py", "check"),
        ):
            with self.subTest(cmd=cmd):
                r = harness(*cmd, cwd=self.alan, env_extra=self.env_alan())
                self.assertNotEqual(0, r.returncode, f"{cmd} debio fallar sin red")
                self.assertIn("--offline", r.stdout + r.stderr)

        # Emergencia --offline arranca en local y marca offline=True
        r_off = harness("worktree.py", "start", "--feature", "1", "--offline",
                        cwd=self.alan, env_extra=self.env_alan())
        self.assertEqual(0, r_off.returncode, r_off.stdout + r_off.stderr)
        self.assertIn("--offline", r_off.stdout)
        f1 = self.local_backlog(self.alan)["features"][0]
        self.assertEqual("in_progress", f1["status"])
        self.assertTrue(f1["desarrollo"].get("offline"))

        # estado.py --offline funciona sin red
        re_off = harness("estado.py", "--offline", cwd=self.alan, env_extra=self.env_alan())
        self.assertEqual(0, re_off.returncode, re_off.stdout + re_off.stderr)
        self.assertIn("--offline", re_off.stdout)

        # Al recuperar la red, gate.py check detecta que #1 no se publico aun en origin.
        sh("git", "remote", "set-url", "origin", str(self.bare), cwd=self.alan)
        chk1 = harness("gate.py", "check", cwd=self.alan, env_extra=self.env_alan())
        self.assertNotEqual(0, chk1.returncode)
        self.assertIn("sin publicar en origin/develop", chk1.stdout)
        self.assertIn("worktree.py sync --feature 1", chk1.stdout)

        # worktree.py sync --feature 1 la publica en origin/develop.
        rs = harness("worktree.py", "sync", "--feature", "1", cwd=self.alan, env_extra=self.env_alan())
        self.assertEqual(0, rs.returncode, rs.stdout + rs.stderr)
        self.assertEqual("Alan", self.remoto_feature(1)["desarrollo"]["por"])

    def test_offline_no_permite_pisar_reclamo_ajeno_ya_conocido_en_local(self):
        self.assertEqual(0, harness("worktree.py", "start", "--feature", "1",
                                    cwd=self.alan, env_extra=self.env_alan()).returncode)
        sh("git", "pull", "-q", "--ff-only", "origin", "develop", cwd=self.maria)

        r = harness("worktree.py", "start", "--feature", "1", "--offline",
                    cwd=self.maria, env_extra=self.env_maria())
        self.assertNotEqual(0, r.returncode)
        self.assertIn("Alan", r.stdout + r.stderr)

    def test_push_fallido_hace_rollback_del_worktree_y_la_rama(self):
        # Hook pre-receive que rechaza cualquier push (ej. branch protection)
        hook = self.bare / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\necho 'protected branch' >&2\nexit 1\n", encoding="utf-8")
        hook.chmod(hook.stat().st_mode | stat.S_IXUSR)

        r = harness("worktree.py", "start", "--feature", "1", cwd=self.alan, env_extra=self.env_alan())
        self.assertNotEqual(0, r.returncode)
        self.assertIn("no se pudo subir", r.stdout + r.stderr)
        self.assertFalse((self.alan.parent / "app-wt" / "1-pagos").exists(),
                         "debe eliminar el worktree al fallar el push")
        ramas = sh("git", "branch", "--list", "feature/1-pagos", cwd=self.alan).stdout.strip()
        self.assertEqual("", ramas, "debe eliminar la rama recien creada al hacer rollback")
        self.assertEqual("todo", self.local_backlog(self.alan)["features"][0]["status"])

    def test_start_desde_rama_ajena_y_arbol_sucio_publica_solo_backlog(self):
        sh("git", "checkout", "-qb", "experimento", cwd=self.alan)
        (self.alan / "borrador.txt").write_text("trabajo sin commitear\n", encoding="utf-8")

        r = harness("worktree.py", "start", "--feature", "1", cwd=self.alan, env_extra=self.env_alan())
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

        rama_actual = sh("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=self.alan).stdout.strip()
        self.assertEqual("experimento", rama_actual, "no debe cambiar la rama activa del repo raiz")
        self.assertTrue((self.alan / "borrador.txt").is_file(), "no debe tocar archivos locales")
        archivos_commit = sh("git", "show", "--name-only", "--pretty=format:", "develop", cwd=self.bare).stdout
        self.assertEqual(["harness/feature_list.json"], [x for x in archivos_commit.splitlines() if x.strip()])

    def test_liberar_propia_y_proteccion_de_feature_ajena(self):
        self.assertEqual(0, harness("worktree.py", "start", "--feature", "1",
                                    cwd=self.alan, env_extra=self.env_alan()).returncode)

        # Maria no puede liberar la feature de Alan sin --forzar --yes
        r_no = harness("worktree.py", "liberar", "--feature", "1",
                       cwd=self.maria, env_extra=self.env_maria())
        self.assertNotEqual(0, r_no.returncode)
        self.assertIn("--forzar --yes", r_no.stdout + r_no.stderr)

        r_sin_yes = harness("worktree.py", "liberar", "--feature", "1", "--forzar",
                            cwd=self.maria, env_extra=self.env_maria())
        self.assertNotEqual(0, r_sin_yes.returncode)

        # Alan libera su propia feature
        r_ok = harness("worktree.py", "liberar", "--feature", "1",
                       cwd=self.alan, env_extra=self.env_alan())
        self.assertEqual(0, r_ok.returncode, r_ok.stdout + r_ok.stderr)
        rem = self.remoto_feature(1)
        self.assertEqual("todo", rem["status"])
        self.assertNotIn("desarrollo", rem)
        self.assertFalse((self.alan.parent / "app-wt" / "1-pagos").exists())

        # Ahora Maria puede tomar #1
        r_maria = harness("worktree.py", "start", "--feature", "1",
                          cwd=self.maria, env_extra=self.env_maria())
        self.assertEqual(0, r_maria.returncode, r_maria.stdout + r_maria.stderr)
        self.assertEqual("Maria", self.remoto_feature(1)["desarrollo"]["por"])

        # Alan puede liberar la de Maria solo con --forzar --yes
        r_forz = harness("worktree.py", "liberar", "--feature", "1", "--forzar", "--yes",
                         cwd=self.alan, env_extra=self.env_alan())
        self.assertEqual(0, r_forz.returncode, r_forz.stdout + r_forz.stderr)
        self.assertEqual("todo", self.remoto_feature(1)["status"])

    def test_colision_de_id_en_remoto_bloquea(self):
        # Alan agrega #3 "Cupones" y la arranca (se publica en origin)
        b_alan = self.local_backlog(self.alan)
        b_alan["features"].append({"id": 3, "name": "Cupones", "kind": "feature", "status": "todo"})
        (self.alan / "harness" / "feature_list.json").write_text(json.dumps(b_alan, indent=2) + "\n")
        self.assertEqual(0, harness("worktree.py", "start", "--feature", "3",
                                    cwd=self.alan, env_extra=self.env_alan()).returncode)

        # Maria agrega otra #3 distinta "Reportes" localmente e intenta arrancarla
        b_maria = self.local_backlog(self.maria)
        b_maria["features"].append({"id": 3, "name": "Reportes", "kind": "feature", "status": "todo"})
        (self.maria / "harness" / "feature_list.json").write_text(json.dumps(b_maria, indent=2) + "\n")
        r = harness("worktree.py", "start", "--feature", "3",
                    cwd=self.maria, env_extra=self.env_maria())
        self.assertNotEqual(0, r.returncode)
        self.assertIn("colision de ID #3", r.stdout + r.stderr)

    def test_regla_require_sync_remoto_true_false_e_invalido(self):
        # Con require_sync_remoto=false incluso con remoto roto no intenta sync.
        sh("git", "remote", "set-url", "origin", str(self.bare.parent / "roto.git"), cwd=self.alan)
        b = self.local_backlog(self.alan)
        b["rules"]["require_sync_remoto"] = False
        (self.alan / "harness" / "feature_list.json").write_text(json.dumps(b, indent=2) + "\n")
        self.assertEqual(0, harness("estado.py", cwd=self.alan, env_extra=self.env_alan()).returncode)

        # Valor invalido falla explicitamente (no apaga la regla en silencio).
        b["rules"]["require_sync_remoto"] = "siempre"
        (self.alan / "harness" / "feature_list.json").write_text(json.dumps(b, indent=2) + "\n")
        r_inv = harness("estado.py", cwd=self.alan, env_extra=self.env_alan())
        self.assertNotEqual(0, r_inv.returncode)
        self.assertIn("require_sync_remoto invalido", r_inv.stdout + r_inv.stderr)

        # Con require_sync_remoto=true sin remoto origin falla salvo --offline.
        sh("git", "remote", "remove", "origin", cwd=self.alan)
        b["rules"]["require_sync_remoto"] = True
        (self.alan / "harness" / "feature_list.json").write_text(json.dumps(b, indent=2) + "\n")
        r_req = harness("estado.py", cwd=self.alan, env_extra=self.env_alan())
        self.assertNotEqual(0, r_req.returncode)
        self.assertIn("require_sync_remoto esta activo", r_req.stdout + r_req.stderr)
        self.assertEqual(0, harness("estado.py", "--offline", cwd=self.alan, env_extra=self.env_alan()).returncode)


class _CursorFalso:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=()):
        self.conn.sql.append((" ".join(sql.split()), tuple(getattr(x, "obj", x) for x in params)))

    def fetchall(self):
        return list(self.conn.filas)


class _ConexionFalsa:
    def __init__(self, filas=()):
        self.sql, self.filas, self.commits = [], list(filas), 0

    def cursor(self):
        return _CursorFalso(self)

    def commit(self):
        self.commits += 1

    def close(self):
        pass


class EspejoHubPostgresTests(EquipoRemotoFixture):
    def setUp(self):
        super().setUp()
        self.hub_env = {
            "DB_HOST": "fake-pg", "DB_USER": "u", "DB_PASSWORD": "p",
            "HARNESS_SIN_HUB": "", "HARNESS_SIN_SYNC_REMOTO": "",
        }

    def test_publicar_y_liberar_en_hub_escriben_nodos_y_arista_desarrollando(self):
        conn = _ConexionFalsa()
        dev = {"por": "Alan", "email": "alan@equipo.test", "id": "alan@equipo.test", "host": "mac-alan"}
        des = sync_remoto.construir_desarrollo(dev, branch="feature/1-pagos", desde="2026-11-21T18:00:00Z")
        f = {"id": 1, "name": "Pagos", "status": "in_progress", "branch": "feature/1-pagos"}

        with mock.patch.dict(os.environ, self.hub_env), mock.patch.object(hub, "conectar", return_value=conn) as cm:
            ok, err = sync_remoto.hub_publicar_desarrollo("tienda", f, des)
        self.assertTrue(ok, err)
        self.assertIsNone(err)
        cm.assert_called_once_with(crear_tablas=True)
        self.assertEqual(1, conn.commits)
        nodos = [p[:2] for s, p in conn.sql if s.startswith("INSERT INTO graph_nodes")]
        self.assertIn(("dev/alan@equipo.test", "Desarrollador"), nodos)
        self.assertIn(("tienda/feature/1", "Feature"), nodos)
        aristas = [p[:3] for s, p in conn.sql if s.startswith("INSERT INTO graph_edges")]
        self.assertIn(("dev/alan@equipo.test", "tienda/feature/1", "DESARROLLANDO"), aristas)

        conn_lib = _ConexionFalsa()
        with mock.patch.dict(os.environ, self.hub_env), mock.patch.object(hub, "conectar", return_value=conn_lib):
            ok_l, err_l = sync_remoto.hub_liberar_desarrollo("tienda", f, nuevo_estado="done")
        self.assertTrue(ok_l, err_l)
        self.assertTrue(any("DELETE FROM graph_edges" in s for s, _ in conn_lib.sql))
        props_feat = next(p[2] for s, p in conn_lib.sql if s.startswith("INSERT INTO graph_nodes"))
        self.assertEqual("cerrada", props_feat["desarrollo_estado"])

    def test_conflicto_solo_en_memory_hub_bloquea_al_segundo_dev_sin_ddl(self):
        """Incluso si Git remoto aun no muestra el reclamo, el espejo del Hub bloquea la colision."""
        filas_hub = [(
            "tienda/feature/1",
            {
                "proyecto": "tienda", "feature_id": "1", "nombre": "Pagos",
                "desarrollo_estado": "desarrollando", "desarrollador": "Alan",
                "desarrollador_id": "alan@equipo.test", "email": "alan@equipo.test",
                "host": "mac-alan", "branch": "feature/1-pagos", "desde": "2026-11-21T18:00:00Z",
            },
        )]
        conn = _ConexionFalsa(filas_hub)
        p = comun.paths(self.maria)
        data = comun.load_backlog(p)
        f = comun.get_feature(data, 1)

        with mock.patch.dict(os.environ, self.hub_env), \
                mock.patch.object(hub, "conectar", return_value=conn) as cm:
            with self.assertRaises(sync_remoto.ErrorConflictoDesarrollo) as ctx:
                sync_remoto.validar_feature_libre(p, data, f, accion="iniciar el desarrollo")
        cm.assert_called_once_with(crear_tablas=False)
        self.assertIn("Alan", str(ctx.exception))
        self.assertIn("Memory Hub Postgres", str(ctx.exception))

    def test_hub_cmd_desarrollo_lista_features_activas_sin_ddl(self):
        filas_hub = [(
            "tienda/feature/2",
            {
                "proyecto": "tienda", "feature_id": "2", "nombre": "Envios",
                "desarrollo_estado": "desarrollando", "desarrollador": "Maria",
                "host": "laptop-maria", "branch": "feature/2-envios", "desde": "2026-11-21T18:10:00Z",
            },
        )]
        conn = _ConexionFalsa(filas_hub)
        salida = io.StringIO()
        with mock.patch.dict(os.environ, self.hub_env), \
                mock.patch.object(hub, "conectar", return_value=conn) as cm, \
                contextlib.redirect_stdout(salida):
            hub.cmd_desarrollo(types.SimpleNamespace(proyecto="tienda", todos=False))
        cm.assert_called_once_with(crear_tablas=False)
        self.assertIn("#2 Envios", salida.getvalue())
        self.assertIn("Maria (laptop-maria)", salida.getvalue())

    def test_carrera_occ_reintenta_y_preserva_ambos_reclamos(self):
        """Si otro dev pushea justo entre nuestro fetch y push, el reintento OCC no lo pisa."""
        p_alan = comun.paths(self.alan)
        data_alan = comun.load_backlog(p_alan)
        f1 = comun.get_feature(data_alan, 1)
        dev_a = sync_remoto.identidad_actual(self.alan, por="alan@equipo.test")
        des_a = sync_remoto.construir_desarrollo(dev_a, branch="feature/1-pagos")
        f1.update(status="in_progress", branch="feature/1-pagos", desarrollo=des_a)

        real_git = sync_remoto._git_cmd
        simulado = {"hecho": False}

        def interceptar(args, cwd, **kw):
            if args and args[0] == "push" and not simulado["hecho"]:
                simulado["hecho"] = True
                # Maria gana la carrera sobre la feature #2 antes del push de Alan.
                r_m = harness("worktree.py", "start", "--feature", "2",
                              cwd=self.maria, env_extra=self.env_maria())
                assert r_m.returncode == 0, r_m.stdout + r_m.stderr
            return real_git(args, cwd, **kw)

        with mock.patch.dict(os.environ, {"HARNESS_SIN_HUB": "1"}), \
                mock.patch.object(sync_remoto, "_git_cmd", side_effect=interceptar):
            res = sync_remoto.publicar_reclamo(p_alan, data_alan, f1, des_a, por="alan@equipo.test")

        self.assertTrue(res["publicado_git"])
        self.assertTrue(simulado["hecho"])
        self.assertEqual("alan@equipo.test", self.remoto_feature(1)["desarrollo"]["id"])
        self.assertEqual("Maria", self.remoto_feature(2)["desarrollo"]["por"])

    def test_close_limpia_desarrollo_y_libera_espejo_hub(self):
        # Preparar #1 para cierre local (sin require_review/verify/leccion en el fixture).
        self.assertEqual(0, harness("gate.py", "approve-spec", "--feature", "1", "--yes",
                                    cwd=self.alan, env_extra=self.env_alan()).returncode)
        r_st = harness("worktree.py", "start", "--feature", "1",
                       cwd=self.alan, env_extra=self.env_alan())
        self.assertEqual(0, r_st.returncode, r_st.stdout + r_st.stderr)
        wt = Path(self.local_backlog(self.alan)["features"][0]["worktree"])
        (wt / "pago.txt").write_text("ok\n", encoding="utf-8")
        sh("git", "add", "-A", cwd=wt)
        sh("git", "commit", "-qm", "feat: pago", cwd=wt)

        # Evidencia y lista de tests (modo pair)
        (self.alan / "docs" / "tests-1.md").write_text(
            "# Tests #1\n\nEstado: draft\n\n- AC-1: cobra_ok [costura: servicio]\n", encoding="utf-8",
        )
        self.assertEqual(0, harness("gate.py", "sellar-tests", "--feature", "1",
                                    cwd=self.alan, env_extra=self.env_alan()).returncode)
        (self.alan / "docs" / "impl-1.md").write_text(
            "# Impl #1\n\n## AC-1\n- pago.txt:1\n", encoding="utf-8",
        )
        sh("git", "add", "-A", cwd=self.alan)
        sh("git", "commit", "-qm", "docs: spec/tests/impl #1", cwd=self.alan)

        conn_lib = _ConexionFalsa()
        import gate
        salida = io.StringIO()
        prev = Path.cwd()
        try:
            os.chdir(self.alan)
            with mock.patch.dict(os.environ, {**self.hub_env, "HARNESS_SIN_CONTEXTO": "1"}), \
                    mock.patch.object(hub, "conectar", return_value=conn_lib), \
                    mock.patch.object(sys, "argv", [
                        "gate.py", "close", "--feature", "1", "--status", "done",
                        "--to", "develop", "--sin-contexto",
                    ]), \
                    contextlib.redirect_stdout(salida):
                gate.main()
        finally:
            os.chdir(prev)

        f1 = self.local_backlog(self.alan)["features"][0]
        self.assertEqual("done", f1["status"])
        self.assertNotIn("desarrollo", f1)
        self.assertEqual("Alan", f1.get("desarrollado_por"))
        self.assertTrue(any("DELETE FROM graph_edges" in s for s, _ in conn_lib.sql))
        self.assertIn("reclamo de desarrollo liberado en Memory Hub Postgres", salida.getvalue())


if __name__ == "__main__":
    unittest.main()
