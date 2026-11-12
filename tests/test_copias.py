"""La normativa del stack llega a TODO el codigo del proyecto y no se queda vieja.

Lo que se midio en dos proyectos reales antes de este cambio:

1. `architecture.md` apuntaba a `src/app/features/**` y el codigo vivia en
   `projects/*/src/app/`: la regla no nombraba ni un archivo del repo. La
   plantilla ya estaba corregida, pero `normalizar` solo agregaba lo que
   faltaba y la copia instalada no se actualizaba nunca.
2. `stack.py verificar` decia "Arquitectura: OK" en repos con todo su codigo
   fuera del layout del stack: el verificador avisaba que no habia medido y el
   aviso se perdia.
3. La raiz del proyecto no se normalizaba si no estaba declarada en
   harness/grafos.json o si una subcarpeta traia un `package.json`.
4. Un worktree de un repo que no versiona `.claude/` nacia sin rules ni skills.

La regla que guia todo: el arnes mira primero donde vive el codigo, y lo vuelve
a mirar en cada normalizacion.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import arquitectura  # noqa: E402
import comun  # noqa: E402
import contexto  # noqa: E402
import copias  # noqa: E402
import stack  # noqa: E402

GO = "golang-hexagonal"
NG = "angular-product"
PY = sys.executable


def sh(*args, cwd: Path) -> str:
    r = subprocess.run(list(args), cwd=str(cwd), capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(f"{' '.join(args)}\n{r.stdout}{r.stderr}")
    return r.stdout


def escribir(ruta: Path, texto: str = "package x\n") -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


def git_init(repo: Path) -> None:
    sh("git", "init", "-q", "-b", "develop", cwd=repo)
    sh("git", "config", "user.email", "t@example.com", cwd=repo)
    sh("git", "config", "user.name", "t", cwd=repo)


def commit(repo: Path, mensaje: str = "c") -> None:
    sh("git", "add", "-A", cwd=repo)
    sh("git", "commit", "-q", "-m", mensaje, cwd=repo)


def globs_de(ruta: Path) -> list[str]:
    return copias.leer_globs(ruta.read_text(encoding="utf-8"))


def sin_cubrir(ruta_regla: Path, archivos: list[str]) -> list[str]:
    patrones = [copias.regex_glob(g) for g in globs_de(ruta_regla)]
    return [a for a in archivos if not any(p.match(a) for p in patrones)]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        stack._planes.clear()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        stack._planes.clear()

    def repo_go(self, nombre: str = "ms-pagos", canonico: bool = True) -> Path:
        repo = self.tmp / nombre
        escribir(repo / "go.mod", f"module example.com/{nombre}\n\ngo 1.24\n")
        escribir(repo / "cmd" / "server" / "main.go", "package main\n\nfunc main() {}\n")
        if canonico:
            escribir(repo / "internal" / "pagos" / "domain" / "pago.go", "package domain\n")
        else:
            escribir(repo / "handlers" / "pagos.go", "package handlers\n")
        return repo

    def repo_angular(self, nombre: str = "front") -> Path:
        repo = self.tmp / nombre
        escribir(repo / "angular.json", "{}")
        escribir(repo / "package.json", json.dumps(
            {"dependencies": {"@angular/core": "22", "@angular/common": "22"}}))
        return repo


# --- 1. el alcance de una regla sale de donde vive el codigo ----------------

class AlcanceDeLasReglasTests(Base):
    def test_un_repo_con_el_layout_canonico_recibe_la_plantilla_tal_cual(self):
        repo = self.repo_go()
        stack.normalizar_repositorio(repo, GO, rules={})
        plantilla = stack.STACKS_DIR / GO / "rules" / "architecture.md"
        self.assertEqual(plantilla.read_bytes(), (repo / ".claude/rules/architecture.md").read_bytes())

    def test_el_codigo_fuera_del_layout_queda_dentro_del_alcance_de_la_regla(self):
        repo = self.repo_go(canonico=False)
        res = stack.normalizar_repositorio(repo, GO, rules={})
        for carpeta in (".claude", ".agents", ".gemini"):
            for regla in ("architecture.md", "security.md"):
                self.assertEqual([], sin_cubrir(repo / carpeta / "rules" / regla,
                                                ["handlers/pagos.go", "cmd/server/main.go"]),
                                 f"{carpeta}/rules/{regla}")
        self.assertTrue(any("handlers/pagos.go" in a for a in res["alcance"]), res["alcance"])

    def test_la_regla_conserva_los_globs_de_la_plantilla(self):
        repo = self.repo_go(canonico=False)
        stack.normalizar_repositorio(repo, GO, rules={})
        plantilla = copias.leer_globs((stack.STACKS_DIR / GO / "rules" / "security.md")
                                      .read_text(encoding="utf-8"))
        instalados = globs_de(repo / ".claude/rules/security.md")
        self.assertEqual(plantilla, instalados[:len(plantilla)])

    def test_angular_con_el_codigo_en_projects_queda_cubierto(self):
        """El caso real: la regla apuntaba a src/app/features y el codigo vivia en projects/."""
        repo = self.repo_angular()
        codigo = ["projects/admin/src/app/shared/tabla.ts", "projects/portal/src/app/layout/menu.ts",
                  "projects/ui/src/lib/boton.ts"]
        for ruta in codigo:
            escribir(repo / ruta, "export const x = 1;\n")
        stack.normalizar_repositorio(repo, NG, rules={})
        self.assertEqual([], sin_cubrir(repo / ".claude/rules/architecture.md", codigo))

    def test_si_el_codigo_se_muda_la_regla_lo_sigue(self):
        """Lo que pidio el usuario: manana el codigo vive en otra carpeta y la regla no se queda atras."""
        repo = self.repo_go()
        stack.normalizar_repositorio(repo, GO, rules={})
        self.assertEqual(["handlers/nuevo.go"],
                         sin_cubrir(repo / ".claude/rules/architecture.md", ["handlers/nuevo.go"]))

        escribir(repo / "handlers" / "nuevo.go", "package handlers\n")
        stack._planes.clear()
        diag = stack.verificar_cumplimiento(repo, GO, rules={})
        self.assertIn(".claude/rules/architecture.md", diag["copias_viejas"])
        self.assertFalse(diag["compliant"])

        res = stack.normalizar_repositorio(repo, GO, rules={})
        self.assertTrue(any(a.startswith("Actualizada regla: .claude/rules/architecture.md")
                            for a in res["actions"]), res["actions"])
        self.assertEqual([], sin_cubrir(repo / ".claude/rules/architecture.md", ["handlers/nuevo.go"]))
        self.assertEqual([], stack.verificar_cumplimiento(repo, GO, rules={})["copias_viejas"])

    def test_lo_de_terceros_y_las_copias_de_skills_no_cuentan_como_codigo(self):
        rutas = ["src/a.py", "node_modules/x/b.py", ".claude/skills/s/scripts/c.py",
                 "vendor/d.py", "scripts/check-architecture.py"]
        self.assertEqual(["src/a.py"],
                         copias.codigo_del_repo(rutas, ["py"], {"scripts/check-architecture.py"}))

    def test_normalizar_dos_veces_no_cambia_nada(self):
        repo = self.repo_go(canonico=False)
        stack.normalizar_repositorio(repo, GO, rules={})
        self.assertEqual([], stack.normalizar_repositorio(repo, GO, rules={})["actions"])


# --- 2. una copia vieja se actualiza; una editada por el proyecto no ---------

class CopiasViejasTests(Base):
    """Con una skill de mentira bajo git: asi la plantilla puede cambiar de version."""

    REGLA = ".claude/rules/testing.md"
    VALIDADOR = "scripts/check-architecture.py"
    SKILL = ".claude/skills/add-feature"

    def setUp(self):
        super().setUp()
        self.skill = self.tmp / "skill"
        shutil.copytree(stack.STACKS_DIR / GO, self.skill / "assets" / "stacks" / GO,
                        ignore=shutil.ignore_patterns("__pycache__"))
        git_init(self.skill)
        commit(self.skill, "v1")
        self.stacks_reales = stack.STACKS_DIR
        stack.STACKS_DIR = self.skill / "assets" / "stacks"
        self.repo = self.repo_go()
        git_init(self.repo)
        commit(self.repo, "base")
        stack.normalizar_repositorio(self.repo, GO, rules={})

    def tearDown(self):
        stack.STACKS_DIR = self.stacks_reales
        super().tearDown()

    def plantilla(self, rel: str) -> Path:
        return stack.STACKS_DIR / GO / rel

    def cambiar_plantilla(self, confirmar: bool = True) -> None:
        for rel in ("rules/testing.md", "scripts/check-architecture.py", "skills/add-feature/SKILL.md"):
            ruta = self.plantilla(rel)
            ruta.write_text(ruta.read_text(encoding="utf-8") + "\n# v2\n", encoding="utf-8")
        if confirmar:
            commit(self.skill, "v2")
        stack._planes.clear()

    def borrar_registro(self) -> None:
        ruta, _ = copias.ruta_registro(self.repo)
        ruta.unlink()

    def test_la_copia_que_nadie_edito_se_actualiza(self):
        self.cambiar_plantilla()
        res = stack.normalizar_repositorio(self.repo, GO, rules={})
        actualizadas = [a for a in res["actions"] if a.startswith("Actualizada")]
        self.assertEqual(6, len(actualizadas), res["actions"])  # 3 reglas, 2 skills, 1 validador
        self.assertEqual(self.plantilla("rules/testing.md").read_bytes(), (self.repo / self.REGLA).read_bytes())
        self.assertEqual(self.plantilla("scripts/check-architecture.py").read_bytes(),
                         (self.repo / self.VALIDADOR).read_bytes())
        self.assertIn("# v2", (self.repo / self.SKILL / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual([], stack.normalizar_repositorio(self.repo, GO, rules={})["actions"])

    def test_sin_registro_el_historial_de_la_plantilla_prueba_que_es_vieja(self):
        """Lo instalado antes de este cambio no tiene registro: se reconoce por el historial git."""
        self.borrar_registro()
        self.cambiar_plantilla()
        res = stack.normalizar_repositorio(self.repo, GO, rules={})
        self.assertEqual(6, len([a for a in res["actions"] if a.startswith("Actualizada")]), res["actions"])
        self.assertTrue(all("version anterior de la plantilla" in a
                            for a in res["actions"] if a.startswith("Actualizada")), res["actions"])

    def test_la_copia_que_el_proyecto_edito_se_conserva_y_se_avisa(self):
        propia = "# regla del proyecto\n"
        (self.repo / self.REGLA).write_text(propia, encoding="utf-8")
        self.cambiar_plantilla()
        res = stack.normalizar_repositorio(self.repo, GO, rules={})
        self.assertEqual(propia, (self.repo / self.REGLA).read_text(encoding="utf-8"))
        self.assertIn(self.REGLA, res["conservadas"])
        self.assertTrue(any("--reemplazar" in a for a in res["warnings"]), res["warnings"])

    def test_reemplazar_cambia_la_copia_editada_por_la_plantilla(self):
        (self.repo / self.REGLA).write_text("# regla del proyecto\n", encoding="utf-8")
        stack._planes.clear()
        res = stack.normalizar_repositorio(self.repo, GO, rules={}, reemplazar=True)
        self.assertEqual(self.plantilla("rules/testing.md").read_bytes(), (self.repo / self.REGLA).read_bytes())
        self.assertTrue(any(a.startswith("Reemplazada") for a in res["actions"]), res["actions"])

    def test_una_skill_editada_por_el_proyecto_no_se_borra(self):
        nota = self.repo / self.SKILL / "NOTAS-DEL-PROYECTO.md"
        nota.write_text("propio\n", encoding="utf-8")
        self.cambiar_plantilla()
        res = stack.normalizar_repositorio(self.repo, GO, rules={})
        self.assertTrue(nota.is_file())
        self.assertIn(self.SKILL, res["conservadas"])

    def test_sin_registro_ni_historial_la_copia_no_se_toca(self):
        """Sin ninguna prueba de que nadie la edito, gana la prudencia."""
        self.borrar_registro()
        self.cambiar_plantilla(confirmar=False)
        shutil.rmtree(self.skill / ".git")
        copias._cache_raiz.clear()
        antes = (self.repo / self.VALIDADOR).read_bytes()
        res = stack.normalizar_repositorio(self.repo, GO, rules={})
        self.assertEqual(antes, (self.repo / self.VALIDADOR).read_bytes())
        self.assertIn(self.VALIDADOR, res["conservadas"])
        self.assertTrue(any("no es un clon git" in a for a in res["warnings"]), res["warnings"])

    def test_verificar_reporta_la_copia_vieja_como_hallazgo(self):
        self.assertTrue(stack.verificar_cumplimiento(self.repo, GO, rules={})["compliant"])
        self.cambiar_plantilla()
        diag = stack.verificar_cumplimiento(self.repo, GO, rules={})
        self.assertFalse(diag["compliant"])
        self.assertIn(self.REGLA, diag["copias_viejas"])
        self.assertTrue(any(f.startswith("Copias desactualizadas") for f in diag["findings"]))

    def test_el_registro_vive_en_el_git_dir_y_no_ensucia_el_repo(self):
        ruta, _ = copias.ruta_registro(self.repo)
        self.assertTrue(ruta.is_file())
        self.assertIn(".git", ruta.parts)
        self.assertNotIn("harness-flow-copias", sh("git", "status", "--porcelain", cwd=self.repo))

    def test_el_arranque_de_sesion_no_reescribe_una_copia_que_el_repo_versiona(self):
        """`close` no integra sobre un arbol con cambios: reescribirla lo dejaria bloqueado."""
        commit(self.repo, "normativa del stack")
        self.cambiar_plantilla()
        res = stack.normalizar_repositorio(self.repo, GO, rules={}, conservar_versionadas=True)
        self.assertEqual("", sh("git", "status", "--porcelain", cwd=self.repo))
        self.assertEqual([], res["actions"])
        self.assertIn(self.REGLA, res["pendientes"])
        # Quien corre `normalizar` a proposito si las actualiza, y las commitea.
        stack._planes.clear()
        res = stack.normalizar_repositorio(self.repo, GO, rules={})
        self.assertEqual(6, len(res["actions"]), res["actions"])
        self.assertNotEqual("", sh("git", "status", "--porcelain", cwd=self.repo))

    def test_el_arranque_de_sesion_si_actualiza_lo_que_el_repo_no_versiona(self):
        self.cambiar_plantilla()
        res = stack.normalizar_repositorio(self.repo, GO, rules={}, conservar_versionadas=True)
        self.assertEqual(6, len(res["actions"]), res["actions"])
        self.assertEqual([], res["pendientes"])

    def test_el_arranque_de_sesion_dice_que_repos_quedaron_con_copias_viejas(self):
        escribir(self.repo / "harness" / "feature_list.json",
                 json.dumps({"project": "p", "rules": {}, "features": []}))
        commit(self.repo, "normativa del stack")
        self.cambiar_plantilla()
        res = stack.auto_normalizar_y_asegurar_cumplimiento(self.repo)
        self.assertEqual([str(self.repo)], res["copias_pendientes"])
        self.assertTrue(any("copias viejas" in a and self.repo.name in a for a in res["nivel_1_acciones"]),
                        res["nivel_1_acciones"])
        self.assertEqual("", sh("git", "status", "--porcelain", cwd=self.repo))

    def test_el_brief_entrega_la_plantilla_vigente_si_la_copia_quedo_vieja(self):
        self.cambiar_plantilla()
        cuerpo, origen = contexto._texto_regla([self.repo], GO, "testing.md")
        self.assertIn("# v2", cuerpo)
        self.assertIn("desactualizada", origen)

    def test_el_brief_entrega_la_copia_que_el_proyecto_edito(self):
        (self.repo / self.REGLA).write_text("---\nglobs: []\n---\n# regla del proyecto\n", encoding="utf-8")
        stack._planes.clear()
        cuerpo, origen = contexto._texto_regla([self.repo], GO, "testing.md")
        self.assertEqual("# regla del proyecto", cuerpo)
        self.assertIn(self.repo.name, origen)

    def test_stack_skill_lee_la_plantilla_si_la_copia_quedo_vieja(self):
        self.cambiar_plantilla()
        ruta, origen = stack.ruta_skill("add-feature", GO, self.repo)
        self.assertEqual(self.plantilla("skills/add-feature/SKILL.md"), ruta)
        self.assertIn("plantilla", origen)

    def test_stack_skill_lee_la_copia_del_repo_si_esta_al_dia(self):
        ruta, origen = stack.ruta_skill("add-feature", GO, self.repo)
        self.assertEqual(self.repo / self.SKILL / "SKILL.md", ruta)
        self.assertIn("copia del repo", origen)


# --- 3. que repos son del proyecto ------------------------------------------

class ReposDelProyectoTests(Base):
    def destinos(self, raiz: Path) -> dict[str, str]:
        return {Path(d["path"]).relative_to(self.tmp).as_posix(): d["stack"]
                for d in stack.detectar_todos_los_destinos(raiz)}

    def test_una_subcarpeta_con_package_json_no_saca_a_la_raiz(self):
        raiz = self.repo_angular()
        escribir(raiz / "e2e" / "package.json", "{}")
        self.assertEqual({"front": NG}, {k: v for k, v in self.destinos(raiz).items() if v != "generico"})

    def test_la_raiz_entra_aunque_grafos_json_solo_declare_los_microservicios(self):
        raiz = self.repo_angular()
        micro = self.repo_go("ms-pagos")
        escribir(raiz / "harness" / "grafos.json",
                 json.dumps({"raices": [{"nombre": "ms", "path": str(micro)}]}))
        self.assertEqual({"front": NG, "ms-pagos": GO}, self.destinos(raiz))

    def test_un_back_dentro_del_front_se_normaliza_tambien(self):
        raiz = self.repo_angular()
        escribir(raiz / "api" / "go.mod", "module example.com/api\n")
        escribir(raiz / "api" / "cmd" / "server" / "main.go", "package main\n")
        self.assertEqual({"front": NG, "front/api": GO}, self.destinos(raiz))

    def test_un_front_dentro_del_back_se_normaliza_tambien(self):
        raiz = self.repo_go("servicio")
        escribir(raiz / "web" / "angular.json", "{}")
        escribir(raiz / "web" / "package.json", json.dumps({"dependencies": {"@angular/core": "22"}}))
        self.assertEqual({"servicio": GO, "servicio/web": NG}, self.destinos(raiz))

    def test_un_modulo_del_mismo_stack_no_es_otro_repo(self):
        raiz = self.repo_go("servicio")
        escribir(raiz / "tools" / "go.mod", "module example.com/tools\n")
        escribir(raiz / "tools" / "gen.go", "package main\n")
        self.assertEqual({"servicio": GO}, self.destinos(raiz))

    def test_un_monorepo_con_apps_a_dos_niveles_se_ve(self):
        raiz = self.tmp / "mono"
        escribir(raiz / "package.json", "{}")
        escribir(raiz / "apps" / "api" / "go.mod", "module example.com/api\n")
        escribir(raiz / "apps" / "api" / "main.go", "package main\n")
        escribir(raiz / "apps" / "web" / "angular.json", "{}")
        escribir(raiz / "apps" / "web" / "package.json",
                 json.dumps({"dependencies": {"@angular/core": "22"}}))
        normativos = {k: v for k, v in self.destinos(raiz).items() if v != "generico"}
        self.assertEqual({"mono/apps/api": GO, "mono/apps/web": NG}, normativos)

    def test_un_clon_ajeno_dentro_de_la_raiz_se_dice_y_no_se_escribe_en_el(self):
        """Otro repo dentro de la raiz no se normaliza solo: es decision del usuario declararlo."""
        raiz = self.repo_angular()
        escribir(raiz / "harness" / "feature_list.json",
                 json.dumps({"project": "p", "rules": {}, "features": []}))
        clon = raiz / "ms-otro"
        escribir(clon / "go.mod", "module example.com/otro\n")
        escribir(clon / "cmd" / "server" / "main.go", "package main\n")
        git_init(clon)
        self.assertNotIn("front/ms-otro", self.destinos(raiz))
        self.assertEqual([str(clon)], [d["path"] for d in stack.repos_sin_declarar(raiz)])

        res = stack.auto_normalizar_y_asegurar_cumplimiento(raiz)
        self.assertFalse((clon / ".claude").exists())
        self.assertFalse((clon / "AGENTS.md").exists())
        self.assertTrue(any("ms-otro" in a and "grafos.json" in a for a in res["nivel_1_acciones"]),
                        res["nivel_1_acciones"])

    def test_un_clon_declarado_si_se_normaliza(self):
        raiz = self.repo_angular()
        clon = raiz / "ms-otro"
        escribir(clon / "go.mod", "module example.com/otro\n")
        git_init(clon)
        escribir(raiz / "harness" / "grafos.json",
                 json.dumps({"raices": [{"nombre": "front", "path": "."},
                                        {"nombre": "ms-otro", "path": "ms-otro"}]}))
        self.assertEqual(GO, self.destinos(raiz)["front/ms-otro"])
        self.assertEqual([], stack.repos_sin_declarar(raiz))

    def test_un_proyecto_gradle_sin_manifiesto_android_no_es_android(self):
        repo = self.tmp / "ktor"
        escribir(repo / "build.gradle.kts", 'plugins { kotlin("jvm") }\n')
        escribir(repo / "settings.gradle.kts", "")
        escribir(repo / "src" / "main" / "kotlin" / "App.kt", "fun main() {}\n")
        self.assertNotEqual("android-compose-clean", stack.detectar_stack_directorio(repo)["stack"])

    def test_un_proyecto_con_manifiesto_android_si_lo_es(self):
        repo = self.tmp / "app-movil"
        escribir(repo / "settings.gradle.kts", "")
        escribir(repo / "app" / "build.gradle.kts", 'plugins { id("com.android.application") }\n')
        escribir(repo / "app" / "src" / "main" / "AndroidManifest.xml", "<manifest/>\n")
        escribir(repo / "app" / "src" / "main" / "java" / "A.kt", "class A\n")
        self.assertEqual("android-compose-clean", stack.detectar_stack_directorio(repo)["stack"])


# --- 4. un OK no tapa lo que no se midio ------------------------------------

class VerificarNoDaVerdeSinMedirTests(Base):
    def verificar_cli(self, repo: Path) -> str:
        r = subprocess.run([PY, str(RAIZ / "scripts" / "stack.py"), "verificar", "--repo", str(repo),
                            "--stack", GO], capture_output=True, text=True, cwd=str(repo))
        return r.stdout + r.stderr

    def test_un_servicio_con_todo_el_codigo_fuera_del_layout_no_sale_conforme(self):
        repo = self.repo_go(canonico=False)
        stack.normalizar_repositorio(repo, GO, rules={})
        diag = stack.verificar_cumplimiento(repo, GO, rules={})
        self.assertTrue(diag["architecture_ok"])  # el verificador no encontro violaciones...
        self.assertEqual(1, diag["heredado"]["archivos"])  # ...pero hay codigo fuera de la norma
        self.assertTrue(any("NO se midieron" in a for a in diag["architecture_warnings"]),
                        diag["architecture_warnings"])
        salida = self.verificar_cli(repo)
        self.assertNotIn("✅ COMPLIANT", salida)
        self.assertNotIn("Arquitectura:        OK", salida)
        self.assertIn("ARQUITECTURA CON PENDIENTES", salida)
        self.assertIn("1 archivos en 1 carpetas viven fuera de la norma", salida)

    def test_un_servicio_dentro_de_la_norma_si_sale_conforme(self):
        repo = self.repo_go()
        stack.normalizar_repositorio(repo, GO, rules={})
        diag = stack.verificar_cumplimiento(repo, GO, rules={})
        self.assertEqual(0, diag["heredado"]["archivos"])
        self.assertIn("✅ COMPLIANT", self.verificar_cli(repo))

    def test_el_arranque_de_sesion_cuenta_lo_heredado_cuando_no_hay_trinquete(self):
        repo = self.repo_go(canonico=False)
        escribir(repo / "harness" / "feature_list.json",
                 json.dumps({"project": "p", "rules": {}, "features": []}))
        p = comun.paths(repo)
        linea = arquitectura.resumen(p, comun.load_backlog(p))
        self.assertIn("1 archivos en 1 carpetas viven fuera de la norma", linea)
        self.assertIn("trinquete sin adoptar", linea)

    def test_el_inventario_dice_el_codigo_que_el_layout_no_mira(self):
        repo = self.repo_angular()
        escribir(repo / "projects" / "ui" / "src" / "lib" / "boton.ts", "export const x = 1;\n")
        escribir(repo / "src" / "app" / "core" / "auth.ts", "export const y = 1;\n")
        layout = arquitectura.layout_de(NG)
        self.assertEqual({"projects/ui": 1}, arquitectura.sin_medir_por_carpeta(repo, NG, layout))
        self.assertEqual(1, stack.codigo_fuera_de_la_norma(repo, NG)["sin_medir"])


# --- 5. el worktree de un repo que no versiona la normativa -----------------

class NormativaEnWorktreesTests(Base):
    def repo_con_worktree(self, ignorar: bool) -> tuple[Path, Path]:
        repo = self.repo_go()
        if ignorar:
            escribir(repo / ".gitignore", ".claude/\n.agents/\n.gemini/\nAGENTS.md\nscripts/\n")
        git_init(repo)
        commit(repo, "base")
        stack.normalizar_repositorio(repo, GO, rules={})
        if not ignorar:
            commit(repo, "normativa del stack")
        arbol = self.tmp / "wt" / "1-feature"
        sh("git", "worktree", "add", "-q", "-b", "feature/1", str(arbol), "develop", cwd=repo)
        return repo, arbol.resolve()

    def test_el_worktree_recibe_las_rules_y_skills_que_el_repo_ignora(self):
        repo, arbol = self.repo_con_worktree(ignorar=True)
        self.assertFalse((arbol / ".claude").exists())
        enlazadas = comun.enlazar_normativa(repo, arbol)
        self.assertEqual(list(comun.CARPETAS_NORMATIVA), enlazadas)
        self.assertTrue((arbol / ".claude/rules/architecture.md").is_file())
        self.assertTrue((arbol / ".agents/skills/add-feature/SKILL.md").is_file())
        self.assertEqual("", sh("git", "status", "--porcelain", cwd=arbol))

    def test_no_enlaza_dos_veces(self):
        repo, arbol = self.repo_con_worktree(ignorar=True)
        comun.enlazar_normativa(repo, arbol)
        self.assertEqual([], comun.enlazar_normativa(repo, arbol))

    def test_un_repo_que_versiona_la_normativa_no_se_toca(self):
        repo, arbol = self.repo_con_worktree(ignorar=False)
        self.assertTrue((arbol / ".claude/rules/architecture.md").is_file())  # la trae la rama
        self.assertEqual([], comun.enlazar_normativa(repo, arbol))
        self.assertFalse((arbol / ".claude/rules").is_symlink())

    def test_el_arranque_de_sesion_encuentra_los_worktrees_en_curso(self):
        repo, arbol = self.repo_con_worktree(ignorar=True)
        data = {"features": [
            {"id": 1, "status": "in_progress", "worktree": str(arbol)},
            {"id": 2, "status": "done", "worktree": str(arbol)},
            {"id": 3, "status": "review",
             "multi_repo": {"repos": [{"repo": str(repo), "worktree": str(arbol)}]}},
        ]}
        self.assertEqual([(repo, arbol)], comun.worktrees_abiertos(data))

    def test_worktree_start_deja_la_normativa_en_el_worktree(self):
        repo = self.repo_go("proyecto")
        escribir(repo / ".gitignore", ".claude/\n.agents/\n.gemini/\nAGENTS.md\nscripts/\n")
        escribir(repo / "harness" / "feature_list.json", json.dumps({
            "project": "p", "rules": {"rama_base": "develop"},
            "features": [{"id": 1, "name": "cobro", "status": "todo", "kind": "task"}]}))
        escribir(repo / "docs" / ".gitkeep", "")
        git_init(repo)
        commit(repo, "base")
        stack.normalizar_repositorio(repo, GO, rules={})
        r = subprocess.run([PY, str(RAIZ / "scripts" / "worktree.py"), "start", "--feature", "1",
                            "--delegado"], cwd=str(repo), capture_output=True, text=True)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        arbol = self.tmp / "proyecto-wt" / "1-cobro"
        self.assertTrue((arbol / ".claude/rules/architecture.md").is_file(), r.stdout + r.stderr)
        self.assertIn(".claude/rules", r.stdout)


if __name__ == "__main__":
    unittest.main()
