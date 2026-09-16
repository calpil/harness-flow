"""Rollback local de cierre; nunca revierte Git ni publicaciones remotas.

Protege errores/excepciones capturables, no caidas del host ni escritores
concurrentes. El caller debe tener propiedad exclusiva de docs/harness.
"""
from contextlib import contextmanager


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
    missing_dirs = set()
    for path in [*files, *(directory / 'placeholder' for directory in directories)]:
        missing_dirs.update(x for x in path.parents if p['root'] in x.parents and not x.exists())
    try:
        yield
    except BaseException:
        # Solo se eliminan salidas creadas por este cierre, nunca arboles Git.
        for directory in directories:
            if directory.is_dir():
                for path in directory.rglob('*'):
                    if path.is_file() and path not in saved:
                        path.unlink()
        for path, content in saved.items():
            if content is None:
                if path.exists():
                    path.unlink()
            elif not path.exists() or path.read_bytes() != content[0]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content[0])
                path.chmod(content[1])
        for path in sorted(missing_dirs, key=lambda x: len(x.parts), reverse=True):
            if path.exists():
                path.rmdir()
        raise
