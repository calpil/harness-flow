"""Medicion obligatoria de cada destino: ejecuta, nunca consume recibos de PASS.

Soporte cerrado a Go JSON/-exec existente y Angular22/Vitest4+Node22 de ADR.
La configuracion solo enumera bases: no puede cambiar comando ni omitir repos.
"""
import hashlib
import os
from pathlib import Path
import sys

import postmerge_medido as runner
import retiros
from comun import now_iso, review_path
from multirepo import Invalid, context, read_manifest, require

COMMAND = 'go test -tags integration -count=1 -json ./...'


def _sha256(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as exc:
        raise Invalid(f'no se pudo leer {path} ({type(exc).__name__})') from exc


def _frontend(repo):
    """El destino se mide con el runner frontend (contrato Angular22/Vitest4)."""
    return (Path(repo) / 'angular.json').exists() or (Path(repo) / 'package.json').exists()


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
                    require(not (Path(repo) / 'go.mod').exists(), 'postmerge: repo mixto no soportado')
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
