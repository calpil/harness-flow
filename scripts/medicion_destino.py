"""Medicion obligatoria de cada destino: ejecuta, nunca consume recibos de PASS.

Soporte cerrado a Go JSON/-exec existente y Angular22/Vitest4+Node22 de ADR.
La configuracion solo enumera bases: no puede cambiar comando ni omitir repos.
"""
import hashlib
import os
from pathlib import Path, PurePosixPath
import sys

import postmerge_medido as runner
import retiros
from comun import now_iso, review_path
from multirepo import Invalid, context, git, read_manifest, require

COMMAND = 'go test -tags integration -count=1 -json ./...'


def _sha256(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as exc:
        raise Invalid(f'no se pudo leer {path} ({type(exc).__name__})') from exc


def _frontend(repo):
    """El destino se mide con el runner frontend (contrato Angular22/Vitest4)."""
    return (Path(repo) / 'angular.json').exists() or (Path(repo) / 'package.json').exists()


def _rechazar_repo_mixto(repo):
    """Un repo con angular.json/package.json Y go.mod no tiene runner: se
    rechaza ANTES de elegir uno, en el camino normal y en el historico (misma
    funcion compartida para que la cobertura de una certifique la otra --
    hallazgo P3 ronda 2, estaba duplicado literal en measure()/measure_historico())."""
    require(not (Path(repo) / 'go.mod').exists(), 'postmerge: repo mixto no soportado')


def measure(p, f, rules, manifest, config_path, retiros_path=None):
    config = read_manifest(config_path)
    require(isinstance(config, dict) and set(config) == {'version', 'feature', 'bases'}
            and type(config['version']) is int and config['version'] == 1
            and config['feature'] == str(f['id']), 'postmerge: mapa invalido')
    bases = config['bases']
    names = {r['microservicio'] for r in manifest['repos']}
    require(isinstance(bases, dict) and set(bases) == names, 'postmerge: faltan/sobran destinos')
    retirados, retiros_hash, revisado = {}, None, None
    if retiros_path:
        retirados = retiros.leer(retiros_path, names, f['id'])
        retiros_hash = _sha256(retiros_path)
        try:
            revisado = review_path(p, f).read_text(encoding='utf-8')
        except OSError as exc:
            raise Invalid(f'retirados: review ilegible ({type(exc).__name__})') from exc
        # Un id del formato ajeno al destino no se verifica en ningun lado:
        # se rechaza antes de correr una sola suite.
        for row in manifest['repos']:
            declarados = retirados.get(row['microservicio'], set())
            front = _frontend(row['repo'])
            require(not declarados or retiros.tipo(declarados) == (retiros.FRONT if front else retiros.GO),
                    f"retirados: {row['microservicio']} es un destino "
                    + ("frontend: no acepta ids Go '<paquete>::<Test>', sino el id medido "
                       '[proyecto, archivo, nombre]' if front else
                       "Go: no acepta ids medidos de frontend, sino '<paquete>::<TestDePrimerNivel>'"))
        # La cita de una baja de frontend exige su titulo hoja, que sale del spec
        # en base_sha: se verifica con el resto de su destino, no aqui.
        go = {x for bajas in retirados.values() for x in bajas if not retiros.es_frontend(x)}
        sin_cita = retiros.sin_cita(revisado, go)
        require(not sin_cita, 'retirados: el review no cita la baja de ' + ', '.join(sin_cita))
    initial_context = context(p, f, rules)
    hashes = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
              for name in ('postmerge_medido.py', 'postmerge_exec.py', 'medicion_destino.py', 'retiros.py',
                           'postmerge_frontend.py', 'frontend_node_reporter.mjs', 'frontend_vitest_reporter.mjs')}
    results, failures = [], []
    env = os.environ.copy()
    try:
        # No GIT_* heredados que redirijan Git, ni GOFLAGS que filtre tests.
        for key in list(os.environ):
            if key.startswith('GIT_'):
                del os.environ[key]
        os.environ.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                          GIT_NO_REPLACE_OBJECTS='1', GIT_OPTIONAL_LOCKS='0',
                          GOFLAGS='', GOWORK='off')
        for row in manifest['repos']:
            name, repo = row['microservicio'], row['repo']
            print(f'[i] postmerge destino {name}: {row["target_sha"]}', flush=True)
            try:
                value = bases[name]
                require(isinstance(value, str) and Path(value).is_absolute(), 'postmerge: base requiere ruta absoluta')
                path = Path(value)
                require(path.is_file() and not path.is_symlink(), 'postmerge: base ausente/no regular')
                base_hash = hashlib.sha256(path.read_bytes()).hexdigest()
                raw = read_manifest(path)  # claves duplicadas no son una base valida
                require(isinstance(raw, dict) and raw.get('sha') == row['base_sha'],
                        'postmerge: base stale/no corresponde a base_sha')
                declared = retirados.get(name, set())
                if _frontend(repo):
                    _rechazar_repo_mixto(repo)
                    require(retiros.tipo(declared) in (None, retiros.FRONT),
                            f'retirados: {name} es un destino frontend: no acepta ids Go '
                            "'<paquete>::<Test>', sino el id medido [proyecto, archivo, nombre]")
                    from postmerge_frontend import check_destination
                    result = check_destination(row, path, declared, revisado)
                    if declared:
                        result.update(retirados=[list(x) for x in sorted(declared)],
                                      retirados_archivo=str(Path(retiros_path).resolve()),
                                      retirados_sha256=retiros_hash)
                    results.append(dict(result, integration=row, context=initial_context, at=now_iso(),
                                        runner_sha256=hashes, python=str(Path(sys.executable).absolute())))
                    continue
                require(retiros.tipo(declared) in (None, retiros.GO),
                        f'retirados: {name} es un destino Go: no acepta ids medidos de '
                        "frontend, sino '<paquete>::<TestDePrimerNivel>'")
                base = runner.leer_base(str(path), repo, row['target_branch'], row['target_sha'], COMMAND)
                tests, packages, processes = runner.correr(repo, COMMAND)
                require('skip' not in tests.values(), 'postmerge: destino contiene tests skip; medicion incompleta')
                measured = {key for key, state in tests.items() if state != 'skip'}
                retiros.verificar(repo, row['base_sha'], (row['source_sha'], row['target_sha']),
                                  base, measured, declared)
                missing = runner.sin_baja(base, measured, packages.keys(), declared)
                require(not missing, 'postmerge: tests/paquetes desaparecidos u omitidos (skip): '
                        + ', '.join(missing))
                for pkg, test in sorted(declared):
                    print(f'[i] retirado por la feature (borrado en su delta, citado en el review): '
                          f'{pkg}::{test}', flush=True)
                red = {key for key, state in tests.items() if state == 'fail'}
                new = red - {tuple(key) for key in base['rojos']}
                require(not new, 'postmerge: rojos nuevos: ' + ', '.join('::'.join(key) for key in sorted(new)))
                require(hashlib.sha256(path.read_bytes()).hexdigest() == base_hash,
                        'postmerge: base cambio durante medicion')
                result = {'integration': row, 'context': initial_context, 'at': now_iso(),
                          'command': COMMAND, 'runner_sha256': hashes,
                          'python': str(Path(sys.executable).absolute()),
                          'base': str(path.resolve()), 'base_sha256': base_hash,
                          'results': [{'Package': pkg, 'Test': test, 'Action': state}
                                      for (pkg, test), state in sorted(tests.items())],
                          'execution': {'protocol': runner.PROTOCOL, 'finals': packages, 'exits': processes}}
                if declared:
                    result.update(retirados=[f'{pkg}::{test}' for pkg, test in sorted(declared)],
                                  retirados_archivo=str(Path(retiros_path).resolve()),
                                  retirados_sha256=retiros_hash)
                results.append(result)
            except (Invalid, SystemExit, OSError, ValueError) as exc:
                failures.append(f'{name}: {exc}')
        require(not failures, 'postmerge sin cierre: ' + '; '.join(failures))
        require(len(results) == len(names), 'postmerge: medicion incompleta')
        require(context(p, f, rules) == initial_context, 'postmerge: contexto cambio durante medicion')
        require(not retiros_path or _sha256(retiros_path) == retiros_hash,
                'postmerge: retirados cambio durante medicion')
        require(all(hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() == digest
                    for name, digest in hashes.items()), 'postmerge: runner cambio durante medicion')
        return results
    finally:
        os.environ.clear()
        os.environ.update(env)


# --- cierre historico (sin base preintegracion medible) ---------------------
#
# Ver docs/diseno-arnes-cierre-historico.md y references/multirepo.md, seccion
# "Cierre historico". Mide el MISMO runner que measure(), pero sin comparar
# contra una base: exige exit real 0, cero rojos y cero skip en el destino
# (garantia 3), y que cada test que la propia feature agrego -- declarado en
# source_sha y ausente en base_sha -- siga midiendose ahi, o este declarado
# como baja historica (garantia 4). Un repo cuyo delta toca codigo sin agregar
# NINGUN test bloquea (garantia 5).


def _enumerar_tests_go(repo, sha) -> set[tuple[str, str]]:
    """(paquete, TestX) de PRIMER NIVEL declarados en sha, ciego a build tags
    (mismo criterio que retiros._definido: git grep sobre *_test.go)."""
    modulo = retiros._modulo(repo, sha)
    salida = git(repo, 'grep', '-n', '-E', '-e', r'^func (Test|Example|Fuzz)[A-Za-z0-9_]*\(',
                sha, '--', ':(glob)**/*_test.go', ok=(0, 1))
    result = set()
    for linea in salida.splitlines():
        try:
            _, ruta, _, contenido = linea.split(':', 3)
        except ValueError:
            continue
        m = retiros.NOMBRE.search(contenido)
        if not m:
            continue
        directorio = str(PurePosixPath(ruta).parent)
        directorio = '' if directorio == '.' else directorio
        paquete = modulo if not directorio else f'{modulo}/{directorio}'
        result.add((paquete, m.group(0)))
    return result


def tests_agregados_go(repo, base_sha, source_sha) -> set[tuple[str, str]]:
    """Tests de primer nivel que la FEATURE agrego: en source_sha y no en
    base_sha. Identidad (paquete, TestX), igual que retiros.py."""
    return _enumerar_tests_go(repo, source_sha) - _enumerar_tests_go(repo, base_sha)


def _archivos_front(repo, sha) -> list[str]:
    from postmerge_frontend import NODE_FILES
    nombres = set(git(repo, 'ls-tree', '-r', '--name-only', sha).splitlines())
    return sorted({f for f in nombres if f.endswith(('.spec.ts', '.test.ts'))} | (nombres & set(NODE_FILES)))


def _declaraciones_commit(repo, sha, archivo) -> set[str]:
    texto = retiros._blob(repo, sha, archivo)
    return retiros.declaraciones(texto) if texto is not None else set()


def tests_agregados_front(repo, base_sha, source_sha) -> set[tuple[str, str]]:
    """(ruta del spec, titulo hoja) que la FEATURE agrego: declarado (retiros.
    declaraciones, el literal de un it/test) en source_sha y no en base_sha."""
    agregados = set()
    for archivo in _archivos_front(repo, source_sha):
        despues = _declaraciones_commit(repo, source_sha, archivo)
        antes = _declaraciones_commit(repo, base_sha, archivo)
        for hoja in despues - antes:
            agregados.add((archivo, hoja))
    return agregados


def _delta(repo, base_sha, source_sha) -> list[str]:
    return [x for x in git(repo, 'diff', '--name-only', '--no-renames', base_sha, source_sha, '--').splitlines() if x]


def delta_solo_tests_go(repo, base_sha, source_sha) -> bool:
    return all(f.endswith('_test.go') for f in _delta(repo, base_sha, source_sha))


def delta_solo_tests_front(repo, base_sha, source_sha) -> bool:
    from postmerge_frontend import NODE_FILES
    return all(f.endswith(('.spec.ts', '.test.ts')) or f in NODE_FILES
              for f in _delta(repo, base_sha, source_sha))


def _historico_go(row, declared) -> dict:
    repo = row['repo']
    agregados = tests_agregados_go(repo, row['base_sha'], row['source_sha'])
    if declared:
        retiros.verificar_historico(repo, row['base_sha'], row['source_sha'], row['target_sha'], declared)
    tests, packages, processes = runner.correr(repo, COMMAND)
    rojos = sorted(f'{p}::{t}' for (p, t), estado in tests.items() if estado == 'fail')
    require(not rojos, 'historico: rojos en el destino: ' + ', '.join(rojos))
    require('skip' not in tests.values(), 'historico: destino contiene tests skip; medicion incompleta')
    medidos = set(tests.keys())
    sigue = sorted(f'{p}::{t}' for p, t in declared if (p, t) in medidos)
    require(not sigue, 'historico: retirados que se siguen midiendo en el destino: ' + ', '.join(sigue))
    faltan = sorted(f'{p}::{t}' for p, t in (agregados - medidos) if (p, t) not in declared)
    require(not faltan, 'historico: tests de la feature ausentes sin declarar: ' + ', '.join(faltan))
    if not agregados:
        require(delta_solo_tests_go(repo, row['base_sha'], row['source_sha']),
                f"historico: {row['microservicio']} modifica codigo sin agregar ningun test "
                "(la garantia 4 quedaria vacia; declara --retirados o agrega cobertura)")
    result = {'command': COMMAND,
              'results': [{'Package': pkg, 'Test': test, 'Action': state}
                          for (pkg, test), state in sorted(tests.items())],
              'execution': {'protocol': runner.PROTOCOL, 'finals': packages, 'exits': processes},
              'tests_agregados': sorted(f'{p}::{t}' for p, t in agregados)}
    if declared:
        result['retirados'] = [f'{p}::{t}' for p, t in sorted(declared)]
    return result


def _historico_frontend(row, declared, revisado) -> dict:
    from postmerge_frontend import leaf_titles, measure as measure_frontend
    repo = row['repo']
    agregados = tests_agregados_front(repo, row['base_sha'], row['source_sha'])
    resueltas = {}
    if declared:
        resueltas = retiros.verificar_frontend_historico(repo, row['base_sha'], row['source_sha'],
                                                          row['target_sha'], declared, revisado)
    measured = measure_frontend(Path(repo))
    require(measured['sha'] == row['target_sha'], 'historico: target stale')
    rojos = sorted('::'.join(r['id']) for r in measured['results'] if r['state'] == 'fail')
    require(not rojos, 'historico: rojos en el destino: ' + ', '.join(rojos))
    medidos_ids = {tuple(r['id']) for r in measured['results']}
    medidas = retiros.midiendo_frontend(medidos_ids, declared)
    require(not medidas, 'historico: retirados que se siguen midiendo en el destino: ' + ', '.join(medidas))
    medidos_hoja = {(archivo, hoja) for (_, archivo, _), hoja in leaf_titles(measured).items()}
    declarados_hoja = {(item[1], hoja) for item, hoja in resueltas.items()}
    faltan = sorted(f'{archivo}::{hoja}' for archivo, hoja in (agregados - medidos_hoja - declarados_hoja))
    require(not faltan, 'historico: tests de la feature ausentes sin declarar: ' + ', '.join(faltan))
    if not agregados:
        require(delta_solo_tests_front(repo, row['base_sha'], row['source_sha']),
                f"historico: {row['microservicio']} modifica codigo sin agregar ningun test "
                "(la garantia 4 quedaria vacia; declara --retirados o agrega cobertura)")
    result = {'measurement': measured, 'tests_agregados': sorted(f'{a}::{h}' for a, h in agregados)}
    if declared:
        result['retirados'] = sorted('::'.join(x) for x in declared)
    return result


def measure_historico(p, f, rules, manifest, retiros_path=None):
    """Cierre historico: mide CADA destino sin base preintegracion (garantia 3),
    exige que los tests de la feature sigan vivos o esten declarados como baja
    historica (garantia 4/5), y persiste una foto igual de completa que measure()
    (garantia 6)."""
    names = {r['microservicio'] for r in manifest['repos']}
    retirados, retiros_hash, revisado = {}, None, None
    if retiros_path:
        retirados = retiros.leer(retiros_path, names, f['id'])
        retiros_hash = _sha256(retiros_path)
        try:
            revisado = review_path(p, f).read_text(encoding='utf-8')
        except OSError as exc:
            raise Invalid(f'retirados: review ilegible ({type(exc).__name__})') from exc
        for row in manifest['repos']:
            declarados = retirados.get(row['microservicio'], set())
            front = _frontend(row['repo'])
            require(not declarados or retiros.tipo(declarados) == (retiros.FRONT if front else retiros.GO),
                    f"retirados: {row['microservicio']} es un destino "
                    + ("frontend: no acepta ids Go '<paquete>::<Test>', sino el id medido "
                       '[proyecto, archivo, nombre]' if front else
                       "Go: no acepta ids medidos de frontend, sino '<paquete>::<TestDePrimerNivel>'"))
        go = {x for bajas in retirados.values() for x in bajas if not retiros.es_frontend(x)}
        sin_cita = retiros.sin_cita(revisado, go)
        require(not sin_cita, 'retirados: el review no cita la baja de ' + ', '.join(sin_cita))
    initial_context = context(p, f, rules)
    hashes = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
              for name in ('postmerge_medido.py', 'postmerge_exec.py', 'medicion_destino.py', 'retiros.py',
                           'postmerge_frontend.py', 'frontend_node_reporter.mjs', 'frontend_vitest_reporter.mjs')}
    results, failures = [], []
    env = os.environ.copy()
    try:
        for key in list(os.environ):
            if key.startswith('GIT_'):
                del os.environ[key]
        os.environ.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                          GIT_NO_REPLACE_OBJECTS='1', GIT_OPTIONAL_LOCKS='0',
                          GOFLAGS='', GOWORK='off')
        for row in manifest['repos']:
            name, repo = row['microservicio'], row['repo']
            print(f'[i] historico destino {name}: {row["target_sha"]}', flush=True)
            try:
                declared = retirados.get(name, set())
                if _frontend(repo):
                    _rechazar_repo_mixto(repo)
                    require(retiros.tipo(declared) in (None, retiros.FRONT),
                            f'retirados: {name} es un destino frontend: no acepta ids Go '
                            "'<paquete>::<Test>', sino el id medido [proyecto, archivo, nombre]")
                    result = _historico_frontend(row, declared, revisado)
                else:
                    require(retiros.tipo(declared) in (None, retiros.GO),
                            f'retirados: {name} es un destino Go: no acepta ids medidos de '
                            "frontend, sino '<paquete>::<TestDePrimerNivel>'")
                    result = _historico_go(row, declared)
                if declared:
                    result.update(retirados_archivo=str(Path(retiros_path).resolve()), retirados_sha256=retiros_hash)
                results.append(dict(result, integration=row, context=initial_context, at=now_iso(),
                                    modo='historico', runner_sha256=hashes,
                                    python=str(Path(sys.executable).absolute())))
            except (Invalid, SystemExit, OSError, ValueError) as exc:
                failures.append(f'{name}: {exc}')
        require(not failures, 'historico sin cierre: ' + '; '.join(failures))
        # Red de seguridad: con el mapa que entrega multirepo.check_registered
        # (dedup de microservicio en multirepo.py) y runners que canalizan toda
        # falla real a Invalid/SystemExit/OSError/ValueError (ya atrapados
        # arriba), esta desigualdad no deberia alcanzarse por el CLI real; sigue
        # bloqueando si esa invariante llegara a romperse (ver
        # tests/test_cierre_historico.py::test_medicion_incompleta_bloquea, que
        # la ejercita en proceso con un manifiesto que duplica un microservicio).
        require(len(results) == len(names), 'historico: medicion incompleta')
        require(context(p, f, rules) == initial_context, 'historico: contexto cambio durante medicion')
        require(not retiros_path or _sha256(retiros_path) == retiros_hash,
                'historico: retirados cambio durante medicion')
        require(all(hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() == digest
                    for name, digest in hashes.items()), 'historico: runner cambio durante medicion')
        return results
    finally:
        os.environ.clear()
        os.environ.update(env)
