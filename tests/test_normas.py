"""Las normas de ingenieria: una sola lista para quien escribe y para quien revisa.

Lo que se midio antes de este cambio:

1. El briefing del revisor mandaba marcar como bloqueante o mayor las
   violaciones de DDIA, Ousterhout, Fowler, CLRS, Chip Huyen y Sam Newman. El
   implementer en modo pair -el modo por defecto- no recibia ninguna: estaban
   solo en `agents/implementer.md`, que es el prompt del modo delegado en
   algunos hosts.
2. OWASP, la construccion defensiva (McConnell) y STE100 se auditaban solo donde
   el revisor carga `agents/revisor.md`. Un host que recibe solo el briefing no
   las veia.
3. El revisor marcaba como mayor un endpoint sin test de rechazo, y a nadie se
   le pedia el AC negativo.
4. Context7: cuatro stacks no declaraban documentacion ni escaner, y
   `stack.py auditar` salia con exit 0 con el escaner ausente o con hallazgos.

Todo se comprueba sobre la salida de los scripts, que es lo unico que reciben
igual Claude Code, Hermes, Codex, Grok, AGY y Kimi.
"""
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"
sys.path.insert(0, str(SCRIPTS))

import comun  # noqa: E402
import contexto  # noqa: E402
import normas  # noqa: E402
import producto  # noqa: E402
import stack  # noqa: E402

SPEC = ("# Spec - Feature #1: cobro\n\nEstado: draft\n\n"
        "## Criterios de aceptacion\n\n"
        "- AC-1 [costura: endpoint]: dado un carro, cuando pago, entonces cobra. `verificar: true`\n\n"
        "## Fuera de alcance\n\nFacturas.\n")
REGLAS = {"rama_base": "main", "require_docs_al_dia": False}
GRAVES = {normas.BLOQUEANTE, normas.MAYOR}


def escribir(ruta: Path, texto: str = "") -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


def harness(script, *args, cwd):
    env = dict(os.environ, HARNESS_SIN_CONTEXTO="1", HARNESS_SIN_HUB="1", HARNESS_SIN_CBM="1")
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          cwd=str(cwd), capture_output=True, text=True, env=env)


class RegistroTests(unittest.TestCase):
    def test_nada_que_el_revisor_bloquea_queda_sin_decir_a_quien_escribe(self):
        """El invariante: una norma con hallazgo bloqueante o mayor le dice que hacer al implementer."""
        for n in normas.NORMAS:
            if any(sev in GRAVES for sev, _ in n["audita"]):
                with self.subTest(norma=n["id"]):
                    self.assertTrue(n.get("construye"), "el revisor bloquea por algo que no se le dijo a nadie")

    def test_el_cuadro_norma_por_rol_no_tiene_ninguna_celda_vacia(self):
        """El cuadro que se le mostro al usuario, como invariante: todo en Si."""
        filas = normas.cuadro()
        self.assertEqual(12, len(filas))
        for titulo, celdas in filas:
            for rol in normas.ROLES:
                with self.subTest(norma=titulo, rol=rol):
                    self.assertTrue(celdas[rol])

    def test_el_cuadro_se_puede_pedir_y_sale_con_cero_si_esta_completo(self):
        r = harness("normas.py", "--cuadro", cwd=RAIZ)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertNotIn("NO", r.stdout)
        self.assertEqual(12 * 5, r.stdout.count("| Sí"))

    def test_una_celda_vacia_haria_fallar_el_cuadro(self):
        """El verde no es evidencia: el cuadro tiene que poder decir NO."""
        original = normas.NORMAS[0]["spec"]
        normas.NORMAS[0]["spec"] = []
        try:
            self.assertFalse(normas.cuadro()[0][1]["leader"])
            self.assertIn("| NO |", normas.lineas_cuadro()[2])
        finally:
            normas.NORMAS[0]["spec"] = original

    def test_cada_norma_dice_que_audita_el_revisor(self):
        for n in normas.NORMAS:
            with self.subTest(norma=n["id"]):
                self.assertTrue(n["audita"])
                for sev, texto in n["audita"]:
                    self.assertIn(sev, (normas.BLOQUEANTE, normas.MAYOR, normas.MENOR))
                    self.assertTrue(texto.strip())

    def test_los_ids_no_se_repiten(self):
        ids = [n["id"] for n in normas.NORMAS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_cada_referencia_citada_existe(self):
        for n in normas.NORMAS:
            for ref in [n["ref"], *n.get("ref_extra", [])]:
                with self.subTest(norma=n["id"], ref=ref):
                    self.assertTrue((normas.REFERENCIAS / ref).is_file())

    def test_estan_los_libros_que_el_readme_promete(self):
        titulos = " ".join(n["titulo"] for n in normas.NORMAS)
        for libro in ("DDIA", "Ousterhout", "Fowler", "GoF", "CLRS", "Chip Huyen", "Sam Newman",
                      "McConnell", "OWASP", "Context7", "STE100", "Orosz"):
            with self.subTest(libro=libro):
                self.assertIn(libro, titulos)

    def test_design_patterns_gof_es_una_norma_propia_y_no_una_referencia_huerfana(self):
        patrones = next(n for n in normas.NORMAS if n["id"] == "patrones")
        self.assertEqual("design-patterns-gof.md", patrones["ref"])
        self.assertTrue(patrones["producto"]["sdd"] and patrones["spec"] and patrones["construye"]
                        and patrones["audita"])

    def test_los_dos_bloques_salen_del_mismo_registro(self):
        construir = "\n".join(normas.lineas_para_construir(con_spec=True))
        revisar = "\n".join(normas.lineas_para_revisar())
        for n in normas.NORMAS:
            with self.subTest(norma=n["id"]):
                self.assertIn(f"[{n['id']}]", construir)
                self.assertIn(f"[{n['id']}]", revisar)

    def test_el_rol_producto_recibe_lo_de_cada_documento(self):
        sdd = "\n".join(normas.lineas_para_producto("sdd"))
        prd = "\n".join(normas.lineas_para_producto("prd"))
        for n in normas.NORMAS:
            with self.subTest(norma=n["id"]):
                self.assertTrue(f"[{n['id']}]" in sdd or f"[{n['id']}]" in prd)
        self.assertIn("casos de abuso", prd)
        self.assertIn("fronteras de confianza", sdd)

    def test_lo_del_spec_solo_se_pide_mientras_el_spec_no_esta_sellado(self):
        self.assertIn("  en el spec: ", "\n".join(normas.lineas_para_construir(con_spec=True)))
        self.assertNotIn("  en el spec: ", "\n".join(normas.lineas_para_construir(con_spec=False)))


class Proyecto(unittest.TestCase):
    """Un repo git con un servicio Go: el caso minimo con stack normativo."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = self.tmp / "ms-pagos"
        escribir(self.root / "go.mod", "module example.com/ms-pagos\n")
        escribir(self.root / "docs" / "spec-feature-1-cobro.md", SPEC)
        self.backlog({"id": 1, "name": "cobro", "status": "todo"})
        self.p = comun.paths(self.root)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def backlog(self, feature: dict) -> None:
        escribir(self.root / "harness" / "feature_list.json",
                 json.dumps({"project": "demo", "rules": REGLAS, "features": [feature]}))

    def brief(self, *extra) -> str:
        r = harness("contexto.py", "brief", "--feature", "1", *extra, cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        return r.stdout

    def briefing(self) -> str:
        r = harness("revision.py", "--feature", "1", "--briefing", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        return r.stdout


class BriefTests(Proyecto):
    def test_el_brief_trae_cada_norma_que_el_revisor_audita(self):
        out = self.brief()
        self.assertIn("NORMAS DE INGENIERIA", out)
        for n in normas.NORMAS:
            with self.subTest(norma=n["id"]):
                self.assertIn(f"[{n['id']}] {n['titulo']}", out)
                self.assertIn(f"  - {n['construye'][0]}", out)

    def test_trae_lo_que_antes_solo_veia_el_revisor(self):
        """DDIA era reviewer-only; OWASP y McConnell ni siquiera llegaban a todos los revisores."""
        out = self.brief()
        for frase in ("Transactional", "parametrizadas", "Ningun error tragado", "Database per Service",
                      "dentro de un bucle", "Structured Output"):
            with self.subTest(frase=frase):
                self.assertIn(frase, out)

    def test_no_depende_del_modo_ni_de_un_prompt_del_host(self):
        """Pair y delegado reciben lo mismo: sale del script, no de agents/implementer.md."""
        for modo in ("pair", "delegado"):
            self.backlog({"id": 1, "name": "cobro", "status": "in_progress", "modo": modo,
                          "last_spec_sig": "x"})
            with self.subTest(modo=modo):
                self.assertIn("[datos] Datos confiables", self.brief())

    def test_tambien_llega_a_un_repo_sin_stack(self):
        (self.root / "go.mod").unlink()
        self.assertIn("NORMAS DE INGENIERIA", self.brief())

    def test_antes_de_sellar_el_spec_el_leader_recibe_lo_de_cada_norma(self):
        out = self.brief()
        for n in normas.NORMAS:
            with self.subTest(norma=n["id"]):
                self.assertIn(f"  en el spec: {n['spec'][0]}", out)

    def test_con_el_spec_sellado_queda_solo_lo_del_implementer(self):
        self.backlog({"id": 1, "name": "cobro", "status": "in_progress", "last_spec_sig": "x"})
        out = self.brief()
        self.assertIn("[seguridad]", out)
        self.assertNotIn("  en el spec: ", out)

    def test_el_recorte_del_brief_no_se_lleva_las_normas(self):
        self.assertIn("[seguridad] Seguridad de aplicaciones", self.brief("--max-lineas", "10"))

    def test_las_referencias_se_pueden_abrir_desde_cualquier_host(self):
        base = re.search(r"detalle en (.+)/<ref>", self.brief()).group(1)
        self.assertTrue((Path(base) / "patrones-datos-ddia.md").is_file())


class PaqueteParaDelegarTests(Proyecto):
    """El brief es el paquete completo de un agente delegado: no hace falta anexarle nada.

    Un agente de otro proyecto delego en ocho subagentes pegandoles el brief y
    tuvo que mandarles un anexo con las skills del stack y las referencias: el
    brief daba rutas de archivo, y un subagente puede no tener permiso para
    abrir un archivo fuera del proyecto. Ahora da un comando que las imprime.
    """

    def correr(self, comando: str) -> subprocess.CompletedProcess:
        return subprocess.run(comando, shell=True, cwd=str(self.root), capture_output=True, text=True)

    def comando(self, brief: str, marca: str) -> str:
        linea = next(ln for ln in brief.splitlines() if marca in ln)
        return linea.split(marca, 1)[1].strip()

    def test_el_comando_del_brief_imprime_la_skill_entera(self):
        cmd = self.comando(self.brief(), "para leer una: ")
        self.assertIn("<nombre>", cmd, "el hueco queda a la vista, sin comillas")
        r = self.correr(cmd.replace("<nombre>", "add-persistence"))
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("name: add-persistence", r.stdout)
        self.assertGreater(len(r.stdout.splitlines()), 20, "el cuerpo, no solo el encabezado")

    def test_el_comando_del_brief_imprime_la_referencia_de_una_norma(self):
        cmd = self.comando(self.brief(), "para leer una referencia sin abrir el archivo: ")
        r = self.correr(cmd.replace("<id>", "comunicacion"))
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("ASD-STE100", r.stdout)

    def test_el_protocolo_de_implementacion_va_en_el_brief_en_cualquier_modo(self):
        for modo in ("pair", "delegado", None):
            f = {"id": 1, "name": "cobro", "status": "in_progress", "last_spec_sig": "x"}
            if modo:
                f["modo"] = modo
            self.backlog(f)
            out = self.brief()
            with self.subTest(modo=modo):
                self.assertIn("protocolo (TDD vertical): un test a la vez", out)
                self.assertIn("5 paradas:", out)
                r = self.correr(self.comando(out, "  detalle: "))
                self.assertEqual(0, r.returncode, r.stdout + r.stderr)
                self.assertIn("Vertical Slice", r.stdout)

    def test_al_delegado_se_le_dice_a_quien_devolver_la_pregunta_y_que_no_falta_nada(self):
        self.backlog({"id": 1, "name": "cobro", "status": "in_progress", "modo": "delegado",
                      "last_spec_sig": "x"})
        out = self.brief()
        self.assertIn("devuelve la pregunta a quien te delego", out)
        self.assertIn("este brief es tu paquete completo", out)

    def test_la_copia_del_repo_gana_y_el_comando_la_pide(self):
        stack.normalizar_repositorio(self.root, "golang-hexagonal", rules={})
        cmd = self.comando(self.brief(), "para leer una: ")
        self.assertIn(f"--repo {self.root}", cmd)
        r = self.correr(cmd.replace("<nombre>", "add-persistence"))
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("copia del repo", r.stdout.splitlines()[0])

    def test_invocado_por_un_enlace_los_comandos_que_imprime_funcionan(self):
        """La skill suele llegar a un host por un enlace (~/.claude/skills -> ~/.hermes/...)."""
        enlace = self.tmp / "enlace-skill"
        enlace.symlink_to(RAIZ, target_is_directory=True)
        env = dict(os.environ, HARNESS_SIN_CONTEXTO="1", HARNESS_SIN_HUB="1", HARNESS_SIN_CBM="1")
        r = subprocess.run([sys.executable, str(enlace / "scripts" / "contexto.py"), "brief", "--feature", "1"],
                           cwd=str(self.root), capture_output=True, text=True, env=env)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        skill = self.correr(self.comando(r.stdout, "para leer una: ").replace("<nombre>", "write-tests"))
        self.assertEqual(0, skill.returncode, skill.stdout + skill.stderr)
        ref = self.correr(self.comando(r.stdout, "para leer una referencia sin abrir el archivo: ")
                          .replace("<id>", "seguridad"))
        self.assertEqual(0, ref.returncode, ref.stdout + ref.stderr)
        base = re.search(r"detalle en (.+)/<ref>", r.stdout).group(1)
        self.assertTrue((Path(base) / "seguridad-owasp-y-zap.md").is_file(), "la ruta impresa existe")


class LeerSkillYReferenciaTests(unittest.TestCase):
    def test_una_skill_que_no_existe_no_devuelve_verde_y_dice_cuales_hay(self):
        r = harness("stack.py", "skill", "no-existe", "--stack", "golang-hexagonal", cwd=RAIZ)
        self.assertEqual(2, r.returncode)
        self.assertIn("add-persistence", r.stderr)

    def test_sin_stack_ni_repo_lo_pide(self):
        r = harness("stack.py", "skill", "add-feature", cwd=tempfile.gettempdir())
        self.assertEqual(2, r.returncode)
        self.assertIn("--stack", r.stderr)

    def test_un_nombre_con_ruta_no_sale_de_las_skills(self):
        r = harness("stack.py", "skill", "../../rules/architecture", "--stack", "golang-hexagonal", cwd=RAIZ)
        self.assertEqual(2, r.returncode)

    def test_la_referencia_se_pide_por_id_de_norma_o_por_archivo(self):
        for nombre, frase in (("datos", "Outbox"), ("vertical-slice", "Vertical Slice"),
                              ("normas-de-ingenieria.md", "norma × rol")):
            r = harness("normas.py", "--ref", nombre, cwd=RAIZ)
            with self.subTest(ref=nombre):
                self.assertEqual(0, r.returncode, r.stdout + r.stderr)
                self.assertIn(frase, r.stdout)

    def test_una_referencia_que_no_existe_no_devuelve_verde(self):
        for nombre in ("no-existe", "../SKILL", "../scripts/gate.py"):
            r = harness("normas.py", "--ref", nombre, cwd=RAIZ)
            with self.subTest(ref=nombre):
                self.assertEqual(2, r.returncode)
                self.assertIn("no hay referencia", r.stderr)


class BriefingDelRevisorTests(Proyecto):
    def test_audita_cada_norma_del_registro(self):
        out = self.briefing()
        for n in normas.NORMAS:
            with self.subTest(norma=n["id"]):
                self.assertEqual(1, out.count(f"- Audita {n['titulo']} [{n['id']}]"))

    def test_owasp_mcconnell_y_ste100_ya_no_dependen_de_agents_revisor_md(self):
        out = self.briefing()
        for frase in ("inyeccion (A03)", "control de acceso roto (A01)", "errores tragados",
                      "barricada defensiva", "frase de hasta 20 palabras"):
            with self.subTest(frase=frase):
                self.assertIn(frase, out)

    def test_conserva_las_severidades_que_ya_bloqueaban(self):
        out = self.briefing()
        for frase in ("BLOQUEANTE: doble escritura (Dual-Write)", "BLOQUEANTE: consultas N+1",
                      "BLOQUEANTE: acceso a la base de datos de otro servicio",
                      "BLOQUEANTE: llamadas a APIs de LLMs sin timeout", "MAYOR: Primitive Obsession",
                      "MAYOR: metodos pass-through"):
            with self.subTest(frase=frase):
                self.assertIn(frase, out)

    def test_las_normas_del_implementer_no_se_repiten_en_el_briefing(self):
        """El revisor recibe que auditar, no la lista de quien escribe."""
        self.assertNotIn("NORMAS DE INGENIERIA", self.briefing())

    def test_el_resto_del_briefing_sigue_en_su_sitio(self):
        out = self.briefing()
        for frase in ("Criterio del veredicto global", "Audita la integridad de los tests",
                      "No modifiques codigo", "DIFF DE LA FEATURE"):
            with self.subTest(frase=frase):
                self.assertIn(frase, out)


class AcNegativosTests(unittest.TestCase):
    BASE = "## Criterios de aceptacion\n\n- AC-1 [costura: endpoint]: crea el cobro. `verificar: true`\n"

    def test_la_marca_se_lee_y_no_rompe_la_costura_ni_el_comando(self):
        texto = self.BASE + "- AC-2 [costura: endpoint] [negativo]: sin token responde 401. `verificar: true`\n"
        self.assertEqual(["AC-2"], comun.ac_negativos(texto))
        self.assertEqual(["AC-1", "AC-2"], comun.spec_acs(texto))
        self.assertEqual("endpoint", comun.ac_costuras(texto)["AC-2"])
        self.assertEqual("true", comun.ac_comandos(texto)["AC-2"])

    def test_un_endpoint_sin_ningun_ac_negativo_se_avisa(self):
        avisos = comun.avisos_vertical_spec(self.BASE)
        self.assertEqual(1, len([a for a in avisos if a.startswith("seguridad:")]))
        self.assertIn("AC-1", avisos[0])

    def test_con_un_ac_negativo_no_avisa(self):
        texto = self.BASE + "- AC-2 [costura: endpoint] [negativo]: sin token responde 401.\n"
        self.assertEqual([], [a for a in comun.avisos_vertical_spec(texto) if a.startswith("seguridad:")])

    def test_un_spec_que_no_expone_nada_no_recibe_el_aviso(self):
        texto = "## Criterios de aceptacion\n\n- AC-1 [costura: servicio]: descuenta stock.\n"
        self.assertEqual([], [a for a in comun.avisos_vertical_spec(texto) if a.startswith("seguridad:")])

    def test_la_marca_dentro_de_un_comentario_no_cuenta(self):
        texto = self.BASE + "<!-- - AC-2 [negativo]: ejemplo -->\n"
        self.assertEqual([], comun.ac_negativos(texto))

    def test_la_plantilla_del_spec_trae_el_ejemplo_y_no_dispara_el_aviso(self):
        plantilla = (RAIZ / "templates" / "spec.md").read_text(encoding="utf-8")
        self.assertIn("[negativo]", plantilla)
        cuerpo = plantilla.split("```markdown", 1)[1]
        self.assertEqual([], [a for a in comun.avisos_vertical_spec(cuerpo) if a.startswith("seguridad:")])

    def test_approve_spec_lo_dice_al_sellar(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        escribir(tmp / "docs" / "spec-feature-1-cobro.md", SPEC)
        escribir(tmp / "harness" / "feature_list.json", json.dumps(
            {"project": "demo", "rules": REGLAS, "features": [{"id": 1, "name": "cobro", "status": "todo"}]}))
        r = harness("gate.py", "approve-spec", "--feature", "1", "--yes", "--por", "T", cwd=tmp)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("ningun AC es negativo", r.stdout)


class DocumentacionPorStackTests(Proyecto):
    def test_los_diez_stacks_declaran_documentacion_context7_y_escaner(self):
        manifests = stack.listar_stacks_disponibles()
        self.assertEqual(10, len(manifests))
        for m in manifests:
            with self.subTest(stack=m["id"]):
                doc = m.get("documentation", {})
                self.assertTrue(doc.get("official_docs", "").startswith("https://"))
                self.assertRegex(doc.get("context7", {}).get("library_id", ""), r"^/[\w.-]+/[\w.-]+")
                self.assertTrue(m.get("security_audit", {}).get("command"))

    def test_la_referencia_nombra_el_mismo_id_que_el_manifest(self):
        """Dos fuentes que dicen ids distintos: el agente no sabe cual vale."""
        ref = (RAIZ / "references" / "context7-documentacion-oficial.md").read_text(encoding="utf-8")
        for m in stack.listar_stacks_disponibles():
            fila = next((ln for ln in ref.splitlines() if f"**`{m['id']}`**" in ln), None)
            with self.subTest(stack=m["id"]):
                self.assertIsNotNone(fila, "el stack no esta en la tabla de la referencia")
                self.assertIn(m["documentation"]["context7"]["library_id"], fila)

    def test_el_brief_dice_donde_contrastar_en_cada_stack(self):
        out = self.brief()
        self.assertIn("DOCUMENTACION VIGENTE DEL STACK golang-hexagonal", out)
        self.assertIn("Context7: /golang/go", out)
        self.assertIn("documentacion oficial: https://go.dev/doc/", out)
        self.assertIn("stack.py auditar", out)

    def test_el_briefing_ya_no_imprime_un_id_de_context7_vacio(self):
        out = self.briefing()
        self.assertNotIn("lib: ''", out)
        self.assertIn("Context7: /golang/go", out)

    def test_el_borrador_del_sdd_tambien_lo_trae(self):
        r = harness("producto.py", "borrador", "--doc", "sdd", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("Context7: /golang/go", r.stdout)

    def test_el_borrador_trae_las_normas_de_su_documento(self):
        for doc, frase in (("sdd", "fronteras de confianza"), ("prd", "casos de abuso")):
            r = harness("producto.py", "borrador", "--doc", doc, cwd=self.root)
            with self.subTest(doc=doc):
                self.assertEqual(0, r.returncode, r.stdout + r.stderr)
                self.assertIn(f"lo que el {doc.upper()} deja escrito", r.stdout)
                self.assertIn(frase, r.stdout)

    def test_un_stack_sin_el_bloque_lo_dice(self):
        self.assertIn("no declara `documentation`", "\n".join(contexto.lineas_documentacion("x", {})))

    def test_el_agents_md_no_inventa_un_id_de_context7(self):
        manifest = dict(stack.cargar_manifest("golang-hexagonal"))
        manifest.pop("documentation")
        texto = stack._generar_agents_md("golang-hexagonal", manifest)
        self.assertNotIn("library `golang-hexagonal`", texto)
        self.assertIn("resolve-library-id", texto)


class AuditarTests(unittest.TestCase):
    """`stack.py auditar` mide: limpio, con hallazgos o sin medir. Con un escaner de mentira."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "ms-java"
        escribir(self.repo / "pom.xml", "<project><parent><artifactId>spring-boot-starter-parent"
                                        "</artifactId></parent></project>\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def escaner(self, codigo: int) -> None:
        ruta = self.repo / "mvnw"
        ruta.write_text(f"#!/bin/sh\necho escaner de prueba\nexit {codigo}\n", encoding="utf-8")
        ruta.chmod(ruta.stat().st_mode | stat.S_IXUSR)

    def auditar(self, *extra) -> subprocess.CompletedProcess:
        return harness("stack.py", "auditar", "--repo", str(self.repo), "--stack", "springboot-hexagonal",
                       *extra, cwd=self.tmp)

    def test_escaner_limpio_sale_con_cero(self):
        self.escaner(0)
        r = self.auditar()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("limpio", r.stdout)

    def test_escaner_con_hallazgos_sale_con_uno(self):
        self.escaner(1)
        r = self.auditar()
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)
        self.assertIn("hallazgos", r.stdout)

    def test_sin_escaner_no_devuelve_verde(self):
        """Un gate que no puede medir no devuelve verdadero."""
        r = self.auditar()
        self.assertEqual(2, r.returncode, r.stdout + r.stderr)
        self.assertIn("NO se pudo medir", r.stdout)

    def test_un_repo_sin_stack_tampoco(self):
        vacio = self.tmp / "vacio"
        vacio.mkdir()
        r = harness("stack.py", "auditar", "--repo", str(vacio), cwd=self.tmp)
        self.assertEqual(2, r.returncode, r.stdout + r.stderr)

    def test_el_json_trae_el_estado(self):
        self.escaner(1)
        r = self.auditar("--json")
        self.assertEqual("hallazgos", json.loads(r.stdout)["estado"])

    def test_un_escaner_que_lista_vulnerables_y_sale_con_cero_no_es_un_verde(self):
        """`dotnet list package --vulnerable` sale con 0 aunque encuentre: lo delata su salida."""
        ruta = self.repo / "mvnw"
        ruta.write_text("#!/bin/sh\necho 'Project X has the following vulnerable packages'\nexit 0\n",
                        encoding="utf-8")
        ruta.chmod(ruta.stat().st_mode | stat.S_IXUSR)
        manifest = dict(stack.cargar_manifest("springboot-hexagonal"))
        manifest["security_audit"] = {"command": "./mvnw", "findings_pattern": "has the following vulnerable packages"}
        with mock.patch.object(stack, "cargar_manifest", return_value=manifest):
            res = stack.auditar_seguridad_y_versiones(self.repo, "springboot-hexagonal")
        self.assertEqual("hallazgos", res["estado"])

    def test_el_escaner_de_cada_stack_no_es_un_subcomando_inventado(self):
        """`swift package audit` no existe en SwiftPM: salia como 'hallazgos' en cualquier repo."""
        for m in stack.listar_stacks_disponibles():
            with self.subTest(stack=m["id"]):
                self.assertNotIn("swift package audit", m["security_audit"]["command"])

    def test_el_wrapper_del_repo_se_busca_en_el_repo(self):
        self.assertFalse(stack._herramienta_disponible("./mvnw", self.repo))
        self.escaner(0)
        self.assertTrue(stack._herramienta_disponible("./mvnw", self.repo))


class PlanDeRefactorTests(unittest.TestCase):
    def test_un_stack_sin_plan_propio_no_devuelve_un_plan_vacio(self):
        tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, tmp, True)
        escribir(tmp / "nest-cli.json", "{}")
        escribir(tmp / "package.json", json.dumps({"dependencies": {"@nestjs/core": "11.0.0"}}))
        plan = stack.generar_plan_refactor(tmp, "nestjs-hexagonal")
        self.assertTrue(plan["needed"])
        self.assertTrue(plan["steps"], "hace falta refactorizar y no dice que")
        self.assertTrue(all(s["description"] for s in plan["steps"]))


class SddTests(unittest.TestCase):
    def test_un_sdd_sin_diagrama_recibe_el_aviso(self):
        self.assertEqual(1, len(producto.avisos_sdd("# SDD\n\n## Componentes\n\nTexto.\n")))

    def test_con_un_diagrama_mermaid_no(self):
        self.assertEqual([], producto.avisos_sdd("## Componentes\n\n```mermaid\ngraph TD; A-->B;\n```\n"))

    def test_un_diagrama_dentro_de_un_comentario_no_cuenta(self):
        self.assertEqual(1, len(producto.avisos_sdd("<!--\n```mermaid\ngraph TD;\n```\n-->\nTexto.\n")))


class TextosPorHostTests(unittest.TestCase):
    """Lo que no sale de un script: que SKILL.md y cada guia de host manden al brief."""

    def leer(self, ruta: str) -> str:
        return (RAIZ / ruta).read_text(encoding="utf-8")

    def test_skill_md_manda_a_las_normas_del_brief_en_los_tres_roles(self):
        skill = self.leer("SKILL.md")
        self.assertGreaterEqual(skill.count("NORMAS DE INGENIERIA"), 3)
        self.assertIn("[negativo]", skill)
        self.assertIn("scripts/normas.py", skill)

    def test_ninguna_guia_de_host_presenta_pair_como_algo_que_hay_que_activar(self):
        for ruta in ("references/openai.md", "references/grok.md", "references/kimi.md",
                     "references/claude.md", "references/modelos.md"):
            texto = self.leer(ruta)
            with self.subTest(guia=ruta):
                self.assertNotIn("Modo Pair interactivo (`--pair`)**", texto)
                self.assertNotRegex(texto, r"se detecta un \*\*stack tecnológico normativo\*\*")

    def test_las_guias_de_los_hosts_sin_comandos_nombran_las_normas(self):
        for ruta in ("references/openai.md", "references/grok.md", "references/kimi.md"):
            with self.subTest(guia=ruta):
                self.assertIn("NORMAS DE INGENIERIA", self.leer(ruta))

    def test_los_comandos_de_claude_code_tambien(self):
        for ruta in ("commands/implementar.md", "commands/spec.md"):
            with self.subTest(comando=ruta):
                self.assertIn("NORMAS DE INGENIERIA", self.leer(ruta))

    def test_el_readme_ya_no_dice_que_un_script_se_conecta_a_context7(self):
        self.assertNotIn("Conexión con el servidor MCP de Context7", self.leer("README.md"))


if __name__ == "__main__":
    unittest.main()
