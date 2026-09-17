"""Rollback local de cierre; nunca revierte Git ni publicaciones remotas.

Protege errores/excepciones capturables, no caidas del host ni escritores
concurrentes. El caller debe tener propiedad exclusiva de docs/harness.
"""
from contextlib import contextmanager
import sys


def _censo(p):
    """Archivos presentes hoy bajo docs/, para detectar los que cree el cierre.

    outputs() solo enumera los documentos de ruta fija; el cierre tambien
    escribe lecciones, specs y revisiones de nombre variable. Comparando el
    censo de antes con el de despues, el rollback sabe cuales nacieron en este
    cierre fallido y debe llevarse, sin tocar nada preexistente.
    """
    docs = p['docs']
    if not docs.is_dir():
        return set()
    return {x for x in docs.rglob('*') if x.is_file()}


def outputs(p, fid):
    return [p['backlog'], p['progress'] / 'history.md',
            p['progress'] / f'current-{fid}.md',
            p['docs'] / 'prd' / 'PRD-master.md', p['docs'] / 'sdd.md']


def preflight(p, fid):
    root = p['root']
    directories = [p['progress'] / 'archive', p['harness'] / 'outbox']
    files = outputs(p, fid)
    for directory in directories:
        if directory.exists():
            if not directory.is_dir():
                raise ValueError('ruta de salida invalida: archive/outbox no es directorio')
            files += list(directory.rglob('*'))
    for path in [*files, *directories]:
        for parent in [path, *path.parents]:
            if parent == root:
                break
            if parent.is_symlink():
                raise ValueError('escritura fuera de contrato: symlink en documentos/progreso')
            if parent != path and parent.exists() and not parent.is_dir():
                raise ValueError('ruta de salida invalida: padre no es directorio')
    for path in outputs(p, fid):
        if path.exists() and not path.is_file():
            raise ValueError(f'ruta de salida invalida: {path.name} no es archivo')


@contextmanager
def transaction(p, fid):
    preflight(p, fid)
    directories = [p['progress'] / 'archive', p['harness'] / 'outbox']
    files = outputs(p, fid) + [x for directory in directories if directory.exists()
                               for x in directory.rglob('*') if x.is_file()]
    saved = {x: (x.read_bytes(), x.stat().st_mode) if x.exists() else None for x in files}
    # Censo previo de docs/: el cierre escribe ahi documentos que no estan en
    # outputs() (lecciones, specs, revisiones). Sin este censo el rollback los
    # dejaba puestos y el arbol quedaba con basura de un cierre que fallo.
    docs_previos = _censo(p)
    missing_dirs = set()
    for path in [*files, *(directory / 'placeholder' for directory in directories)]:
        missing_dirs.update(x for x in path.parents if p['root'] in x.parents and not x.exists())
    try:
        yield
    except BaseException:
        # El rollback es best-effort y NUNCA debe tapar la excepcion original:
        # si una restauracion falla (permisos, disco), se anota y se sigue con
        # las demas. Abortar aca dejaba el arbol a medio revertir y cambiaba la
        # causa raiz por un PermissionError del propio rollback.
        problemas = []

        def _intentar(accion, descripcion):
            try:
                accion()
            except OSError as exc:
                problemas.append(f'{descripcion}: {exc}')

        # Solo se eliminan salidas creadas por este cierre, nunca arboles Git.
        for directory in directories:
            if directory.is_dir():
                for path in directory.rglob('*'):
                    if path.is_file() and path not in saved:
                        _intentar(path.unlink, f'no se pudo borrar {path}')
        for path in sorted(_censo(p) - docs_previos):
            _intentar(path.unlink, f'no se pudo borrar {path}')
        for path, content in saved.items():
            if content is None:
                if path.exists():
                    _intentar(path.unlink, f'no se pudo borrar {path}')
            elif not path.exists() or path.read_bytes() != content[0]:
                def _restaurar(path=path, content=content):
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content[0])
                    path.chmod(content[1])
                _intentar(_restaurar, f'no se pudo restaurar {path}')
        for path in sorted(missing_dirs, key=lambda x: len(x.parts), reverse=True):
            if path.exists():
                _intentar(path.rmdir, f'no se pudo quitar el directorio {path}')
        if problemas:
            # Va por stderr, no como excepcion: la original manda.
            print('[!] rollback incompleto:\n     - ' + '\n     - '.join(problemas),
                  file=sys.stderr)
        raise
