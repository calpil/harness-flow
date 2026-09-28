"""Bajas de SUBTESTS Go en --retirados. FIXTURE: Git y Go reales, sin red.

Contrato: docs/diseno-arnes-bajas-subtests.md del proyecto ADR (decidido por
Alan el 2026-09-28). Un subtest renombrado o borrado cuyo test padre SIGUE vivo
se declara `<paquete>::<TestX>/<seg>[/<seg>...]`, con el nombre exacto que
reporto `go test -json` en la base. La baja se verifica igual que la de primer
nivel -- medida en la base, ausente del destino, borrada por la feature y
citada en el review --, pero "borrada" se prueba sobre los LITERALES de cadena
de los *_test.go del paquete (reescritos como testing.rewrite), no sobre un
`func TestX(`.

Los controles negativos atraviesan el CLI real (`gate.py close` y
`postmerge_medido.py check`): exit != 0 con su motivo y backlog/documentos
byte-identicos, no solo una funcion interna en rojo.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(os.environ.get("HARNESS_TEST_SCRIPTS", Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(SCRIPTS))
import retiros  # noqa: E402  el lector de literales y la cita tambien se prueban en proceso

CMD = "go test -tags integration -count=1 -json ./..."
MOD = "fixture.invalid/alpha"
CABECERA = 'package contract\n\nimport "testing"\n\n'

# t.Run con el nombre literal: el caso de la #10 en database.
RUN_BASE = CABECERA + (
    'func TestRenombrado(t *testing.T) {\n'
    '\tt.Run("la boleta (39) sigue fuera de alcance", func(t *testing.T) {})\n'
    '\tt.Run("sigue vivo", func(t *testing.T) {})\n'
    '}\n')
RUN_RENOMBRADO = RUN_BASE.replace("la boleta (39)", "la boleta exenta (41)")
# El subtest sigue ESCRITO, solo que ya no corre: no es una baja.
RUN_ESCONDIDO = CABECERA + (
    'func TestRenombrado(t *testing.T) {\n'
    '\tif false {\n'
    '\t\tt.Run("la boleta (39) sigue fuera de alcance", func(t *testing.T) {})\n'
    '\t}\n'
    '\tt.Run("sigue vivo", func(t *testing.T) {})\n'
    '}\n')
RUN_CONSTANTE = RUN_RENOMBRADO + 'const nombreViejo = "la boleta (39) sigue fuera de alcance"\n'

# Subtest de tabla: el nombre vive en un struct, no en el argumento de t.Run.
TABLA_BASE = CABECERA + (
    'func TestTabla(t *testing.T) {\n'
    '\tcasos := []struct {\n'
    '\t\tnombre string\n'
    '\t\tcodigo int\n'
    '\t}{\n'
    '\t\t{"409 in_progress es transitorio", 409},\n'
    '\t\t{"503 unavailable es transitorio", 503},\n'
    '\t\t{"repetido", 1},\n'
    '\t\t{"repetido", 2},\n'
    '\t}\n'
    '\tfor _, c := range casos {\n'
    '\t\tt.Run(c.nombre, func(t *testing.T) {\n'
    '\t\t\tif c.codigo == 0 {\n'
    '\t\t\t\tt.Fatal("sin codigo")\n'
    '\t\t\t}\n'
    '\t\t})\n'
    '\t}\n'
    '}\n')
TABLA_RENOMBRADA = TABLA_BASE.replace("409 in_progress es transitorio", "409 in_progress es incierto")
# El segundo "repetido" se midio como `repetido#01`: go test desambiguo el nombre.
TABLA_SIN_DUPLICADO = TABLA_BASE.replace('{"repetido", 2}', '{"repetido distinto", 2}')

# Anidado TestX/a/b; la hoja es un literal CRUDO (backticks).
ANIDADO_BASE = CABECERA + (
    'func TestAnidado(t *testing.T) {\n'
    '\tt.Run("grupo", func(t *testing.T) {\n'
    '\t\tt.Run(`hoja vieja`, func(t *testing.T) {})\n'
    '\t\tt.Run("hoja viva", func(t *testing.T) {})\n'
    '\t})\n'
    '}\n')
ANIDADO_RENOMBRADO = ANIDADO_BASE.replace("`hoja vieja`", "`hoja nueva`")
ANIDADO_GRUPO_RENOMBRADO = ANIDADO_BASE.replace('t.Run("grupo"', 't.Run("grupo nuevo"')

# Nombres armados en runtime: no hay literal que pruebe que la feature los borro.
ARMADO_BASE = ('package contract\n\nimport (\n\t"fmt"\n\t"testing"\n)\n\n'
               'func TestArmado(t *testing.T) {\n'
               '\tt.Run(fmt.Sprintf("caso %d", 7), func(t *testing.T) {})\n'
               '\tt.Run(fmt.Sprintf("grupo %d", 1), func(t *testing.T) {\n'
               '\t\tt.Run("dentro", func(t *testing.T) {})\n'
               '\t})\n'
               '\tt.Run("vivo", func(t *testing.T) {})\n'
               '}\n')
ARMADO_RECORTADO = (ARMADO_BASE
                    .replace('\tt.Run(fmt.Sprintf("caso %d", 7), func(t *testing.T) {})\n', '')
                    .replace('\t\tt.Run("dentro", func(t *testing.T) {})\n', ''))

PADRE_BASE = CABECERA + 'func TestPadre(t *testing.T) {\n\tt.Run("hijo", func(t *testing.T) {})\n}\n'

# Review r1, P2-1: el subtest SIGUE corriendo con el mismo id, terminado en skip,
# y su nombre ya no es un literal de un *_test.go (armado en runtime, o una
# constante de un .go comun del paquete). Registrado no es borrado.
RUN_SKIP_ARMADO = ('package contract\n\nimport (\n\t"strings"\n\t"testing"\n)\n\n'
                   'func TestRenombrado(t *testing.T) {\n'
                   '\tt.Run(strings.Join([]string{"la boleta (39)", "sigue fuera de alcance"}, " "),'
                   ' func(t *testing.T) { t.Skip("escondido") })\n'
                   '\tt.Run("sigue vivo", func(t *testing.T) {})\n'
                   '}\n')
CASOS_NO_TEST = 'package contract\n\nconst NombreViejo = "la boleta (39) sigue fuera de alcance"\n'
RUN_SKIP_CONSTANTE = CABECERA + ('func TestRenombrado(t *testing.T) {\n'
                                 '\tt.Run(NombreViejo, func(t *testing.T) { t.Skip("escondido") })\n'
                                 '\tt.Run("sigue vivo", func(t *testing.T) {})\n'
                                 '}\n')

# Review r2, P2-2: `t.Run("grupo/hoja vieja")` registra `TestAnidado/grupo/hoja_vieja`
# SIN registrar `TestAnidado/grupo`. Armado en runtime y con skip, la baja del
# prefijo `TestAnidado/grupo` lo cubria en sin_baja.
ANIDADO_PLANO_SKIP = ('package contract\n\nimport (\n\t"fmt"\n\t"testing"\n)\n\n'
                      'func TestAnidado(t *testing.T) {\n'
                      '\tt.Run(fmt.Sprintf("%s/hoja vieja", string(rune(103))+"rupo"),'
                      ' func(t *testing.T) { t.Skip("escondido") })\n'
                      '\tt.Run("grupo nuevo", func(t *testing.T) {\n'
                      '\t\tt.Run("hoja viva", func(t *testing.T) {})\n'
                      '\t})\n'
                      '}\n')
# Control: el mismo aplanado, pero el descendiente CORRE y se mide: es un renombre.
ANIDADO_PLANO_MEDIDO = CABECERA + ('func TestAnidado(t *testing.T) {\n'
                                   '\tt.Run("grupo/hoja viva", func(t *testing.T) {})\n'
                                   '}\n')

# Review r3, P3-7 (ya estaba en main): go test registra por AST, pero _definido
# busca `^func TestX\(`. Sin gofmt, el TestPadre que sigue corriendo para
# terminar en skip no se ve "definido" y el check lo aceptaba como baja.
PADRE_SIN_GOFMT_SKIP = CABECERA + ('func TestPadre (t *testing.T) {\n\tt.Skip("escondido")\n'
                                   '\tt.Run("hijo", func(t *testing.T) {})\n}\n')
PADRE_INDENTADO_SKIP = CABECERA + ('\tfunc TestPadre(t *testing.T) {\n\tt.Skip("escondido")\n'
                                   '\tt.Run("hijo", func(t *testing.T) {})\n}\n')


class Enlace(str):
    """Un symlink a crear en lugar de un archivo (Go compila un *_test.go symlink)."""

# OTRO paquete (subdirectorio) con los mismos literales: no cuenta para el
# paquete raiz, igual que `_definido` no cruza a subdirectorios.
OTRO = ('package otro\n\nimport "testing"\n\n'
        'func TestOtro(t *testing.T) {\n'
        '\tt.Run("la boleta (39) sigue fuera de alcance", func(t *testing.T) {})\n'
        '\tt.Run("409 in_progress es transitorio", func(t *testing.T) {})\n'
        '\tt.Run("hoja vieja", func(t *testing.T) {})\n'
        '}\n')

BASE = {
    "go.mod": f"module {MOD}\n\ngo 1.22\n",
    "contract_test.go": CABECERA + "func TestBaseContract(t *testing.T) {}\n",
    "run_test.go": RUN_BASE,
    "tabla_test.go": TABLA_BASE,
    "anidado_test.go": ANIDADO_BASE,
    "armado_test.go": ARMADO_BASE,
    "padre_test.go": PADRE_BASE,
    "otro/otro_test.go": OTRO,
}

RUN = f"{MOD}::TestRenombrado/la_boleta_(39)_sigue_fuera_de_alcance"
TABLA = f"{MOD}::TestTabla/409_in_progress_es_transitorio"
ANIDADO = f"{MOD}::TestAnidado/grupo/hoja_vieja"
GRUPO = f"{MOD}::TestAnidado/grupo"
VIVO = f"{MOD}::TestRenombrado/sigue_vivo"
HIJO = f"{MOD}::TestPadre/hijo"
DUPLICADO = f"{MOD}::TestTabla/repetido#01"
CASO_ARMADO = f"{MOD}::TestArmado/caso_7"
DENTRO = f"{MOD}::TestArmado/grupo_1/dentro"
NO_MEDIDO = f"{MOD}::TestRenombrado/no_existe"


def corto(item):
    return item.split("::", 1)[1]


def review_citando(*ids, completo=False):
    """Review que DECLARA cada baja en su propia linea, como palabra completa."""
    lineas = "".join(f"Baja revisada: `{i if completo else corto(i)}` (el caso cambio con la enmienda).\n"
                     for i in ids)
    return "## AC-1\nalpha/feature.txt:1\n" + lineas


class _Fixture(unittest.TestCase):
    FEATURE = "10"
    ARCHIVOS = BASE

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.root = self.home / "project"
        (self.root / "harness" / "progress").mkdir(parents=True)
        (self.root / "docs").mkdir()
        self.env = {"PATH": os.environ["PATH"], "HOME": str(self.home),
                    "USERPROFILE": str(self.home), "CI": "1", "PYTHONDONTWRITEBYTECODE": "1",
                    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                    "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
                    "HARNESS_SKILLS_DIR": str(self.home / "skills"),
                    "GOPROXY": "off", "GOSUMDB": "off", "GOTOOLCHAIN": "local", "GOWORK": "off",
                    "GOCACHE": os.environ.get("HARNESS_TEST_GOCACHE", str(self.home / "go-cache"))}
        lesson = self.home / "skills" / "closure-contract"
        lesson.mkdir(parents=True)
        (lesson / "SKILL.md").write_text("---\nname: closure-contract\ndescription: Fixture\n---\n")
        self.backlog = self.root / "harness" / "feature_list.json"
        (self.root / "docs" / f"spec-feature-{self.FEATURE}-subtests-fixture.md").write_text(
            'Estado: draft\n- AC-1: Given repo When subtest renombrado Then integrado\n'
            'Comando: `git -C alpha merge-base --is-ancestor HEAD HEAD`\n')
        (self.root / "docs" / f"impl-{self.FEATURE}.md").write_text("## AC-1\nalpha/feature.txt:1\n")
        (self.root / "harness" / "progress" / f"current-{self.FEATURE}.md").write_text("Fixture progress\n")
        self.backlog.write_text(json.dumps({"project": "fixture", "rules": {}, "features": [
            {"id": int(self.FEATURE), "name": "Subtests fixture", "status": "in_progress",
             "microservicios": ["alpha"]}]}))
        self.repo = self.root / "alpha"
        self.repo.mkdir()
        self.git(self.repo, "init", "-b", "develop")
        self.aplicar(self.repo, self.ARCHIVOS)
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-m", "fixture: baseline")
        self.base_sha = self.git(self.repo, "rev-parse", "HEAD")
        self.retirados = self.home / "retirados.json"
        self.ok("gate.py", "approve-spec", "--feature", self.FEATURE, "--yes", "--por", "Fixture")

    def git(self, path, *args):
        r = subprocess.run(["git", "-C", str(path), *args], env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout.strip()

    def cli(self, script, *args):
        return subprocess.run([sys.executable, "-B", str(SCRIPTS / script), *args], cwd=self.root,
                              env=self.env, capture_output=True, text=True)

    def ok(self, script, *args):
        r = self.cli(script, *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    @staticmethod
    def aplicar(raiz, cambios):
        for ruta, texto in cambios.items():
            destino = raiz / ruta
            if texto is None or isinstance(texto, Enlace):
                destino.unlink(missing_ok=True)
                if texto is None:
                    continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(texto, Enlace):
                os.symlink(str(texto), destino)
            else:
                destino.write_text(texto)

    def commit(self, path, mensaje):
        self.git(path, "add", "-A")
        self.git(path, "commit", "-m", mensaje)
        return self.git(path, "rev-parse", "HEAD")

    def registrar(self, source, target, worktree):
        manifest = self.home / "manifest.json"
        manifest.write_text(json.dumps({"version": 1, "feature": self.FEATURE, "repos": [
            {"microservicio": "alpha", "repo": str(self.repo), "worktree": str(worktree),
             "base_sha": self.base_sha, "source_sha": source, "target_branch": "develop",
             "target_sha": target}]}))
        self.ok("worktree.py", "register", "--feature", self.FEATURE, "--manifest", str(manifest))

    def sellar(self, review, por="Fixture reviewer"):
        (self.root / "docs" / f"review-{self.FEATURE}.md").write_text(review)
        self.ok("gate.py", "verify", "--feature", self.FEATURE)
        self.ok("gate.py", "revision", "--feature", self.FEATURE, "--veredicto", "approved", "--por", por)

    def declarar(self, bajas, feature=None, micro="alpha"):
        self.retirados.write_text(json.dumps(
            {"version": 1, "feature": feature or self.FEATURE, "retirados": {micro: bajas}}))
        return str(self.retirados)

    def snapshot(self):
        return {str(p): p.read_bytes() for d in (self.root / "docs", self.root / "harness")
                for p in d.rglob("*") if p.is_file()}

    def rechazado(self, razon, *extra):
        before = self.snapshot()
        r = self.close(*extra)
        salida = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0, salida)
        self.assertIn(razon, salida)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(self.snapshot(), before)
        return salida

    def cerrado(self, *extra):
        r = self.close(*extra)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        f = json.loads(self.backlog.read_text())["features"][0]
        self.assertEqual(f["status"], "done")
        return f


class SubtestsTests(_Fixture):
    """Cierre integrado normal: `close --integrated --postmerge`."""

    def setUp(self):
        super().setUp()
        self.base = self.home / "base-alpha.json"
        self.ok("postmerge_medido.py", "base", "--repo", str(self.repo), "--cmd", CMD, "--guardar", str(self.base))
        medidos = {f'{r["Package"]}::{r["Test"]}' for r in json.loads(self.base.read_text())["resultados"]}
        # El fixture mide lo que el contrato dice que mide: nombres ya reescritos.
        self.assertLessEqual({RUN, TABLA, ANIDADO, GRUPO, VIVO, HIJO, DUPLICADO, CASO_ARMADO, DENTRO,
                              f"{MOD}/otro::TestOtro/la_boleta_(39)_sigue_fuera_de_alcance"}, medidos)
        self.mapa = self.home / "postmerge-map.json"
        self.mapa.write_text(json.dumps({"version": 1, "feature": self.FEATURE, "bases": {"alpha": str(self.base)}}))

    def integrar(self, cambios, tardio=None, review=None, por="Fixture reviewer"):
        """La feature aplica su delta en un worktree y se integra por fast-forward;
        `tardio` es un commit posterior del destino."""
        wt = self.home / "worktrees" / "alpha"
        self.git(self.repo, "worktree", "add", "--detach", str(wt))
        (wt / "feature.txt").write_text("fixture feature\n")
        self.aplicar(wt, cambios)
        source = self.commit(wt, "fixture: delta de la feature")
        self.git(self.repo, "merge", "--ff-only", source)
        target = source
        if tardio is not None:
            self.aplicar(self.repo, tardio)
            target = self.commit(self.repo, "fixture: commit tardio del destino")
        self.registrar(source, target, wt)
        self.sellar(review if review is not None else review_citando(RUN, TABLA, ANIDADO), por)
        return source, target

    def close(self, *extra):
        return self.cli("gate.py", "close", "--feature", self.FEATURE, "--status", "done", "--to", "develop",
                        "--integrated", "--leccion", "closure-contract", "--postmerge", str(self.mapa), *extra)

    def check(self, *extra):
        return self.cli("postmerge_medido.py", "check", "--repo", str(self.repo), "--base", str(self.base),
                        "--cmd", CMD, *extra)

    # -- verdes -------------------------------------------------------------

    def test_subtest_de_t_run_renombrado_y_declarado_cierra(self):
        self.integrar({"run_test.go": RUN_RENOMBRADO}, review=review_citando(RUN))
        f = self.cerrado("--retirados", self.declarar([RUN]))
        medicion = f["mediciones_destino"][0]
        # Persistencia: el id COMPLETO, como hoy.
        self.assertEqual(medicion["retirados"], [RUN])
        self.assertEqual(len(medicion["retirados_sha256"]), 64)

    def test_subtest_de_tabla_renombrado_y_declarado_cierra(self):
        # Cita con el id entero `<paquete>::TestX/<segs>`.
        self.integrar({"tabla_test.go": TABLA_RENOMBRADA}, review=review_citando(TABLA, completo=True))
        f = self.cerrado("--retirados", self.declarar([TABLA]))
        self.assertEqual(f["mediciones_destino"][0]["retirados"], [TABLA])

    def test_subtest_anidado_renombrado_y_declarado_cierra(self):
        self.integrar({"anidado_test.go": ANIDADO_RENOMBRADO}, review=review_citando(ANIDADO))
        f = self.cerrado("--retirados", self.declarar([ANIDADO]))
        self.assertEqual(f["mediciones_destino"][0]["retirados"], [ANIDADO])

    def test_un_prefijo_declarado_cubre_sus_subtests(self):
        """Contrato 5: `TestAnidado/grupo` declarado cubre `TestAnidado/grupo/hoja_*`."""
        self.integrar({"anidado_test.go": ANIDADO_GRUPO_RENOMBRADO}, review=review_citando(GRUPO))
        f = self.cerrado("--retirados", self.declarar([GRUPO]))
        self.assertEqual(f["mediciones_destino"][0]["retirados"], [GRUPO])

    def test_las_tres_formas_juntas_y_primer_nivel_intacto(self):
        """Subtests y una baja de primer nivel en el mismo archivo de bajas."""
        self.integrar({"run_test.go": RUN_RENOMBRADO, "tabla_test.go": TABLA_RENOMBRADA,
                       "anidado_test.go": ANIDADO_RENOMBRADO, "padre_test.go": None},
                      review=review_citando(RUN, TABLA, ANIDADO) + "Baja de primer nivel: TestPadre.\n")
        f = self.cerrado("--retirados", self.declarar([RUN, TABLA, ANIDADO, f"{MOD}::TestPadre"]))
        self.assertEqual(sorted(f["mediciones_destino"][0]["retirados"]),
                         sorted([RUN, TABLA, ANIDADO, f"{MOD}::TestPadre"]))

    def test_check_manual_acepta_el_subtest_verificado(self):
        self.integrar({"run_test.go": RUN_RENOMBRADO}, review=review_citando(RUN))
        r = self.check()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("alcance incompleto", r.stdout)
        self.assertIn(RUN, r.stdout)
        r = self.check("--retirados", self.declarar([RUN]), "--microservicio", "alpha")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(RUN, r.stdout)

    # -- negativos ------------------------------------------------------------

    def test_negativos_sobre_una_integracion_amplia(self):
        """Una sola integracion con todos los casos; cada declaracion invalida se
        rechaza por SU motivo, sin tocar backlog ni documentos."""
        self.integrar({"run_test.go": RUN_RENOMBRADO, "tabla_test.go": TABLA_RENOMBRADA.replace(
                           '{"repetido", 2}', '{"repetido distinto", 2}'),
                       "anidado_test.go": ANIDADO_RENOMBRADO, "padre_test.go": None,
                       "armado_test.go": ARMADO_RECORTADO},
                      review=review_citando(RUN, TABLA, ANIDADO, VIVO, HIJO, CASO_ARMADO, DENTRO, NO_MEDIDO))
        retirados = str(self.retirados)
        with self.subTest("subtest no declarado"):
            salida = self.rechazado("desaparecidos")
            self.assertIn(RUN, salida)
            self.declarar([TABLA, ANIDADO])
            salida = self.rechazado("desaparecidos", "--retirados", retirados)
            self.assertIn(RUN, salida)
        with self.subTest("todavia medido en el destino"):
            self.declarar([VIVO])
            self.assertIn(VIVO, self.rechazado("se sigue midiendo en el destino", "--retirados", retirados))
        with self.subTest("padre borrado"):
            self.declarar([HIJO])
            salida = self.rechazado("su test padre TestPadre ya no se mide en el destino", "--retirados", retirados)
            self.assertIn(HIJO, salida)
        with self.subTest("sufijo #NN"):
            self.declarar([DUPLICADO])
            salida = self.rechazado("#NN", "--retirados", retirados)
            self.assertIn("repetido#01", salida)
        with self.subTest("no medido en la base"):
            self.declarar([NO_MEDIDO])
            self.assertIn(NO_MEDIDO, self.rechazado("no se midio en la base", "--retirados", retirados))
        with self.subTest("hoja armada en runtime"):
            self.declarar([CASO_ARMADO])
            salida = self.rechazado("no esta escrito en la base", "--retirados", retirados)
            self.assertIn("'caso_7'", salida)
        with self.subTest("segmento intermedio armado en runtime"):
            self.declarar([DENTRO])
            salida = self.rechazado("no esta escrito en la base", "--retirados", retirados)
            self.assertIn("'grupo_1'", salida)

    def test_declarado_pero_todavia_escrito_en_la_fuente_bloquea(self):
        """La fuente lo deja escrito tras un `if false`; un commit tardio del destino
        lo borra. La feature no lo borro: el destino no alcanza."""
        source, _ = self.integrar({"run_test.go": RUN_ESCONDIDO}, tardio={"run_test.go": RUN_RENOMBRADO},
                                  review=review_citando(RUN))
        salida = self.rechazado("sigue escrito en " + source[:12], "--retirados", self.declarar([RUN]))
        self.assertIn(RUN, salida)

    def test_declarado_pero_todavia_escrito_en_el_destino_bloquea(self):
        _, target = self.integrar({"run_test.go": RUN_RENOMBRADO}, tardio={"run_test.go": RUN_CONSTANTE},
                                  review=review_citando(RUN))
        self.rechazado("sigue escrito en " + target[:12], "--retirados", self.declarar([RUN]))

    def test_check_manual_rechaza_el_subtest_escondido(self):
        self.integrar({"run_test.go": RUN_ESCONDIDO}, review=review_citando(RUN))
        r = self.check("--retirados", self.declarar([RUN]), "--microservicio", "alpha")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("sigue escrito", r.stdout)

    def test_un_prefijo_no_cubre_un_descendiente_registrado_con_skip(self):
        """Review r2, P2-2: la baja de `TestAnidado/grupo` cubre lo que cuelga de ella;
        un descendiente que el destino todavia registra (skip) no es una baja."""
        hoja = f"{MOD}::TestAnidado/grupo/hoja_vieja"
        self.integrar({"anidado_test.go": ANIDADO_PLANO_SKIP}, review=review_citando(GRUPO))
        r = self.check("--retirados", self.declarar([GRUPO]), "--microservicio", "alpha")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn(f"{GRUPO} cubre subtests que el destino todavia registra (skip): {hoja}", r.stdout)
        self.rechazado("skip", "--retirados", self.declarar([GRUPO]))

    def test_un_prefijo_con_su_descendiente_medido_cierra(self):
        """Sin sobrebloqueo: el descendiente aplanado corre y se mide."""
        self.integrar({"anidado_test.go": ANIDADO_PLANO_MEDIDO}, review=review_citando(GRUPO))
        f = self.cerrado("--retirados", self.declarar([GRUPO]))
        self.assertEqual(f["mediciones_destino"][0]["retirados"], [GRUPO])

    def primer_nivel_registrado_con_skip(self, fuente):
        """Review r3, P3-7: el rechazo por registro vale para TODO id declarado."""
        padre = f"{MOD}::TestPadre"
        self.integrar({"padre_test.go": fuente},
                      review="## AC-1\nalpha/feature.txt:1\nBaja de primer nivel: TestPadre.\n")
        r = self.check("--retirados", self.declarar([padre]), "--microservicio", "alpha")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn(f"{padre} sigue registrado en el destino (skip)", r.stdout)
        self.rechazado("skip", "--retirados", self.declarar([padre]))

    def test_check_manual_rechaza_primer_nivel_registrado_con_skip_sin_gofmt(self):
        self.primer_nivel_registrado_con_skip(PADRE_SIN_GOFMT_SKIP)

    def test_check_manual_rechaza_primer_nivel_registrado_con_skip_indentado(self):
        self.primer_nivel_registrado_con_skip(PADRE_INDENTADO_SKIP)

    def registrado_con_skip(self, cambios):
        """Review r1, P2-1: el check manual es el unico verificador de --retirados
        en el flujo monorepo legacy; el close ya lo frena por el skip global."""
        self.integrar(cambios, review=review_citando(RUN))
        r = self.check("--retirados", self.declarar([RUN]), "--microservicio", "alpha")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn(f"{RUN} sigue registrado en el destino (skip)", r.stdout)
        self.rechazado("skip", "--retirados", self.declarar([RUN]))

    def test_check_manual_rechaza_el_subtest_registrado_con_skip_y_nombre_armado(self):
        self.registrado_con_skip({"run_test.go": RUN_SKIP_ARMADO})

    def test_check_manual_rechaza_el_subtest_registrado_con_skip_y_constante_no_test(self):
        self.registrado_con_skip({"run_test.go": RUN_SKIP_CONSTANTE, "casos.go": CASOS_NO_TEST})

    def test_un_test_go_symlink_bloquea_la_busqueda_de_literales(self):
        """Review r1, P3-1: el blob de un symlink es la ruta, no el codigo que Go
        compila; el literal tras `if false` quedaba invisible y la baja cerraba."""
        self.integrar({"fuentes/run.txt": RUN_ESCONDIDO, "run_test.go": Enlace("fuentes/run.txt")},
                      review=review_citando(RUN))
        salida = self.rechazado("es un symlink", "--retirados", self.declarar([RUN]))
        self.assertIn("run_test.go", salida)

    def test_un_test_go_symlink_bloquea_en_primer_nivel(self):
        """Lo mismo para `func TestX(` (git grep tampoco sigue el symlink): escondido
        tras un build tag en un *_test.go symlink, la baja de primer nivel cerraba."""
        self.integrar({"padre_test.go": None, "fuentes/padre.txt": "//go:build nunca\n\n" + PADRE_BASE,
                       "alias_test.go": Enlace("fuentes/padre.txt")},
                      review="## AC-1\nalpha/feature.txt:1\nBaja de primer nivel: TestPadre.\n")
        baja = self.declarar([f"{MOD}::TestPadre"])
        self.assertIn("alias_test.go", self.rechazado("es un symlink", "--retirados", baja))
        r = self.check("--retirados", baja, "--microservicio", "alpha")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("es un symlink", r.stdout)

    def test_review_sin_cita_bloquea_nombrando_el_id(self):
        self.integrar({"run_test.go": RUN_RENOMBRADO},
                      review="## AC-1\nalpha/feature.txt:1\nSe renombro un caso de TestRenombrado.\n")
        salida = self.rechazado("no cita", "--retirados", self.declarar([RUN]))
        self.assertIn(RUN, salida)

    def test_la_cita_solo_dentro_del_sello_no_cuenta(self):
        self.integrar({"run_test.go": RUN_RENOMBRADO},
                      review="## AC-1\nalpha/feature.txt:1\nSin mencion de las bajas.\n", por=corto(RUN))
        sello = [x for x in (self.root / "docs" / f"review-{self.FEATURE}.md").read_text().splitlines()
                 if x.startswith("Revisado:")]
        self.assertEqual(len(sello), 1)
        self.assertIn(corto(RUN), sello[0])
        self.rechazado("no cita", "--retirados", self.declarar([RUN]))

    def test_la_cita_es_de_palabra_completa(self):
        """Nombrar un subtest MAS PROFUNDO o un hermano con el mismo prefijo no cita el prefijo."""
        review = ("## AC-1\nalpha/feature.txt:1\n"
                  f"Se revisaron `{corto(ANIDADO)}` y `{corto(GRUPO)}_nuevo`.\n")
        self.integrar({"anidado_test.go": ANIDADO_GRUPO_RENOMBRADO}, review=review)
        salida = self.rechazado("no cita", "--retirados", self.declarar([GRUPO]))
        self.assertIn(GRUPO, salida)

    def test_formas_invalidas_no_autorizan_nada(self):
        self.integrar({"run_test.go": RUN_RENOMBRADO}, review=review_citando(RUN))
        casos = [
            ("segmento", [f"{MOD}::TestRenombrado/"]),
            ("segmento", [f"{MOD}::TestRenombrado//la_boleta_(39)_sigue_fuera_de_alcance"]),
            ("segmento", [RUN + "/"]),
            ("segmento", [f"{MOD}::TestRenombrado/la boleta"]),
            ("se declara", [f"{MOD}::testRenombrado/la_boleta_(39)_sigue_fuera_de_alcance"]),
            ("se declara", [f"{MOD}::/la_boleta_(39)_sigue_fuera_de_alcance"]),
            ("mezcla", [RUN, ["angular:app", "projects/app/src/x.spec.ts", "X hace algo"]]),
        ]
        for razon, bajas in casos:
            with self.subTest(razon=razon, bajas=bajas):
                self.declarar(bajas)
                self.rechazado(razon, "--retirados", str(self.retirados))


class SubtestsHistoricoTests(_Fixture):
    """Cierre historico: la misma forma, con semantica historica (escrito en la
    fuente, ausente del destino, y -- como toda baja historica -- agregado por la
    propia feature: ausente de la base)."""

    FEATURE = "15"
    VIEJO = CABECERA + 'func TestViejo(t *testing.T) {\n\tt.Run("caso previo", func(t *testing.T) {})\n}\n'
    ARCHIVOS = {"go.mod": BASE["go.mod"], "contract_test.go": BASE["contract_test.go"], "viejo_test.go": VIEJO}
    NUEVA = CABECERA + ('func TestFeatureNueva(t *testing.T) {\n'
                        '\tt.Run("caso viejo", func(t *testing.T) {})\n'
                        '\tt.Run("caso estable", func(t *testing.T) {})\n'
                        '}\n')
    VIEJO_AMPLIADO = VIEJO.replace('\tt.Run("caso previo"', '\tt.Run("caso agregado", func(t *testing.T) {})\n'
                                   '\tt.Run("caso previo"')
    CASO = f"{MOD}::TestFeatureNueva/caso_viejo"

    def integrar(self, posterior, review, extra=None):
        """#15 agrega TestFeatureNueva y un caso a TestViejo (y `extra`); una feature
        POSTERIOR aplica `posterior` sobre la misma rama (ya integrado: worktree == repo)."""
        self.aplicar(self.repo, {"feature_test.go": self.NUEVA, "viejo_test.go": self.VIEJO_AMPLIADO,
                                 "feature.txt": "fixture feature\n", **(extra or {})})
        source = self.commit(self.repo, "fixture: la feature 15")
        self.aplicar(self.repo, posterior)
        target = self.commit(self.repo, "fixture: una feature posterior")
        self.registrar(source, target, self.repo)
        self.sellar(review)
        return source, target

    def close(self, *extra):
        return self.cli("gate.py", "close", "--feature", self.FEATURE, "--status", "done", "--to", "develop",
                        "--integrated", "--historico", "--yes", "--motivo",
                        "Base preintegracion no medible con el contrato vigente", "--leccion",
                        "closure-contract", *extra)

    def test_subtest_historico_renombrado_y_declarado_cierra(self):
        self.integrar({"feature_test.go": self.NUEVA.replace('"caso viejo"', '"caso nuevo"')},
                      review_citando(self.CASO))
        f = self.cerrado("--retirados", self.declarar([self.CASO]))
        medicion = f["mediciones_destino"][0]
        self.assertEqual(medicion["modo"], "historico")
        self.assertEqual(medicion["retirados"], [self.CASO])

    def test_un_test_go_symlink_bloquea_la_enumeracion_historica(self):
        """Review r2, P3-5: git grep no lee detras de un *_test.go symlink. TestOculto,
        agregado por la feature y borrado despues SIN declararlo, escapaba a la
        garantia 4 y el cierre historico pasaba."""
        oculto = CABECERA + "func TestOculto(t *testing.T) {}\n"
        self.integrar({"oculto_test.go": None}, "## AC-1\nalpha/feature.txt:1\n",
                      extra={"fuentes/oculto.txt": oculto, "oculto_test.go": Enlace("fuentes/oculto.txt")})
        salida = self.rechazado("es un symlink")
        self.assertIn("oculto_test.go", salida)

    def test_subtest_historico_todavia_escrito_en_el_destino_bloquea(self):
        escondido = self.NUEVA.replace('\tt.Run("caso viejo", func(t *testing.T) {})\n',
                                       '\tif false {\n\t\tt.Run("caso viejo", func(t *testing.T) {})\n\t}\n')
        _, target = self.integrar({"feature_test.go": escondido}, review_citando(self.CASO))
        salida = self.rechazado("sigue escrito en el destino " + target[:12], "--retirados",
                                self.declarar([self.CASO]))
        self.assertIn(self.CASO, salida)

    def test_subtest_historico_que_ya_estaba_en_la_base_bloquea(self):
        caso = f"{MOD}::TestViejo/caso_previo"
        self.integrar({"viejo_test.go": self.VIEJO_AMPLIADO.replace('"caso previo"', '"caso posterior"')},
                      review_citando(caso))
        salida = self.rechazado("ya estaba escrito en la base", "--retirados", self.declarar([caso]))
        self.assertIn(caso, salida)

    def test_subtest_historico_con_el_padre_borrado_bloquea(self):
        caso = f"{MOD}::TestViejo/caso_agregado"
        self.integrar({"viejo_test.go": None}, review_citando(caso))
        salida = self.rechazado("padre", "--retirados", self.declarar([caso]))
        self.assertIn(caso, salida)

    def test_subtest_historico_que_la_fuente_no_escribe_bloquea(self):
        """Sin base medida, la fuente es la unica prueba de que el subtest existio."""
        sin_literal = f"{MOD}::TestFeatureNueva/no_existe"
        sin_padre = f"{MOD}::TestNoExiste/caso_viejo"
        self.integrar({"feature_test.go": self.NUEVA.replace('"caso viejo"', '"caso nuevo"')},
                      review_citando(sin_literal, sin_padre))
        for razon, item in (("no esta escrito en la fuente", sin_literal),
                            ("su test padre TestNoExiste no esta definido en la fuente", sin_padre)):
            with self.subTest(item=item):
                self.assertIn(item, self.rechazado(razon, "--retirados", self.declarar([item])))

    def test_subtest_historico_sin_cita_bloquea(self):
        self.integrar({"feature_test.go": self.NUEVA.replace('"caso viejo"', '"caso nuevo"')},
                      "## AC-1\nalpha/feature.txt:1\nSin mencion de la baja.\n")
        self.rechazado("no cita", "--retirados", self.declarar([self.CASO]))


class LiteralesGoTests(unittest.TestCase):
    """«Escrito» = un literal de cadena Go cuyo texto, reescrito como testing, es
    el segmento. Los esperados salen de `go test -json` real (Go 1.27)."""

    def test_reescribe_como_testing_rewrite(self):
        casos = {
            "409 in_progress es transitorio": "409_in_progress_es_transitorio",
            "la boleta (39) sigue": "la_boleta_(39)_sigue",
            "tab\there": "tab_here", "nbsp\u00a0x": "nbsp_x", "bell\a": "bell\\a",
            "nul\x00": "nul\\x00", "del\x7f": "del\\x7f", "zw\u200bx": "zw\\u200bx",
            "ñandú 🍞": "ñandú_🍞", "soft\u00adhyphen": "soft\\u00adhyphen",
            "linea\u2028sep": "linea_sep", "tag\U000e0001": "tag\\U000e0001",
            "cr\rlf\nvt\vff\f": "cr_lf_vt_ff_", "ideo\u3000x": "ideo_x", "en\u2002x": "en_x",
            "a/b": "a/b",
        }
        for crudo, esperado in casos.items():
            with self.subTest(crudo=crudo):
                self.assertEqual(retiros.reescribir(crudo), esperado)

    def test_literales_de_un_fuente_go(self):
        fuente = (
            'package x\n'
            "var r = '\"'  // una runa con comilla no desincroniza\n"
            "var r2, s2 = '\"', \"tras la runa\"\n"
            'var a = "uno \\"dos\\" \\t tres"\n'
            'var b = `crudo "con" comillas\r\n y salto`\n'
            'var c = "oct\\101\\x41 \\u00e9 \\U0001F35E"\n'
            'var d = "bad\\xffbyte" + "trunc\\xe2\\x82x"\n'
            'var e = "no // es comentario"\n'
            '// comentado: t.Run("en comentario", nil)\n'
            '/* bloque: {"en bloque", 1} */\n'
            "var f = '\\''\n"
            'var g = "despues de runas"\n'
        )
        literales = retiros.literales_go(fuente)
        for esperado in ("tras la runa", 'uno "dos" \t tres', 'crudo "con" comillas\n y salto', "octAA é 🍞",
                         "bad\ufffdbyte", "trunc\ufffd\ufffdx", "no // es comentario",
                         "en comentario", "en bloque", "despues de runas"):
            with self.subTest(esperado=esperado):
                self.assertIn(esperado, literales)
        self.assertNotIn('"', literales)  # la runa no es una cadena

    def test_un_literal_con_barra_cubre_varios_segmentos(self):
        # t.Run("a/b") inside TestX se mide `TestX/a/b`: el literal nombra los dos.
        self.assertEqual(retiros.cubiertos({"a/b"}, ["a", "b"]), {0, 1})
        self.assertEqual(retiros.cubiertos({"b"}, ["a", "b"]), {1})
        self.assertEqual(retiros.cubiertos({"a"}, ["a", "b"]), {0})
        self.assertEqual(retiros.cubiertos({"b/c"}, ["a", "b"]), set())


class CitaSubtestTests(unittest.TestCase):
    """Contrato 4: el id `TestX/<segs>` como palabra completa en una linea que no
    sea la del sello, o el id entero. El primer nivel conserva su regla."""

    SELLO = ("Revisado: approved · 2026-09-28T00:00:00Z · TestX/a y pkg::TestX/b · "
             "estampado por gate.py revision")

    def falta(self, texto, *ids):
        return retiros.sin_cita(texto, {tuple(i.split("::", 1)) for i in ids})

    def test_formas_que_citan(self):
        for linea in ("Baja: TestX/a.", "Baja: `TestX/a`, revisada.", "(TestX/a)", "«TestX/a»",
                      "| `pkg::TestX/a` | ok |", "pkg::TestX/a", "**TestX/a**:"):
            with self.subTest(linea=linea):
                self.assertEqual(self.falta(linea + "\n", "pkg::TestX/a"), [])

    def test_formas_que_no_citan(self):
        for linea in ("TestX/a/b", "TestX/a_b", "TestX/ab", "TestX/a#01", "TestX/a.go", "TestX/a(1)",
                      "otroTestX/a", "OtroTest/TestX/a", "otro/pkg::TestX/a", "TestX a", "TestX"):
            with self.subTest(linea=linea):
                self.assertEqual(self.falta(linea + "\n", "pkg::TestX/a"), ["pkg::TestX/a"])

    def test_el_sello_no_cita_un_subtest(self):
        self.assertEqual(self.falta(self.SELLO + "\n", "pkg::TestX/a", "pkg::TestX/b"),
                         ["pkg::TestX/a", "pkg::TestX/b"])

    def test_el_primer_nivel_conserva_su_regla(self):
        # Palabra en cualquier parte del texto, sello incluido: sin cambios.
        self.assertEqual(self.falta(self.SELLO.replace("TestX/a", "TestY") + "\n", "pkg::TestY"), [])
        self.assertEqual(self.falta("ver TestY/sub\n", "pkg::TestY"), [])
        self.assertEqual(self.falta("TestYZ\n", "pkg::TestY"), ["pkg::TestY"])


if __name__ == "__main__":
    unittest.main()
