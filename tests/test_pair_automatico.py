"""Pair automatico: el agente avanza solo y pregunta solo cuando hace falta.

Reportado por el usuario: "la idea es que pregunte en formulario cuando sea
realmente necesario; ahora se da muchas vueltas y no avanza". Medido en la
sesion de un proyecto real: 166 preguntas de formulario, y en 150 el usuario
eligio la primera opcion. Las 17 listas de tests se aprobaron sin cambiar una
linea, y cada lista que crecia volvia a preguntar.

La causa estaba en el arnes, que decia dos cosas a la vez: "avanza de forma
autonoma" y "haz 1 paso y detente". Y `close` exigia el SI del usuario para
cada version de la lista de tests.

Decisiones del usuario que estos tests fijan:
- la lista de tests la sella quien implementa, sin formulario; el gate exige el
  SI del usuario solo si quita un test sellado o deja un AC solo manual;
- una decision de diseno fuera del spec se sigue preguntando;
- el rol de spec no cambia.
"""
import re
import unittest

from test_pair_y_reglas import LISTA, RAIZ, SPEC, Proyecto, escribir, harness, sh

AC2 = "- AC-2: el_reintento_no_cobra_dos_veces [costura: servicio]\n"


class ListaSinFormularioTests(Proyecto):
    def setUp(self):
        super().setUp()
        self.ruta = self.root / "docs" / "tests-5.md"

    def lista(self, texto=LISTA):
        escribir(self.ruta, texto)

    def agregar(self, linea):
        self.ruta.write_text(self.ruta.read_text(encoding="utf-8") + linea, encoding="utf-8")

    def quitar(self, linea):
        texto = self.ruta.read_text(encoding="utf-8")
        self.assertIn(linea, texto)
        self.ruta.write_text(texto.replace(linea, ""), encoding="utf-8")

    def sellar(self, *extra, comando="sellar-tests"):
        return harness("gate.py", comando, "--feature", "5", "--por", "T", *extra, cwd=self.root)

    def sellada(self, texto=LISTA):
        self.lista(texto)
        r = self.sellar()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_la_lista_que_cubre_cada_ac_se_sella_sin_el_si_del_usuario(self):
        self.lista()
        r = self.sellar()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        texto = self.ruta.read_text(encoding="utf-8")
        self.assertIn("Estado: sellada", texto)
        self.assertIn("gate.py sellar-tests", texto)
        self.assertNotIn("con el si del usuario", texto)
        self.assertFalse(self.feature()["tests_aprobados"]["con_si_del_usuario"])
        self.assertIn("no esperes su aprobacion", r.stdout)

    def test_el_nombre_anterior_del_comando_sigue_valiendo(self):
        self.lista()
        self.assertEqual(0, self.sellar(comando="aprobar-tests").returncode)
        self.assertEqual(0, self.sellar("--yes", comando="aprobar-tests").returncode)

    def test_un_ac_sin_test_se_niega_aunque_venga_el_si(self):
        """El control: el SI del usuario no reemplaza la cobertura."""
        self.lista(LISTA.replace(AC2, ""))
        r = self.sellar("--yes")
        self.assertNotEqual(0, r.returncode)
        self.assertIn("AC-2", r.stdout + r.stderr)

    def test_agregar_tests_se_vuelve_a_sellar_sin_preguntar(self):
        self.sellada()
        self.agregar("- AC-1: rechaza_un_carro_vacio [costura: endpoint]\n")
        r = self.sellar()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertEqual(3, len(self.feature()["tests_sellados"]))

    def test_quitar_un_test_sellado_se_niega_y_lo_nombra(self):
        self.sellada(LISTA + "- AC-1: rechaza_un_carro_vacio [costura: endpoint]\n")
        firma = self.feature()["tests_sig"]
        self.quitar("- AC-1: rechaza_un_carro_vacio [costura: endpoint]\n")
        r = self.sellar()
        self.assertNotEqual(0, r.returncode)
        salida = r.stdout + r.stderr
        self.assertIn("--yes", salida)
        self.assertIn("AC-1: rechaza_un_carro_vacio", salida)
        self.assertIn("USUARIO", salida)
        self.assertEqual(firma, self.feature()["tests_sig"], "una negativa no toca el sello")

    def test_quitarlo_con_el_si_del_usuario_sella_y_deja_constancia(self):
        self.sellada(LISTA + "- AC-1: rechaza_un_carro_vacio [costura: endpoint]\n")
        self.quitar("- AC-1: rechaza_un_carro_vacio [costura: endpoint]\n")
        r = self.sellar("--yes")
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("con el si del usuario", self.ruta.read_text(encoding="utf-8"))
        self.assertTrue(self.feature()["tests_aprobados"]["con_si_del_usuario"])
        historia = (self.root / "harness" / "progress" / "history.md").read_text(encoding="utf-8")
        self.assertIn("con el si del usuario: quita 1", historia)

    def test_renombrar_un_test_sellado_cuenta_como_quitarlo(self):
        self.sellada()
        self.ruta.write_text(self.ruta.read_text(encoding="utf-8").replace(
            "el_reintento_no_cobra_dos_veces", "el_reintento_responde_200"), encoding="utf-8")
        r = self.sellar()
        self.assertNotEqual(0, r.returncode)
        self.assertIn("el_reintento_no_cobra_dos_veces", r.stdout + r.stderr)

    def test_cambiar_solo_la_costura_no_es_quitar_el_test(self):
        self.sellada()
        self.ruta.write_text(self.ruta.read_text(encoding="utf-8").replace(
            "[costura: servicio]", "[costura: integracion]"), encoding="utf-8")
        self.assertEqual(0, self.sellar().returncode)

    def test_los_tests_de_un_ac_que_el_spec_ya_no_trae_se_van_sin_preguntar(self):
        """Ese AC lo quito el usuario con una enmienda: su SI ya esta dado."""
        self.sellada()
        spec = self.root / "docs" / "spec-feature-5-cobro.md"
        texto = spec.read_text(encoding="utf-8")
        spec.write_text(re.sub(r"^- AC-2:.*\n", "", texto, flags=re.M), encoding="utf-8")
        self.quitar(AC2)
        r = self.sellar()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_una_lista_sellada_antes_de_este_cambio_no_tiene_linea_base(self):
        """No se le inventa un sello anterior a lo que ya estaba en curso."""
        self.sellada(LISTA + "- AC-1: rechaza_un_carro_vacio [costura: endpoint]\n")
        data = self.feature()
        del data["tests_sellados"]
        self.backlog(data)
        self.quitar("- AC-1: rechaza_un_carro_vacio [costura: endpoint]\n")
        self.assertEqual(0, self.sellar().returncode)

    def test_un_ac_solo_con_verificacion_manual_que_el_spec_no_declara_se_niega(self):
        self.lista(LISTA.replace("el_reintento_no_cobra_dos_veces [costura: servicio]",
                                 "verificacion manual: el boton queda deshabilitado"))
        r = self.sellar()
        self.assertNotEqual(0, r.returncode)
        salida = r.stdout + r.stderr
        self.assertIn("AC-2", salida)
        self.assertIn("verificacion manual", salida)
        self.assertNotIn("tests_sig", self.feature())

    def test_un_ac_que_el_spec_declara_manual_se_sella_sin_preguntar(self):
        spec = self.root / "docs" / "spec-feature-5-cobro.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace(
            "- AC-2: dado", "- AC-2 [costura: manual]: dado"), encoding="utf-8")
        self.lista(LISTA.replace("el_reintento_no_cobra_dos_veces [costura: servicio]",
                                 "Verificación manual: el boton queda deshabilitado"))
        r = self.sellar()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)

    def test_un_ac_con_un_test_y_ademas_una_verificacion_manual_no_pregunta(self):
        self.lista(LISTA + "- AC-2: verificacion manual: el boton queda deshabilitado\n")
        self.assertEqual(0, self.sellar().returncode)

    def test_una_linea_dentro_de_un_comentario_no_es_un_test(self):
        self.sellada("# Lista\n\nEstado: draft\n\n<!-- ejemplo:\n- AC-1: nombre_de_ejemplo\n-->\n" + LISTA.split("\n\n", 2)[2])
        self.assertEqual(2, len(self.feature()["tests_sellados"]))


class CloseConListaTests(Proyecto):
    def cerrar(self, preparar):
        self.backlog({"id": 5, "name": "cobro", "kind": "feature", "status": "in_progress", "modo": "pair",
                      "branch": "feature/5", "base_sha": sh("git", "rev-parse", "HEAD", cwd=self.root)})
        self.commit("backlog")
        sh("git", "checkout", "-q", "-b", "feature/5", cwd=self.root)
        preparar()
        escribir(self.root / "src" / "b.go", "package src\n")
        self.commit("trabajo")
        return harness("gate.py", "close", "--feature", "5", "--status", "done", "--to", "main", cwd=self.root)

    def sellar(self):
        escribir(self.root / "docs" / "tests-5.md", LISTA)
        r = harness("gate.py", "sellar-tests", "--feature", "5", "--por", "T", cwd=self.root)
        assert r.returncode == 0, r.stdout + r.stderr

    def test_cierra_con_la_lista_que_sello_quien_implementa(self):
        r = self.cerrar(self.sellar)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertEqual("done", self.feature()["status"])

    def test_sin_sello_no_cierra(self):
        """El control: quitar el formulario no quita el gate."""
        r = self.cerrar(lambda: escribir(self.root / "docs" / "tests-5.md", LISTA))
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)
        self.assertIn("falta la lista de tests sellada", r.stdout)

    def test_la_lista_que_crecio_pide_volver_a_sellar_sin_mandar_a_preguntar(self):
        def preparar():
            self.sellar()
            ruta = self.root / "docs" / "tests-5.md"
            ruta.write_text(ruta.read_text(encoding="utf-8") + "- AC-1: otro_test\n", encoding="utf-8")
        r = self.cerrar(preparar)
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)
        self.assertIn("vuelve a sellarla", r.stdout)
        self.assertIn("no hace falta preguntar", r.stdout)
        self.assertNotIn("muestrasela", r.stdout)


class BriefTests(Proyecto):
    def brief(self, modo):
        self.backlog({"id": 5, "name": "cobro", "status": "in_progress", "modo": modo})
        r = harness("contexto.py", "brief", "--feature", "5", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        return r.stdout

    def test_en_pair_ordena_avanzar_sin_preguntar_si_sigue(self):
        out = self.brief("pair")
        self.assertIn("modo pair automatico: ACTIVADO", out)
        self.assertIn("sin preguntar si sigues", out)
        self.assertIn("Commitea en la rama de la feature sin pedir permiso", out)
        self.assertIn('"paso a paso"', out)

    def test_en_pair_la_lista_la_sella_quien_implementa(self):
        out = self.brief("pair")
        self.assertIn("sellar-tests --feature 5", out)
        self.assertIn("no esperes aprobacion", out)
        self.assertNotIn("aprobada por el usuario", out)

    def test_en_pair_dice_cuando_un_formulario_hace_falta(self):
        out = self.brief("pair")
        self.assertIn("formulario SOLO para", out)
        self.assertIn("quitar un test sellado", out)
        self.assertIn("UN formulario", out)
        self.assertIn("sigue con lo que no depende de la respuesta", out)

    def test_en_pair_un_subagente_devuelve_la_pregunta(self):
        """Varias features en paralelo: el implementer es un subagente y no ve al usuario."""
        self.assertIn("si eres un subagente", self.brief("pair"))

    def test_cada_parada_dice_si_pregunta_o_no(self):
        for modo in ("pair", "delegado"):
            with self.subTest(modo=modo):
                out = self.brief(modo)
                self.assertIn("5 paradas:", out)
                self.assertIn("(1), (3) y (4) preguntan", out)
                self.assertIn("(2) no pregunta", out)
                self.assertIn("(5) no pregunta", out)

    def test_delegado_no_recibe_el_protocolo_de_formularios(self):
        """El control: un delegado no tiene usuario a quien preguntar."""
        out = self.brief("delegado")
        self.assertNotIn("formulario SOLO para", out)
        self.assertIn("devuelve la pregunta a quien te delego", out)

    def test_el_arranque_del_worktree_dice_lo_mismo(self):
        self.backlog({"id": 5, "name": "cobro", "status": "todo"})
        self.commit("backlog")
        r = harness("worktree.py", "start", "--feature", "5", "--sin-contexto", cwd=self.root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("sellar-tests --feature 5", r.stdout)
        self.assertIn("sin pausar", r.stdout)
        self.assertNotIn("la aprueba", r.stdout)


class LosTextosDicenLoMismoTests(unittest.TestCase):
    """La causa fue una contradiccion entre textos: uno decia avanzar y otro pausar."""

    ROLES = ("SKILL.md", "README.md", "commands/implementar.md", "templates/tests.md",
             "references/vertical-slice.md", "references/modelos.md", "references/claude.md",
             "references/kimi.md", "references/openai.md", "references/grok.md")
    RITMO_VIEJO = (r"1 paso y (te )?det", r"pausando (tras|en) cada", r"1 ciclo por turno",
                   r"lista de tests aprobada", r"aprobar-tests --feature", r"la aprueba\s+el\s+usuario",
                   r"espera el OK", r"espera la aprobaci[oó]n del usuario")

    def test_ningun_texto_de_rol_conserva_el_ritmo_anterior(self):
        for nombre in self.ROLES:
            texto = (RAIZ / nombre).read_text(encoding="utf-8")
            for patron in self.RITMO_VIEJO:
                with self.subTest(archivo=nombre, patron=patron):
                    self.assertIsNone(re.search(patron, texto, flags=re.I))

    def test_el_rol_implementer_dice_que_no_se_pregunta(self):
        texto = (RAIZ / "commands" / "implementar.md").read_text(encoding="utf-8")
        self.assertIn("**No preguntes**", texto)
        self.assertIn("sellar-tests --feature", texto)
        self.assertIn("No esperes aprobacion", texto)
        self.assertIn("UN formulario", texto)

    def test_la_guia_tiene_las_dos_tablas(self):
        texto = (RAIZ / "references" / "vertical-slice.md").read_text(encoding="utf-8")
        self.assertIn("### Cuándo un formulario hace falta", texto)
        self.assertIn("### Cuándo NO hace falta", texto)
        self.assertIn("### Varias features en paralelo", texto)

    def test_el_refactor_en_verde_no_espera_el_ok_del_usuario(self):
        r = harness("normas.py", "--rol", "implementer", cwd=RAIZ)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertNotIn("con el OK del usuario", r.stdout)
        self.assertIn("Aplicalo tu, en pair y en delegado", r.stdout)


if __name__ == "__main__":
    unittest.main()
