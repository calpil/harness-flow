#!/usr/bin/env python3
"""Base/check Terraform: fmt + init(-backend=false) + validate + `terraform test`.

Solo stdlib y el binario `terraform` del PATH. Sin shell ni --cmd. Nunca corre
plan/apply contra un state: init va SIEMPRE con -backend=false y TF_DATA_DIR en
un directorio temporal propio de la medicion (el repo no recibe .terraform/ ni
cambios en .terraform.lock.hcl: init corre con -lockfile=readonly).
Una RAIZ es un directorio con al menos un *.tftest.hcl versionado en
<dir>/tests/ o en <dir>/. Cada raiz aporta un caso de formato (`<fmt>`) y un
caso por cada `run "<nombre>"` de sus archivos de test.
0: medicion completa sin regresiones; 1: rojos nuevos; 2: no pude medir.
No hay --retirados: un test que desaparece bloquea siempre.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

from multirepo import Invalid, require, read_manifest, git, _clean

PROTOCOL = 'terraform-test-json-v1'
FMT = '<fmt>'
TEST_SUFFIX = '.tftest.hcl'
TIMEOUT = 1800
STATUS = ('pass', 'fail', 'error', 'skip')
# Variables TF_* que se conservan (no cambian el resultado): el resto se descarta.
TF_CONSERVADAS = ('TF_PLUGIN_CACHE_DIR', 'TF_CLI_CONFIG_FILE')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'JSON con clave duplicada')
            result[key] = value
        return result
    try:
        return json.loads(text, object_pairs_hook=unique)
    except ValueError as exc:
        if isinstance(exc, Invalid):
            raise
        raise Invalid('terraform: salida JSON invalida (' + str(exc)[:80] + ')') from exc


def count(value, expected, label):
    require(type(value) is int and value == expected, label + ': conteo/exit incoherente')


def environment():
    env = {k: v for k, v in os.environ.items() if not k.startswith('TF_') or k in TF_CONSERVADAS}
    env.pop('CHECKPOINT_DISABLE', None)
    env.update(TF_IN_AUTOMATION='1', TF_INPUT='0', CHECKPOINT_DISABLE='1')
    return env


def _cola(text, n=2000):
    text = (text or '').strip()
    return text if len(text) <= n else '...' + text[-n:]


# --- descubrimiento de raices -------------------------------------------------

def _archivos(repo, ref=None):
    """Rutas versionadas: del indice (HEAD con arbol limpio) o de un commit."""
    if ref is None:
        salida = git(repo, 'ls-files', '-z')
    else:
        salida = git(repo, 'ls-tree', '-r', '--name-only', '-z', ref)
    return [x for x in salida.split('\0') if x]


def archivos_test(repo, ref=None):
    """*.tftest.hcl versionados, fuera de .terraform/."""
    return sorted(x for x in _archivos(repo, ref)
                  if x.endswith(TEST_SUFFIX) and '.terraform' not in PurePosixPath(x).parts)


def raices(repo, ref=None):
    """Directorios (rutas POSIX relativas, '.' = raiz del repo) con tests."""
    encontradas = set()
    for ruta in archivos_test(repo, ref):
        carpeta = PurePosixPath(ruta).parent
        if carpeta.name == 'tests':
            carpeta = carpeta.parent
        encontradas.add(carpeta.as_posix())
    require(encontradas, 'terraform: sin tests (*.tftest.hcl): nada que medir')
    return sorted(encontradas)


# --- ejecucion ------------------------------------------------------------------

def toolchain(repo, env):
    binary = shutil.which('terraform', path=env.get('PATH'))
    if binary is None:
        raise Invalid('Terraform ausente')
    binary = str(Path(binary).resolve())
    r = subprocess.run([binary, 'version', '-json'], cwd=repo, env=env, capture_output=True,
                       text=True, encoding='utf-8', timeout=120)
    require(r.returncode == 0, 'terraform version fallo: ' + _cola(r.stderr))
    data = load_json(r.stdout)
    version = data.get('terraform_version') if isinstance(data, dict) else None
    require(isinstance(version, str) and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?', version),
            'toolchain fuera de contrato: terraform sin version')
    return {'terraform': binary, 'terraform_version': version,
            'platform': data.get('platform') if isinstance(data.get('platform'), str) else '',
            'terraform_sha256': digest(binary)}


def run_process(argv, cwd, env):
    print('$ ' + json.dumps(argv), flush=True)
    r = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True,
                       encoding='utf-8', timeout=TIMEOUT)
    return {'argv': argv, 'exit': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}


def comandos(binary):
    return {'fmt': [binary, 'fmt', '-check', '-recursive', '-no-color'],
            'init': [binary, 'init', '-backend=false', '-input=false', '-no-color', '-lockfile=readonly'],
            'validate': [binary, 'validate', '-json', '-no-color'],
            'test': [binary, 'test', '-json', '-no-color']}


def evaluar_fmt(raiz, run):
    require(run['exit'] in (0, 3), f'terraform fmt fallo en {raiz}: ' + _cola(run['stderr'] or run['stdout']))
    return {'id': [raiz, FMT, 'fmt'], 'state': 'pass' if run['exit'] == 0 else 'fail'}


def evaluar_init(raiz, run):
    require(run['exit'] == 0, f'terraform init fallo en {raiz}: ' + _cola(run['stderr'] or run['stdout']))


def evaluar_validate(raiz, run):
    data = load_json(run['stdout']) if run['stdout'].strip() else None
    require(isinstance(data, dict) and data.get('valid') is True and run['exit'] == 0,
            f'terraform validate no es valido en {raiz}: ' + _cola(run['stdout'] or run['stderr']))


def parse_test(raiz, run):
    """Eventos de `terraform test -json` -> casos [raiz, archivo, run]."""
    abstract, complete, summaries = None, {}, []
    for line in run['stdout'].splitlines():
        if not line.strip():
            continue
        event = load_json(line)
        require(isinstance(event, dict), 'terraform test: evento invalido')
        kind = event.get('type')
        if kind == 'test_abstract':
            require(abstract is None, 'terraform test: test_abstract duplicado')
            abstract = event['test_abstract']
            require(isinstance(abstract, dict) and all(
                isinstance(k, str) and isinstance(v, list) and all(isinstance(x, str) for x in v)
                and len(v) == len(set(v)) for k, v in abstract.items()),
                'terraform test: test_abstract invalido/run duplicado en un archivo')
        elif kind == 'test_run':
            item = event['test_run']
            if item.get('progress') != 'complete':
                continue
            key = (item['path'], item['run'])
            require(key not in complete, 'terraform test: run con dos finales: ' + '::'.join(key))
            require(item.get('status') in STATUS, 'terraform test: estado de run desconocido')
            complete[key] = item['status']
        elif kind == 'test_summary':
            summaries.append(event['test_summary'])
    require(abstract is not None, 'terraform test: falta test_abstract')
    declared = {(path, name) for path, names in abstract.items() for name in names}
    require(declared, 'terraform test: cero runs en ' + raiz)
    require(set(complete) == declared, 'terraform test: runs declarados sin final o finales fuera del abstract')
    require(len(summaries) == 1, 'terraform test: falta/duplicado test_summary')
    tally = {s: sum(v == s for v in complete.values()) for s in STATUS}
    summary = summaries[0]
    for field, status in (('passed', 'pass'), ('failed', 'fail'), ('errored', 'error'), ('skipped', 'skip')):
        count(summary.get(field), tally[status], 'terraform test ' + field)
    count(run['exit'], int(tally['fail'] + tally['error'] > 0), 'terraform test exit')
    require(not tally['skip'], f"terraform test: runs en skip en {raiz}; medicion incompleta: "
            + ', '.join('::'.join(k) for k, v in sorted(complete.items()) if v == 'skip'))
    return [{'id': [raiz, path, name], 'state': 'pass' if complete[(path, name)] == 'pass' else 'fail'}
            for path, names in abstract.items() for name in names]


def unique_results(tests):
    require(tests and all(r['state'] in ('pass', 'fail') for r in tests), 'tests vacios/skip/no terminales')
    require(len(tests) == len({tuple(r['id']) for r in tests}), 'identidad test duplicada/ambigua')
    return tests


def evaluar(raiz, execution):
    """Resultados de una raiz a partir del raw de sus 4 comandos."""
    out = [evaluar_fmt(raiz, execution['fmt'])]
    evaluar_init(raiz, execution['init'])
    evaluar_validate(raiz, execution['validate'])
    return out + parse_test(raiz, execution['test'])


def _ignorados(repo):
    return sorted(x for x in git(repo, 'ls-files', '-o', '-i', '--exclude-standard', '--directory', '-z').split('\0') if x)


def _raiz_dir(repo, raiz):
    path = (repo / raiz).resolve()
    require(path.is_dir() and path.is_relative_to(repo), 'terraform: raiz fuera del repo: ' + raiz)
    return path


def measure(repo, trace=None):
    repo = Path(repo).resolve()
    env = environment()
    _clean(repo)
    branch, sha = git(repo, 'branch', '--show-current'), git(repo, 'rev-parse', 'HEAD')
    require(branch, 'rama destino detached: no pude medir integracion')
    tree = git(repo, 'rev-parse', 'HEAD^{tree}')
    found, tools = raices(repo), toolchain(repo, env)
    ignorados = _ignorados(repo)
    execution, results = {}, []
    if trace is not None:
        trace.update(repo=str(repo), rama=branch, sha=sha, toolchain=tools, execution=execution)
    cmds = comandos(tools['terraform'])
    for raiz in found:
        cwd = _raiz_dir(repo, raiz)
        runs = execution[raiz] = {}
        with tempfile.TemporaryDirectory(prefix='terraform-measure-') as data_dir:
            renv = dict(env, TF_DATA_DIR=data_dir)
            runs['fmt'] = run_process(cmds['fmt'], cwd, renv)
            results.append(evaluar_fmt(raiz, runs['fmt']))
            runs['init'] = run_process(cmds['init'], cwd, renv)
            evaluar_init(raiz, runs['init'])
            runs['validate'] = run_process(cmds['validate'], cwd, renv)
            evaluar_validate(raiz, runs['validate'])
            runs['test'] = run_process(cmds['test'], cwd, renv)
            results += parse_test(raiz, runs['test'])
    _clean(repo)
    require(_ignorados(repo) == ignorados, 'terraform dejo archivos ignorados en el repo (.terraform/?)')
    require((branch, sha) == (git(repo, 'branch', '--show-current'), git(repo, 'rev-parse', 'HEAD')),
            'contexto Git cambio durante medicion')
    require(toolchain(repo, environment()) == tools, 'toolchain cambio durante medicion')
    measured = {'version': 1, 'protocol': PROTOCOL, 'repo': str(repo), 'rama': branch, 'sha': sha,
                'tree': tree, 'toolchain': tools, 'results': unique_results(results), 'execution': execution}
    validate_measurement(measured)
    return measured


def validate_measurement(data):
    require(isinstance(data, dict) and set(data) == {'version', 'protocol', 'repo', 'rama', 'sha', 'tree',
            'toolchain', 'results', 'execution'}, 'base esquema invalido')
    count(data['version'], 1, 'base version')
    require(data['protocol'] == PROTOCOL, 'base protocolo incompatible')
    tools = data['toolchain']
    require(isinstance(tools, dict) and set(tools) == {'terraform', 'terraform_version', 'platform', 'terraform_sha256'}
            and all(isinstance(v, str) for v in tools.values()), 'base toolchain invalido')
    execution = data['execution']
    require(isinstance(execution, dict) and execution and list(execution) == sorted(execution),
            'base falta/desordena raices')
    cmds, tests = comandos(tools['terraform']), []
    for raiz, runs in execution.items():
        require(isinstance(raiz, str) and raiz and not PurePosixPath(raiz).is_absolute()
                and '..' not in PurePosixPath(raiz).parts, 'base raiz invalida')
        require(isinstance(runs, dict) and set(runs) == set(cmds), 'base ejecucion esquema invalido')
        for name, run in runs.items():
            require(isinstance(run, dict) and set(run) == {'argv', 'exit', 'stdout', 'stderr'}
                    and type(run['exit']) is int and isinstance(run['stdout'], str)
                    and isinstance(run['stderr'], str), 'base ejecucion sin raw completo')
            require(run['argv'] == cmds[name], 'base ejecucion no corresponde al comando cerrado')
        tests += evaluar(raiz, runs)
    unique_results(tests)
    require(data['results'] == tests, 'base resultados no corresponden a ejecucion real')
    return data


def read_base(path, repo, branch, tip, expected_base=None):
    path, repo = Path(path), Path(repo).resolve()
    require(path.is_file() and not path.is_symlink(), 'base ausente/no regular')
    data = validate_measurement(read_manifest(path))
    require(data['repo'] == str(repo) and data['rama'] == branch, 'base de repo/rama ajena')
    require(re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', data['sha']), 'base SHA invalido')
    require(expected_base is None or data['sha'] == expected_base, 'base stale/no corresponde a base_sha')
    git(repo, 'merge-base', '--is-ancestor', data['sha'], tip)
    require(data['tree'] == git(repo, 'rev-parse', data['sha'] + '^{tree}'), 'base tree/SHA incoherente')
    # La base tiene que haber medido TODAS las raices de su propio commit: si no,
    # los tests de una raiz omitida podrian desaparecer sin aviso.
    require(sorted(data['execution']) == raices(repo, data['sha']), 'base no midio todas las raices de su commit')
    require(data['toolchain'] == toolchain(repo, environment()), 'base toolchain stale')
    return data


def compare(base, measured):
    before = {tuple(r['id']): r['state'] for r in base['results']}
    after = {tuple(r['id']): r['state'] for r in measured['results']}
    missing = sorted(before.keys() - after.keys())
    require(not missing, 'tests desaparecidos u omitidos: ' + ', '.join('::'.join(x) for x in missing))
    reds = {k for k, state in after.items() if state == 'fail'}
    debt = {k for k, state in before.items() if state == 'fail'}
    return {'new': sorted(reds - debt), 'debt': sorted(reds & debt),
            'cured': sorted(k for k in debt if after.get(k) == 'pass')}


def check_destination(row, path):
    """Invocado por close, nunca un recibo PASS ni un comando configurable."""
    path = Path(path)
    trace = {'exit': 2, 'execution': {}, 'integration': row}
    evidence = path.with_name(path.name + '.' + uuid.uuid4().hex + '.close.evidence.json')
    require(not evidence.resolve().is_relative_to(Path(row['repo']).resolve()),
            'evidencia de cierre debe vivir fuera del repo medido')
    with evidence.open('x', encoding='utf-8') as stream:
        try:
            before = digest(path)
            base = read_base(path, row['repo'], row['target_branch'], row['target_sha'], row['base_sha'])
            measured = measure(row['repo'], trace)
            require(measured['sha'] == row['target_sha'], 'postmerge: target stale')
            delta = compare(base, measured)
            require(digest(path) == before, 'postmerge: base cambio durante medicion')
            trace.update(exit=1 if delta['new'] else 0, delta=delta, measurement=measured)
            require(not delta['new'], 'postmerge: rojos nuevos: ' + ', '.join('::'.join(x) for x in delta['new']))
            return {'base': str(path.resolve()), 'base_sha256': before, 'measurement': measured,
                    'delta': delta, 'evidence': str(evidence)}
        except (Invalid, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            trace['error'] = str(exc)
            raise Invalid('terraform no comparable/sin cierre: ' + str(exc)) from exc
        finally:
            stream.write(json.dumps(trace, indent=2) + '\n')
            print('[i] evidencia terraform: ' + str(evidence))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='action', required=True)
    for action, flag in (('base', '--guardar'), ('check', '--base')):
        p = sub.add_parser(action)
        p.add_argument('--repo', required=True)
        p.add_argument(flag, required=True)
        p.add_argument('--evidence', help='JSON durable fuera del repo; nunca se sobrescribe')
        if action == 'check':
            p.add_argument('--retirados', help='NO soportado en destinos Terraform: se rechaza')
    args = ap.parse_args()
    trace = {'exit': 2, 'execution': {}}
    evidence = None
    try:
        require(not getattr(args, 'retirados', None),
                'terraform no admite --retirados: un test que desaparece bloquea siempre')
        repo = Path(args.repo).resolve()
        output = Path(args.guardar if args.action == 'base' else args.base).resolve()
        require(not output.is_relative_to(repo), 'base debe vivir fuera del repo medido')
        evidence_path = Path(args.evidence) if args.evidence else output.with_name(output.name + '.' + uuid.uuid4().hex + '.evidence.json')
        require(not evidence_path.resolve().is_relative_to(repo), 'evidencia debe vivir fuera del repo medido')
        evidence = evidence_path.open('x', encoding='utf-8')
        trace.update(action=args.action, evidence=str(evidence_path.absolute()))
        base = None
        if args.action == 'check':
            base_hash = digest(args.base)
            head = git(repo, 'rev-parse', 'HEAD')
            base = read_base(args.base, repo, git(repo, 'branch', '--show-current'), head)
        measured = measure(repo, trace)
        if args.action == 'base':
            with Path(args.guardar).open('x', encoding='utf-8') as stream:
                stream.write(json.dumps(measured, indent=2))
            print('[ok] base terraform medida: ' + str(len(measured['results'])) + ' casos en '
                  + str(len(measured['execution'])) + ' raices')
            trace.update(exit=0, measurement=measured)
            return 0
        require(digest(args.base) == base_hash, 'base cambio durante medicion')
        delta = compare(base, measured)
        for key, label in (('new', 'rojo nuevo'), ('debt', 'deuda preexistente'), ('cured', 'se curo')):
            for identity in delta[key]:
                print(f'[{key}] {label}: ' + '::'.join(identity))
        trace.update(exit=1 if delta['new'] else 0, delta=delta, measurement=measured)
        return trace['exit']
    except (Invalid, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        trace['error'] = str(exc)
        print(f'[!!] no pude medir: {exc}', file=sys.stderr)
        return 2
    finally:
        if evidence is not None:
            with evidence:
                evidence.write(json.dumps(trace, indent=2) + '\n')
            print('[i] evidencia: ' + trace['evidence'])


if __name__ == '__main__':
    sys.exit(main())
