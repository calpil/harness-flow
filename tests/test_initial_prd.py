"""Primera generacion de PRD manual: solo fixtures Git, nunca documentos reales."""
import sys
import unittest
import importlib
import tempfile
from pathlib import Path

import test_multirepo_close as fixtures

sys.path.insert(0, str(fixtures.SCRIPTS))
import documentacion
bloques = importlib.import_module('bloques')
multirepo = importlib.import_module('multirepo')


class InitialPrdTests(unittest.TestCase):
    def setUp(self):
        self.t = fixtures.MultiRepoCloseTests()
        self.t.setUp()
        self.addCleanup(self.t.doCleanups)

    def test_first_generation_preserves_registration_and_review(self):
        t = self.t
        prd = t.root / 'docs/prd/PRD-master.md'
        prd.parent.mkdir()
        manual = b'# User PRD\r\n\r\n  Actual requirements\t\r\n'
        prd.write_bytes(manual)
        t.register()
        t.seal()
        initial = t.load()['multi_repo_protected']
        t.ok('documentacion.py', 'sync')
        generated = prd.read_bytes()
        self.assertTrue(generated.startswith(manual))
        self.assertIn(documentacion.INICIO.encode(), generated)
        result = t.cli('worktree.py', 'register', '--feature', '7', '--manifest', str(t.manifest_path))
        self.assertEqual(result.returncode, 0, 'F4-R1 primera insercion legitima rechazada: ' + result.stderr)
        self.assertNotEqual(t.load()['multi_repo_protected'], initial)
        # El avance de estado de generacion no vuelve stale una revision valida.
        result = t.close()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(t.load()['status'], 'done')
        self.assertTrue(prd.read_bytes().startswith(manual))

    def test_git_allows_only_initial_generated_append(self):
        t = self.t
        prd = t.root / 'docs/prd/PRD-master.md'
        prd.parent.mkdir()
        manual = b'# User PRD\r\n requirements\t\r\n'
        prd.write_bytes(manual)
        t.git(t.root, 'init', '-b', 'develop')
        (t.root / '.gitignore').write_text('/alpha/\n/beta/\n/gamma/\n')
        t.git(t.root, 'add', '.gitignore', 'docs', 'harness')
        t.git(t.root, 'commit', '-m', 'fixture: manual PRD before generator')
        t.ok('documentacion.py', 'sync')
        result = t.cli('gate.py', 'check')
        self.assertEqual(result.returncode, 0, 'F4-R1 initial generated Git diff rejected: ' + result.stdout)
        generated = prd.read_bytes()
        self.assertTrue(generated.startswith(manual))
        prd.write_bytes(generated.replace(b'requirements', b'changed requirement'))
        result = t.cli('gate.py', 'check')
        self.assertNotEqual(result.returncode, 0, 'manual edit was authorized by initial generation')

    def test_close_initializes_once_and_rejects_later_marker_removal(self):
        t = self.t
        prd = t.root / 'docs/prd/PRD-master.md'
        prd.parent.mkdir()
        manual = b'# Original manual\r\n\timmutable\r\n'
        prd.write_bytes(manual)
        t.register()
        t.seal()
        result = t.close()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(prd.read_bytes().startswith(manual))
        prd.write_bytes(manual)
        before = (t.root / 'harness/feature_list.json').read_bytes()
        result = t.close()
        self.assertNotEqual(result.returncode, 0, 'F4-R1 cierre olvido que el bloque ya fue generado')
        self.assertEqual((t.root / 'harness/feature_list.json').read_bytes(), before)


class InitialPrdBlockTests(unittest.TestCase):
    def test_removed_generated_file_is_not_initial_absence(self):
        generated = bloques.PRD_PREFIX + bloques.START + b'\ngenerated\n' + bloques.END + b'\n'
        self.assertFalse(bloques.compatible(bloques.fingerprint(generated), bloques.fingerprint(None)),
                         'F4-R1 archivo generado eliminado indistinguible de ausencia inicial')

    def test_initial_transition_is_exact_and_directional(self):
        block = documentacion.INICIO + '\ngenerated\n' + documentacion.FIN + '\n'
        for manual in (b'', b'no newline', b'LF\n', b'CRLF\r\n\t', b'\xff\x00\r\n', bloques.PRD_PREFIX):
            with self.subTest(manual=manual), tempfile.TemporaryDirectory() as tmp:
                prd = Path(tmp) / 'PRD.md'
                prd.write_bytes(manual)
                documentacion._actualizar_bloque(prd, 'PRD maestro', block)
                generated = prd.read_bytes()
                self.assertEqual(generated, manual + block.encode())
                old, new = bloques.fingerprint(manual), bloques.fingerprint(generated)
                self.assertTrue(bloques.compatible(old, new))
                self.assertTrue(bloques.allowed(manual, generated))
                self.assertEqual(bloques.context_fingerprint(old), new)
                for removed in (manual, None):
                    self.assertFalse(bloques.compatible(new, bloques.fingerprint(removed)))
                for altered in (b' ' + generated, generated[:-1], generated + b'\r\n'):
                    self.assertFalse(bloques.allowed(manual, altered))
                    self.assertFalse(bloques.compatible(old, bloques.fingerprint(altered)))
                with self.assertRaises(ValueError):
                    bloques.fingerprint(generated + block.encode())

    def test_initial_transition_cannot_rebaseline_other_paths_or_roots(self):
        rel = 'docs/prd/PRD-master.md'
        manual = b'Contract\r\n'
        generated = manual + bloques.START + b'\nx\n' + bloques.END + b'\n'
        before = {'/fixture': {rel: bloques.fingerprint(manual), 'docs/constitution.md': 'original'}}
        after = {'/fixture': {rel: bloques.fingerprint(generated), 'docs/constitution.md': 'original'}}
        self.assertTrue(multirepo.snapshot_matches(before, after))
        self.assertEqual(multirepo.protected_context(before), multirepo.protected_context(after))
        self.assertFalse(multirepo.snapshot_matches(after, before))
        self.assertFalse(multirepo.snapshot_matches(before, {**after, '/other': after['/fixture']}))
        self.assertFalse(multirepo.snapshot_matches(before, {'/fixture': {rel: after['/fixture'][rel]}}))
        altered = {'/fixture': {**after['/fixture'], 'docs/constitution.md': 'changed'}}
        self.assertFalse(multirepo.snapshot_matches(before, altered))
