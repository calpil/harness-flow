#!/usr/bin/env python3
"""Base/check Terraform: fmt, init(-backend=false), validate y `terraform test`.

Solo stdlib y el binario `terraform` del PATH. Sin shell ni --cmd.
Mide el COMMIT, no el directorio de trabajo: lo exporta (git archive) a un temporal
fuera del repo y alli corre todo. Terraform carga archivos que git ignora
(terraform.tfvars, *.auto.tfvars, override.tf): medir el checkout daria resultados
que el sha no explica. Init va con -backend=false, -lockfile=readonly (el lock sale
del commit) y TF_DATA_DIR temporal; el repo no recibe nada.
Una RAIZ es un directorio con .terraform.lock.hcl versionado o con *.tftest.hcl/json
en <dir>/ o <dir>/tests/. Cada raiz aporta un caso `fmt` por archivo, un caso
`<validate>` y, si tiene tests, un caso por cada `run "<nombre>"`.
Entorno minimo: HOME vacio y sin credenciales (GOOGLE_*, AWS_*, ...), de modo que un
test sin mock_provider falla en rojo en vez de tocar infraestructura real.
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

PROTOCOL = 'terraform-test-json-v2'
VALIDATE = '<validate>'
LOCK = '.terraform.lock.hcl'
TEST_SUFFIXES = ('.tftest.hcl', '.tftest.json')
FMT_SUFFIXES = ('.tf', '.tfvars', '.tftest.hcl', '.tfmock.hcl')
# Un run con este nombre chocaria con el id [raiz, archivo, 'fmt'] de un caso de formato.
RESERVADO = 'fmt'
# Segundos por comando: un terraform colgado es Invalid, nunca un cuelgue del cierre.
TIMEOUTS = {'version': 120, 'fmt': 300, 'init': 900, 'validate': 300, 'test': 900}
STATUS = ('pass', 'fail', 'error', 'skip')
# Lo UNICO que se hereda del entorno del llamador: ruta de binarios, locale, red/proxy
# y certificados. Nada de TF_*, GOOGLE_*, CLOUDSDK_*, AWS_*, AZURE_*, ARM_* ni HOME.
HEREDADAS = ('PATH', 'LANG', 'LC_ALL', 'TMPDIR', 'HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY',
             'http_proxy', 'https_proxy', 'no_proxy', 'SSL_CERT_FILE', 'SSL_CERT_DIR')


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


def _plugin_cache():
    """El plugin cache que el operador tiene configurado (env o ~/.terraformrc): es lo
    UNICO que se saca del HOME real, porque el HOME de la medicion esta vacio."""
    candidates = [os.environ.get('TF_PLUGIN_CACHE_DIR')]
    for name in ('.terraformrc', 'terraform.rc'):
        try:
            text = (Path(os.path.expanduser('~')) / name).read_text(encoding='utf-8')
        except OSError:
            continue
        m = re.search(r'(?m)^\s*plugin_cache_dir\s*=\s*"([^"\n]+)"', text)
        if m:
            candidates.append(os.path.expandvars(os.path.expanduser(m.group(1))))
    return next((c for c in candidates if c and Path(c).is_dir()), None)


def environment(home):
    """Entorno minimo y explicito. HOME apunta a un directorio vacio: el provider no
    encuentra credenciales de gcloud/aws/azure, y un test sin mock_provider falla en
    rojo en vez de tocar infraestructura real."""
    env = {k: os.environ[k] for k in HEREDADAS if k in os.environ}
    env.update(HOME=str(home), TF_IN_AUTOMATION='1', TF_INPUT='0', CHECKPOINT_DISABLE='1')
    cache = _plugin_cache()
    if cache:
        env['TF_PLUGIN_CACHE_DIR'] = cache
    config = os.environ.get('TF_CLI_CONFIG_FILE')
    if config and Path(config).is_file():
        env['TF_CLI_CONFIG_FILE'] = config
    return env


def _cola(text, n=2000):
    text = (text or '').strip()
    return text if len(text) <= n else '...' + text[-n:]


# --- descubrimiento de raices e inventario ---------------------------------------

def _archivos(repo, ref=None):
    """Rutas versionadas (fuera de .terraform/): del indice o de un commit."""
    if ref is None:
        salida = git(repo, 'ls-files', '-z')
    else:
        salida = git(repo, 'ls-tree', '-r', '--name-only', '-z', ref)
    return [x for x in salida.split('\0') if x and '.terraform' not in PurePosixPath(x).parts]


def archivos_test(repo, ref=None):
    """*.tftest.hcl / *.tftest.json versionados."""
    return sorted(x for x in _archivos(repo, ref) if x.endswith(TEST_SUFFIXES))


def raices(repo, ref=None):
    """Directorios (rutas POSIX relativas, '.' = raiz del repo) a medir: los que tienen
    un .terraform.lock.hcl versionado o tests (*.tftest.hcl/json) en <dir>/ o <dir>/tests/."""
    encontradas = set()
    for ruta in _archivos(repo, ref):
        carpeta = PurePosixPath(ruta).parent
        if ruta.endswith(TEST_SUFFIXES):
            if carpeta.name == 'tests':
                carpeta = carpeta.parent
            encontradas.add(carpeta.as_posix())
        elif PurePosixPath(ruta).name == LOCK:
            encontradas.add(carpeta.as_posix())
    require(encontradas, 'terraform: sin raices (.terraform.lock.hcl ni *.tftest.hcl): nada que medir')
    return sorted(encontradas)


def inventario(repo, ref, found):
    """Por raiz, lo que el COMMIT declara: sus archivos de test y los archivos de formato."""
    todos = _archivos(repo, ref)
    result = {}
    for raiz in found:
        base = PurePosixPath(raiz)
        tests, fmt = [], []
        for ruta in todos:
            p = PurePosixPath(ruta)
            if raiz != '.' and not p.is_relative_to(base):
                continue
            rel = p.relative_to(base).as_posix()
            if ruta.endswith(TEST_SUFFIXES) and p.parent in (base, base / 'tests'):
                tests.append(rel)
            if ruta.endswith(FMT_SUFFIXES):
                fmt.append(rel)
        result[raiz] = {'tests': sorted(tests), 'fmt': sorted(fmt)}
    return result


def exportar(repo, sha, destino):
    """El commit, blob por blob y nada mas: ni ignorados (tfvars, override.tf), ni
    .terraform/ previos, ni `export-ignore`/`export-subst` (git archive los aplica, tambien
    desde .git/info/attributes local). `cat-file --batch` no aplica filtros ni atributos.
    Respeta el modo (100755 ejecutable) y escribe los symlinks (120000) SIN seguirlos;
    los submodulos (160000) no se soportan."""
    destino = Path(destino)
    try:
        entradas = git(repo, 'ls-tree', '-r', '-z', '--full-tree', sha, binary=True).split(b'\0')
        esperadas = set()
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS='0',
                   GIT_NO_REPLACE_OBJECTS='1')
        with subprocess.Popen(['git', '-c', 'core.fsmonitor=false', '-C', str(repo), 'cat-file', '--batch'],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env) as lector:
            for entrada in filter(None, entradas):
                meta, _, ruta = entrada.partition(b'\t')
                modo, tipo, oid = meta.decode().split(' ')
                ruta = ruta.decode('utf-8', 'surrogateescape')
                pure = PurePosixPath(ruta)
                require(not pure.is_absolute() and '..' not in pure.parts and '.' not in pure.parts,
                        'export: ruta insegura en el commit: ' + ruta)
                require(modo != '160000', 'export: submodulo no soportado (' + ruta + '): el commit no se puede '
                        'reconstruir sin red; vendorizalo o quitalo del repo medido')
                require(tipo == 'blob' and modo in ('100644', '100755', '120000'), f'export: modo {modo} no soportado: {ruta}')
                lector.stdin.write(oid.encode() + b'\n')
                lector.stdin.flush()
                cabecera = lector.stdout.readline().split()
                require(len(cabecera) == 3 and cabecera[1] == b'blob', 'export: git cat-file no devolvio el blob de ' + ruta)
                datos = lector.stdout.read(int(cabecera[2]))
                lector.stdout.read(1)
                require(len(datos) == int(cabecera[2]), 'export: blob truncado: ' + ruta)
                destino_ruta = destino.joinpath(*pure.parts)
                require(not any(x.is_symlink() for x in (destino_ruta.parent, *destino_ruta.parent.parents)
                                if destino in x.parents or x == destino), 'export: directorio padre es un symlink: ' + ruta)
                destino_ruta.parent.mkdir(parents=True, exist_ok=True)
                if modo == '120000':
                    os.symlink(datos.decode('utf-8', 'surrogateescape'), destino_ruta)
                else:
                    destino_ruta.write_bytes(datos)
                    destino_ruta.chmod(0o755 if modo == '100755' else 0o644)
                esperadas.add(ruta)
            lector.stdin.close()
        obtenidas = {Path(d, f).relative_to(destino).as_posix() for d, _, files in os.walk(destino)
                     for f in files}
        obtenidas |= {Path(d, n).relative_to(destino).as_posix() for d, dirs, _ in os.walk(destino)
                      for n in dirs if Path(d, n).is_symlink()}
        require(obtenidas == esperadas, 'export: el arbol exportado no es exactamente el del commit')
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        if isinstance(exc, Invalid):
            raise
        raise Invalid(f'export: no se pudo reconstruir el commit ({type(exc).__name__}: {exc})') from exc


# --- ejecucion ------------------------------------------------------------------------

def toolchain(env):
    binary = shutil.which('terraform', path=env.get('PATH'))
    if binary is None:
        raise Invalid('Terraform ausente')
    binary = str(Path(binary).resolve())
    run = run_process([binary, 'version', '-json'], env['HOME'], env, 'version', quiet=True)
    require(run['exit'] == 0, 'terraform version fallo: ' + _cola(run['stderr']))
    data = load_json(run['stdout'])
    version = data.get('terraform_version') if isinstance(data, dict) else None
    require(isinstance(version, str) and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?', version),
            'toolchain fuera de contrato: terraform sin version')
    return {'terraform': binary, 'terraform_version': version,
            'platform': data.get('platform') if isinstance(data.get('platform'), str) else '',
            'terraform_sha256': digest(binary)}


def run_process(argv, cwd, env, name, quiet=False):
    if not quiet:
        print('$ ' + json.dumps(argv), flush=True)
    try:
        r = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True,
                           encoding='utf-8', timeout=TIMEOUTS[name])
    except subprocess.TimeoutExpired as exc:
        raise Invalid(f'terraform {name} excedio {TIMEOUTS[name]}s') from exc
    except (OSError, ValueError) as exc:
        raise Invalid(f'terraform {name} no se pudo ejecutar ({type(exc).__name__})') from exc
    return {'argv': argv, 'exit': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}


def comandos(binary):
    return {'fmt': [binary, 'fmt', '-check', '-list=true', '-recursive', '-no-color'],
            'init': [binary, 'init', '-backend=false', '-input=false', '-no-color', '-lockfile=readonly'],
            'validate': [binary, 'validate', '-json', '-no-color'],
            'test': [binary, 'test', '-json', '-no-color']}


def casos_fmt(raiz, inv, run):
    """Un caso por archivo versionado de la raiz: fail si fmt lo lista como desformateado."""
    require(run['exit'] in (0, 3), f'terraform fmt fallo en {raiz}: ' + _cola(run['stderr'] or run['stdout']))
    listados = {PurePosixPath(x.strip()).as_posix() for x in run['stdout'].splitlines() if x.strip()}
    require(listados <= set(inv['fmt']), f'terraform fmt lista archivos ajenos al commit en {raiz}: '
            + ', '.join(sorted(listados - set(inv['fmt']))[:5]))
    require((run['exit'] == 3) == bool(listados), f'terraform fmt: exit y lista incoherentes en {raiz}')
    return [{'id': [raiz, f, 'fmt'], 'state': 'fail' if f in listados else 'pass'} for f in inv['fmt']]


def evaluar_init(raiz, run):
    require(run['exit'] == 0, f'terraform init fallo en {raiz}: ' + _cola(run['stderr'] or run['stdout']))


def caso_validate(raiz, run):
    data = load_json(run['stdout']) if run['stdout'].strip() else None
    require(isinstance(data, dict) and type(data.get('valid')) is bool,
            f'terraform validate sin veredicto en {raiz}: ' + _cola(run['stdout'] or run['stderr']))
    count(run['exit'], 0 if data['valid'] else 1, 'terraform validate exit')
    return {'id': [raiz, VALIDATE, 'validate'], 'state': 'pass' if data['valid'] else 'fail'}


def parse_test(raiz, run, tests):
    """Eventos de `terraform test -json` -> casos [raiz, archivo, run]. `tests`: los
    archivos de test que el COMMIT declara en la raiz (inventario independiente)."""
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
            require(isinstance(item, dict), 'terraform test: test_run invalido')
            if item.get('progress') != 'complete':
                continue
            key = (item['path'], item['run'])
            require(key not in complete, 'terraform test: run con dos finales: ' + '::'.join(key))
            require(item.get('status') in STATUS, 'terraform test: estado de run desconocido')
            complete[key] = item['status']
        elif kind == 'test_summary':
            require(isinstance(event['test_summary'], dict), 'terraform test: test_summary invalido')
            summaries.append(event['test_summary'])
    require(abstract is not None, 'terraform test: falta test_abstract')
    require(sorted(abstract) == sorted(tests), f'terraform test: inventario incompleto en {raiz}: el commit declara '
            + ', '.join(sorted(tests)) + ' y terraform reporto ' + ', '.join(sorted(abstract)))
    declared = {(path, name) for path, names in abstract.items() for name in names}
    require(declared, 'terraform test: cero runs en ' + raiz)
    require(all(name != RESERVADO for _, name in declared), f"terraform test: '{RESERVADO}' es un nombre de run reservado")
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


def evaluar(raiz, inv, runs):
    """Resultados de una raiz a partir del raw de sus comandos. Todo lo que no
    cuadra con el contrato (tambien un campo ausente o de otro tipo) es Invalid."""
    try:
        out = casos_fmt(raiz, inv, runs['fmt'])
        evaluar_init(raiz, runs['init'])
        validate = caso_validate(raiz, runs['validate'])
        out.append(validate)
        corre = bool(inv['tests'])
        # Con tests, un validate rojo deja sus runs sin correr: medicion incompleta (como un
        # build roto en Go). El validate como deuda es solo para raices SIN tests.
        require(not corre or validate['state'] == 'pass', f"terraform: validate rojo en {raiz} deja sin correr sus "
                f"runs ({', '.join(inv['tests'])}): medicion incompleta")
        require(('test' in runs) == corre, f'terraform: ejecucion de test ausente/sobrante en {raiz}')
        if corre:
            out += parse_test(raiz, runs['test'], inv['tests'])
        return out
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise Invalid(f'terraform: salida fuera de contrato en {raiz} ({type(exc).__name__}: {exc})') from exc


def _raiz_dir(base, raiz):
    path = (base / raiz).resolve()
    require(path.is_dir() and path.is_relative_to(base), 'terraform: raiz fuera del repo: ' + raiz)
    return path


def measure(repo, trace=None):
    """Mide el COMMIT (HEAD), no el directorio de trabajo: se exporta a un temporal
    fuera del repo y alli corren todos los comandos."""
    repo = Path(repo).resolve()
    _clean(repo)
    branch, sha = git(repo, 'branch', '--show-current'), git(repo, 'rev-parse', 'HEAD')
    require(branch, 'rama destino detached: no pude medir integracion')
    tree = git(repo, 'rev-parse', 'HEAD^{tree}')
    found = raices(repo, sha)
    inv = inventario(repo, sha, found)
    execution, results = {}, []
    with tempfile.TemporaryDirectory(prefix='terraform-measure-') as tmp:
        tmp = Path(tmp).resolve()
        (tmp / 'home').mkdir()
        (tmp / 'tree').mkdir()
        env = environment(tmp / 'home')
        tools = toolchain(env)
        if trace is not None:
            trace.update(repo=str(repo), rama=branch, sha=sha, toolchain=tools, inventory=inv, execution=execution)
        exportar(repo, sha, tmp / 'tree')
        cmds = comandos(tools['terraform'])
        for n, raiz in enumerate(found):
            cwd = _raiz_dir(tmp / 'tree', raiz)
            renv = dict(env, TF_DATA_DIR=str(tmp / 'data' / str(n)))
            runs = execution[raiz] = {}
            runs['fmt'] = run_process(cmds['fmt'], cwd, renv, 'fmt')
            runs['init'] = run_process(cmds['init'], cwd, renv, 'init')
            evaluar_init(raiz, runs['init'])
            runs['validate'] = run_process(cmds['validate'], cwd, renv, 'validate')
            if inv[raiz]['tests'] and caso_validate(raiz, runs['validate'])['state'] == 'pass':
                runs['test'] = run_process(cmds['test'], cwd, renv, 'test')
            results += evaluar(raiz, inv[raiz], runs)
        _clean(repo)
        require((branch, sha) == (git(repo, 'branch', '--show-current'), git(repo, 'rev-parse', 'HEAD')),
                'contexto Git cambio durante medicion')
        require(toolchain(environment(tmp / 'home')) == tools, 'toolchain cambio durante medicion')
    measured = {'version': 1, 'protocol': PROTOCOL, 'repo': str(repo), 'rama': branch, 'sha': sha,
                'tree': tree, 'toolchain': tools, 'inventory': inv, 'results': unique_results(results),
                'execution': execution}
    validate_measurement(measured)
    return measured


def validate_measurement(data):
    require(isinstance(data, dict) and set(data) == {'version', 'protocol', 'repo', 'rama', 'sha', 'tree',
            'toolchain', 'inventory', 'results', 'execution'}, 'base esquema invalido')
    count(data['version'], 1, 'base version')
    require(data['protocol'] == PROTOCOL, 'base protocolo incompatible')
    tools = data['toolchain']
    require(isinstance(tools, dict) and set(tools) == {'terraform', 'terraform_version', 'platform', 'terraform_sha256'}
            and all(isinstance(v, str) for v in tools.values()), 'base toolchain invalido')
    execution, inv = data['execution'], data['inventory']
    require(isinstance(execution, dict) and execution and list(execution) == sorted(execution)
            and isinstance(inv, dict) and list(inv) == list(execution), 'base falta/desordena raices')
    cmds, tests = comandos(tools['terraform']), []
    for raiz, runs in execution.items():
        require(isinstance(raiz, str) and raiz and not PurePosixPath(raiz).is_absolute()
                and '..' not in PurePosixPath(raiz).parts, 'base raiz invalida')
        item = inv[raiz]
        require(isinstance(item, dict) and set(item) == {'tests', 'fmt'} and all(
            isinstance(item[k], list) and item[k] == sorted(set(item[k])) and all(isinstance(x, str) for x in item[k])
            for k in item), 'base inventario invalido')
        require(isinstance(runs, dict) and {'fmt', 'init', 'validate'} <= set(runs) <= set(cmds),
                'base ejecucion esquema invalido')
        for name, run in runs.items():
            require(isinstance(run, dict) and set(run) == {'argv', 'exit', 'stdout', 'stderr'}
                    and type(run['exit']) is int and isinstance(run['stdout'], str)
                    and isinstance(run['stderr'], str), 'base ejecucion sin raw completo')
            require(run['argv'] == cmds[name], 'base ejecucion no corresponde al comando cerrado')
        tests += evaluar(raiz, item, runs)
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
    # La base tiene que haber medido TODAS las raices de su propio commit y con el
    # mismo inventario: si no, los tests de una raiz omitida podrian desaparecer sin aviso.
    found = raices(repo, data['sha'])
    require(sorted(data['execution']) == found, 'base no midio todas las raices de su commit')
    require(data['inventory'] == inventario(repo, data['sha'], found), 'base inventario no corresponde a su commit')
    with tempfile.TemporaryDirectory(prefix='terraform-toolchain-') as home:
        require(data['toolchain'] == toolchain(environment(home)), 'base toolchain stale')
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
        except (Invalid, OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError) as exc:
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
    except (Invalid, OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError) as exc:
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
