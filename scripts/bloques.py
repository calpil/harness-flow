"""Contrato unico de bloques generados, comparado en bytes sin strip/newlines."""
import hashlib
import json

START = b'<!-- harness-flow:features:start -->'
END = b'<!-- harness-flow:features:end -->'
PRD_PREFIX = b'# PRD maestro\n\nContenido manual arriba; harness-flow mantiene solo el bloque generado.\n\n'


def parts(content):
    if b'harness-flow:features' not in content:
        return None
    if content.count(START) != 1 or content.count(END) != 1 or content.count(b'harness-flow:features') != 2:
        raise ValueError('marcadores generados malformados/duplicados')
    prefix, rest = content.split(START)
    if END not in rest:
        raise ValueError('marcadores generados invertidos')
    _, suffix = rest.split(END)
    return prefix, suffix


def allowed(before, after):
    try:
        current = parts(after)
        if current is None:
            return False
        previous = parts(before) if before is not None else (PRD_PREFIX, b'\n')
        if previous is None and before is not None:
            previous = (before, b'\n')
        return previous is not None and previous == current
    except ValueError:
        return False


def fingerprint(content):
    if content is None:
        return {'kind': 'missing', 'generated_sha256': hashlib.sha256(
            json.dumps([PRD_PREFIX.hex(), b'\n'.hex()]).encode()).hexdigest()}
    manual = parts(content) if content is not None else (PRD_PREFIX, b'\n')
    if manual is None:
        assert content is not None  # None usa siempre PRD_PREFIX y sufijo LF.
        # Compromiso de la unica insercion permitida: prefijo exacto + bloque + LF.
        return {'kind': 'manual', 'sha256': hashlib.sha256(content).hexdigest(),
                'generated_sha256': hashlib.sha256(
                    json.dumps([content.hex(), b'\n'.hex()]).encode()).hexdigest()}
    return {'kind': 'generated', 'sha256': hashlib.sha256(
        json.dumps([x.hex() for x in manual]).encode()).hexdigest()}


def context_fingerprint(value):
    """La primera insercion no cambia el compromiso sobre los bytes manuales."""
    if isinstance(value, dict) and set(value) == {'kind', 'generated_sha256'} and value['kind'] == 'missing':
        return {'kind': 'generated', 'sha256': value['generated_sha256']}
    if isinstance(value, dict) and set(value) == {'kind', 'sha256', 'generated_sha256'} and value['kind'] == 'manual':
        return {'kind': 'generated', 'sha256': value['generated_sha256']}
    return value


def compatible(before, after):
    # Direccional: no habilita quitar un bloque ya registrado ni alterar manuales.
    return before == after or (
        isinstance(before, dict) and before.get('kind') in {'manual', 'missing'}
        and context_fingerprint(before) != before and context_fingerprint(before) == after)
