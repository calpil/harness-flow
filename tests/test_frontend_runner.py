"""CLI real Angular 22/Vitest 4 + node:test, solo fixtures efimeros.

Requiere HARNESS_TEST_FRONTEND_MODULES con node_modules ya instalados.
No instala ni omite pruebas si falta el toolchain. No ejecuta npm scripts.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(os.environ.get('HARNESS_TEST_SCRIPTS', Path(__file__).resolve().parents[1] / 'scripts'))
NODE_FILES = ['scripts/verificar-dist.test.mjs', 'scripts/catalogo-snapshot.test.mjs']


def _modulos_requeridos() -> str:
    """El toolchain es un prerequisito declarado, no algo que se omita.

    Sigue siendo rojo si falta -- este arnes no da por buena una suite que no
    corrio -- pero un KeyError crudo no decia que faltaba ni como resolverlo.
    """
    valor = os.environ.get('HARNESS_TEST_FRONTEND_MODULES')
    if not valor:
        raise AssertionError(  # falla, no omite: el prerequisito es parte del contrato
            "falta HARNESS_TEST_FRONTEND_MODULES: apuntala a un node_modules ya "
            "instalado con Angular 22 + Vitest 4 (ver references/multirepo.md). "
            "Estas pruebas NO se omiten: miden el runner real.")
    return valor


class FrontendFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='frontend-fixture-')
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.repo = self.home / 'repo con espacios'
        self.repo.mkdir()
        modules = Path(_modulos_requeridos()).resolve()
        self.assertTrue((modules / '@angular/cli/bin/ng.js').is_file())
        (self.repo / 'node_modules').symlink_to(modules, target_is_directory=True)
        self.env = dict(PATH=os.environ['PATH'], HOME=str(self.home), USERPROFILE=str(self.home),
                        CI='1', PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(self.home), TEMP=str(self.home), TMP=str(self.home),
                        GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                        GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')
        self.write('.gitignore', 'node_modules/\n.angular/\n')
        self.write('package.json', json.dumps({'private': True, 'type': 'module', 'scripts': {
            'test': 'npm run test:dist && ng test app',
            'test:dist': 'node --test ' + ' '.join(NODE_FILES)}}))
        # El contrato toma la version de Node de lo que DECLARA el repo: el
        # fixture declara la del Node que este primero en PATH.
        self.node_version = subprocess.check_output(['node', '--version'], env=self.env, text=True).strip()
        self.write('.nvmrc', self.node_version.removeprefix('v') + '\n')
        self.write('package-lock.json', (modules.parent / 'package-lock.json').read_text())
        self.write('angular.json', json.dumps({'version': 1, 'projects': {'app': {
            'projectType': 'application', 'root': 'projects/app', 'sourceRoot': 'projects/app/src',
            'architect': {'build': {'builder': '@angular/build:application',
                'options': {'browser': 'projects/app/src/main.ts', 'tsConfig': 'tsconfig.json'},
                'configurations': {'development': {}}},
                'test': {'builder': '@angular/build:unit-test',
                         'options': {'tsConfig': 'tsconfig.json'}}}}}}))
        self.write('tsconfig.json', json.dumps({'compilerOptions': {'target': 'es2022',
            'module': 'preserve', 'moduleResolution': 'bundler', 'skipLibCheck': True,
            'types': ['vitest/globals']}, 'include': ['projects/**/*.ts']}))
        self.write('projects/app/src/main.ts', 'export {};\n')
        self.write('projects/app/src/a.spec.ts', "import {test, expect} from 'vitest';\ntest('healthy', () => expect(1).toBe(1));\n")
        for path in NODE_FILES:
            self.write(path, "import {test} from 'node:test';\nimport assert from 'node:assert/strict';\ntest('healthy', () => assert.equal(1, 1));\n")
        self.git('init', '-b', 'develop')
        self.commit('fixture base')
        self.base = self.home / 'base.json'
        self.logs = []

    def write(self, path, content):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        return target

    def git(self, *args):
        r = subprocess.run(['git', '-c', 'core.hooksPath=' + str(self.home / 'no-hooks'),
                            '-C', str(self.repo), *args], env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout.strip()

    def commit(self, label):
        self.git('add', '.')
        self.git('commit', '-m', label)
        return self.git('rev-parse', 'HEAD')

    def cli(self, action, *extra):
        args = [sys.executable, '-B', str(SCRIPTS / 'postmerge_frontend.py'), action,
                '--repo', str(self.repo), '--guardar' if action == 'base' else '--base', str(self.base), *extra]
        r = subprocess.run(args, cwd=self.repo, env=self.env, capture_output=True, text=True, timeout=120)
        log = dict(argv=args, exit=r.returncode, stdout=r.stdout, stderr=r.stderr)
        self.logs.append(log)
        directory = os.environ.get('HARNESS_TEST_FRONTEND_LOGS')
        if directory:
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            with (path / (self.id() + '.jsonl')).open('a') as stream:
                stream.write(json.dumps(log) + '\n')
            if self.base.exists():
                shutil.copy2(self.base, path / (self.id() + '.base.json'))
            for artifact in self.home.glob('*.evidence.json'):
                shutil.copy2(artifact, path / (self.id() + '.' + artifact.name))
            if (self.home / 'evidence.json').is_file():
                shutil.copy2(self.home / 'evidence.json', path / (self.id() + '.evidence.json'))
        return r

    def expect(self, result, code, reason=''):
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stdout + result.stderr)
        if reason:
            self.assertIn(reason, result.stdout + result.stderr)

    def measured_base(self):
        self.expect(self.cli('base'), 0)
        return json.loads(self.base.read_text())

    def test_real_base_measures_project_file_and_test(self):
        data = self.measured_base()
        self.assertEqual({tuple(x['id']) for x in data['results']}, {
            ('angular:app', 'projects/app/src/a.spec.ts', 'healthy'),
            ('node:test', NODE_FILES[0], 'healthy'), ('node:test', NODE_FILES[1], 'healthy')})
        self.assertEqual({x['state'] for x in data['results']}, {'pass'})
        self.assertEqual(data['sha'], self.git('rev-parse', 'HEAD'))
        self.assertEqual(data['rama'], 'develop')
        self.assertTrue(data['execution'])
        self.assertEqual(data['toolchain']['versions']['vitest'].split('.')[0], '4')

    def test_real_debt_new_red_and_cure_keep_identity(self):
        file = 'projects/app/src/a.spec.ts'
        original = (self.repo / file).read_text()
        self.write(file, original + "test('debt', () => expect(1).toBe(2));\n")
        self.commit('debt')
        base = self.measured_base()
        self.expect(self.cli('check'), 0, 'deuda')
        self.write(NODE_FILES[1], (self.repo / NODE_FILES[1]).read_text().replace('equal(1, 1)', 'equal(1, 2)'))
        self.commit('new node red')
        self.expect(self.cli('check'), 1, NODE_FILES[1])
        self.write(file, original + "test('debt', () => expect(1).toBe(1));\n")
        self.write(NODE_FILES[1], (self.repo / NODE_FILES[1]).read_text().replace('equal(1, 2)', 'equal(1, 1)'))
        self.commit('cure')
        self.expect(self.cli('check'), 0, 'se curo')
        self.assertEqual(json.loads(self.base.read_text()), base)

    def test_angular_late_errors_skips_only_and_duplicates_are_not_measured(self):
        original = (self.repo / 'projects/app/src/a.spec.ts').read_text()
        variants = {
            'teardown': original + "import {afterAll} from 'vitest'; test('debt', () => expect(1).toBe(2)); afterAll(() => { throw Error('late failure'); });\n",
            'unhandled': original + "test('debt', async () => { Promise.reject(Error('late')); await new Promise(r => setTimeout(r, 20)); expect(1).toBe(2); });\n",
            'skip': original + "test.skip('missing', () => {});\n",
            'only': original.replace("test('healthy'", "test.only('healthy'"),
            'duplicate': original + "test('healthy', () => {});\n",
            'empty-file': "export {};\n",
        }
        for label, content in variants.items():
            with self.subTest(case=label):
                self.write('projects/app/src/a.spec.ts', content)
                self.commit(label)
                self.base.unlink(missing_ok=True)
                self.expect(self.cli('base'), 2, 'no pude medir')
                self.assertFalse(self.base.exists())

    def test_node_late_exit_skips_duplicates_and_empty_are_not_measured(self):
        original = (self.repo / NODE_FILES[0]).read_text()
        variants = {
            'late23': original + "test('debt', () => assert.equal(1, 2)); process.on('exit', () => { process.exitCode = 23; });\n",
            'late1': original + "process.on('exit', () => { process.exitCode = 1; });\n",
            'skip': original + "test.skip('missing', () => {});\n",
            'duplicate': original + "test('healthy', () => {});\n",
            'empty-file': 'export {};\n',
        }
        for label, content in variants.items():
            with self.subTest(case=label):
                self.write(NODE_FILES[0], content)
                self.commit(label)
                self.base.unlink(missing_ok=True)
                self.expect(self.cli('base'), 2, 'no pude medir')
                self.assertFalse(self.base.exists())

    def test_base_context_and_raw_corruption_rejected_before_running(self):
        import copy
        base = self.measured_base()
        changes = {
            'foreign repo': lambda b: b.update(repo=str(self.home)),
            'foreign branch': lambda b: b.update(rama='other'),
            'invalid SHA': lambda b: b.update(sha='0' * 40),
            'wrong command': lambda b: b['scope'].update(command='true'),
            'toolchain': lambda b: b['toolchain']['versions'].update(node='v22.0.0'),
            'skip': lambda b: b['results'][0].update(state='skip'),
            'fake results': lambda b: b.update(results=[]),
            'no execution': lambda b: b.pop('execution'),
            'missing project': lambda b: b['execution'].pop('angular:app'),
            'exit bool': lambda b: b['execution']['node:test'].update(exit=False),
            'exit late': lambda b: b['execution']['angular:app'].update(exit=23),
            'truncated events': lambda b: b['execution']['angular:app'].update(events=b['execution']['angular:app']['events'].splitlines()[0]),
            'truncated JSON': lambda b: b['execution']['angular:app'].update(json='{'),
            'truncated node': lambda b: b['execution']['node:test'].update(stdout='\n'.join(b['execution']['node:test']['stdout'].splitlines()[:-1])),
        }
        for label, mutate in changes.items():
            with self.subTest(case=label):
                value = copy.deepcopy(base)
                mutate(value)
                self.base.write_text(json.dumps(value))
                r = self.cli('check')
                self.expect(r, 2, 'no pude medir')
                self.assertNotIn('$ [', r.stdout, 'la base invalida no debe ejecutar tests')
        for raw in ('{}', '{', '[]', json.dumps(base).replace('"version": 1', '"version": 1, "version": 1')):
            self.base.write_text(raw)
            r = self.cli('check')
            self.expect(r, 2)
            self.assertNotIn('$ [', r.stdout)

    def test_configuration_and_environment_cannot_filter_the_suite(self):
        import copy
        angular = json.loads((self.repo / 'angular.json').read_text())
        package = json.loads((self.repo / 'package.json').read_text())
        for key, value in [('include', ['**/a.spec.ts']), ('exclude', ['**/*']),
                           ('runnerConfig', True), ('filter', 'healthy'), ('runner', 'karma')]:
            with self.subTest(option=key):
                config = copy.deepcopy(angular)
                config['projects']['app']['architect']['test']['options'][key] = value
                self.write('angular.json', json.dumps(config))
                self.commit('filter')
                self.expect(self.cli('base'), 2, 'contrato')
        self.write('angular.json', json.dumps(angular))
        for text in ('true', 'npm run test:dist', 'npm run test:dist && ng test app --include=x'):
            config = copy.deepcopy(package)
            config['scripts']['test'] = text
            self.write('package.json', json.dumps(config))
            self.commit('command override')
            self.expect(self.cli('base'), 2, 'contrato')
        self.write('package.json', json.dumps(package))
        self.commit('restore')
        for key, value in [('NODE_OPTIONS', '--test-name-pattern=absent'), ('DIST_REAL_REGRESSION', '/missing'),
                           ('VITEST_MAX_THREADS', '1')]:
            self.env[key] = value
            self.expect(self.cli('base'), 2, 'entorno')
            del self.env[key]

    def test_disappeared_test_and_omitted_project_are_not_cures(self):
        self.measured_base()
        self.write('projects/app/src/a.spec.ts', (self.repo / 'projects/app/src/a.spec.ts').read_text().replace('healthy', 'renamed'))
        self.commit('disappeared')
        self.expect(self.cli('check'), 2, 'desaparecidos')
        config = json.loads((self.repo / 'angular.json').read_text())
        config['projects']['other'] = config['projects']['app']
        self.write('angular.json', json.dumps(config))
        self.commit('omitted project')
        self.expect(self.cli('base'), 2, 'contrato')

    def test_failed_measurement_saves_raw_exit_without_writing_base(self):
        path = self.home / 'evidence.json'
        self.write(NODE_FILES[0], (self.repo / NODE_FILES[0]).read_text() +
                   "test('debt', () => assert.equal(1, 2)); process.on('exit', () => { process.exitCode = 23; });\n")
        self.commit('late failure')
        self.expect(self.cli('base', '--evidence', str(path)), 2, 'no pude medir')
        self.assertFalse(self.base.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data['exit'], 2)
        self.assertIn('23', data['execution']['node:test']['stdout'])
        self.assertEqual(data['execution']['node:test']['exit'], 1)
        self.assertNotIn('results', data)

    def test_configuration_types_fail_cleanly_before_execution(self):
        self.write('package.json', json.dumps({'scripts': {'test': 7, 'test:dist': 'node --test ' + ' '.join(NODE_FILES)}}))
        self.commit('invalid command type')
        result = self.cli('base')
        self.expect(result, 2, 'contrato')
        self.assertNotIn('$ [', result.stdout)

    def test_baseline_command_payload_is_closed(self):
        import copy
        base = self.measured_base()
        variants = {
            'argv': lambda b: b['execution']['node:test'].update(argv=['true']),
            'angular argv': lambda b: b['execution']['angular:app']['argv'].append('--filter=healthy'),
            'extra field': lambda b: b['execution']['node:test'].update(status='PASS'),
        }
        for label, mutate in variants.items():
            with self.subTest(case=label):
                b = copy.deepcopy(base)
                mutate(b)
                self.base.write_text(json.dumps(b))
                result = self.cli('check')
                self.expect(result, 2, 'ejecucion')
                self.assertNotIn('$ [', result.stdout)

    def test_effective_inventory_cannot_omit_a_test_file(self):
        self.write('projects/app/outside-source.spec.ts', "import {test} from 'vitest'; test('not collected', () => {});\n")
        self.commit('outside configured sourceRoot')
        r = self.cli('base')
        self.expect(r, 2, 'inventario')
        self.assertFalse(self.base.exists())

    def test_more_native_incomplete_results_are_rejected(self):
        original = (self.repo / NODE_FILES[0]).read_text()
        variants = {
            'todo': original + "test.todo('pending');\n",
            'unhandled': original + "test('late', () => { setImmediate(() => { throw Error('unhandled'); }); });\n",
            'teardown': original + "import {after} from 'node:test'; after(() => { throw Error('teardown'); });\n",
        }
        for label, content in variants.items():
            with self.subTest(case=label):
                self.write(NODE_FILES[0], content)
                self.commit(label)
                self.expect(self.cli('base'), 2, 'no pude medir')
                self.assertFalse(self.base.exists())

    def test_node_only_is_not_full_measurement(self):
        self.write(NODE_FILES[0], (self.repo / NODE_FILES[0]).read_text().replace("test('healthy'", "test.only('healthy'"))
        self.commit('only')
        self.expect(self.cli('base'), 2, 'no pude medir')
        self.assertFalse(self.base.exists())

    # --- test:dist con N archivos y Node declarado por el repo (ADR 2026-10) ---

    def package(self):
        return json.loads((self.repo / 'package.json').read_text())

    def set_test_dist(self, command):
        package = self.package()
        package['scripts']['test:dist'] = command
        self.write('package.json', json.dumps(package))

    def node_test(self, path, *names, red=()):
        body = "import {test} from 'node:test';\nimport assert from 'node:assert/strict';\n"
        body += ''.join(f"test('{n}', () => assert.equal(1, {2 if n in red else 1}));\n" for n in names)
        self.write(path, body)

    def version(self):
        return tuple(int(x) for x in self.node_version.removeprefix('v').split('.'))

    def fake_node(self, version):
        """Un `node` que REPORTA otra version y delega todo lo demas en el real.

        Prueba que el contrato decide por la version declarada y no por una
        fija, sin instalar otro Node.
        """
        import shlex
        real = shutil.which('node', path=self.env['PATH'])
        bindir = self.home / ('node-v' + version)
        bindir.mkdir()
        (bindir / 'node').write_text('#!/bin/sh\nif [ "$1" = "--version" ]; then echo v' + version
                                     + '; exit 0; fi\nexec ' + shlex.quote(real) + ' "$@"\n')
        (bindir / 'node').chmod(0o755)
        self.env['PATH'] = str(bindir) + os.pathsep + self.env['PATH']

    def test_test_dist_con_n_archivos_mide_cada_archivo_con_su_identidad(self):
        files = [*NODE_FILES, 'scripts/tercero.test.mjs', 'scripts/sub/cuarto.test.mjs']
        for path in files[2:]:
            self.node_test(path, 'healthy')
        self.set_test_dist('node --test ' + ' '.join(files))
        self.commit('cuatro archivos node:test')
        data = self.measured_base()
        # Mismo titulo en cada archivo: la identidad es (ruta, titulo), no colapsa.
        self.assertEqual({tuple(x['id']) for x in data['results']},
                         {('angular:app', 'projects/app/src/a.spec.ts', 'healthy'),
                          *(('node:test', f, 'healthy') for f in files)})
        self.assertEqual(data['scope']['node_files'], files)
        self.assertEqual(data['scope']['files']['node:test'], sorted(files))
        self.assertEqual(data['execution']['node:test']['argv'][-4:], files)

    def test_test_dist_ambiguo_o_arbitrario_no_se_mide(self):
        self.write('scripts/sin-sufijo.mjs', "import {test} from 'node:test'; test('x', () => {});\n")
        self.node_test('scripts/real.test.mjs', 'healthy')
        (self.repo / 'scripts/enlace.test.mjs').symlink_to(self.repo / 'scripts/real.test.mjs')
        (self.repo / 'enlazado').symlink_to(self.repo / 'scripts', target_is_directory=True)
        lista = ' '.join(NODE_FILES)
        variants = {
            'glob': 'node --test scripts/*.test.mjs',
            'llaves': 'node --test scripts/{verificar-dist,catalogo-snapshot}.test.mjs',
            'duplicado': f'node --test {lista} {NODE_FILES[0]}',
            'flag only': f'node --test --test-only {lista}',
            'flag pattern': f'node --test --test-name-pattern=healthy {lista}',
            'encadenado': f'node --test {lista} && true',
            'doble espacio': f'node --test  {lista}',
            'espacio final': f'node --test {lista} ',
            'sube de nivel': 'node --test ../fuera.test.mjs',
            'absoluta': 'node --test ' + str(self.repo / NODE_FILES[0]),
            'punto': f'node --test ./{NODE_FILES[0]}',
            'sin sufijo': 'node --test scripts/sin-sufijo.mjs',
            'comillas': f"node --test '{NODE_FILES[0]}'",
            'vacio': 'node --test',
            'entorno': f'NODE_ENV=test node --test {lista}',
            'otro runner': f'npx vitest {lista}',
            'archivo ausente': f'node --test {lista} scripts/no-existe.test.mjs',
            'symlink': f'node --test {lista} scripts/enlace.test.mjs',
            'directorio symlink': f'node --test {lista} enlazado/real.test.mjs',
        }
        for label, command in variants.items():
            with self.subTest(case=label):
                self.set_test_dist(command)
                self.commit(label)
                self.base.unlink(missing_ok=True)
                result = self.cli('base')
                self.expect(result, 2, 'contrato node:test')
                self.assertNotIn('$ [', result.stdout, 'un test:dist fuera de contrato no se ejecuta')
                self.assertFalse(self.base.exists())

    def test_agregar_un_archivo_a_test_dist_mide_sus_rojos_como_nuevos(self):
        # Es el caso de ADR 0f9b945 -> 938ff68: la integracion suma un archivo.
        self.measured_base()
        files = [*NODE_FILES, 'scripts/tercero.test.mjs']
        self.node_test(files[2], 'healthy', 'nuevo', red=('nuevo',))
        self.set_test_dist('node --test ' + ' '.join(files))
        self.commit('suma un archivo node:test con un rojo')
        self.expect(self.cli('check'), 1, 'node:test::scripts/tercero.test.mjs::nuevo')
        self.node_test(files[2], 'healthy', 'nuevo')
        self.commit('arregla el rojo')
        self.expect(self.cli('check'), 0)

    def test_quitar_un_archivo_de_test_dist_no_es_una_curacion(self):
        files = [*NODE_FILES, 'scripts/tercero.test.mjs']
        self.node_test(files[2], 'healthy', 'deuda', red=('deuda',))
        self.set_test_dist('node --test ' + ' '.join(files))
        self.commit('tres archivos, uno con deuda')
        self.measured_base()
        self.set_test_dist('node --test ' + ' '.join(NODE_FILES))
        self.commit('saca el archivo de test:dist sin borrarlo')
        self.expect(self.cli('check'), 2, 'node:test::scripts/tercero.test.mjs::deuda')

    def test_base_que_no_midio_todo_el_test_dist_de_su_commit_se_rechaza(self):
        files = [*NODE_FILES, 'scripts/tercero.test.mjs']
        self.node_test(files[2], 'healthy')
        self.commit('tercer archivo fuera de test:dist')
        base = self.measured_base()
        self.set_test_dist('node --test ' + ' '.join(files))
        tip = self.commit('test:dist lo incluye')
        # Base coherente consigo misma, pero atribuida a un commit cuyo test:dist
        # tiene un archivo que esa base nunca midio.
        base.update(sha=tip, tree=self.git('rev-parse', 'HEAD^{tree}'))
        self.base.write_text(json.dumps(base))
        result = self.cli('check')
        self.expect(result, 2, 'test:dist de su commit')
        self.assertNotIn('$ [', result.stdout)

    def test_version_de_node_sale_de_lo_que_declara_el_repo(self):
        major = self.version()[0]
        otra = f'{major + 2}.1.0'
        self.write('.nvmrc', otra + '\n')
        self.commit('el repo declara otro Node')
        self.fake_node(otra)
        data = self.measured_base()
        self.assertEqual(data['toolchain']['versions']['node'], 'v' + otra)
        self.assertEqual(data['toolchain']['node_declarado'], {'nvmrc': otra})
        # El mismo Node con el repo declarando otra version no mide.
        self.write('.nvmrc', self.node_version + '\n')
        self.commit('vuelve a declarar el Node real')
        self.base.unlink()
        result = self.cli('base')
        self.expect(result, 2, 'toolchain fuera de contrato')
        self.assertNotIn('$ [', result.stdout)

    def test_node_que_no_cumple_lo_declarado_no_mide(self):
        major, minor, patch = self.version()
        exacta = f'{major}.{minor}.{patch}'
        package = self.package()
        variants = {
            'nvmrc otra': ({'.nvmrc': f'{major + 2}.0.0'}, None, 'toolchain fuera de contrato'),
            'nvmrc menor': ({'.nvmrc': f'{major}.{minor + 1}'}, None, 'toolchain fuera de contrato'),
            'sin declarar': ({}, None, 'no declara'),
            'nvmrc alias': ({'.nvmrc': 'lts/*'}, None, '.nvmrc'),
            'nvmrc vacio': ({'.nvmrc': ''}, None, '.nvmrc'),
            'engines otro major': ({}, f'^{major + 1}.0.0', 'toolchain fuera de contrato'),
            'engines tilde': ({}, f'~{major}.{minor + 1}.0', 'toolchain fuera de contrato'),
            'engines minimo': ({}, f'>={major}.{minor}.{patch + 1}', 'toolchain fuera de contrato'),
            'engines rango compuesto': ({}, f'>={major} <{major + 9}', 'engines'),
            'engines x': ({}, f'{major}.x', 'engines'),
            'engines no texto': ({}, major, 'engines'),
            'inconsistentes': ({'.nvmrc': exacta}, f'^{major + 1}.0.0', 'toolchain fuera de contrato'),
        }
        for label, (files, engines, reason) in variants.items():
            with self.subTest(case=label):
                (self.repo / '.nvmrc').unlink(missing_ok=True)
                for path, content in files.items():
                    self.write(path, content + '\n')
                value = dict(package)
                if engines is not None:
                    value['engines'] = {'node': engines}
                self.write('package.json', json.dumps(value))
                self.commit(label)
                self.base.unlink(missing_ok=True)
                result = self.cli('base')
                self.expect(result, 2, reason)
                self.assertNotIn('$ [', result.stdout)
                self.assertFalse(self.base.exists())
        with self.subTest(case='nvmrc symlink'):
            self.write('version-node', exacta + '\n')
            (self.repo / '.nvmrc').unlink(missing_ok=True)
            (self.repo / '.nvmrc').symlink_to(self.repo / 'version-node')
            self.write('package.json', json.dumps(package))
            self.commit('nvmrc symlink')
            self.expect(self.cli('base'), 2, '.nvmrc')

    def test_node_declarado_en_las_formas_soportadas_mide(self):
        major, minor, patch = self.version()
        exacta = f'{major}.{minor}.{patch}'
        package = self.package()
        variants = {
            'nvmrc con v': ({'.nvmrc': 'v' + exacta}, None),
            'nvmrc major': ({'.nvmrc': str(major)}, None),
            'engines caret': ({}, '^' + exacta),
            'engines tilde': ({}, f'~{major}.{minor}.0'),
            'engines minimo': ({}, '>=22.0.0'),
            'engines exacta': ({}, exacta),
            'ambos': ({'.nvmrc': exacta}, f'^{major}.0.0'),
        }
        for label, (files, engines) in variants.items():
            with self.subTest(case=label):
                (self.repo / '.nvmrc').unlink(missing_ok=True)
                for path, content in files.items():
                    self.write(path, content + '\n')
                value = dict(package)
                if engines is not None:
                    value['engines'] = {'node': engines}
                self.write('package.json', json.dumps(value))
                self.commit(label)
                self.base.unlink(missing_ok=True)
                data = self.measured_base()
                declared = {**({'nvmrc': files['.nvmrc']} if files else {}),
                            **({'engines': engines} if engines else {})}
                self.assertEqual(data['toolchain']['node_declarado'], declared)

    def test_node_bajo_el_minimo_del_protocolo_no_mide(self):
        self.write('.nvmrc', '20.11.0\n')
        self.commit('Node 20')
        self.fake_node('20.11.0')
        result = self.cli('base')
        self.expect(result, 2, 'Node 22')
        self.assertNotIn('$ [', result.stdout)

    def test_cambiar_el_node_declarado_deja_la_base_incomparable(self):
        self.measured_base()
        self.write('.nvmrc', str(self.version()[0]) + '\n')
        self.commit('relaja .nvmrc al major')
        self.expect(self.cli('check'), 2, 'toolchain')

    def test_cierre_historico_ve_los_tests_de_todo_test_dist(self):
        sys.path.insert(0, str(SCRIPTS))
        self.addCleanup(sys.path.remove, str(SCRIPTS))
        import medicion_destino
        base_sha = self.git('rev-parse', 'HEAD')
        files = [*NODE_FILES, 'scripts/tercero.test.mjs']
        self.node_test(files[2], 'agregado')
        self.set_test_dist('node --test ' + ' '.join(files))
        source = self.commit('la feature agrega un archivo node:test')
        self.assertIn((files[2], 'agregado'),
                      medicion_destino.tests_agregados_front(str(self.repo), base_sha, source))
        self.node_test(files[2], 'agregado', 'otro')
        solo_tests = self.commit('solo toca ese archivo de test')
        self.assertTrue(medicion_destino.delta_solo_tests_front(str(self.repo), source, solo_tests))


if __name__ == '__main__':
    unittest.main()
