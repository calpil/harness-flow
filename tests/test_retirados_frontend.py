"""Bajas de tests declaradas en destinos FRONTEND. FIXTURE: Git, Angular y Node reales.

Las garantias son las mismas que en Go (tests/test_retirados.py): medida en la
base, borrada por la feature en su delta, citada en el review sellado. Aqui el id
es el que mide el runner (`[proyecto, archivo, nombre completo]`) y "borrada" se
comprueba sobre las DECLARACIONES del spec, no sobre una linea de texto.

Los controles negativos atraviesan el CLI real (`gate.py close` y
`postmerge_frontend.py check`): exigen exit != 0 con su motivo y documentos
byte-identicos, no solo una funcion interna en rojo.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import test_frontend_runner as frontend
from test_frontend_runner import SCRIPTS, NODE_FILES

sys.path.insert(0, str(SCRIPTS))
import retiros  # noqa: E402  el parser de declaraciones tambien se prueba en proceso
from multirepo import Invalid  # noqa: E402

SPEC = 'projects/app/src/retirado.spec.ts'
MOVIDO = 'projects/app/src/movido.spec.ts'
SUITE = 'CafeteriasApi'
HOJA = '`me` es POST porque VINCULA, no solo consulta'
NOMBRE = SUITE + ' ' + HOJA
VIVO = SUITE + ' sigue vivo'
LEGAL = 'versiones legales vigentes'
GO_CMD = 'go test -tags integration -count=1 -json ./...'

BAJA_BORRADA = ['angular:app', SPEC, NOMBRE]
BAJA_MOVIDA = ['angular:app', MOVIDO, LEGAL]
BAJAS = [BAJA_BORRADA, BAJA_MOVIDA]

CABECERA = "import {describe, it, expect} from 'vitest';\n"
BASE_SPEC = (CABECERA + "describe('" + SUITE + "', () => {\n"
             "  it('" + HOJA + "', () => expect(1).toBe(1));\n"
             "  it('sigue vivo', () => expect(1).toBe(1));\n"
             "});\n")
SIN_LA_BAJA = (CABECERA + "describe('" + SUITE + "', () => {\n"
               "  it('sigue vivo', () => expect(1).toBe(1));\n"
               "});\n")
BASE_MOVIDO = ("import {test, expect} from 'vitest';\n"
               "test('" + LEGAL + "', () => expect(1).toBe(1));\n")
# Titulo CONCATENADO en runtime: ni el parser ni la busqueda de literales lo ven
# (limite conocido) y el test sigue corriendo con el mismo id: lo caza la medicion.
TITULO_DINAMICO = (CABECERA + "const vivo = 'sigue' + ' vivo';\n"
                   "describe('" + SUITE + "', () => {\n"
                   "  it(vivo, () => expect(1).toBe(1));\n"
                   "});\n")
# El test SIGUE en el archivo con su titulo literal; un wrapper no-op no lo
# registra, asi que tampoco lo mide el destino. No es una baja (P3-1 del review).
WRAPPER_NOOP = (CABECERA
                + "const itSi = (c: boolean) => (c ? it : (_n: string, _f: () => void) => {});\n"
                + "describe('" + SUITE + "', () => {\n"
                  "  itSi(false)('" + HOJA + "', () => expect(1).toBe(1));\n"
                  "  it('sigue vivo', () => expect(1).toBe(1));\n"
                  "});\n")
# El mismo wrapper con un apostrofo suelto ANTES: emparejar comillas por todo el
# archivo se desincroniza y dejaba de ver el titulo (R2-1 del review).
WRAPPER_TRAS_APOSTROFO = WRAPPER_NOOP.replace(CABECERA, CABECERA + "// the user's cart keeps IVA\n", 1)
# Dos titulos hoja distintos donde uno es sufijo del otro: la hoja sale de la
# base medida, no de adivinar el sufijo del nombre completo.
HOMONIMOS = (CABECERA + "describe('" + SUITE + "', () => {\n"
             "  it('es POST', () => expect(1).toBe(1));\n"
             "  it('POST', () => expect(1).toBe(1));\n"
             "});\n")
HOMONIMOS_SIN_LARGO = (CABECERA + "describe('" + SUITE + "', () => {\n"
                       "  it('POST', () => expect(1).toBe(1));\n"
                       "});\n")
CADA = (CABECERA + "describe('" + SUITE + "', () => {\n"
        "  it.each([1, 2])('cada %s', () => expect(1).toBe(1));\n"
        "  it('sigue vivo', () => expect(1).toBe(1));\n"
        "});\n")

REVIEW = ('## AC-1\nfront/feature.txt:1\n'
          "Baja revisada: '" + HOJA + "' en " + SPEC + " (el contrato paso a GET).\n"
          "Baja revisada: '" + LEGAL + "' en " + MOVIDO + " (movido a otro proyecto).\n")


def spec_con(modificador):
    """El mismo archivo con la baja escondida tras un modificador, no borrada."""
    return BASE_SPEC.replace("  it('" + HOJA + "'", '  ' + modificador + "('" + HOJA + "'")


class FrontendRetirosTests(unittest.TestCase):
    def setUp(self):
        t = frontend.FrontendFixture('runTest')
        t.setUp()
        self.addCleanup(t.doCleanups)
        self.t = t
        self.root = t.home / 'project'
        (self.root / 'docs').mkdir(parents=True)
        (self.root / 'harness/progress').mkdir(parents=True)
        repo = self.root / 'front'
        t.repo.rename(repo)
        t.repo = repo
        t.env['HARNESS_SKILLS_DIR'] = str(t.home / 'skills')
        lesson = t.home / 'skills/closure-contract/SKILL.md'
        lesson.parent.mkdir(parents=True)
        lesson.write_text('---\nname: closure-contract\ndescription: Fixture\n---\n')
        t.write(SPEC, BASE_SPEC)
        t.write(MOVIDO, BASE_MOVIDO)
        self.base_sha = t.commit('fixture: specs retirables')
        self.map = t.home / 'postmerge.json'
        self.manifest = t.home / 'manifest.json'
        self.retirados = t.home / 'retirados.json'
        self.backlog = self.root / 'harness/feature_list.json'
        self.backlog.write_text(json.dumps(dict(
            project='fixture', rules={'rutas_protegidas': ['docs/constitution.md']},
            features=[dict(id=7, name='Frontend fixture', status='in_progress',
                           microservicios=['front'])])))
        (self.root / 'docs/spec-feature-7-frontend-fixture.md').write_text(
            'Estado: draft\n- AC-1: Given frontend When integrated Then measured\n'
            'Comando: `git -C front merge-base --is-ancestor HEAD HEAD`\n')
        (self.root / 'docs/impl-7.md').write_text('## AC-1\nfront/feature.txt:1\n')
        (self.root / 'docs/constitution.md').write_text('User contract\n')
        (self.root / 'harness/progress/current-7.md').write_text('Fixture progress\n')
        self.ok('gate.py', 'approve-spec', '--feature', '7', '--yes', '--por', 'Fixture')
        self.medir_base()

    # --- utilidades de fixture -------------------------------------------------

    def medir_base(self):
        self.t.base.unlink(missing_ok=True)
        self.t.measured_base()
        self.map.write_text(json.dumps(dict(version=1, feature='7',
                                            bases={'front': str(self.t.base)})))

    def command(self, script, *args):
        argv = [sys.executable, '-B', str(SCRIPTS / script), *args]
        r = subprocess.run(argv, cwd=self.root, env=self.t.env, capture_output=True,
                           text=True, timeout=600)
        directory = os.environ.get('HARNESS_TEST_FRONTEND_LOGS')
        if directory:
            p = Path(directory)
            p.mkdir(parents=True, exist_ok=True)
            with (p / (self.id() + '.jsonl')).open('a') as f:
                f.write(json.dumps(dict(argv=argv, exit=r.returncode, stdout=r.stdout,
                                        stderr=r.stderr)) + '\n')
            for artifact in self.t.home.glob('*.evidence.json'):
                shutil.copy2(artifact, p / (self.id() + '.' + artifact.name))
        return r

    def ok(self, script, *args):
        r = self.command(script, *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def aplicar(self, delta):
        for ruta, contenido in (delta or {}).items():
            if contenido is None:
                (self.t.repo / ruta).unlink()
            else:
                self.t.write(ruta, contenido)

    def integrar(self, delta, tardio=None, review=REVIEW, extra=(), por='Fixture reviewer'):
        """Aplica el delta de la feature (y un commit tardio opcional del destino)."""
        t = self.t
        t.write('feature.txt', 'feature fixture\n')
        self.aplicar(delta)
        source = t.commit('fixture: delta de la feature')
        target = source
        if tardio is not None:
            self.aplicar(tardio)
            target = t.commit('fixture: commit tardio del destino')
        self.row = dict(microservicio='front', repo=str(t.repo), worktree=str(t.repo),
                        base_sha=self.base_sha, source_sha=source, target_sha=target,
                        target_branch='develop')
        (self.root / 'docs/review-7.md').write_text(review)
        self.manifest.write_text(json.dumps(dict(version=1, feature='7',
                                                 repos=[self.row, *extra])))
        self.ok('worktree.py', 'register', '--feature', '7', '--manifest', str(self.manifest))
        self.ok('gate.py', 'verify', '--feature', '7')
        self.ok('gate.py', 'revision', '--feature', '7', '--veredicto', 'approved', '--por', por)

    def declarar(self, bajas, feature='7', micro='front'):
        self.retirados.write_text(json.dumps(
            {'version': 1, 'feature': feature, 'retirados': {micro: bajas}}))
        return str(self.retirados)

    def close(self, *extra):
        return self.command('gate.py', 'close', '--feature', '7', '--status', 'done',
                            '--to', 'develop', '--integrated', '--leccion', 'closure-contract',
                            '--postmerge', str(self.map), *extra)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for base in (self.root / 'docs', self.root / 'harness')
                for p in base.rglob('*') if p.is_file()}

    def rechazado(self, razon, *extra):
        before = self.snapshot()
        r = self.close(*extra)
        salida = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0, salida)
        self.assertIn(razon, salida)
        self.assertNotIn('Traceback', r.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertNotEqual(json.loads(self.backlog.read_text())['features'][0]['status'], 'done')
        return r

    def faltantes(self, salida):
        lineas = [x for x in salida.splitlines() if 'desaparecidos u omitidos:' in x]
        self.assertEqual(len(lineas), 1, salida)
        return lineas[0].split('desaparecidos u omitidos:', 1)[1]

    def check(self, *extra):
        return self.command('postmerge_frontend.py', 'check', '--repo', str(self.t.repo),
                            '--base', str(self.t.base), *extra)

    # --- verdes ----------------------------------------------------------------

    def test_baja_borrada_y_archivo_movido_citados_cierran(self):
        self.integrar({SPEC: SIN_LA_BAJA, MOVIDO: None})
        r = self.close('--retirados', self.declarar(BAJAS))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('retirado por la feature', r.stdout)
        f = json.loads(self.backlog.read_text())['features'][0]
        self.assertEqual(f['status'], 'done')
        recibo = f['mediciones_destino'][0]
        self.assertEqual(sorted(recibo['retirados']), sorted(BAJAS))
        self.assertEqual(recibo['retirados_archivo'], str(self.retirados.resolve()))
        self.assertEqual(len(recibo['retirados_sha256']), 64)
        self.assertEqual(recibo['delta']['new'], [])
        medidos = {tuple(x['id']) for x in recibo['measurement']['results']}
        self.assertNotIn(tuple(BAJA_BORRADA), medidos)
        self.assertNotIn(tuple(BAJA_MOVIDA), medidos)
        self.assertIn(('angular:app', SPEC, VIVO), medidos)

    def test_baja_de_node_test_borrada_cierra(self):
        vivo = (self.t.repo / NODE_FILES[0]).read_text()
        self.t.write(NODE_FILES[0], vivo + "test('inventario legado', () => assert.equal(1, 1));\n")
        self.base_sha = self.t.commit('fixture: test node retirable')
        self.medir_base()
        baja = ['node:test', NODE_FILES[0], 'inventario legado']
        self.integrar({NODE_FILES[0]: vivo},
                      review="## AC-1\nfront/feature.txt:1\nBaja: 'inventario legado' en "
                             + NODE_FILES[0] + ', el inventario portable ya no lo cubre.\n')
        r = self.close('--retirados', self.declarar([baja]))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        recibo = json.loads(self.backlog.read_text())['features'][0]['mediciones_destino'][0]
        self.assertEqual(recibo['retirados'], [baja])

    # --- controles negativos ---------------------------------------------------

    def test_baja_no_declarada_sigue_bloqueando_y_la_nombra(self):
        self.integrar({SPEC: SIN_LA_BAJA, MOVIDO: None})
        r = self.rechazado('desaparecidos')
        self.assertIn(NOMBRE, self.faltantes(r.stdout + r.stderr))
        self.assertIn(LEGAL, self.faltantes(r.stdout + r.stderr))
        r = self.rechazado('desaparecidos', '--retirados', self.declarar([BAJA_BORRADA]))
        faltan = self.faltantes(r.stdout + r.stderr)
        self.assertIn(LEGAL, faltan)
        self.assertNotIn(NOMBRE, faltan)

    def test_no_medido_en_la_base_no_es_baja(self):
        self.integrar({SPEC: SIN_LA_BAJA, MOVIDO: None})
        ajena = ['angular:app', SPEC, SUITE + ' nunca existio']
        self.rechazado('no se midio en la base', '--retirados', self.declarar(BAJAS + [ajena]))

    def test_test_que_sigue_midiendose_no_es_baja(self):
        """El parser no ve un titulo armado en runtime; la medicion si lo ve."""
        self.integrar({SPEC: TITULO_DINAMICO, MOVIDO: None},
                      review=REVIEW + "Baja revisada: 'sigue vivo' en " + SPEC + '\n')
        vivo = ['angular:app', SPEC, VIVO]
        self.rechazado('se sigue midiendo en el destino', '--retirados',
                       self.declarar(BAJAS + [vivo]))

    def test_sigue_declarado_en_la_fuente_no_es_baja(self):
        # El destino los borro en un commit posterior: no los borro la feature.
        self.integrar({}, tardio={SPEC: SIN_LA_BAJA, MOVIDO: None})
        self.rechazado('sigue declarado', '--retirados', self.declarar(BAJAS))

    def test_skip_todo_only_y_xit_no_son_baja(self):
        for modificador in ('it.skip', 'it.todo', 'it.only', 'xit'):
            with self.subTest(modificador=modificador):
                self.t.git('reset', '--hard', self.base_sha)
                self.integrar({SPEC: spec_con(modificador), MOVIDO: None})
                self.rechazado('sigue declarado', '--retirados', self.declarar(BAJAS))

    def test_renombrar_solo_el_describe_no_es_baja(self):
        self.integrar({SPEC: BASE_SPEC.replace(SUITE, SUITE + 'V2'), MOVIDO: None})
        self.rechazado('sigue declarado', '--retirados', self.declarar(BAJAS))

    def test_wrapper_que_no_registra_el_test_no_es_baja(self):
        """P3-1: el test sigue en el archivo con su titulo, pero no corre."""
        self.integrar({SPEC: WRAPPER_NOOP, MOVIDO: None})
        r = self.rechazado('sigue declarado', '--retirados', self.declarar(BAJAS))
        self.assertIn(HOJA, r.stdout + r.stderr)
        self.assertIn("itSi(false)('" + HOJA + "'", (self.t.repo / SPEC).read_text())

    def test_wrapper_tras_un_apostrofo_suelto_sigue_sin_ser_baja(self):
        """R2-1: un apostrofo previo desincronizaba el emparejado de comillas."""
        self.integrar({SPEC: WRAPPER_TRAS_APOSTROFO, MOVIDO: None})
        r = self.rechazado('sigue declarado', '--retirados', self.declarar(BAJAS))
        self.assertIn(HOJA, r.stdout + r.stderr)
        texto = (self.t.repo / SPEC).read_text()
        self.assertIn("itSi(false)('" + HOJA + "'", texto)
        self.assertIn("the user's cart", texto)

    def test_el_destino_que_vuelve_a_declarar_la_baja_bloquea(self):
        """La fuente lo borro, pero un commit tardio del destino lo redeclara."""
        revive = (SIN_LA_BAJA.rstrip('\n') + "\ndescribe('" + SUITE + "V2', () => {\n"
                  "  it('" + HOJA + "', () => expect(1).toBe(1));\n});\n")
        self.integrar({SPEC: SIN_LA_BAJA, MOVIDO: None}, tardio={SPEC: revive})
        self.rechazado('sigue declarado', '--retirados', self.declarar(BAJAS))

    def test_review_sin_cita_bloquea(self):
        self.integrar({SPEC: SIN_LA_BAJA, MOVIDO: None},
                      review='## AC-1\nfront/feature.txt:1\nSin mencion de las bajas.\n')
        self.rechazado('no cita', '--retirados', self.declarar(BAJAS))

    def test_review_que_cita_la_hoja_sin_la_ruta_bloquea(self):
        self.integrar({SPEC: SIN_LA_BAJA, MOVIDO: None},
                      review="## AC-1\nfront/feature.txt:1\nBajas: '" + HOJA + "' y '"
                             + LEGAL + "'\n")
        self.rechazado('no cita', '--retirados', self.declarar(BAJAS))

    def test_la_hoja_suelta_en_otra_palabra_no_es_cita(self):
        """P2-1 del review: 'ok' dentro de 'token' no nombra la baja."""
        self.t.write(SPEC, CABECERA + "describe('Login', () => {\n"
                     "  it('ok', () => expect(1).toBe(1));\n"
                     "  it('falla bien', () => expect(1).toBe(1));\n});\n")
        self.base_sha = self.t.commit('fixture: login')
        self.medir_base()
        sin_ok = CABECERA + "describe('Login', () => {\n  it('falla bien', () => expect(1).toBe(1));\n});\n"
        review = ('## AC-1\nfront/feature.txt:1\n'
                  'Evidencia revisada en ' + SPEC + ' (token renovado).\n')
        self.integrar({SPEC: sin_ok}, review=review)
        self.rechazado('no cita', '--retirados', self.declarar([['angular:app', SPEC, 'Login ok']]))

    def test_la_cita_partida_en_dos_lineas_no_cuenta(self):
        review = ("## AC-1\nfront/feature.txt:1\nArchivo tocado: " + SPEC + "\n"
                  "Baja: '" + HOJA + "'\n")
        self.integrar({SPEC: SIN_LA_BAJA, MOVIDO: None}, review=review)
        self.rechazado('no cita', '--retirados', self.declarar([BAJA_BORRADA]))

    def test_el_sello_no_admite_saltos_de_linea_en_por(self):
        """R2-2: `--por` va DENTRO del sello; un salto ahi inyecta una cita."""
        self.integrar({SPEC: SIN_LA_BAJA, MOVIDO: None},
                      review='## AC-1\nfront/feature.txt:1\nSin mencion de bajas.\n')
        sellado = (self.root / 'docs/review-7.md').read_text()
        r = self.command('gate.py', 'revision', '--feature', '7', '--veredicto', 'approved',
                         '--por', "\n" + SPEC + " '" + HOJA + "'\n")
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('--por', r.stdout + r.stderr)
        self.assertNotIn('Traceback', r.stderr)
        # El review sellado no cambio: el sello viejo sigue intacto.
        self.assertEqual((self.root / 'docs/review-7.md').read_text(), sellado)
        self.rechazado('no cita', '--retirados', self.declarar([BAJA_BORRADA]))

    def test_la_cita_en_la_linea_del_sello_no_cuenta(self):
        """El sello lo estampa el gate; no es el revisor nombrando la baja."""
        self.integrar({SPEC: SIN_LA_BAJA, MOVIDO: None},
                      review='## AC-1\nfront/feature.txt:1\nSin mencion de las bajas.\n',
                      por="'" + HOJA + "' en " + SPEC)
        sello = [x for x in (self.root / 'docs/review-7.md').read_text().splitlines()
                 if x.startswith('Revisado:')]
        self.assertEqual(len(sello), 1)
        self.assertIn(SPEC, sello[0])
        self.assertIn("'" + HOJA + "'", sello[0])
        self.rechazado('no cita', '--retirados', self.declarar([BAJA_BORRADA]))

    def test_declaraciones_invalidas_no_autorizan_nada(self):
        self.integrar({SPEC: SIN_LA_BAJA, MOVIDO: None})
        casos = [
            ('destino frontend', dict(bajas=['fixture.invalid/app::TestRetirado'])),
            ('mezcla', dict(bajas=BAJAS + ['fixture.invalid/app::TestRetirado'])),
            ('se declara', dict(bajas=[['angular:app', SPEC]])),
            ('se declara', dict(bajas=[['angular:app', SPEC, NOMBRE, 'extra']])),
            ('se declara', dict(bajas=[['angular:app', SPEC, '']])),
            ('se declara', dict(bajas=[['angular:app', SPEC, 7]])),
            ('se declara', dict(bajas=[['karma:app', SPEC, NOMBRE]])),
            ('se declara', dict(bajas=[['angular:app', '/' + SPEC, NOMBRE]])),
            ('se declara', dict(bajas=[['angular:app', 'projects/app/../x.spec.ts', NOMBRE]])),
            ('se declara', dict(bajas=[['angular:otro', SPEC, NOMBRE]])),
            ('se declara', dict(bajas=[['angular:app', SPEC, NOMBRE + '\nhoja']])),
            ('duplicada', dict(bajas=[BAJA_BORRADA, list(BAJA_BORRADA)])),
            ('vacia', dict(bajas=[])),
            ('otra feature', dict(bajas=BAJAS, feature='8')),
            ('ajeno', dict(bajas=BAJAS, micro='otro')),
        ]
        for razon, kwargs in casos:
            with self.subTest(razon=razon, bajas=kwargs.get('bajas')):
                self.rechazado(razon, '--retirados', self.declarar(**kwargs))

    def backend_go(self):
        """Repo Go real de fixture, con base medida y un test retirado."""
        backend = self.root / 'backend'
        backend.mkdir()
        self.t.env.update(GOPROXY='off', GOSUMDB='off', GOTOOLCHAIN='local', GOWORK='off',
                          GOCACHE=os.environ.get('HARNESS_TEST_GOCACHE',
                                                 str(self.t.home / 'go-cache')))

        def git(*args):
            r = subprocess.run(['git', '-C', str(backend), *args], env=self.t.env,
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stdout.strip()

        git('init', '-b', 'develop')
        (backend / 'go.mod').write_text('module fixture.invalid/backend\n\ngo 1.22\n')
        (backend / 'contract_test.go').write_text(
            'package contract\nimport "testing"\nfunc TestHealthy(t *testing.T) {}\n')
        (backend / 'legacy_test.go').write_text(
            'package contract\nimport "testing"\nfunc TestLegacy(t *testing.T) {}\n')
        git('add', '.')
        git('commit', '-m', 'fixture base')
        base_go = git('rev-parse', 'HEAD')
        base_path = self.t.home / 'backend-base.json'
        self.ok('postmerge_medido.py', 'base', '--repo', str(backend), '--cmd', GO_CMD,
                '--guardar', str(base_path))
        (backend / 'legacy_test.go').unlink()
        git('add', '.')
        git('commit', '-m', 'fixture: retiro Go')
        tip = git('rev-parse', 'HEAD')
        return backend, base_go, base_path, tip

    def test_mapa_mixto_exige_el_formato_de_cada_destino(self):
        backend, base_go, base_path, tip = self.backend_go()
        fila = dict(microservicio='backend', repo=str(backend), worktree=str(backend),
                    base_sha=base_go, source_sha=tip, target_sha=tip, target_branch='develop')
        data = json.loads(self.backlog.read_text())
        data['features'][0]['microservicios'].append('backend')
        self.backlog.write_text(json.dumps(data))
        self.map.write_text(json.dumps(dict(version=1, feature='7', bases={
            'front': str(self.t.base), 'backend': str(base_path)})))
        self.integrar({SPEC: SIN_LA_BAJA, MOVIDO: None}, extra=[fila],
                      review=REVIEW + 'Baja Go revisada: TestLegacy en backend/legacy_test.go\n')
        cruzado = self.t.home / 'cruzado.json'
        cruzado.write_text(json.dumps({'version': 1, 'feature': '7', 'retirados': {
            'front': BAJAS, 'backend': [['angular:app', SPEC, NOMBRE]]}}))
        self.rechazado('destino Go', '--retirados', str(cruzado))
        mixto = self.t.home / 'mixto.json'
        mixto.write_text(json.dumps({'version': 1, 'feature': '7', 'retirados': {
            'front': BAJAS, 'backend': ['fixture.invalid/backend::TestLegacy']}}))
        r = self.close('--retirados', str(mixto))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        recibos = json.loads(self.backlog.read_text())['features'][0]['mediciones_destino']
        porservicio = {x['integration']['microservicio']: x for x in recibos}
        self.assertEqual(sorted(porservicio['front']['retirados']), sorted(BAJAS))
        self.assertEqual(porservicio['backend']['retirados'],
                         ['fixture.invalid/backend::TestLegacy'])

    # --- check manual ----------------------------------------------------------

    def test_check_manual_acepta_la_misma_baja_verificada(self):
        self.integrar({SPEC: SIN_LA_BAJA, MOVIDO: None})
        self.t.expect(self.check(), 2, 'desaparecidos')
        archivo = self.declarar(BAJAS)
        r = self.check('--retirados', archivo, '--microservicio', 'front')
        self.t.expect(r, 0, 'retirado por la feature')
        self.assertIn(LEGAL, r.stdout)
        self.t.expect(self.check('--retirados', archivo), 2, '--microservicio')
        self.t.expect(self.check('--retirados', archivo, '--microservicio', 'otro'),
                      2, 'no declara bajas')

    def test_check_manual_rechaza_una_baja_que_sigue_declarada(self):
        self.integrar({SPEC: spec_con('it.skip'), MOVIDO: None})
        r = self.check('--retirados', self.declarar(BAJAS), '--microservicio', 'front')
        self.t.expect(r, 2, 'sigue declarado')
        self.assertNotIn('$ [', r.stdout)

    def test_check_manual_rechaza_ids_de_go(self):
        self.integrar({SPEC: SIN_LA_BAJA, MOVIDO: None})
        archivo = self.declarar(['fixture.invalid/app::TestRetirado'])
        r = self.check('--retirados', archivo, '--microservicio', 'front')
        self.t.expect(r, 2, 'destino frontend')

    def test_check_manual_rechaza_una_baja_que_se_sigue_midiendo(self):
        """El CLI manual aplica la misma ausencia en el destino que el cierre."""
        self.integrar({SPEC: TITULO_DINAMICO, MOVIDO: None})
        vivo = ['angular:app', SPEC, VIVO]
        archivo = self.declarar(BAJAS + [vivo])
        r = self.check('--retirados', archivo, '--microservicio', 'front')
        self.t.expect(r, 2, 'se sigue midiendo en el destino')
        self.assertNotIn('retirado por la feature', r.stdout)

    def test_check_manual_go_rechaza_ids_de_frontend_antes_de_medir(self):
        backend, base_go, base_path, tip = self.backend_go()
        archivo = self.declarar([['angular:app', SPEC, NOMBRE]], micro='backend')
        r = self.command('postmerge_medido.py', 'check', '--repo', str(backend),
                         '--base', str(base_path), '--cmd', GO_CMD,
                         '--retirados', archivo, '--microservicio', 'backend')
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn('destino Go', r.stdout + r.stderr)
        self.assertNotIn('Traceback', r.stderr)
        self.assertNotIn('$ (cd', r.stdout)  # ni una suite corrida para rechazarlo

    # --- parser de declaraciones y guardas internas (en proceso) ---------------

    def test_el_parser_reconoce_las_formas_de_declarar_un_test(self):
        casos = {
            "it('simple', fn);": {'simple'},
            'test("doble", fn);': {'doble'},
            'it(`plantilla`, fn);': {'plantilla'},
            "it.skip('saltado', fn);": {'saltado'},
            "it.only('solo', fn);": {'solo'},
            "test.todo('pendiente');": {'pendiente'},
            "xit('equis', fn);": {'equis'},
            "fit('efe', fn);": {'efe'},
            "xtest('equis test', fn);": {'equis test'},
            "it.concurrent.skip('encadenado', fn);": {'encadenado'},
            "it.each([1, 2])('cada %s', fn);": {'cada %s'},
            "it(\n  'multilinea',\n  fn);": {'multilinea'},
            "it('escapado\\'s', fn);": {"escapado's"},
            "it('con `backtick`', fn);": {'con `backtick`'},
            "// it('comentado', fn);": {'comentado'},
            "describe('suite', () => {});": set(),
            "describe.skip('suite', () => {});": set(),
            "myit('ajeno', fn);": set(),
            "objeto.it('miembro', fn);": set(),
            "import {test, expect} from 'vitest';": set(),
            "it(nombre, fn);": set(),
            "it('uno', fn);\ntest('dos', fn);": {'uno', 'dos'},
        }
        for fuente, esperado in casos.items():
            with self.subTest(fuente=fuente):
                self.assertEqual(retiros.declaraciones(fuente), esperado)

    def test_escrito_encuentra_el_titulo_aunque_las_comillas_esten_desparejas(self):
        """R2-1: busqueda por subcadena delimitada, sin emparejar comillas."""
        casos = {
            ("it('x', fn);", 'x'): True,
            ('it("x", fn);', 'x'): True,
            ('const t = `x`;', 'x'): True,
            ("itSi(false)('x', fn);", 'x'): True,
            ("// the user's cart\nitSi(false)('x', fn);", 'x'): True,
            ("const r = /'/;\nitSi(false)('x', fn);", 'x'): True,
            ("const alias = it;\n// don't\nalias('x', fn);", 'x'): True,
            ("it('xy', fn);", 'x'): False,
            ("const t = 'otro';", 'x'): False,
            ('const n = 7;', 'x'): False,
        }
        for (fuente, hoja), esperado in casos.items():
            with self.subTest(fuente=fuente, hoja=hoja):
                self.assertEqual(retiros.escrito(fuente, hoja), esperado)

    def base_falsa(self, ids):
        return {'results': [{'id': list(i), 'state': 'pass'} for i in ids]}

    def test_archivo_ausente_en_la_base_no_es_baja(self):
        """Guarda interna: el CLI no puede llegar aqui porque un id medido en la
        base implica que su archivo existia en base_sha."""
        ausente = ('angular:app', 'projects/app/src/ausente.spec.ts', NOMBRE)
        with self.assertRaises(Invalid) as caso:
            retiros.verificar_frontend(str(self.t.repo), self.base_sha, (self.base_sha,),
                                       self.base_falsa([ausente]), {ausente: HOJA}, {ausente})
        self.assertIn('no existe en la base', str(caso.exception))

    def test_hoja_vacia_no_se_puede_citar(self):
        """P2-1: con hoja vacia, cualquier review la 'citaria'."""
        item = ('angular:app', SPEC, SUITE + ' ')
        with self.assertRaises(Invalid) as caso:
            retiros.verificar_frontend(str(self.t.repo), self.base_sha, (self.base_sha,),
                                       self.base_falsa([item]), {item: ''}, {item})
        self.assertIn('titulo hoja vacio', str(caso.exception))

    def test_la_hoja_no_declarada_en_la_base_bloquea(self):
        """Si el spec de base_sha no declara ese titulo literal, su ausencia
        posterior no prueba nada (caso it.each y titulos formateados)."""
        item = ('angular:app', SPEC, SUITE + ' cada 1')
        with self.assertRaises(Invalid) as caso:
            retiros.verificar_frontend(str(self.t.repo), self.base_sha, (self.base_sha,),
                                       self.base_falsa([item]), {item: 'cada 1'}, {item})
        self.assertIn('no declara', str(caso.exception))

    def test_la_cita_exige_ruta_y_titulo_delimitado_en_la_misma_linea(self):
        item = ('angular:app', SPEC, NOMBRE)
        bajas = {item: HOJA}
        acepta = [
            "Baja: '" + HOJA + "' en " + SPEC,
            'Baja: "' + HOJA + '" en ' + SPEC,
            'Baja: «' + HOJA + '» en ' + SPEC,
            "Baja: '" + NOMBRE + "' en " + SPEC,
            'Baja: ' + retiros.marca(item),
            "Baja: '" + HOJA + "' en " + SPEC + '.',   # punto final, no otra ruta
            "Baja: '" + HOJA + "' en front-adr/" + SPEC,
        ]
        rechaza = [
            'Evidencia revisada en ' + SPEC + ' (token renovado).',
            'Baja: ' + HOJA + ' en ' + SPEC,                      # sin delimitar
            "Baja: '" + HOJA + "'\nArchivo: " + SPEC,             # en dos lineas
            "Revisado: approved · 2026-01-01T00:00:00Z · '" + HOJA + "' en " + SPEC
            + " · estampado por gate.py revision",
            # R2-2: el sello estampado puede ocupar varias lineas si quien sello
            # metio saltos en --por. No es el revisor escribiendo.
            "Sin mencion de bajas.\nRevisado: approved · 2026-01-01T00:00:00Z · \n"
            + SPEC + " '" + HOJA + "'\n · estampado por gate.py revision",
            "Baja: '" + HOJA + "' en projects/app/src/otro.spec.ts",
            # R2-3: la ruta tiene que estar completa, no como prefijo de otra.
            "Baja: '" + HOJA + "' en " + SPEC + '.orig',
            "Baja: '" + HOJA + "' en " + SPEC + 'x',
        ]
        for texto in acepta:
            with self.subTest(acepta=texto[:60]):
                self.assertEqual(retiros.sin_cita_frontend(texto, bajas), [])
        for texto in rechaza:
            with self.subTest(rechaza=texto[:60]):
                self.assertEqual(retiros.sin_cita_frontend(texto, bajas), [retiros.marca(item)])

    def test_una_base_con_hoja_incoherente_no_es_comparable(self):
        """R2-4: `title` y `fullName` tienen que cuadrar entre si en el raw."""
        base = json.loads(self.t.base.read_text())
        run = base['execution']['angular:app']
        datos = json.loads(run['json'])
        eventos = [json.loads(x) for x in run['events'].splitlines()]
        cambiados = 0
        for modulo in datos['testResults']:
            for caso in modulo['assertionResults']:
                if caso['title'] == 'sigue vivo':
                    caso['title'] = 'otra cosa'   # fullName y ancestorTitles intactos
                    cambiados += 1
        for modulo in eventos[1]['modules']:
            for vivo in modulo['tests']:
                if vivo['name'] == 'sigue vivo':
                    vivo['name'] = 'otra cosa'    # coherente con el JSON
        self.assertEqual(cambiados, 1)
        run['json'] = json.dumps(datos)
        run['events'] = '\n'.join(json.dumps(x) for x in eventos)
        self.t.base.write_text(json.dumps(base))
        r = self.check()
        self.t.expect(r, 2, 'hoja')
        self.assertNotIn('$ [', r.stdout)

    # --- la hoja sale de la base medida, no de un sufijo -----------------------

    def test_hojas_homonimas_en_el_mismo_archivo_cierran(self):
        """'es POST' y 'POST' conviven: la hoja la da la base, no el sufijo."""
        self.t.write(SPEC, HOMONIMOS)
        self.base_sha = self.t.commit('fixture: hojas homonimas')
        self.medir_base()
        baja = ['angular:app', SPEC, SUITE + ' es POST']
        self.integrar({SPEC: HOMONIMOS_SIN_LARGO, MOVIDO: None},
                      review="## AC-1\nfront/feature.txt:1\nBaja: 'es POST' en " + SPEC + "\n"
                             "Baja: '" + LEGAL + "' en " + MOVIDO + "\n")
        r = self.close('--retirados', self.declarar([baja, BAJA_MOVIDA]))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        recibo = json.loads(self.backlog.read_text())['features'][0]['mediciones_destino'][0]
        self.assertIn(baja, recibo['retirados'])
        medidos = {tuple(x['id']) for x in recibo['measurement']['results']}
        self.assertIn(('angular:app', SPEC, SUITE + ' POST'), medidos)

    def test_test_movido_a_otro_archivo_del_proyecto_cierra(self):
        """Diseno declarado: al cambiar de archivo el id cambia, y es el review
        quien confirma que el test sigue corriendo con el id nuevo."""
        otro = 'projects/app/src/otro.spec.ts'
        self.integrar({SPEC: SIN_LA_BAJA, MOVIDO: None, otro: BASE_MOVIDO},
                      review="## AC-1\nfront/feature.txt:1\n"
                             "Baja: '" + HOJA + "' en " + SPEC + " (el contrato paso a GET).\n"
                             "Baja: '" + LEGAL + "' en " + MOVIDO + ", movido a " + otro
                             + "; sigue corriendo con id nuevo.\n")
        r = self.close('--retirados', self.declarar(BAJAS))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        recibo = json.loads(self.backlog.read_text())['features'][0]['mediciones_destino'][0]
        medidos = {tuple(x['id']) for x in recibo['measurement']['results']}
        self.assertIn(('angular:app', otro, LEGAL), medidos)
        self.assertNotIn(tuple(BAJA_MOVIDA), medidos)

    def test_titulo_formateado_de_it_each_no_es_declarable(self):
        """Sobrebloqueo documentado: el nombre medido no es un literal del spec."""
        self.t.write(SPEC, CADA)
        self.base_sha = self.t.commit('fixture: it.each')
        self.medir_base()
        baja = ['angular:app', SPEC, SUITE + ' cada 1']
        self.integrar({SPEC: SIN_LA_BAJA, MOVIDO: None},
                      review="## AC-1\nfront/feature.txt:1\nBaja: 'cada 1' en " + SPEC + "\n"
                             "Baja: '" + LEGAL + "' en " + MOVIDO + "\n")
        self.rechazado('no declara', '--retirados', self.declarar([baja, BAJA_MOVIDA]))


if __name__ == '__main__':
    unittest.main()
