"""Memory Hub: logica de hub.py sin tocar ninguna base de datos.

`hub.py` no tenia tests propios; solo se probaba lo que lo rodea, con el hub
simulado entero. Lo que cubren estos, cada uno un defecto visto contra un hub
real:

1. Los servicios salian de una convencion de nombres (`ms-*-service`, `*-ui`):
   `front-adr` o `billing-api` nunca tenian dependencias derivadas.
2. `descubrir` solo miraba la raiz del arnes: no veia los servicios de las otras
   raices de harness/grafos.json, y registraba worktrees como microservicios.
3. Una dependencia que desaparecia del codigo seguia en el hub para siempre.
4. El brief decia "sin dependencias" de un servicio que el hub ni conocia.
5. Leer exigia permiso de DDL, y nada impedia que un test abriera la base real.

La conexion es siempre falsa: registra el SQL y devuelve filas preparadas.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

try:                                    # los gates locales corren sin psycopg:
    import psycopg  # noqa: F401        # estos tests tambien
except ImportError:
    falso = types.ModuleType("psycopg")
    falso.Error = type("Error", (Exception,), {})
    tipos, js = types.ModuleType("psycopg.types"), types.ModuleType("psycopg.types.json")
    js.Jsonb = type("Jsonb", (), {"__init__": lambda self, obj: setattr(self, "obj", obj)})
    sys.modules.update({"psycopg": falso, "psycopg.types": tipos, "psycopg.types.json": js})

import comun  # noqa: E402
import contexto  # noqa: E402
import hub  # noqa: E402


class Cursor:
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

    def fetchone(self):
        return self.conn.filas[0] if self.conn.filas else None


class Conexion:
    def __init__(self, filas=()):
        self.sql, self.filas, self.commits = [], list(filas), 0

    def cursor(self):
        return Cursor(self)

    def commit(self):
        self.commits += 1

    def close(self):
        pass

    def aristas(self, verbo="INSERT INTO graph_edges"):
        return [p for s, p in self.sql if s.startswith(verbo)]

    def nodos(self):
        return [p[0] for s, p in self.sql if s.startswith("INSERT INTO graph_nodes")]


def repo(ruta: Path) -> Path:
    (ruta / ".git").mkdir(parents=True)
    return ruta


class Proyecto(unittest.TestCase):
    """Front en la raiz (repo) y servicios en otra carpeta, con nombres sin convencion."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = repo(self.tmp / "tienda")
        self.micros = self.tmp / "servicios"
        repo(self.micros / "billing-api")
        repo(self.micros / "front-adr")
        repo(self.micros / "docs")                       # del proceso, no un servicio
        wt = self.micros / "billing-api-137"             # worktree: trabajo en curso
        wt.mkdir()
        (wt / ".git").write_text("gitdir: /x/billing-api/.git/worktrees/billing-api-137\n")
        sub = self.micros / "catalogo"                   # submodulo: si es un servicio
        sub.mkdir()
        (sub / ".git").write_text("gitdir: ../.git/modules/catalogo\n")
        (self.root / "harness").mkdir()
        (self.root / "harness" / "feature_list.json").write_text(
            json.dumps({"project": "demo", "rules": {}, "features": []}))
        (self.root / "harness" / "grafos.json").write_text(json.dumps({"raices": [
            {"nombre": "web", "path": "."}, {"nombre": "servicios", "path": str(self.micros)}]}))
        self.p = comun.paths(self.root)
        self._cwd = os.getcwd()
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self._cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def grafo(self, nodos, aristas) -> None:
        self.p["graph"].parent.mkdir(parents=True, exist_ok=True)
        self.p["graph"].write_text(json.dumps({"nodes": nodos, "edges": aristas}))

    def correr(self, fn, conn, **args) -> str:
        salida = io.StringIO()
        with mock.patch.object(hub, "conectar", return_value=conn), contextlib.redirect_stdout(salida):
            fn(types.SimpleNamespace(**args))
        return salida.getvalue()


class ServiciosTests(Proyecto):
    def test_salen_de_los_repos_de_todas_las_raices_con_cualquier_nombre(self):
        s = comun.servicios_del_proyecto(self.p)
        self.assertEqual(["billing-api", "catalogo", "front-adr", "web"], sorted(s))
        self.assertTrue(s["web"]["es_raiz"], "la raiz que es un repo lleva su nombre declarado")
        self.assertEqual(self.micros / "billing-api", s["billing-api"]["path"])

    def test_un_worktree_no_es_un_servicio(self):
        self.assertNotIn("billing-api-137", comun.servicios_del_proyecto(self.p))

    def test_docs_y_harness_no_son_servicios(self):
        s = comun.servicios_del_proyecto(self.p)
        self.assertNotIn("docs", s)
        self.assertNotIn("harness", s)

    def test_sin_grafos_json_valen_los_repos_de_la_raiz(self):
        (self.root / "harness" / "grafos.json").unlink()
        repo(self.root / "ms-uno")
        self.assertEqual(["ms-uno", "tienda"], sorted(comun.servicios_del_proyecto(self.p)))


class DescubrirTests(Proyecto):
    def test_sin_aplicar_lista_y_no_abre_conexion(self):
        with mock.patch.object(hub, "conectar", side_effect=AssertionError("no debe conectar")):
            salida = io.StringIO()
            with contextlib.redirect_stdout(salida):
                hub.cmd_descubrir(types.SimpleNamespace(aplicar=False))
        self.assertIn("billing-api", salida.getvalue())
        self.assertIn("solo lectura", salida.getvalue())

    def test_aplicar_registra_cada_servicio_con_su_ruta(self):
        conn = Conexion()
        self.correr(hub.cmd_descubrir, conn, aplicar=True)
        self.assertEqual(["demo", "demo/billing-api", "demo/catalogo", "demo/front-adr", "demo/web"],
                         sorted(conn.nodos()))
        rutas = {p[0]: p[2]["path"] for s, p in conn.sql
                 if s.startswith("INSERT INTO graph_nodes") and p[1] == "Microservicio"}
        self.assertEqual(str(self.micros / "billing-api"), rutas["demo/billing-api"])
        self.assertEqual(1, conn.commits)


class DerivarTests(Proyecto):
    def nodos_y_arista(self, origen, destino, relacion="references"):
        nodos = [{"id": "a", "label": "Cliente", "source_file": origen[0], "repo": origen[1]},
                 {"id": "b", "label": "Factura", "source_file": destino[0], "repo": destino[1]}]
        return nodos, [{"source": "a", "target": "b", "relation": relacion}]

    def test_la_convencion_de_nombres_no_reconocia_estos_servicios(self):
        """El control: con la regla de antes, ninguno de los dos existe."""
        self.assertIsNone(hub.SERVICE_RE.search("billing-api/pkg/factura.go"))
        self.assertIsNone(hub.SERVICE_RE.search("front-adr/src/cliente.ts"))

    def test_deriva_la_dependencia_entre_servicios_de_cualquier_nombre(self):
        self.grafo(*self.nodos_y_arista(("front-adr/src/cliente.ts", "tmp_servicios"),
                                        ("billing-api/pkg/factura.go", "tmp_servicios")))
        conn = Conexion()
        salida = self.correr(hub.cmd_derivar_graphify, conn)
        aristas = conn.aristas()
        self.assertEqual(1, len(aristas), salida)
        self.assertEqual(("demo/front-adr", "demo/billing-api", "DEPENDE_DE"), aristas[0][:3])
        self.assertEqual("graphify", aristas[0][3]["origen"])

    def test_el_codigo_de_la_raiz_cuenta_como_el_servicio_de_la_raiz(self):
        """Los archivos del front no traen su nombre en la ruta: lo dice la etiqueta del grafo."""
        etiqueta = f"{self.root.parent.name}_{self.root.name}"
        self.grafo(*self.nodos_y_arista(("src/app/cliente.ts", etiqueta),
                                        ("billing-api/pkg/factura.go", "tmp_servicios")))
        conn = Conexion()
        self.correr(hub.cmd_derivar_graphify, conn)
        self.assertEqual(("demo/web", "demo/billing-api", "DEPENDE_DE"), conn.aristas()[0][:3])

    def test_sin_repos_conocidos_sigue_valiendo_la_convencion_de_antes(self):
        for d in (self.micros, self.root / ".git"):
            shutil.rmtree(d)
        self.grafo(*self.nodos_y_arista(("ms-cobros-service/a.go", None), ("portal-ui/b.ts", None)))
        conn = Conexion()
        self.correr(hub.cmd_derivar_graphify, conn)
        self.assertEqual(("demo/ms-cobros-service", "demo/portal-ui", "DEPENDE_DE"), conn.aristas()[0][:3])

    def test_dentro_del_mismo_servicio_no_hay_dependencia(self):
        self.grafo(*self.nodos_y_arista(("billing-api/a.go", "x"), ("billing-api/b.go", "x")))
        conn = Conexion()
        self.correr(hub.cmd_derivar_graphify, conn)
        self.assertEqual([], conn.aristas())

    def test_una_relacion_que_no_es_de_dependencia_no_cuenta(self):
        self.grafo(*self.nodos_y_arista(("front-adr/a.ts", "x"), ("billing-api/b.go", "x"), "contains"))
        conn = Conexion()
        self.correr(hub.cmd_derivar_graphify, conn)
        self.assertEqual([], conn.aristas())


class PurgaTests(Proyecto):
    def setUp(self):
        super().setUp()
        # El grafo conoce front-adr, billing-api y catalogo; solo front-adr -> billing-api depende.
        self.grafo(
            [{"id": "a", "label": "A", "source_file": "front-adr/a.ts", "repo": "x"},
             {"id": "b", "label": "B", "source_file": "billing-api/b.go", "repo": "x"},
             {"id": "c", "label": "C", "source_file": "catalogo/c.go", "repo": "x"}],
            [{"source": "a", "target": "b", "relation": "references"}])

    def borradas(self, filas):
        conn = Conexion(filas)
        salida = self.correr(hub.cmd_derivar_graphify, conn)
        return [p[:2] for p in conn.aristas("DELETE FROM graph_edges")], conn, salida

    def test_retira_la_dependencia_que_ya_no_esta_en_el_grafo(self):
        borradas, _, salida = self.borradas([("demo/front-adr", "demo/billing-api"),
                                              ("demo/catalogo", "demo/billing-api")])
        self.assertEqual([("demo/catalogo", "demo/billing-api")], borradas)
        self.assertIn("retiradas del hub", salida)

    def test_no_toca_las_de_un_servicio_que_el_grafo_no_contiene(self):
        """Raiz sin refrescar o merge a medias: su ausencia no prueba que la dependencia murio."""
        borradas, _, _ = self.borradas([("demo/catalogo", "demo/servicio-ausente")])
        self.assertEqual([], borradas)

    def test_solo_mira_y_borra_las_de_origen_graphify_de_este_proyecto(self):
        """Las de `vincular` (manuales) y las de otros proyectos no entran ni a la consulta."""
        _, conn, _ = self.borradas([("demo/catalogo", "demo/billing-api")])
        consulta = next(s for s, _ in conn.sql if s.startswith("SELECT source,target FROM graph_edges"))
        self.assertIn("props->>'origen'='graphify'", consulta)
        params = next(p for s, p in conn.sql if s.startswith("SELECT source,target FROM graph_edges"))
        self.assertEqual(("DEPENDE_DE", "demo/%"), params)
        borrado = next(s for s, _ in conn.sql if s.startswith("DELETE FROM graph_edges"))
        self.assertIn("props->>'origen'='graphify'", borrado)

    def test_lo_vigente_no_se_borra(self):
        borradas, _, _ = self.borradas([("demo/front-adr", "demo/billing-api")])
        self.assertEqual([], borradas)


class ConexionTests(unittest.TestCase):
    def setUp(self):
        self.conn = Conexion()
        self.psy = types.SimpleNamespace(connect=mock.Mock(return_value=self.conn),
                                         Error=type("Error", (Exception,), {}))
        self.env = {"DB_HOST": "h", "DB_USER": "u", "DB_PASSWORD": "p",
                    "HARNESS_HUB": tempfile.mkdtemp(), "HARNESS_SIN_HUB": ""}

    def tearDown(self):
        shutil.rmtree(self.env["HARNESS_HUB"], ignore_errors=True)

    def conectar(self, **kw):
        with mock.patch.dict(sys.modules, {"psycopg": self.psy}), mock.patch.dict(os.environ, self.env):
            return hub.conectar(**kw)

    def test_leer_no_ejecuta_ddl(self):
        self.conectar(crear_tablas=False)
        self.assertEqual([], self.conn.sql)

    def test_escribir_si_asegura_las_tablas(self):
        self.conectar()
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS graph_nodes" in s for s, _ in self.conn.sql))

    def test_los_comandos_de_lectura_piden_la_conexion_sin_ddl(self):
        for fn, args in ((hub.cmd_mapa, {}), (hub.cmd_impacto, {"microservicio": "demo/x"}),
                         (hub.cmd_consultar, {"artefacto": "x"})):
            with self.subTest(comando=fn.__name__):
                conectar = mock.Mock(return_value=Conexion())
                with mock.patch.object(hub, "conectar", conectar), \
                        mock.patch.dict(os.environ, self.env), contextlib.redirect_stdout(io.StringIO()):
                    fn(types.SimpleNamespace(**args))
                conectar.assert_called_once_with(crear_tablas=False)

    def test_harness_sin_hub_impide_conectar(self):
        self.env["HARNESS_SIN_HUB"] = "1"
        with self.assertRaises(SystemExit) as salida:
            self.conectar()
        self.assertIn("HARNESS_SIN_HUB", str(salida.exception))
        self.psy.connect.assert_not_called()

    def test_un_fallo_de_conexion_sale_en_una_linea_y_sin_la_clave(self):
        self.psy.connect.side_effect = self.psy.Error("connection refused\ndetalle largo")
        with self.assertRaises(SystemExit) as salida:
            self.conectar()
        self.assertEqual("[!!] no se pudo conectar al hub: connection refused", str(salida.exception))


class BriefTests(unittest.TestCase):
    def compacto(self, filas):
        with mock.patch.object(contexto, "_impacto_hub", return_value=filas):
            return contexto._impacto_compacto("demo", "ms-x")[0]

    def test_un_servicio_que_el_hub_no_conoce_no_es_un_servicio_sin_dependencias(self):
        linea = self.compacto(["[!] demo/ms-x no existe en el hub. Corre: hub.py descubrir --aplicar",
                               "== Impacto de demo/ms-x ==", "Si tocas esto, se puede romper (0):",
                               "(nadie declarado depende de el)", "Depende de (0):"])
        self.assertIn("NO esta en el hub", linea)
        self.assertNotIn("sin dependencias", linea)

    def test_un_servicio_conocido_sin_dependencias_si_lo_dice(self):
        linea = self.compacto(["== Impacto de demo/ms-x ==", "Si tocas esto, se puede romper (0):",
                               "(nadie declarado depende de el)", "Depende de (0):"])
        self.assertIn("sin dependencias declaradas en el hub", linea)

    def test_con_dependencias_las_resume(self):
        linea = self.compacto(["Si tocas esto, se puede romper (1):", "<- demo/ms-a  [DEPENDE_DE]",
                               "Depende de (1):", "-> demo/ms-b  [DEPENDE_DE]"])
        self.assertIn("rompe a: ms-a | usa: ms-b", linea)

    def test_los_servicios_que_no_se_consultan_se_nombran(self):
        micros = [f"ms-{i}" for i in range(6)]
        with mock.patch.object(contexto, "_impacto_hub", return_value=[]):
            lineas = contexto._lineas_impacto("demo", micros)
        self.assertIn("+2 sin consultar: ms-4, ms-5", lineas[-1])
        self.assertEqual(4, sum(1 for l in lineas if l.startswith("  [ms-")))

    def test_sin_microservicios_no_hay_seccion(self):
        self.assertEqual([], contexto._lineas_impacto("demo", []))

    def test_el_brief_no_abre_el_hub_en_tests_ni_en_ci(self):
        for var in ("HARNESS_SIN_HUB", "HARNESS_SIN_CONTEXTO"):
            with self.subTest(variable=var):
                limpio = {"HARNESS_SIN_HUB": "", "HARNESS_SIN_CONTEXTO": "", var: "1"}
                with mock.patch.dict(os.environ, limpio), \
                        mock.patch.object(contexto, "_run", side_effect=AssertionError("no debe lanzar hub.py")):
                    filas = contexto._impacto_hub("demo/ms-x")
                self.assertIn(var, filas[0])
                self.assertIn("no disponible", filas[0])

    def test_sin_esas_variables_el_brief_si_consulta(self):
        """El control: el interruptor no deja el hub apagado siempre."""
        limpio = {"HARNESS_SIN_HUB": "", "HARNESS_SIN_CONTEXTO": ""}
        with mock.patch.dict(os.environ, limpio), \
                mock.patch.object(contexto, "_run", return_value=(0, "linea")) as run:
            self.assertEqual(["linea"], contexto._impacto_hub("demo/ms-x"))
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
