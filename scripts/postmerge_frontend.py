#!/usr/bin/env python3
"""Base/check frontend ADR: Angular 22/Vitest 4 y node:test. Sin shell ni --cmd.

0: medicion completa sin regresiones; 1: rojos nuevos; 2: no pude medir.
No es build/SSG ni la suite legal cross-repo. No instala dependencias.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

from multirepo import Invalid, require, read_manifest, git, _clean

PROTOCOL = 'angular22-vitest4-node22-v1'
NODE_FILES = ['scripts/verificar-dist.test.mjs', 'scripts/catalogo-snapshot.test.mjs']
HELPERS = ('postmerge_frontend.py', 'frontend_node_reporter.mjs', 'frontend_vitest_reporter.mjs')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def environment():
    forbidden = [k for k, v in os.environ.items() if v and
                 (k.startswith(('NODE_', 'VITEST', 'NG_BUILD_', 'DIST_')) or k == 'HARNESS_FRONTEND_EVENTS')]
    require(not forbidden, 'entorno con override no permitido: ' + ', '.join(sorted(forbidden)))
    env = {k: os.environ[k] for k in ('PATH', 'HOME', 'USERPROFILE', 'TMPDIR', 'TEMP', 'TMP',
                                    'SystemRoot', 'SYSTEMROOT', 'COMSPEC', 'PATHEXT') if k in os.environ}
    env.update(CI='1', NG_CLI_ANALYTICS='false', NO_COLOR='1', TZ='UTC')
    return env


def scope(repo):
    package = read_manifest(repo / 'package.json')
    angular = read_manifest(repo / 'angular.json')
    projects = angular['projects']
    scripts = package['scripts']
    require(isinstance(projects, dict) and projects and all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', x)
                                                          for x in projects), 'contrato de proyectos invalido')
    require(scripts['test:dist'] == 'node --test ' + ' '.join(NODE_FILES), 'contrato node:test no soportado')
    require(not any(x in scripts for x in ('pretest', 'posttest', 'pretest:dist', 'posttest:dist')),
            'contrato no incluye hooks npm de test')
    require(isinstance(scripts, dict) and isinstance(scripts.get('test'), str),
            'contrato npm test requiere comando string')
    commands = scripts['test'].split(' && ')
    order = [c.removeprefix('ng test ') for c in commands[1:]]
    require(commands[0] == 'npm run test:dist' and len(order) == len(set(order))
            and set(order) == set(projects) and all(c == 'ng test ' + n for c, n in zip(commands[1:], order)),
            'contrato npm test omite/duplica/filtra proyectos')
    inventory = {}
    for name, project in projects.items():
        root = 'projects/' + name
        require(project['root'] == root, 'contrato Angular requiere raiz projects/<nombre>')
        target = project['architect']['test']
        require(set(target) == {'builder', 'options'} and target['builder'] == '@angular/build:unit-test'
                and set(target['options']) == {'tsConfig'}, 'contrato Angular no permite filtros/configuracion runner')
        for path in (repo / root).rglob('*'):
            require(not path.is_symlink(), 'contrato Angular: symlink en fuentes no soportado')
        inventory['angular:' + name] = sorted(p.relative_to(repo).as_posix() for p in (repo / root).rglob('*')
                                               if p.is_file() and (p.name.endswith('.spec.ts') or p.name.endswith('.test.ts')))
        require(inventory['angular:' + name], 'contrato Angular: proyecto sin tests')
    for path in NODE_FILES:
        require((repo / path).is_file() and not (repo / path).is_symlink(), 'contrato node:test archivo ausente/symlink')
    inventory['node:test'] = sorted(NODE_FILES)
    return {'projects': order, 'node_files': NODE_FILES, 'command': scripts['test'], 'files': inventory}


def toolchain(repo, env):
    node = shutil.which('node', path=env.get('PATH'))
    if node is None:
        raise Invalid('Node ausente')
    versions = {name: read_manifest(repo / 'node_modules' / name / 'package.json')['version']
                for name in ('@angular/cli', '@angular/build', 'vitest')}
    versions['node'] = subprocess.check_output([node, '--version'], env=env, text=True).strip()
    for name, prefix in (('node', 'v22.'), ('@angular/cli', '22.'), ('@angular/build', '22.'), ('vitest', '4.')):
        require(versions[name].startswith(prefix), 'toolchain fuera de contrato Angular22/Vitest4/Node22')
    return {'node': str(Path(node).resolve()), 'versions': versions, 'node_sha256': digest(node),
            'lock_sha256': digest(repo / 'package-lock.json'),
            'runner_sha256': {name: digest(Path(__file__).with_name(name)) for name in HELPERS}}


def run_process(argv, repo, env):
    print('$ ' + json.dumps(argv), flush=True)
    result = subprocess.run(argv, cwd=repo, env=env, capture_output=True, text=True,
                            encoding='utf-8', timeout=900)
    return {'argv': argv, 'exit': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}


def relative(repo, path):
    return Path(path).resolve().relative_to(repo).as_posix()


def load_json(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'JSON con clave duplicada')
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=unique)


def count(value, expected, label):
    require(type(value) is int and value == expected, label + ': conteo/exit incoherente')


def unique_results(tests):
    require(tests and all(r['state'] in ('pass', 'fail') for r in tests), 'tests vacios/skip/no terminales')
    require(len(tests) == len({tuple(r['id']) for r in tests}), 'identidad test duplicada/ambigua')
    return tests


def parse_node(repo, run):
    events = [load_json(line) for line in run['stdout'].splitlines()]
    tests, starts, finals, summaries, completes = [], set(), set(), {}, {}
    for e in events:
        kind, data = e['type'], e['data']
        if kind in ('test:start', 'test:pass', 'test:fail'):
            file, name = relative(repo, data['file']), data['name']
            require(file in NODE_FILES and isinstance(name, str) and name, 'node:test identidad ajena')
            require(data['nesting'] == 0, 'node:test anidado fuera del contrato ADR plano')
            key = (file, name)
            if kind == 'test:start':
                require(key not in starts, 'node:test inicio duplicado')
                starts.add(key)
            else:
                require(key in starts and key not in finals, 'node:test final sin inicio/duplicado')
                require(data['details']['type'] == 'test' and not data.get('skip') and not data.get('todo'),
                        'node:test skip/todo/suite: medicion incompleta')
                if kind == 'test:fail':
                    require(data['details']['error']['failureType'] == 'testCodeFailure',
                            'node:test fallo de archivo/proceso, no de test')
                finals.add(key)
                tests.append({'id': ['node:test', file, name], 'state': 'pass' if kind == 'test:pass' else 'fail'})
        elif kind == 'test:diagnostic':
            # ADR no usa diagnosticos de test; Node comunica only/runOnly aqui.
            # No decidir por palabras del mensaje (pueden cambiar o ser falsas).
            require('file' not in data, 'node:test diagnostico de archivo: medicion incompleta')
        elif kind == 'test:summary':
            file = relative(repo, data['file']) if 'file' in data else '*'
            require(file not in summaries, 'node:test resumen duplicado')
            summaries[file] = data
        elif kind == 'test:complete':
            # Node emite un final del proceso de CADA archivo, aparte de los tests.
            file = relative(repo, data['file'])
            if data['name'] in (file, str(repo / file)):
                require(file not in completes, 'node:test final de archivo duplicado')
                completes[file] = data['details']
    unique_results(tests)
    require(starts == finals, 'node:test truncado: faltan finales')
    require(set(summaries) == {*NODE_FILES, '*'} and set(completes) == set(NODE_FILES),
            'node:test falta resumen/final de archivo (vacio/truncado)')
    require(events[-1]['type'] == 'test:summary' and 'file' not in events[-1]['data'],
            'node:test falta final global')
    for file, summary in summaries.items():
        selected = [r for r in tests if file == '*' or r['id'][1] == file]
        require(selected, 'node:test archivo vacio')
        failed = sum(r['state'] == 'fail' for r in selected)
        expected = dict(tests=len(selected), passed=len(selected)-failed, failed=failed,
                        skipped=0, cancelled=0, todo=0, suites=0, topLevel=len(selected))
        for key, value in expected.items():
            count(summary['counts'][key], value, 'node:test ' + key)
        require(summary['success'] is (failed == 0), 'node:test resumen incoherente')
        if file != '*':
            end = completes[file]
            require(end['passed'] is (failed == 0), 'node:test fallo tardio de proceso')
            if failed:
                error = end['error']
                count(error.get('exitCode'), 1, 'node:test exit real del archivo')
                require(error.get('signal') is None and error.get('failureType') == 'subtestsFailed',
                        'node:test fallo tardio de archivo')
            else:
                require(not end.get('error'), 'node:test fallo tardio de archivo')
    count(run['exit'], int(any(r['state'] == 'fail' for r in tests)), 'node:test exit del runner')
    return tests


def parse_angular(repo, project, run):
    data = load_json(run['json'])
    events = [load_json(line) for line in run['events'].splitlines()]
    require(len(events) == 2 and events[0]['event'] == 'start' and events[1]['event'] == 'end',
            'Angular truncado/sin inicio y final')
    end = events[1]
    require(not end['errors'] and end['reason'] in ('passed', 'failed'), 'Angular error tardio/no controlado')
    starts = [relative(repo, f) for f in events[0]['files']]
    files = [relative(repo, m['name']) for m in data['testResults']]
    modules = {relative(repo, m['file']): m for m in end['modules']}
    require(files and len(files) == len(set(files)) == len(modules) == len(end['modules'])
            and len(starts) == len(set(starts)) and set(starts) == set(files) == set(modules),
            'Angular inventario de archivos incompleto/duplicado')
    tests = []
    for module in data['testResults']:
        file = relative(repo, module['name'])
        final = modules[file]
        require(not final['errors'] and not module['message'], 'Angular error de suite/teardown')
        for item in [*final['suites'], *final['tests']]:
            options = item['options']
            require(options['mode'] == 'run' and not options.get('retry') and not options.get('repeats')
                    and not options.get('fails'), 'Angular skip/only/retry/fails no medido')
        for suite in final['suites']:
            require(not suite['errors'] and suite['state'] in ('passed', 'failed'), 'Angular suite no medida/teardown')
        actual = module['assertionResults']
        require(actual and len(actual) == len(final['tests']), 'Angular archivo vacio/incompleto')
        states = []
        for test, live in zip(actual, final['tests']):
            state = test['status']
            require(live['started'] is True, 'Angular test no ejecutado (only/coleccion)')
            require(state in ('passed', 'failed') and state == live['result']['state']
                    and test['title'] == live['name'], 'Angular test skip/no terminal/incoherente')
            require(bool(test['failureMessages']) == (state == 'failed'), 'Angular fallo test incoherente')
            states.append(state)
            tests.append({'id': ['angular:' + project, file, test['fullName']],
                          'state': 'pass' if state == 'passed' else 'fail'})
        status = 'failed' if 'failed' in states else 'passed'
        require(module['status'] == final['state'] == status, 'Angular final de archivo incoherente')
    unique_results(tests)
    failed = sum(r['state'] == 'fail' for r in tests)
    for key, value in dict(numTotalTests=len(tests), numPassedTests=len(tests)-failed,
                           numFailedTests=failed, numPendingTests=0, numTodoTests=0).items():
        count(data[key], value, 'Angular ' + key)
    require(data['success'] is (failed == 0) and end['reason'] == ('failed' if failed else 'passed'),
            'Angular resultado global incoherente')
    count(run['exit'], int(failed > 0), 'Angular exit real')
    return tests


def measure(repo, trace=None):
    repo = Path(repo).resolve()
    env = environment()
    _clean(repo)
    branch, sha = git(repo, 'branch', '--show-current'), git(repo, 'rev-parse', 'HEAD')
    require(branch, 'rama destino detached: no pude medir integracion')
    tree = git(repo, 'rev-parse', 'HEAD^{tree}')
    contract, tools = scope(repo), toolchain(repo, env)
    execution, results = {}, []
    if trace is not None:
        trace.update(repo=str(repo), rama=branch, sha=sha, toolchain=tools, scope=contract, execution=execution)
    with tempfile.TemporaryDirectory(prefix='frontend-measure-') as tmp:
        node = tools['node']
        argv = [node, '--test', '--test-reporter=' + str(Path(__file__).with_name('frontend_node_reporter.mjs').resolve()), *NODE_FILES]
        execution['node:test'] = run_process(argv, repo, env)
        results += parse_node(repo, execution['node:test'])
        for project in contract['projects']:
            output, events = Path(tmp) / (project + '.json'), Path(tmp) / (project + '.jsonl')
            argv = [node, str(repo / 'node_modules/@angular/cli/bin/ng.js'), 'test', project,
                    '--no-watch', '--reporters=json',
                    '--reporters=' + str(Path(__file__).with_name('frontend_vitest_reporter.mjs').resolve()),
                    '--output-file=' + str(output)]
            run = run_process(argv, repo, dict(env, HARNESS_FRONTEND_EVENTS=str(events)))
            execution['angular:' + project] = run
            run['json'] = output.read_text(encoding='utf-8') if output.is_file() else None
            run['events'] = events.read_text(encoding='utf-8') if events.is_file() else None
            results += parse_angular(repo, project, run)
    _clean(repo)
    require((branch, sha) == (git(repo, 'branch', '--show-current'), git(repo, 'rev-parse', 'HEAD')),
            'contexto Git cambio durante medicion')
    require(scope(repo) == contract and toolchain(repo, environment()) == tools,
            'contexto runner/toolchain/inventario cambio durante medicion')
    measured = {'version': 1, 'protocol': PROTOCOL, 'repo': str(repo), 'rama': branch, 'sha': sha,
                'tree': tree, 'scope': contract, 'toolchain': tools, 'environment': {'CI': '1', 'TZ': 'UTC'},
                'results': results, 'execution': execution}
    validate_measurement(measured)
    return measured


def validate_execution(repo, name, run, tools):
    angular = name.startswith('angular:')
    fields = {'argv', 'exit', 'stdout', 'stderr'} | ({'json', 'events'} if angular else set())
    require(isinstance(run, dict) and set(run) == fields, 'base ejecucion esquema invalido')
    require(all(isinstance(run[k], str) for k in fields - {'argv', 'exit'}),
            'base ejecucion sin raw completo')
    argv = run['argv']
    require(isinstance(argv, list) and all(isinstance(x, str) for x in argv), 'base ejecucion argv invalido')
    node = tools['node']
    if angular:
        project = name.removeprefix('angular:')
        require(len(argv) == 8 and argv[-1].startswith('--output-file='), 'base ejecucion Angular comando alterado')
        output = Path(argv[-1].removeprefix('--output-file='))
        require(output.is_absolute() and not output.is_relative_to(repo) and output.name == project + '.json',
                'base ejecucion Angular output invalido')
        expected = [node, str(repo / 'node_modules/@angular/cli/bin/ng.js'), 'test', project,
                    '--no-watch', '--reporters=json',
                    '--reporters=' + str(Path(__file__).with_name('frontend_vitest_reporter.mjs').resolve()), argv[-1]]
    else:
        expected = [node, '--test', '--test-reporter=' + str(Path(__file__).with_name('frontend_node_reporter.mjs').resolve()), *NODE_FILES]
    require(argv == expected, 'base ejecucion no corresponde al comando cerrado')


def validate_measurement(data):
    require(isinstance(data, dict) and set(data) == {'version', 'protocol', 'repo', 'rama', 'sha', 'tree',
            'scope', 'toolchain', 'environment', 'results', 'execution'}, 'base esquema invalido')
    count(data['version'], 1, 'base version')
    require(data['protocol'] == PROTOCOL and data['environment'] == {'CI': '1', 'TZ': 'UTC'},
            'base protocolo/entorno incompatible')
    contract = data['scope']
    require(set(contract) == {'projects', 'node_files', 'command', 'files'}
            and contract['node_files'] == NODE_FILES, 'base contrato incompleto')
    projects = contract['projects']
    require(isinstance(projects, list) and projects and len(projects) == len(set(projects))
            and all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', p) for p in projects), 'base proyectos invalidos')
    expected = {'node:test', *('angular:' + p for p in projects)}
    require(set(data['execution']) == set(contract['files']) == expected, 'base falta proyecto/ejecucion')
    require(contract['command'] == 'npm run test:dist' + ''.join(' && ng test ' + p for p in projects),
            'base comando no corresponde al contrato')
    repo = Path(data['repo'])
    for name, run in data['execution'].items():
        validate_execution(repo, name, run, data['toolchain'])
    tests = parse_node(repo, data['execution']['node:test'])
    for project in projects:
        tests += parse_angular(repo, project, data['execution']['angular:' + project])
    unique_results(tests)
    require(data['results'] == tests, 'base resultados no corresponden a ejecucion real')
    for name, files in contract['files'].items():
        require(files and len(files) == len(set(files)) and set(files) == {r['id'][1] for r in tests if r['id'][0] == name},
                'archivo/proyecto omitido: inventario incompleto')
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
    current = scope(repo)
    require(all(current[k] == data['scope'][k] for k in ('projects', 'node_files', 'command')),
            'base contrato/proyecto cambio')
    require(data['toolchain'] == toolchain(repo, environment()), 'base toolchain/runner/lock stale')
    return data


def compare(base, measured):
    before = {tuple(r['id']): r['state'] for r in base['results']}
    after = {tuple(r['id']): r['state'] for r in measured['results']}
    require(before.keys() <= after.keys(), 'tests desaparecidos u omitidos')
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
            raise Invalid('frontend no comparable/sin cierre: ' + str(exc)) from exc
        finally:
            stream.write(json.dumps(trace, indent=2) + '\n')
            print('[i] evidencia frontend: ' + str(evidence))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='action', required=True)
    for action, flag in (('base', '--guardar'), ('check', '--base')):
        p = sub.add_parser(action)
        p.add_argument('--repo', required=True)
        p.add_argument(flag, required=True)
        p.add_argument('--evidence', help='JSON durable fuera del repo; nunca se sobrescribe')
    args = ap.parse_args()
    trace = {'exit': 2, 'execution': {}}
    evidence = None
    try:
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
            base = read_base(args.base, repo, git(repo, 'branch', '--show-current'), git(repo, 'rev-parse', 'HEAD'))
        measured = measure(repo, trace)
        if args.action == 'base':
            with Path(args.guardar).open('x', encoding='utf-8') as stream:
                stream.write(json.dumps(measured, indent=2))
            print('[ok] base frontend medida: ' + str(len(measured['results'])) + ' tests')
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
