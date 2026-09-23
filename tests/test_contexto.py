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
        # grafo con nodos: '{}' lo rechaza _grafo_utilizable, y con razon.
        # Aca lo que se prueba son las rutas absolutas del merge, no el
        # contenido, pero el stub igual debe parecerse a un grafo real.
        grafo = json.dumps({"nodes": [{"id": "a"}], "edges": []})
        (self.root / "graphify-out").mkdir(parents=True, exist_ok=True)
        (self.root / "graphify-out" / "graph.json").write_text(grafo, encoding="utf-8")
        (self.otra / "graphify-out" / "graph.json").write_text(grafo, encoding="utf-8")
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

    # --- vault: contrato de los nodos del grafo ----------------------------

    def _vault_build(self, *flags):
        """Corre vault.py como lo corre el flujo, sobre este proyecto."""
        import subprocess
        (self.root / "graphify-out").mkdir(exist_ok=True)
        (self.root / "graphify-out" / "graph.json").write_text(json.dumps(_grafo(
            [{"id": "a", "label": "cobrar", "type": "function", "source_file": "app.py"},
             {"id": "b", "label": "validar", "type": "function", "source_file": "app.py"}],
            [{"source": "a", "target": "b", "relation": "calls"}])), encoding="utf-8")
        r = subprocess.run([sys.executable, str(SCRIPTS / "vault.py"), "build", *flags],
                           cwd=str(self.root), capture_output=True, text=True)
        self.assertEqual(0, r.returncode, r.stderr[-400:])
        return self.root / "docs" / "vault" / "grafo"

    def test_el_vault_por_defecto_no_trae_nodos_del_grafo(self):
        """SKILL.md prometia 'wikilinks a nodos de graphify' sobre `vault.py build`.

        Nunca los trajo: son opt-in con --con-grafo, y ni el comando documentado
        ni contexto.py refrescar la pasan. Quien abria el vault buscando navegar
        del spec al nodo de codigo no encontraba la carpeta.
        """
        self.assertFalse(self._vault_build().exists())

    def test_con_grafo_si_escribe_una_nota_por_nodo(self):
        gd = self._vault_build("--con-grafo")
        self.assertTrue(gd.is_dir())
        self.assertEqual(2, len(list(gd.glob("*.md"))))
        self.assertIn("[[vault/grafo/validar|validar]]",
                      (gd / "cobrar.md").read_text(encoding="utf-8"))

    # --- vault: enlaces que Obsidian puede seguir ---------------------------

    def _backlog_como_el_real(self):
        """Lo que trae un backlog de verdad y rompia los enlaces del vault."""
        self._declarar()
        (self.otra / "ms-baz-service" / ".git").mkdir(parents=True)
        (self.root / "docs" / ".git").mkdir()  # docs como submodulo
        data = json.loads((self.root / "harness" / "feature_list.json").read_text())
        data["features"] += [
            {"id": 2, "name": "Prefijo del hub", "status": "done",
             "microservicios": ["demo/ms-foo-service"], "leccion": "ninguna"},
            {"id": 3, "name": "Texto libre", "status": "todo",
             "microservicios": ["ms-bar-service (solo lectura, evidencia), admin"],
             "leccion": "gates-que-no-mienten"},
        ]
        (self.root / "harness" / "feature_list.json").write_text(json.dumps(data))
        (self.root / "docs" / "impl-1.md").write_text("| AC-1 | a.go:1 |\n")
        (self.root / "docs" / "review-1.md").write_text("Veredicto: approved\n")
        # un .md fuera del vault con el mismo nombre que una nota generada:
        # un wikilink por nombre pelado seria ambiguo
        (self.root / "docs" / "copias").mkdir()
        (self.root / "docs" / "copias" / "gates-que-no-mienten.md").write_text("x\n")

    def test_el_vault_no_deja_enlaces_sin_nota(self):
        """En realestate, 281 de 506 wikilinks no llevaban a ninguna nota.

        Microservicios con prefijo del hub o texto libre, `[[ninguna]]`, micros
        de otra raiz sin nota, y spec/evidencia/review enlazados FUERA del
        vault, donde Obsidian no llega. La raiz del vault es docs/.
        """
        import re
        self._backlog_como_el_real()
        self._vault_build()
        docs = self.root / "docs"
        todas = [q for q in docs.rglob("*.md") if ".obsidian" not in q.parts]
        rutas = {q.relative_to(docs).with_suffix("").as_posix() for q in todas}
        nombres = [q.stem for q in todas]
        rotos, fuera = [], []
        for q in (docs / "vault").rglob("*.md"):
            texto = q.read_text(encoding="utf-8")
            for m in re.findall(r"\[\[([^\]]+)\]\]", texto):
                destino = m.split("|")[0].split("#")[0]
                if destino not in rutas and nombres.count(destino) != 1:
                    rotos.append(f"{q.name}: [[{m}]]")
            for m in re.findall(r"\]\(([^)]+\.md)\)", texto):
                if not (q.parent / m).resolve().is_relative_to(docs.resolve()):
                    fuera.append(f"{q.name}: {m}")
        self.assertEqual([], rotos)
        self.assertEqual([], fuera)
        servicios = {q.stem for q in (docs / "vault" / "servicios").glob("*.md")}
        self.assertIn("ms-baz-service", servicios)  # vive en la otra raiz
        self.assertNotIn("docs", servicios)         # es del proceso
        self.assertTrue((docs / ".obsidian" / "app.json").exists())
        self.assertFalse((docs / "vault" / ".obsidian").exists())

    def test_la_nota_de_leccion_cita_la_skill_real(self):
        """Decia 'Skill de Hermes' aunque el archivo viviera en otro host.

        En Grok la leccion esta en ~/.grok/skills. La nota tiene que citar ese
        SKILL.md, no un host fijo.
        """
        import subprocess
        skills = Path(self.tmp.name) / "skills"
        clase = "gates-que-no-mienten"
        (skills / clase).mkdir(parents=True)
        (skills / clase / "SKILL.md").write_text(
            "---\nname: gates-que-no-mienten\ndescription: x\n---\n",
            encoding="utf-8")
        self._backlog_como_el_real()
        env = dict(os.environ, HARNESS_SKILLS_DIR=str(skills), HARNESS_HOST="grok")
        r = subprocess.run([sys.executable, str(SCRIPTS / "vault.py"), "build"],
                           cwd=str(self.root), capture_output=True, text=True, env=env)
        self.assertEqual(0, r.returncode, r.stderr[-400:] + r.stdout[-400:])
        nota = (self.root / "docs" / "vault" / "lecciones" / f"{clase}.md"
                ).read_text(encoding="utf-8")
        resuelto = str((skills / clase / "SKILL.md").resolve())
        casa = str(Path.home())
        citado = "~" + resuelto[len(casa):] if resuelto.startswith(casa + os.sep) else resuelto
        self.assertIn(f"Archivo: `{citado}`", nota)
        self.assertNotIn("Skill de Hermes", nota)
        self.assertNotIn("skills de Hermes", nota)

    def test_micros_declarados_sin_comas_de_comentario_ni_prefijo(self):
        f = {"microservicios": ["docs (SUBMODULO, mode 160000: es OTRO repo), "
                                "demo/ms-foo-service", "ninguno"]}
        self.assertEqual(contexto._micros_declarados(f), ["docs", "ms-foo-service"])

    def test_el_vault_borra_solo_lo_generado_que_ya_no_corresponde(self):
        """Un servicio renombrado dejaba su nota vieja para siempre."""
        import vault
        sv = self.root / "docs" / "vault" / "servicios"
        sv.mkdir(parents=True)
        (sv / "viejo.md").write_text(vault.AVISO + "\n")
        (sv / "a-mano.md").write_text("mia\n")
        self._vault_build()
        self.assertFalse((sv / "viejo.md").exists())
        self.assertTrue((sv / "a-mano.md").exists())

    def test_refrescar_sin_graphify_igual_regenera_el_vault(self):
        """El vault no usa graphify: cortar antes lo dejaba sin regenerar nunca."""
        with mock.patch.object(contexto.shutil, "which", return_value=None):
            parte = contexto.refrescar(comun.paths(self.root), verboso=False)
        self.assertIn("graphify no esta en el PATH", parte["fallos"])
        self.assertEqual("ok", parte["vault"])
        self.assertTrue((self.root / "docs" / "vault" / "Indice.md").exists())

    def test_backlog_mas_nuevo_que_el_vault_lo_regenera_sin_tocar_el_grafo(self):
        """Con el grafo fresco, `start` no regeneraba el vault: mostraba estados
        viejos toda la feature."""
        self._vault_build()
        viejo = time.time() - 3600
        os.utime(self.root / "docs" / "vault" / "Indice.md", (viejo, viejo))
        p = comun.paths(self.root)
        e = contexto.estado_contexto(p)
        self.assertTrue(e["fresco"], e["vencidas"])
        self.assertTrue(e["vault"]["vencido"])
        vistos = []

        def fake_run(cmd, cwd):
            vistos.append(cmd)
            return 0, ""

        with mock.patch.object(contexto, "_run", fake_run), \
                mock.patch.dict(os.environ, {"HARNESS_SIN_CONTEXTO": "0"}), \
                contextlib.redirect_stdout(io.StringIO()):
            parte = contexto.refrescar_si_vencido(p, etiqueta="arrancar #1")
        self.assertEqual("ok", parte["vault"])
        self.assertEqual(1, len(vistos), vistos)
        self.assertTrue(any("vault.py" in str(x) for x in vistos[0]))

    def test_el_refresco_automatico_no_pasa_con_grafo(self):
        """Deliberado: una nota por nodo (tope 2000) en cada refresco ahoga el vault.

        Si alguien lo cambia, este rojo obliga a corregir SKILL.md en el mismo
        commit, en vez de dejar la doc contando otra cosa.
        """
        vistos = []

        def fake_run(cmd, cwd):
            vistos.append(cmd)
            return 0, ""

        with mock.patch.object(contexto, "_run", fake_run), \
             mock.patch.object(contexto.shutil, "which", lambda _: "/usr/bin/graphify"):
            contexto.refrescar(comun.paths(), con_vault=True, con_hub=False, verboso=False)

        vault = [c for c in vistos if any("vault.py" in str(x) for x in c)]
        self.assertEqual(1, len(vault), f"vault.py no se invoco: {vistos}")
        self.assertNotIn("--con-grafo", vault[0])

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
