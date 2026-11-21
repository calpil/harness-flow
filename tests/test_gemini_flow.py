"""Cobertura completa de harness-flow para Gemini (AGY / Antigravity y Gemini CLI).

Verifica los 5 cambios especificos del flujo Gemini:
1. `gemini_sesion.py`: publica rules (con `trigger: always_on`) y skills de front y
   backend en `.agents/` (AGY) y `.gemini/` (Gemini CLI) sin duplicar copias nativas
   ya vigentes, sin ensuciar git (`info/exclude`) y sin tocar archivos del usuario.
2. `_repos_de_la_feature`: en una feature nueva (spec draft sin microservicios ni
   worktree) cuya raiz es frontend (`angular-product`), el brief del Leader carga
   TAMBIEN los stacks de repos hermanos del proyecto (backend).
3. Politica Gemini 4 por rol (`modelo.py gemini`, `estado.py`, `producto.py borrador`,
   `contexto.py brief`, `revision.py --briefing`): Carbon High en Producto/Leader,
   Argon High en Implementer/Revisor, Hydrogen en Cierre/Estado; silencioso en otros hosts.
4. Context7 lazy-loaded (`call_mcp_tool` en AGY) y formulario (`ask_question` en AGY /
   Markdown en Gemini CLI) impresos en `contexto.py brief` y `revision.py --briefing`.
5. `GEMINI.md` generado por `stack.py normalizar` importando `@./AGENTS.md`, sin
   sobrescribir un `GEMINI.md` del usuario, y guia dedicada `references/gemini.md`.
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

import comun  # noqa: E402
import contexto  # noqa: E402
import gemini_sesion  # noqa: E402
import stack  # noqa: E402
from comun import load_backlog, micros_declarados, paths  # noqa: E402

SPEC_DRAFT = (
    "# Spec - Feature #1: cobro\n\nEstado: draft\n\n"
    "## Criterios de aceptacion\n\n"
    "- AC-1: dado un carro, cuando pago, entonces cobra. `verificar: true`\n"
)


def escribir(ruta: Path, texto: str = "") -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


class GeminiFlowBase(unittest.TestCase):
    def setUp(self):
        self._host = os.environ.get("HARNESS_HOST")
        os.environ["HARNESS_HOST"] = "gemini"
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = self.tmp / "front"
        self.go = self.tmp / "servicios" / "ms-pagos"
        self.wt = self.tmp / "wt-cobro"
        escribir(self.root / "angular.json", "{}")
        escribir(self.root / "package.json", json.dumps({"dependencies": {"@angular/core": "19.0.0"}}))
        escribir(self.go / "go.mod", "module example.com/ms-pagos\n")
        escribir(self.wt / "angular.json", "{}")
        escribir(self.wt / "package.json", json.dumps({"dependencies": {"@angular/core": "19.0.0"}}))
        escribir(self.root / "harness" / "grafos.json", json.dumps({"raices": [
            {"nombre": "front", "path": "."},
            {"nombre": "servicios", "path": str(self.go.parent)},
        ]}))
        escribir(self.root / "docs" / "spec-feature-1-cobro.md", SPEC_DRAFT)
        self.backlog({
            "id": 1, "name": "cobro", "status": "in_progress", "modo": "pair",
            "microservicios": ["ms-pagos"], "worktree": str(self.wt),
        })
        self._git(self.root, "init")
        escribir(self.root / "README.md", "front\n")
        self._git(self.root, "add", "-A")
        self._git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "init")
        self.p = paths(self.root)

    def tearDown(self):
        if self._host is None:
            os.environ.pop("HARNESS_HOST", None)
        else:
            os.environ["HARNESS_HOST"] = self._host
        stack._planes.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _git(self, repo: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(repo), *args], check=True,
                              capture_output=True, text=True)

    def backlog(self, feature: dict, rules: dict | None = None) -> None:
        escribir(self.root / "harness" / "feature_list.json",
                 json.dumps({"project": "demo", "rules": rules or {"rama_base": "main", "require_docs_al_dia": False},
                             "features": [feature]}))

    def run_script(self, script: str, *args: str, host: str = "gemini", cwd: Path | None = None):
        env = dict(os.environ, HARNESS_HOST=host, HARNESS_SIN_CONTEXTO="1",
                   HARNESS_SIN_HUB="1", HARNESS_SIN_CBM="1")
        return subprocess.run(
            [sys.executable, str(SCRIPTS / script), *args],
            cwd=str(cwd or self.root), capture_output=True, text=True, env=env,
        )


class GeminiSesionTests(GeminiFlowBase):
    def reglas(self, rol: str = "implementer") -> str:
        data = load_backlog(self.p)
        f = data["features"][0]
        return "\n".join(contexto.lineas_reglas(self.p, data, f, micros_declarados(f), rol=rol))

    def test_publica_front_y_backend_en_agents_y_gemini_con_always_on(self):
        out = self.reglas("implementer")
        self.assertIn("gemini sesion (implementer)", out)
        for base in (self.root, self.go, self.wt):
            for carpeta in (".agents", ".gemini"):
                go_skill = base / carpeta / "skills" / "golang-hexagonal--add-api-endpoint" / "SKILL.md"
                ang_skill = base / carpeta / "skills" / "angular-product--add-ui-component" / "SKILL.md"
                regla = base / carpeta / "rules" / "golang-hexagonal--architecture.md"
                sesion = base / carpeta / "rules" / "harness-flow-sesion.md"
                self.assertTrue(go_skill.is_file(), (base, carpeta))
                self.assertTrue(ang_skill.is_file(), (base, carpeta))
                self.assertIn("trigger: always_on", regla.read_text(encoding="utf-8"))
                self.assertIn("trigger: always_on", sesion.read_text(encoding="utf-8"))
                self.assertIn("Gemini 4 Argon (High)", sesion.read_text(encoding="utf-8"))
                self.assertIn("name: golang-hexagonal--add-api-endpoint", go_skill.read_text(encoding="utf-8"))

    def test_no_duplica_stack_nativo_ya_instalado_y_si_publica_hermano(self):
        stack.normalizar_repositorio(self.root, "angular-product", rules={})
        stack._planes.clear()
        self.reglas("implementer")
        # En la raiz Angular normalizada, NO se duplica angular-product--*, pero SI llega golang-hexagonal--*
        for carpeta in (".agents", ".gemini"):
            self.assertTrue((self.root / carpeta / "rules" / "architecture.md").is_file())
            self.assertFalse((self.root / carpeta / "rules" / "angular-product--architecture.md").exists())
            self.assertFalse((self.root / carpeta / "skills" / "angular-product--add-ui-component").exists())
            self.assertTrue((self.root / carpeta / "rules" / "golang-hexagonal--architecture.md").is_file())
            self.assertTrue((self.root / carpeta / "skills" / "golang-hexagonal--add-api-endpoint" / "SKILL.md").is_file())

    def test_la_copia_no_ensucia_git(self):
        self.reglas("implementer")
        self.assertEqual("", self._git(self.root, "status", "--porcelain").stdout)
        for ruta in (".agents/skills/golang-hexagonal--add-api-endpoint",
                     ".gemini/rules/golang-hexagonal--architecture.md",
                     ".agents/rules/harness-flow-sesion.md"):
            chk = subprocess.run(["git", "-C", str(self.root), "check-ignore", "-q", ruta],
                                 capture_output=True, text=True)
            self.assertEqual(0, chk.returncode, ruta)

    def test_excluidas_no_entran_y_usuario_no_se_toca(self):
        mia = self.root / ".agents" / "skills" / "mia" / "SKILL.md"
        escribir(mia, "---\nname: mia\ndescription: Mia.\n---\n\n# Mia\n")
        self.backlog(
            {"id": 1, "name": "cobro", "status": "in_progress",
             "microservicios": ["ms-pagos"], "worktree": str(self.wt)},
            {"rama_base": "main", "stack_skills_excluidas": {"golang-hexagonal": ["add-persistence"]}},
        )
        self.reglas("implementer")
        self.assertFalse((self.root / ".agents" / "skills" / "golang-hexagonal--add-persistence").exists())
        self.assertFalse((self.root / ".gemini" / "skills" / "golang-hexagonal--add-persistence").exists())
        self.assertTrue((self.root / ".agents" / "skills" / "golang-hexagonal--add-api-endpoint").is_dir())
        self.assertTrue(mia.is_file())

    def test_rol_siguiente_retira_stack_que_ya_no_toca(self):
        self.reglas("implementer")
        self.assertTrue((self.root / ".agents" / "skills" / "golang-hexagonal--add-api-endpoint").is_dir())
        data = load_backlog(self.p)
        f = data["features"][0]
        f["microservicios"] = []
        self.backlog(f)
        self.reglas("implementer")
        self.assertFalse((self.root / ".agents" / "skills" / "golang-hexagonal--add-api-endpoint").exists())
        self.assertFalse((self.root / ".gemini" / "skills" / "golang-hexagonal--add-api-endpoint").exists())

    def test_worktree_con_carpetas_enlazadas_se_omite_sin_error(self):
        stack.normalizar_repositorio(self.root, "angular-product", rules={})
        # Simula worktree donde `.agents/rules` es symlink al checkout principal
        wt_link = self.tmp / "wt-link"
        escribir(wt_link / "angular.json", "{}")
        escribir(wt_link / "package.json", json.dumps({"dependencies": {"@angular/core": "19.0.0"}}))
        (wt_link / ".agents").mkdir(parents=True)
        (wt_link / ".agents" / "rules").symlink_to((self.root / ".agents" / "rules").resolve())
        (wt_link / ".gemini").mkdir(parents=True)
        (wt_link / ".gemini" / "rules").symlink_to((self.root / ".gemini" / "rules").resolve())
        self.backlog({"id": 1, "name": "cobro", "status": "in_progress",
                      "microservicios": ["ms-pagos"], "worktree": str(wt_link)})
        out = self.reglas("implementer")
        self.assertNotIn("[!] gemini sesion", out)
        # Al escribir en root, el symlink en wt_link ve la regla hermana automaticamente
        self.assertTrue((wt_link / ".agents" / "rules" / "golang-hexagonal--architecture.md").is_file())

    def test_sdd_publica_y_prd_no_publica_y_otro_host_no_escribe(self):
        limpio = self.tmp / "limpio"
        shutil.copytree(self.root, limpio, ignore=shutil.ignore_patterns(".git", ".agents", ".gemini"))
        r_prd = self.run_script("producto.py", "borrador", "--doc", "prd", host="gemini", cwd=limpio)
        self.assertEqual(0, r_prd.returncode, r_prd.stdout + r_prd.stderr)
        self.assertNotIn("gemini sesion", r_prd.stdout)
        self.assertFalse((limpio / ".agents" / "rules" / gemini_sesion.SESION).exists())

        r_sdd = self.run_script("producto.py", "borrador", "--doc", "sdd", host="gemini", cwd=limpio)
        self.assertEqual(0, r_sdd.returncode, r_sdd.stdout + r_sdd.stderr)
        self.assertIn("gemini sesion (sdd)", r_sdd.stdout)
        self.assertTrue((limpio / ".agents" / "rules" / "golang-hexagonal--architecture.md").is_file())
        self.assertTrue((limpio / ".gemini" / "rules" / "angular-product--architecture.md").is_file())

        # En otro host no escribe gemini_sesion
        os.environ["HARNESS_HOST"] = "claude"
        limpio2 = self.tmp / "limpio2"
        shutil.copytree(self.root, limpio2, ignore=shutil.ignore_patterns(".git", ".agents", ".gemini"))
        p2 = paths(limpio2)
        d2 = load_backlog(p2)
        out_claude = "\n".join(contexto.lineas_reglas(p2, d2, d2["features"][0], ["ms-pagos"]))
        self.assertNotIn("gemini sesion", out_claude)
        self.assertFalse((limpio2 / ".agents" / "rules" / gemini_sesion.SESION).exists())


class LeaderDraftFrontBackTests(GeminiFlowBase):
    def test_feature_nueva_en_raiz_front_carga_tambien_backend_hermano(self):
        """En raiz Angular con backend Go en grafos.json, una feature nueva (todo,
        spec draft sin microservicios ni worktree) recibe front Y backend."""
        self.backlog({"id": 1, "name": "cobro", "status": "todo", "microservicios": []})
        r = self.run_script("contexto.py", "brief", "--feature", "1", host="gemini")
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("REGLAS DEL STACK angular-product", r.stdout)
        self.assertIn("REGLAS DEL STACK golang-hexagonal", r.stdout)
        self.assertIn("SKILLS DEL STACK golang-hexagonal", r.stdout)

    def test_feature_in_progress_sin_microservicios_solo_carga_front(self):
        self.backlog({"id": 1, "name": "cobro", "status": "in_progress", "microservicios": []})
        r = self.run_script("contexto.py", "brief", "--feature", "1", host="gemini")
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("REGLAS DEL STACK angular-product", r.stdout)
        self.assertNotIn("REGLAS DEL STACK golang-hexagonal", r.stdout)


class ModelosYContext7GeminiTests(GeminiFlowBase):
    def test_modelo_py_gemini_asigna_carbon_argon_hydrogen(self):
        r_all = self.run_script("modelo.py", "gemini", "--todos")
        self.assertEqual(0, r_all.returncode, r_all.stdout + r_all.stderr)
        self.assertIn("Gemini 4 Carbon (High)", r_all.stdout)
        self.assertIn("Gemini 4 Argon (High)", r_all.stdout)
        self.assertIn("Gemini 4 Hydrogen", r_all.stdout)

        for rol, esperado in (
            ("producto", "gemini-4-carbon"),
            ("leader", "gemini-4-carbon"),
            ("implementer", "gemini-4-argon"),
            ("revisor", "gemini-4-argon"),
            ("cierre", "gemini-4-hydrogen"),
            ("estado", "gemini-4-hydrogen"),
        ):
            r = self.run_script("modelo.py", "gemini", "--rol", rol)
            self.assertEqual(0, r.returncode, r.stdout + r.stderr)
            self.assertIn(esperado, r.stdout, rol)

    def test_roles_emiten_modelo_gemini_4_context7_agy_y_ask_question_solo_en_gemini(self):
        # Rol 0 Producto -> Carbon High
        r_prd = self.run_script("producto.py", "borrador", "--doc", "prd", host="gemini")
        self.assertIn("Gemini 4 Carbon (High)", r_prd.stdout)

        # Rol 1 Leader (spec sin sello) -> Carbon High + Context7 AGY lazy + ask_question
        self.backlog({"id": 1, "name": "cobro", "status": "todo", "modo": "pair", "microservicios": ["ms-pagos"]})
        r_lead = self.run_script("contexto.py", "brief", "--feature", "1", host="gemini")
        self.assertIn("modelo Gemini 4 (leader): Gemini 4 Carbon (High)", r_lead.stdout)
        self.assertIn("call_mcp_tool", r_lead.stdout)
        self.assertIn("ask_question", r_lead.stdout)

        # Rol 2 Implementer (spec sellado) -> Argon High
        self.backlog({
            "id": 1, "name": "cobro", "status": "in_progress", "modo": "pair",
            "last_spec_sig": "abc123", "microservicios": ["ms-pagos"], "worktree": str(self.wt),
        })
        r_impl = self.run_script("contexto.py", "brief", "--feature", "1", host="gemini")
        self.assertIn("modelo Gemini 4 (implementer): Gemini 4 Argon (High)", r_impl.stdout)

        # Rol 3 Revisor -> Argon High + Context7 AGY + reglas front/back
        r_rev = self.run_script("revision.py", "--feature", "1", "--briefing", host="gemini")
        self.assertIn("modelo Gemini 4 (revisor): Gemini 4 Argon (High)", r_rev.stdout)
        self.assertIn("call_mcp_tool", r_rev.stdout)
        self.assertIn("REGLAS DEL STACK golang-hexagonal", r_rev.stdout)

        # Estado -> Hydrogen
        r_est = self.run_script("estado.py", host="gemini")
        self.assertIn("modelo Gemini 4 (estado): Gemini 4 Hydrogen", r_est.stdout)

        # En Claude NO se filtran avisos Gemini
        r_claude = self.run_script("contexto.py", "brief", "--feature", "1", host="claude")
        self.assertNotIn("modelo Gemini 4", r_claude.stdout)
        self.assertNotIn("call_mcp_tool", r_claude.stdout)


class GeminiMdYDocumentacionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()

    def tearDown(self):
        stack._planes.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_normalizar_genera_gemini_md_y_no_pisa_uno_del_usuario(self):
        repo = self.tmp / "ms-pagos"
        escribir(repo / "go.mod", "module example.com/ms-pagos\n")
        res = stack.normalizar_repositorio(repo, "golang-hexagonal", rules={})
        gemini_md = repo / "GEMINI.md"
        self.assertTrue(gemini_md.is_file())
        contenido = gemini_md.read_text(encoding="utf-8")
        self.assertIn("@./AGENTS.md", contenido)
        self.assertIn("Gemini 4 Carbon (High)", contenido)
        self.assertIn("Gemini 4 Argon (High)", contenido)
        self.assertIn("Gemini 4 Hydrogen", contenido)
        self.assertTrue(any("GEMINI.md" in a for a in res["actions"]))

        # Un GEMINI.md del usuario se respeta
        propio = "# GEMINI.md propio del equipo\n\nNo tocar.\n"
        gemini_md.write_text(propio, encoding="utf-8")
        stack._planes.clear()
        res2 = stack.normalizar_repositorio(repo, "golang-hexagonal", rules={})
        self.assertEqual(propio, gemini_md.read_text(encoding="utf-8"))
        self.assertTrue(any("GEMINI.md" in w for w in res2["warnings"]), res2["warnings"])

    def test_referencia_gemini_md_cubre_agy_y_gemini_cli(self):
        doc = (RAIZ / "references" / "gemini.md").read_text(encoding="utf-8")
        for marca in ("Antigravity (AGY)", "Gemini CLI", "Gemini 4 Carbon (High)",
                      "Gemini 4 Argon (High)", "Gemini 4 Hydrogen", "call_mcp_tool",
                      "ask_question", "GEMINI.md", "swarm", "gemini_sesion.py"):
            with self.subTest(marca=marca):
                self.assertIn(marca, doc)


if __name__ == "__main__":
    unittest.main()
