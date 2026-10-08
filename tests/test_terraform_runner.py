"""Runner Terraform (postmerge_terraform.py) y su despacho en medicion_destino.

Usa el `terraform` REAL del PATH sobre raices de fixture que solo usan el
provider integrado (terraform_data, variable, output): sin red ni state.
Si no hay terraform el test FALLA, no se omite: el prerequisito es parte del
contrato (mismo criterio que los tests del runner frontend).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(os.environ.get('HARNESS_TEST_SCRIPTS', Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(SCRIPTS))

import medicion_destino  # noqa: E402
import postmerge_terraform as tf  # noqa: E402
from multirepo import Invalid  # noqa: E402

MAIN = '''variable "x" {
  type    = number
  default = 1
}

output "y" {
  value = var.x
}
'''
TESTS = '''run "defaults" {
  command = plan

  assert {
    condition     = output.y == 1
    error_message = "y debe ser 1"
  }
}

run "override" {
  command = plan

  variables {
    x = 2
  }

  assert {
    condition     = output.y == 2
    error_message = "y debe ser 2"
  }
}
'''
TEST_FILE = 'infra/tests/a.tftest.hcl'


def run_ok(extra: str) -> str:
    return f'''
run "{extra}" {{
  command = plan

  assert {{
    condition     = output.y == 1
    error_message = "y debe ser 1"
  }}
}}
'''


def _terraform_requerido() -> str:
    binary = shutil.which('terraform')
    if not binary:
        raise AssertionError(  # falla, no omite: el prerequisito es parte del contrato
            'falta terraform en el PATH: estas pruebas miden el runner real con el binario real '
            'y NO se omiten.')
    return binary


class TerraformFixture(unittest.TestCase):
    def setUp(self):
        _terraform_requerido()
        self.tmp = tempfile.TemporaryDirectory(prefix='terraform-fixture-')
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.repo = self.home / 'repo con espacios'
        self.repo.mkdir()
        self.env = dict(PATH=os.environ['PATH'], HOME=str(self.home), USERPROFILE=str(self.home),
                        PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(self.home),
                        GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                        GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')
        self.write('.gitignore', '.terraform/\nignored-dir/\n*.tfvars\noverride.tf\n')
        self.write('infra/main.tf', MAIN)
        self.write(TEST_FILE, TESTS)
        self.git('init', '-b', 'develop')
        self.commit('fixture base')
        self.base = self.home / 'base.json'

    def write(self, path, content):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        return target

    def git(self, *args):
        r = subprocess.run(['git', '-C', str(self.repo), *args], env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout.strip()

    def commit(self, label):
        self.git('add', '.')
        self.git('commit', '-m', label)
        return self.git('rev-parse', 'HEAD')

    def cli(self, action, *extra):
        args = [sys.executable, '-B', str(SCRIPTS / 'postmerge_terraform.py'), action,
                '--repo', str(self.repo), '--guardar' if action == 'base' else '--base', str(self.base), *extra]
        return subprocess.run(args, cwd=self.repo, env=self.env, capture_output=True, text=True, timeout=300)

    def expect(self, result, code, reason=''):
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stdout + result.stderr)
        if reason:
            self.assertIn(reason, result.stdout + result.stderr)

    def measured_base(self):
        self.expect(self.cli('base'), 0)
        return json.loads(self.base.read_text())

    def assert_repo_intact(self):
        self.assertEqual(self.git('status', '--porcelain', '--ignored'), '')


class TerraformRunnerTests(TerraformFixture):
    def test_base_en_verde_mide_fmt_y_runs_sin_ensuciar_el_repo(self):
        data = self.measured_base()
        self.assertEqual({tuple(x['id']) for x in data['results']}, {
            ('infra', 'main.tf', 'fmt'), ('infra', 'tests/a.tftest.hcl', 'fmt'), ('infra', '<validate>', 'validate'),
            ('infra', 'tests/a.tftest.hcl', 'defaults'), ('infra', 'tests/a.tftest.hcl', 'override')})
        self.assertEqual({x['state'] for x in data['results']}, {'pass'})
        self.assertEqual((data['sha'], data['rama'], data['protocol']),
                         (self.git('rev-parse', 'HEAD'), 'develop', 'terraform-test-json-v2'))
        self.assertEqual(data['tree'], self.git('rev-parse', 'HEAD^{tree}'))
        self.assertEqual(data['repo'], str(self.repo))
        self.assertEqual(data['toolchain']['terraform_version'],
                         json.loads(subprocess.check_output(['terraform', 'version', '-json'], env=self.env))['terraform_version'])
        self.assertEqual(set(data['execution']['infra']), {'fmt', 'init', 'validate', 'test'})
        self.assertIn('-backend=false', data['execution']['infra']['init']['argv'])
        self.assertIn('-lockfile=readonly', data['execution']['infra']['init']['argv'])
        self.assert_repo_intact()  # ni .terraform/ ni .terraform.lock.hcl

    def test_check_sin_cambios_da_cero_y_no_toca_la_base(self):
        self.measured_base()
        before = self.base.read_bytes()
        self.expect(self.cli('check'), 0)
        self.assertEqual(self.base.read_bytes(), before)
        self.assert_repo_intact()

    def test_rojo_nuevo_da_uno_y_se_cura_con_deuda_conservada(self):
        self.measured_base()
        self.write(TEST_FILE, TESTS.replace('output.y == 2', 'output.y == 3'))
        self.commit('rojo nuevo')
        self.expect(self.cli('check'), 1, 'infra::tests/a.tftest.hcl::override')
        self.write(TEST_FILE, TESTS)
        self.commit('cura')
        self.expect(self.cli('check'), 0)

    def test_deuda_preexistente_de_la_base_no_bloquea(self):
        self.write(TEST_FILE, TESTS.replace('output.y == 2', 'output.y == 3'))
        self.commit('deuda')
        data = self.measured_base()
        self.assertIn('fail', {x['state'] for x in data['results']})
        self.expect(self.cli('check'), 0, 'deuda preexistente')

    def test_run_que_desaparece_bloquea(self):
        self.measured_base()
        self.write(TEST_FILE, TESTS.split('\nrun "override"')[0])
        self.commit('quita un run')
        self.expect(self.cli('check'), 2, 'desaparecidos')
        self.assertIn('override', self.cli('check').stdout + self.cli('check').stderr)

    def test_raiz_que_desaparece_bloquea(self):
        self.measured_base()
        self.git('rm', '-q', '-r', 'infra')
        self.write('otra/main.tf', MAIN)
        self.write('otra/tests/b.tftest.hcl', TESTS)
        self.commit('mueve la raiz')
        self.expect(self.cli('check'), 2, 'desaparecidos')

    def test_run_en_skip_bloquea(self):
        self.write(TEST_FILE, 'run "boom" {\n  command = plan\n\n  assert {\n    condition     = output.nope == 1\n'
                              '    error_message = "x"\n  }\n}\n' + run_ok('despues'))
        self.commit('un error deja el siguiente run en skip')
        self.expect(self.cli('base'), 2, 'skip')
        self.assertFalse(self.base.exists())

    def test_arbol_sucio_bloquea_antes_y_despues(self):
        self.write('sucio.txt', 'x')
        self.expect(self.cli('base'), 2, 'arbol sucio')
        (self.repo / 'sucio.txt').unlink()
        self.measured_base()
        self.write('infra/main.tf', MAIN + '\n')
        self.expect(self.cli('check'), 2, 'arbol sucio')

    def test_lo_que_un_test_apply_escribe_va_al_export_y_no_al_repo(self):
        self.write('infra/main.tf', MAIN + '''
resource "terraform_data" "escribe" {
  provisioner "local-exec" {
    command = "echo x > ../fuga.txt && mkdir ../ignored-dir"
  }
}
''')
        self.write(TEST_FILE, TESTS + '''
run "aplica" {
  command = apply
}
''')
        self.commit('un test apply escribe en ../')
        self.measured_base()
        self.assertFalse((self.repo / 'fuga.txt').exists())
        self.assert_repo_intact()

    def test_archivos_ignorados_que_terraform_carga_no_cambian_la_medicion(self):
        """terraform.tfvars, *.auto.tfvars (tambien en tests/) y override.tf harian
        pasar o fallar un run segun lo que haya en el disco de quien mide."""
        ignorados = {
            'tfvars': ('infra/terraform.tfvars', 'x = 9\n'),
            'auto.tfvars en tests/': ('infra/tests/z.auto.tfvars', 'x = 9\n'),
            'override.tf': ('infra/override.tf', 'variable "x" {\n  default = 9\n}\n'),
            'directorio ignorado sin formato': ('infra/ignored-dir/malo.tf', 'variable   "q"{\n  default = 1\n}\n'),
        }
        for label, (ruta, contenido) in ignorados.items():
            with self.subTest(label):
                self.write(ruta, contenido)
                self.assertEqual(self.git('status', '--porcelain'), '')
                self.base.unlink(missing_ok=True)
                data = self.measured_base()
                self.assertEqual({x['state'] for x in data['results']}, {'pass'}, data['results'])
                self.assertEqual(len(data['results']), 5)
                (self.repo / ruta).unlink()
        # y el check sigue viendo la regresion real aunque haya un archivo ignorado a favor
        self.write('infra/override.tf', 'variable "x" {\n  default = 1\n}\n')
        self.write('infra/main.tf', MAIN.replace('default = 1', 'default = 5'))
        self.commit('el default cambia')
        self.expect(self.cli('check'), 1, 'infra::tests/a.tftest.hcl::defaults')

    def test_el_entorno_del_llamador_no_se_hereda(self):
        self.write('infra/tests/b.tftest.hcl', run_ok('b'))
        self.commit('segundo archivo de test')
        self.env.update(TF_CLI_ARGS_test='-filter=tests/a.tftest.hcl', TF_CLI_ARGS='-no-color -var=x=8',
                        TF_VAR_x='7', TF_WORKSPACE='otro', TF_LOG='TRACE')
        data = self.measured_base()
        self.assertIn(['infra', 'tests/b.tftest.hcl', 'b'], [x['id'] for x in data['results']])
        self.assertEqual({x['state'] for x in data['results']}, {'pass'})

    def test_las_credenciales_y_el_home_del_llamador_no_llegan_a_terraform(self):
        # El provisioner corre con el entorno de terraform: si algo se heredo, el apply falla.
        chequeo = ('test -z \\"$GOOGLE_APPLICATION_CREDENTIALS\\" && test -z \\"$AWS_ACCESS_KEY_ID\\" '
                   '&& test -z \\"$CLOUDSDK_CONFIG\\" && test -z \\"$ARM_CLIENT_SECRET\\" '
                   f'&& test \\"$HOME\\" != \\"{self.home}\\"')
        self.write('infra/main.tf', MAIN + f'''
resource "terraform_data" "entorno" {{
  provisioner "local-exec" {{
    command = "{chequeo}"
  }}
}}
''')
        self.write(TEST_FILE, TESTS + '''
run "aplica" {
  command = apply
}
''')
        self.commit('un apply que exige entorno sin credenciales')
        self.env.update(GOOGLE_APPLICATION_CREDENTIALS='/x/adc.json', AWS_ACCESS_KEY_ID='AKIAXXXX',
                        CLOUDSDK_CONFIG='/x/gcloud', ARM_CLIENT_SECRET='s')
        data = self.measured_base()
        self.assertEqual({x['state'] for x in data['results']}, {'pass'}, data['results'])

    def test_fmt_es_por_archivo_la_deuda_de_uno_no_tapa_a_otro(self):
        self.write('infra/viejo.tf', 'variable   "v"{\n  default = 1\n}\n')
        self.commit('deuda de formato')
        data = self.measured_base()
        estados = {tuple(x['id']): x['state'] for x in data['results']}
        self.assertEqual(estados[('infra', 'viejo.tf', 'fmt')], 'fail')
        self.assertEqual(estados[('infra', 'main.tf', 'fmt')], 'pass')
        self.write('infra/nuevo.tf', 'variable   "n"{\n  default = 1\n}\n')
        self.commit('mas deuda')
        self.expect(self.cli('check'), 1, 'infra::nuevo.tf::fmt')

    def test_raiz_con_lockfile_sin_tests_se_valida_y_se_formatea(self):
        self.write('otra/main.tf', MAIN)
        self.write('otra/.terraform.lock.hcl', '# lock vacio\n')
        self.commit('raiz sin tests, solo lockfile')
        data = self.measured_base()
        ids = {tuple(x['id']): x['state'] for x in data['results']}
        self.assertEqual(ids[('otra', '<validate>', 'validate')], 'pass')
        self.assertEqual(ids[('otra', 'main.tf', 'fmt')], 'pass')
        self.assertNotIn('test', data['execution']['otra'])
        self.write('otra/main.tf', MAIN.replace('type    = number', 'type=number') + 'output "z" {\n  value = var.no_existe\n}\n')
        self.commit('la raiz sin tests se rompe')
        r = self.cli('check')
        self.expect(r, 1, 'otra::<validate>::validate')
        self.assertIn('otra::main.tf::fmt', r.stdout)

    def test_tests_en_json_tambien_se_miden_y_cuentan_en_el_inventario(self):
        self.write('infra/tests/j.tftest.json', json.dumps({'run': {'json_run': {'command': 'plan', 'assert': [
            {'condition': '${output.y == 1}', 'error_message': 'y debe ser 1'}]}}}))
        self.commit('un test en JSON')
        data = self.measured_base()
        self.assertIn(['infra', 'tests/j.tftest.json', 'json_run'], [x['id'] for x in data['results']])
        self.assertIn('tests/j.tftest.json', data['inventory']['infra']['tests'])

    def test_base_con_inventario_recortado_no_corresponde_a_su_commit(self):
        data = self.measured_base()
        data['inventory']['infra']['fmt'].remove('tests/a.tftest.hcl')
        data['results'] = [r for r in data['results'] if r['id'] != ['infra', 'tests/a.tftest.hcl', 'fmt']]
        self.base.write_text(json.dumps(data))
        self.expect(self.cli('check'), 2, 'inventario no corresponde')

    def test_stub_con_salida_fuera_de_contrato_termina_en_exit_2_sin_traceback(self):
        real = shutil.which('terraform')
        casos = {'evento que no es objeto': '[1]', 'test_run que no es objeto': '{"type":"test_run","test_run":5}',
                 'abstract sin contenido': '{"type":"test_abstract"}', 'summary que no es objeto': '{"type":"test_summary","test_summary":3}'}
        for label, salida in casos.items():
            with self.subTest(label):
                bin_dir = self.home / ('bin-' + str(abs(hash(label))))
                bin_dir.mkdir()
                stub = bin_dir / 'terraform'
                stub.write_text(f"#!/bin/sh\ncase \"$1\" in\n  version) exec {real} \"$@\" ;;\n  fmt|init) exit 0 ;;\n"
                                f"  validate) echo '{{\"valid\": true}}' ;;\n  test) echo '{salida}'; exit 0 ;;\nesac\n")
                stub.chmod(0o755)
                self.env['PATH'] = str(bin_dir) + os.pathsep + os.environ['PATH']
                self.base.unlink(missing_ok=True)
                r = self.cli('base')
                self.expect(r, 2, 'no pude medir')
                self.assertFalse(self.base.exists())
        self.env['PATH'] = os.environ['PATH']

    def test_un_comando_que_se_cuelga_es_invalid_por_timeout(self):
        with mock.patch.dict(tf.TIMEOUTS, {'test': 1}):
            with self.assertRaisesRegex(Invalid, 'excedio 1s'):
                tf.run_process(['sleep', '10'], self.home, os.environ.copy(), 'test', quiet=True)

    def test_base_con_otra_version_de_terraform_se_rechaza(self):
        data = self.measured_base()
        data['toolchain']['terraform_version'] = '0.0.1'
        self.base.write_text(json.dumps(data))
        self.expect(self.cli('check'), 2, 'toolchain stale')

    def test_base_cuyo_sha_no_es_ancestro_del_head_se_rechaza(self):
        anterior = self.git('rev-parse', 'HEAD')
        self.write('infra/extra.tf', 'variable "e" {\n  default = 1\n}\n')
        self.commit('rama que se abandona')
        self.measured_base()
        self.git('reset', '-q', '--hard', anterior)
        self.expect(self.cli('check'), 2, 'merge-base')

    def test_init_o_validate_rotos_bloquean(self):
        self.measured_base()
        self.write('infra/main.tf', MAIN + 'output "z" {\n  value = var.no_existe\n}\n')
        self.commit('validate roto en una raiz con tests')
        # sus runs ya no se miden: desaparecen respecto de la base
        self.expect(self.cli('check'), 2, 'desaparecidos')
        self.base.unlink()
        data = self.measured_base()  # como base es deuda: validate en rojo y sin runs
        self.assertEqual({tuple(x['id']): x['state'] for x in data['results']}[('infra', '<validate>', 'validate')], 'fail')

    def test_init_escribe_su_data_dir_fuera_del_repo(self):
        self.write('infra/main.tf', MAIN + 'module "m" {\n  source = "./m"\n}\n')
        self.write('infra/m/main.tf', 'output "z" {\n  value = 1\n}\n')
        self.commit('un modulo local obliga a init a escribir .terraform/modules')
        self.measured_base()
        self.assertFalse((self.repo / 'infra/.terraform').exists())
        self.assert_repo_intact()

    def test_lock_que_init_cambiaria_bloquea_y_no_se_toca(self):
        lock = ('provider "registry.terraform.io/hashicorp/null" {\n  version     = "3.2.4"\n'
                '  constraints = "~> 3.0"\n  hashes = [\n    "h1:hPknxdlW/xw7bBLlEmbunPTPwEEOUWdoHPtH/bjJ6g0=",\n  ]\n}\n')
        self.write('infra/.terraform.lock.hcl', lock)
        self.commit('lock con un provider que ya no se usa')
        self.expect(self.cli('base'), 2, 'terraform init fallo')
        self.assertEqual((self.repo / 'infra/.terraform.lock.hcl').read_text(), lock)
        self.assert_repo_intact()

    def test_fmt_desformateado_cuenta_como_fail(self):
        self.measured_base()
        self.write('infra/main.tf', MAIN.replace('type    = number', 'type=number'))
        self.commit('desformatea')
        r = self.cli('check')
        self.expect(r, 1, 'infra::main.tf::fmt')
        # como deuda de la base, no bloquea
        self.base.unlink()
        data = self.measured_base()
        self.assertEqual({tuple(x['id']): x['state'] for x in data['results']}[('infra', 'main.tf', 'fmt')], 'fail')
        self.expect(self.cli('check'), 0, 'deuda preexistente')

    def test_repo_sin_tftest_es_invalid(self):
        self.git('rm', '-q', TEST_FILE)
        self.commit('sin tests')
        self.expect(self.cli('base'), 2, 'terraform: sin raices (.terraform.lock.hcl ni *.tftest.hcl): nada que medir')

    def test_head_detached_bloquea(self):
        self.git('checkout', '-q', '--detach')
        self.expect(self.cli('base'), 2, 'detached')

    def test_retirados_se_rechaza_explicitamente(self):
        self.measured_base()
        retirados = self.home / 'retirados.json'
        retirados.write_text('{}')
        self.expect(self.cli('check', '--retirados', str(retirados)), 2, 'no admite --retirados')

    def test_base_ajena_o_adulterada_no_se_acepta(self):
        data = self.measured_base()
        for label, mutate, reason in (
                ('repo', lambda d: d.update(repo='/otro'), 'ajena'),
                ('resultado', lambda d: d['results'][0].update(state='fail'), 'no corresponden'),
                ('comando', lambda d: d['execution']['infra']['test'].update(argv=['terraform', 'test']), 'comando cerrado'),
                ('sha', lambda d: d.update(sha='0' * 40), 'ancestro|Git no verificable|tree'),
        ):
            with self.subTest(label):
                value = json.loads(json.dumps(data))
                mutate(value)
                self.base.write_text(json.dumps(value))
                r = self.cli('check')
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertTrue(any(x in r.stdout + r.stderr for x in reason.split('|')), r.stdout + r.stderr)

    def test_base_que_no_midio_todas_las_raices_de_su_commit_no_sirve(self):
        self.write('otra/main.tf', MAIN)
        self.write('otra/b.tftest.hcl', run_ok('b'))
        self.commit('segunda raiz, la base ya existe sin ella')
        data = self.measured_base()
        data['execution'].pop('otra')
        data['inventory'].pop('otra')
        data['results'] = [r for r in data['results'] if r['id'][0] != 'otra']
        self.base.write_text(json.dumps(data))
        self.expect(self.cli('check'), 2, 'todas las raices')

    def test_dos_raices_cada_una_con_su_fmt(self):
        self.write('otra/main.tf', MAIN)
        self.write('otra/b.tftest.hcl', run_ok('b'))
        self.commit('segunda raiz con el test junto al main')
        data = self.measured_base()
        self.assertEqual(sorted(data['execution']), ['infra', 'otra'])
        ids = {tuple(x['id']) for x in data['results']}
        self.assertIn(('otra', 'b.tftest.hcl', 'b'), ids)
        self.assertIn(('otra', 'main.tf', 'fmt'), ids)
        self.expect(self.cli('check'), 0)

    def test_base_dentro_del_repo_no_se_acepta(self):
        self.base = self.repo / 'base.json'
        self.expect(self.cli('base'), 2, 'fuera del repo')


class RaicesTests(TerraformFixture):
    def test_raices_en_tests_o_junto_al_main_y_sin_terraform_dir(self):
        self.write('a/tests/x.tftest.hcl', run_ok('x'))
        self.write('b/y.tftest.hcl', run_ok('y'))
        self.write('b/tests/z.tftest.hcl', run_ok('z'))
        self.write('c/.terraform/modules/m/tests/w.tftest.hcl', run_ok('w'))
        self.write('tests/r.tftest.hcl', run_ok('r'))
        self.git('add', '-f', 'c')  # .terraform/ esta en .gitignore: se fuerza como si estuviera versionado
        self.commit('raices')
        self.write('lock/.terraform.lock.hcl', '# lock\n')
        self.commit('raiz solo con lockfile')
        self.assertEqual(tf.raices(self.repo), ['.', 'a', 'b', 'infra', 'lock'])
        self.assertEqual(tf.inventario(self.repo, 'HEAD', ['b'])['b']['tests'], ['tests/z.tftest.hcl', 'y.tftest.hcl'])

    def test_sin_tests_es_invalid(self):
        self.git('rm', '-q', TEST_FILE)
        self.commit('sin tests')
        with self.assertRaisesRegex(Invalid, r'terraform: sin raices'):
            tf.raices(self.repo)

    def test_no_versionados_no_cuentan(self):
        self.write('extra/q.tftest.hcl', run_ok('q'))  # sin git add
        self.assertEqual(tf.raices(self.repo), ['infra'])


def evento(tipo, **datos):
    return json.dumps(dict({'type': tipo}, **datos))


def salida(runs, *, abstract=None, resumen=None, extra=()):
    """runs: [(archivo, nombre, status)] -> stdout de `terraform test -json`."""
    if abstract is None:
        abstract = {}
        for archivo, nombre, _ in runs:
            abstract.setdefault(archivo, []).append(nombre)
    lines = [evento('test_abstract', test_abstract=abstract)]
    for archivo, nombre, status in runs:
        lines.append(evento('test_run', test_run=dict(path=archivo, run=nombre, progress='complete', status=status)))
    tally = {s: sum(r[2] == s for r in runs) for s in ('pass', 'fail', 'error', 'skip')}
    resumen = resumen or dict(status='pass', passed=tally['pass'], failed=tally['fail'],
                              errored=tally['error'], skipped=tally['skip'])
    lines += list(extra) + [evento('test_summary', test_summary=resumen)]
    return '\n'.join(lines) + '\n'


class ParseTestTests(unittest.TestCase):
    """Las coherencias de parse_test sobre eventos sinteticos (no ejecutan terraform)."""

    def parse(self, stdout, exit=0, tests=None):
        if tests is None:  # inventario coherente con lo que reporta el abstract
            tests = []
            for line in stdout.splitlines():
                if line.startswith('{') and '"test_abstract"' in line:
                    try:
                        tests = sorted(json.loads(line)['test_abstract'])
                    except (ValueError, TypeError, KeyError):
                        pass
        return tf.parse_test('r', dict(argv=[], exit=exit, stdout=stdout, stderr=''), tests)

    def test_verde_y_rojo_con_error_contado_como_fail(self):
        verde = self.parse(salida([('t.tftest.hcl', 'a', 'pass'), ('t.tftest.hcl', 'b', 'pass')]))
        self.assertEqual([x['state'] for x in verde], ['pass', 'pass'])
        rojo = self.parse(salida([('t.tftest.hcl', 'a', 'fail'), ('t.tftest.hcl', 'b', 'error')]), exit=1)
        self.assertEqual([x['state'] for x in rojo], ['fail', 'fail'])
        self.assertEqual(rojo[0]['id'], ['r', 't.tftest.hcl', 'a'])

    def test_incoherencias_son_invalid(self):
        a = ('t.tftest.hcl', 'a', 'pass')
        casos = {
            'skip': (salida([a, ('t.tftest.hcl', 'b', 'skip')]), 0, 'skip'),
            'cero runs': (salida([]), 0, 'cero runs'),
            'run sin final': (salida([a], abstract={'t.tftest.hcl': ['a', 'b']}), 0, 'sin final'),
            'run fuera del abstract': (salida([a, ('t.tftest.hcl', 'c', 'pass')], abstract={'t.tftest.hcl': ['a']}), 0, 'fuera del abstract'),
            'dos finales': (salida([a, a], abstract={'t.tftest.hcl': ['a']}), 0, 'dos finales'),
            'conteo del resumen': (salida([a], resumen=dict(status='pass', passed=2, failed=0, errored=0, skipped=0)), 0, 'passed'),
            'exit 1 sin rojos': (salida([a]), 1, 'exit'),
            'exit 0 con rojos': (salida([('t.tftest.hcl', 'a', 'fail')]), 0, 'exit'),
            'sin resumen': (salida([a]).rsplit('\n', 2)[0] + '\n', 0, 'test_summary'),
            'sin abstract': ('\n'.join(salida([a]).splitlines()[1:]) + '\n', 0, 'test_abstract'),
            'run duplicado en el abstract': (salida([a], abstract={'t.tftest.hcl': ['a', 'a']}), 0, 'duplicado'),
            'json roto': ('no es json\n', 0, 'JSON'),
        }
        for label, (stdout, exit, reason) in casos.items():
            with self.subTest(label):
                with self.assertRaises(Invalid) as ctx:
                    self.parse(stdout, exit)
                self.assertIn(reason, str(ctx.exception))

    def test_inventario_independiente_y_nombre_reservado(self):
        a = ('t.tftest.hcl', 'a', 'pass')
        with self.assertRaisesRegex(Invalid, 'inventario incompleto'):
            self.parse(salida([a]), tests=['t.tftest.hcl', 'otro.tftest.hcl'])
        with self.assertRaisesRegex(Invalid, 'inventario incompleto'):
            self.parse(salida([a]), tests=[])
        with self.assertRaisesRegex(Invalid, 'reservado'):
            self.parse(salida([('t.tftest.hcl', 'fmt', 'pass')]))

    def test_campos_de_otro_tipo_son_invalid_no_excepciones(self):
        run = dict(argv=[], exit=0, stdout='', stderr='')
        for label, runs in {'fmt sin exit': dict(fmt={}, init=run, validate=run),
                            'validate sin json': dict(fmt=run, init=run, validate=dict(run, stdout='[]'))}.items():
            with self.subTest(label):
                with self.assertRaises(Invalid):
                    tf.evaluar('r', {'tests': [], 'fmt': []}, runs)

    def test_ids_duplicados_entre_raices_o_archivos_no_se_aceptan(self):
        dup = [{'id': ['r', 'f', 'a'], 'state': 'pass'}, {'id': ['r', 'f', 'a'], 'state': 'pass'}]
        with self.assertRaises(Invalid):
            tf.unique_results(dup)
        with self.assertRaises(Invalid):
            tf.unique_results([])


class TerraformDispatchTests(TerraformFixture):
    def test_terraform_solo_con_tf_y_sin_go_ni_frontend(self):
        self.assertTrue(medicion_destino._terraform(self.repo))
        for marca in ('go.mod', 'package.json', 'angular.json'):
            with self.subTest(marca):
                self.write(marca, '{}')
                self.assertFalse(medicion_destino._terraform(self.repo))
                (self.repo / marca).unlink()
        self.assertTrue(medicion_destino._terraform(self.repo))

    def test_repo_sin_tf_versionados_no_es_terraform(self):
        self.git('rm', '-q', '-r', 'infra')
        self.write('README.md', 'x')
        self.commit('sin tf')
        self.assertFalse(medicion_destino._terraform(self.repo))

    def test_tf_sin_versionar_no_cuenta(self):
        self.git('rm', '-q', '-r', 'infra')
        self.commit('sin tf')
        self.write('suelto/x.tf', MAIN)
        self.assertFalse(medicion_destino._terraform(self.repo))

    def test_repo_mixto_go_mod_mas_tf_no_se_trata_como_terraform(self):
        self.write('go.mod', 'module fixture.invalid/mixto\n\ngo 1.22\n')
        self.commit('go.mod')
        self.assertFalse(medicion_destino._terraform(self.repo))
        self.assertFalse(medicion_destino._frontend(self.repo))


class CierreTerraformTests(TerraformFixture):
    """close --integrated con destino Terraform, por --postmerge y por --historico."""

    def setUp(self):
        super().setUp()
        # El repo vive como microservicio `infra` dentro de la raiz del proyecto.
        self.root = self.home / 'project'
        (self.root / 'docs').mkdir(parents=True)
        (self.root / 'harness/progress').mkdir(parents=True)
        repo = self.root / 'infra'
        self.repo.rename(repo)
        self.repo = repo
        self.env.update(HARNESS_SKILLS_DIR=str(self.home / 'skills'))
        lesson = self.home / 'skills/closure-contract/SKILL.md'
        lesson.parent.mkdir(parents=True)
        lesson.write_text('---\nname: closure-contract\ndescription: Fixture\n---\n')
        self.base_sha = self.git('rev-parse', 'HEAD')
        self.backlog = self.root / 'harness/feature_list.json'
        self.backlog.write_text(json.dumps(dict(project='fixture', rules={}, features=[
            dict(id=9, name='Terraform fixture', status='in_progress', microservicios=['infra'])])))
        (self.root / 'docs/spec-feature-9-terraform-fixture.md').write_text(
            'Estado: draft\n- AC-1: Given terraform When integrated Then measured\n'
            'Comando: `git -C infra merge-base --is-ancestor HEAD HEAD`\n')
        for name in ('impl-9.md', 'review-9.md'):
            (self.root / 'docs' / name).write_text('## AC-1\ninfra/feature.txt:1\n')
        (self.root / 'harness/progress/current-9.md').write_text('Fixture progress\n')
        self.script('gate.py', 'approve-spec', '--feature', '9', '--yes', '--por', 'Fixture')

    def script(self, name, *args, code=0):
        r = subprocess.run([sys.executable, '-B', str(SCRIPTS / name), *args], cwd=self.root, env=self.env,
                           capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        return r

    def feature(self, test=None, main=None, marca=True):
        """La feature se integra en el mismo repo (worktree == repo)."""
        if marca:
            self.write('feature.txt', 'delta\n')
        if test is not None:
            self.write(TEST_FILE, test)
        if main is not None:
            self.write('infra/main.tf', main)
        return self.commit('feature')

    def register(self, source, target=None):
        row = dict(microservicio='infra', repo=str(self.repo), worktree=str(self.repo), base_sha=self.base_sha,
                   source_sha=source, target_sha=target or source, target_branch='develop')
        manifest = self.home / 'manifest.json'
        manifest.write_text(json.dumps(dict(version=1, feature='9', repos=[row])))
        self.script('worktree.py', 'register', '--feature', '9', '--manifest', str(manifest))
        self.script('gate.py', 'verify', '--feature', '9')
        self.script('gate.py', 'revision', '--feature', '9', '--veredicto', 'approved', '--por', 'Fixture reviewer')
        return row

    def snapshot(self):
        return {str(p): p.read_bytes() for base in (self.root / 'docs', self.root / 'harness')
                for p in base.rglob('*') if p.is_file()}

    def close(self, *extra, historico=False):
        args = ['gate.py', 'close', '--feature', '9', '--status', 'done', '--to', 'develop', '--integrated',
                '--leccion', 'closure-contract']
        if historico:
            args += ['--historico', '--yes', '--motivo', 'Base preintegracion no medible']
        r = subprocess.run([sys.executable, '-B', str(SCRIPTS / args[0]), *args[1:], *extra], cwd=self.root,
                           env=self.env, capture_output=True, text=True, timeout=900)
        self.assertNotIn('Traceback', r.stderr)
        return r

    # -- --postmerge -----------------------------------------------------------

    def test_postmerge_mide_terraform_y_ata_la_medicion_al_target(self):
        mapa = self.postmerge_map_en_base()
        source = self.feature(test=TESTS + run_ok('nuevo'))
        row = self.register(source)
        r = self.close('--postmerge', str(mapa))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        receipt = json.loads(self.backlog.read_text())['features'][0]['mediciones_destino'][0]
        self.assertEqual(receipt['integration'], row)
        self.assertEqual(receipt['measurement']['sha'], row['target_sha'])
        self.assertEqual(len(receipt['measurement']['results']), 6)
        self.assertIn('postmerge_terraform.py', receipt['runner_sha256'])
        self.assertEqual(receipt['delta']['new'], [])

    def test_postmerge_rojo_nuevo_bloquea_y_preserva_documentos(self):
        mapa = self.postmerge_map_en_base()
        source = self.feature(test=TESTS.replace('output.y == 2', 'output.y == 3'))
        self.register(source)
        before = self.snapshot()
        r = self.close('--postmerge', str(mapa))
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('rojos nuevos', r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_postmerge_con_retirados_se_rechaza_para_terraform(self):
        mapa = self.postmerge_map_en_base()
        source = self.feature(test=TESTS + run_ok('nuevo'))
        self.register(source)
        retirados = self.home / 'retirados.json'
        retirados.write_text(json.dumps(dict(version=1, feature='9', retirados={'infra': ['pkg::TestX']})))
        before = self.snapshot()
        r = self.close('--postmerge', str(mapa), '--retirados', str(retirados))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('destino Terraform: no admite --retirados', r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)

    def postmerge_map_en_base(self):
        """Mide la base en base_sha (rama develop, antes de la feature)."""
        base = self.home / 'base-infra.json'
        r = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'postmerge_terraform.py'), 'base', '--repo',
                            str(self.repo), '--guardar', str(base)], env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        mapa = self.home / 'postmerge.json'
        mapa.write_text(json.dumps(dict(version=1, feature='9', bases={'infra': str(base)})))
        return mapa

    # -- --historico -----------------------------------------------------------

    def test_historico_run_agregado_y_medido_cierra(self):
        source = self.feature(test=TESTS + run_ok('nuevo'))
        self.register(source)
        r = self.close(historico=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        medicion = json.loads(self.backlog.read_text())['features'][0]['mediciones_destino'][0]
        self.assertEqual(medicion['modo'], 'historico')
        self.assertEqual(medicion['tests_agregados'], ['infra/tests/a.tftest.hcl::nuevo'])
        self.assertEqual(medicion['measurement']['sha'], source)
        self.assertEqual(len(medicion['measurement']['results']), 6)
        self.assertNotIn('base', medicion)

    def test_historico_run_agregado_que_no_se_mide_bloquea(self):
        source = self.feature(test=TESTS + run_ok('nuevo'))
        self.write(TEST_FILE, TESTS)
        target = self.commit('otra feature borra el run')
        self.register(source, target)
        before = self.snapshot()
        r = self.close(historico=True)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('historico: tests de la feature ausentes sin declarar: infra/tests/a.tftest.hcl::nuevo',
                      r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_historico_run_que_la_feature_borra_bloquea(self):
        source = self.feature(test=TESTS.split('\nrun "override"')[0])
        self.register(source)
        before = self.snapshot()
        r = self.close(historico=True)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('la feature borra runs y terraform no admite --retirados: infra/tests/a.tftest.hcl::override',
                      r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_historico_delta_de_codigo_sin_tests_nuevos_bloquea(self):
        source = self.feature(main=MAIN + '\noutput "z" {\n  value = var.x\n}\n', marca=False)
        self.register(source)
        before = self.snapshot()
        r = self.close(historico=True)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('modifica codigo sin agregar ningun test', r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_historico_delta_solo_de_tests_sin_runs_nuevos_cierra(self):
        source = self.feature(test=TESTS.replace('y debe ser 1', 'y vale 1'), marca=False)
        self.register(source)
        r = self.close(historico=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        medicion = json.loads(self.backlog.read_text())['features'][0]['mediciones_destino'][0]
        self.assertEqual(medicion['tests_agregados'], [])

    def test_historico_rojo_en_el_destino_bloquea(self):
        source = self.feature(test=TESTS.replace('output.y == 2', 'output.y == 3') + run_ok('nuevo'))
        self.register(source)
        r = self.close(historico=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('historico: rojos en el destino: infra::tests/a.tftest.hcl::override', r.stdout + r.stderr)

    def test_historico_con_retirados_se_rechaza_para_terraform(self):
        source = self.feature(test=TESTS + run_ok('nuevo'))
        self.register(source)
        retirados = self.home / 'retirados.json'
        retirados.write_text(json.dumps(dict(version=1, feature='9', retirados={'infra': ['pkg::TestX']})))
        before = self.snapshot()
        r = self.close('--retirados', str(retirados), historico=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('destino Terraform: no admite --retirados', r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_runs_agregados_lee_los_blobs_por_archivo_y_nombre(self):
        self.write(TEST_FILE, TESTS + '# run "comentado" {\n' + run_ok('real'))
        self.write('infra/otro.tftest.hcl', run_ok('defaults'))  # mismo nombre, otro archivo: es nuevo
        self.commit('mas runs')
        agregados = medicion_destino.runs_agregados_tf(str(self.repo), self.base_sha, self.git('rev-parse', 'HEAD'))
        self.assertEqual(agregados, {(TEST_FILE, 'real'), ('infra/otro.tftest.hcl', 'defaults')})


if __name__ == '__main__':
    unittest.main()
