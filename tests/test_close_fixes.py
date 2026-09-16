"""Review regressions: only ephemeral Git fixtures, never project state."""
import contextlib
import io
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

import test_multirepo_close as fixtures

sys.path.insert(0, str(fixtures.SCRIPTS))
import gate
import documentacion
import atlassian


class CloseFixes(unittest.TestCase):
    def setUp(self):
        self.t = fixtures.MultiRepoCloseTests()
        self.t.setUp()
        self.addCleanup(self.t.doCleanups)

    def snapshot(self):
        t = self.t
        return {str(p.relative_to(t.root)): (p.read_bytes() if p.is_file() else None)
                for base in (t.root / 'docs', t.root / 'harness')
                for p in base.rglob('*')}

    def invoke(self, integrated=True, publish=False):
        t = self.t
        args = ['gate.py', 'close', '--feature', '7', '--status', 'done', '--to', 'develop',
                '--leccion', 'closure-contract']
        if integrated:
            args.extend(['--integrated', '--postmerge', str(t.postmerge_path)])
        if publish:
            args.append('--publicar-atlassian')
        out = io.StringIO()
        previous = Path.cwd()
        try:
            os.chdir(t.root)
            with mock.patch.dict(os.environ, t.env, clear=True), mock.patch.object(sys, 'argv', args), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                try:
                    gate.main()
                    code = 0
                except (Exception, SystemExit) as exc:
                    code = 1
                    print(type(exc).__name__, str(exc))
        finally:
            os.chdir(previous)
        return code, out.getvalue()

    def monorepo(self):
        t = self.t
        t.git(t.root, 'init', '-b', 'develop')
        (t.root / '.gitignore').write_text('/alpha/\n/beta/\n/gamma/\n')
        t.load()['branch'] = 'feature/fixture'
        t.save()
        t.seal()
        t.git(t.root, 'add', '.gitignore', 'docs', 'harness')
        t.git(t.root, 'commit', '-m', 'fixture: mono process')
        t.git(t.root, 'checkout', '-b', 'feature/fixture')
        (t.root / 'mono.txt').write_text('feature\n')
        t.git(t.root, 'add', 'mono.txt')
        t.git(t.root, 'commit', '-m', 'fixture: mono feature')
        source = t.git(t.root, 'rev-parse', 'HEAD')
        t.git(t.root, 'checkout', 'develop')
        return source

    def test_F1_partial_write_restores_all_local_bytes_multi_and_mono(self):
        for multi in (True, False):
            with self.subTest(multi=multi):
                if not multi:
                    self.t.doCleanups()
                    self.setUp()
                    source = self.monorepo()
                else:
                    self.t.register()
                    self.t.seal()
                before = self.snapshot()
                real = documentacion._actualizar_bloque
                written = []

                def fail_second(path, *args):
                    if written:
                        raise OSError('fixture: second document failed')
                    result = real(path, *args)
                    written.append(path)
                    return result

                with mock.patch.object(documentacion, '_actualizar_bloque', side_effect=fail_second):
                    code, output = self.invoke(multi)
                self.assertEqual(code, 1, output)
                self.assertEqual(len(written), 1, output)
                self.assertEqual(before, self.snapshot(), 'F1 local state changed after partial sync')
                self.assertEqual(self.t.load()['status'], 'in_progress')
                if not multi:
                    self.t.git(self.t.root, 'merge-base', '--is-ancestor', source, 'develop')
                    self.assertIn('merge local conservado', output)

    def test_F1_invalid_output_path_never_persists_done(self):
        t = self.t
        t.register()
        t.seal()
        (t.root / 'docs' / 'sdd.md').mkdir()
        before = self.snapshot()
        code, output = self.invoke()
        self.assertEqual(code, 1, output)
        self.assertEqual(before, self.snapshot(), 'F1 invalid path persisted partial done')

    def test_F3_restored_protected_history_is_not_a_clean_net_diff(self):
        for destination in ('source', 'target', 'merged_side'):
            with self.subTest(history=destination):
                if destination != 'source':
                    self.t.doCleanups()
                    self.setUp()
                t = self.t
                row = t.manifest['repos'][0]
                repo = Path(row['repo'])
                tree = Path(row['worktree']) if destination == 'source' else repo
                if destination == 'merged_side':
                    t.git(repo, 'checkout', '-b', 'fixture-side')
                (tree / 'docs').mkdir()
                (tree / 'docs/constitution.md').write_text('Fixture contract, not a secret\n')
                t.git(tree, 'add', 'docs/constitution.md')
                t.git(tree, 'commit', '-m', 'fixture: protected commit')
                t.git(tree, 'rm', 'docs/constitution.md')
                t.git(tree, 'commit', '-m', 'fixture: restore tree')
                if destination == 'source':
                    row['source_sha'] = t.git(tree, 'rev-parse', 'HEAD')
                    t.git(repo, 'merge', '--ff-only', row['source_sha'])
                if destination == 'merged_side':
                    t.git(repo, 'checkout', 'develop')
                    t.git(repo, 'merge', '--no-ff', 'fixture-side', '-m', 'fixture: merged side history')
                row['target_sha'] = t.git(repo, 'rev-parse', 'HEAD')
                t.write_manifest()
                net = t.git(repo, 'diff', '--name-only', row['base_sha'], row['target_sha'])
                self.assertNotIn('constitution.md', net)
                before = self.snapshot()
                result = t.cli('worktree.py', 'register', '--feature', '7', '--manifest', str(t.manifest_path))
                self.assertNotEqual(result.returncode, 0, 'F3 restored history accepted: ' + result.stdout)
                self.assertIn('protegidas modificadas en commits', result.stderr)
                self.assertEqual(before, self.snapshot())

    def test_F4_generated_refresh_preserves_manual_bytes_and_registration(self):
        t = self.t
        prd = t.root / 'docs/prd/PRD-master.md'
        prd.parent.mkdir()
        prefix, suffix = b'User prefix  \r\n\r\n\t', b'\r\n\r\nUser suffix \t\r\n'
        prd.write_bytes(prefix + documentacion.INICIO.encode() + b'\nSTALE\n' + documentacion.FIN.encode() + suffix)
        t.register()
        t.seal()
        original_registration = t.load()['multi_repo_protected']
        t.ok('documentacion.py', 'sync')
        current = prd.read_bytes()
        self.assertEqual(current.split(documentacion.INICIO.encode())[0], prefix, 'F4 changed manual prefix bytes')
        self.assertEqual(current.split(documentacion.FIN.encode())[1], suffix, 'F4 changed manual suffix bytes')
        t.register()
        self.assertEqual(t.load()['multi_repo_protected'], original_registration)
        result = t.close()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_F4_gate_rejects_manual_whitespace_and_bad_markers(self):
        t = self.t
        prd = t.root / 'docs/prd/PRD-master.md'
        prd.parent.mkdir()
        original = b' manual  \n\n' + documentacion.INICIO.encode() + b'\nold\n' + documentacion.FIN.encode() + b'\n suffix \n'
        prd.write_bytes(original)
        t.git(t.root, 'init', '-b', 'develop')
        (t.root / '.gitignore').write_text('/alpha/\n/beta/\n/gamma/\n')
        t.git(t.root, 'add', '.gitignore', 'docs', 'harness')
        t.git(t.root, 'commit', '-m', 'fixture: protected PRD')
        valid = original.replace(b'old', b'generated update')
        prd.write_bytes(valid)
        t.ok('gate.py', 'check')
        mutations = [valid.lstrip(), valid.replace(b' suffix', b' changed suffix'),
                     valid + documentacion.INICIO.encode(), valid.replace(documentacion.FIN.encode(), b''),
                     valid.replace(b'features:start', b'features:start-invalid')]
        for content in mutations:
            with self.subTest(content=content):
                prd.write_bytes(content)
                result = t.cli('gate.py', 'check')
                self.assertNotEqual(result.returncode, 0, 'F4 malformed/manual PRD accepted')
                self.assertIn('rutas protegidas modificadas', result.stdout)
        prd.write_bytes(original)

    def test_F2_source_verify_is_not_destination_measurement(self):
        t = self.t
        t.register()
        t.seal()
        before = self.snapshot()
        result = t.cli('gate.py', 'close', '--feature', '7', '--status', 'done', '--to', 'develop',
                       '--integrated', '--leccion', 'closure-contract')
        self.assertNotEqual(result.returncode, 0, 'F2 close accepted unmeasured destination tips')
        self.assertIn('postmerge', result.stdout + result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_F2_real_target_red_does_not_close_after_source_green(self):
        t = self.t
        row = t.manifest['repos'][1]
        repo = Path(row['repo'])
        (repo / 'base.txt').write_text('integration regression\n')
        t.git(repo, 'add', 'base.txt')
        t.git(repo, 'commit', '-m', 'fixture: break target only')
        row['target_sha'] = t.git(repo, 'rev-parse', 'HEAD')
        t.write_manifest()
        import subprocess
        for key, expected in (('worktree', 0), ('repo', 1)):
            r = subprocess.run(['go', 'test', '-count=1', './...'], cwd=row[key], env=t.env, capture_output=True, text=True)
            self.assertEqual(r.returncode, expected, r.stdout + r.stderr)
        t.register()
        t.seal()
        before = self.snapshot()
        result = t.close()
        self.assertNotEqual(result.returncode, 0, 'F2 target suite red but done persisted')
        self.assertIn('postmerge', result.stdout + result.stderr)
        self.assertIn('TestBaseContract', result.stdout + result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_F1_standalone_sync_rolls_back_first_write(self):
        t = self.t
        before = self.snapshot()
        real = documentacion._actualizar_bloque
        written = []
        def fail_second(path, *args):
            if written:
                raise OSError('fixture: second sync write failed')
            result = real(path, *args)
            written.append(path)
            return result
        with mock.patch.object(documentacion, '_actualizar_bloque', side_effect=fail_second):
            with self.assertRaises(OSError):
                documentacion.sync(gate.paths(t.root), t.data)
        self.assertEqual(len(written), 1)
        self.assertEqual(before, self.snapshot(), 'F1 standalone sync left partial documents')

    def test_F4_history_allows_only_generated_prd_commit(self):
        t = self.t
        row = t.manifest['repos'][0]
        wt = Path(row['worktree'])
        prd = wt / 'docs/prd/PRD-master.md'
        documentacion._actualizar_bloque(prd, 'PRD maestro', documentacion.INICIO + '\nGenerated fixture\n' + documentacion.FIN)
        t.git(wt, 'add', 'docs/prd/PRD-master.md')
        t.git(wt, 'commit', '-m', 'fixture: generated PRD only')
        row['source_sha'] = t.git(wt, 'rev-parse', 'HEAD')
        t.git(row['repo'], 'merge', '--ff-only', row['source_sha'])
        row['target_sha'] = t.git(row['repo'], 'rev-parse', 'HEAD')
        t.write_manifest()
        t.register()
        old = prd.read_bytes()
        prd.write_bytes(b'Unauthorized manual header\n' + old)
        t.git(wt, 'add', 'docs/prd/PRD-master.md')
        t.git(wt, 'commit', '-m', 'fixture: protected manual history')
        prd.write_bytes(old)
        t.git(wt, 'add', 'docs/prd/PRD-master.md')
        t.git(wt, 'commit', '-m', 'fixture: restore manual bytes')
        row['source_sha'] = t.git(wt, 'rev-parse', 'HEAD')
        t.git(row['repo'], 'merge', '--ff-only', row['source_sha'])
        row['target_sha'] = t.git(row['repo'], 'rev-parse', 'HEAD')
        t.write_manifest()
        r = t.cli('worktree.py', 'register', '--feature', '7', '--manifest', str(t.manifest_path))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('protegidas modificadas en commits', r.stderr)

    def test_F2_baselines_reject_missing_corrupt_foreign_stale_or_unexecuted(self):
        import copy
        import json
        t = self.t
        t.register()
        t.seal()
        path = t.home / 'base-beta.json'
        original = path.read_bytes()
        raw = json.loads(original)
        variants = [('corrupt', b'{'), ('empty', b'{}')]
        changes = [('foreign repo', lambda b: b.update(repo=str(t.root / 'alpha'))),
                   ('stale', lambda b: b.update(sha=t.manifest['repos'][1]['target_sha'])),
                   ('command', lambda b: b.update(cmd='true')),
                   ('unexecuted', lambda b: b.pop('ejecucion')),
                   ('incoherent', lambda b: b['ejecucion']['exits'].update({'fixture.invalid/beta': 23})),
                   ('zero tests', lambda b: b.update(resultados=[], rojos=[]))]
        for name, change in changes:
            value = copy.deepcopy(raw)
            change(value)
            variants.append((name, json.dumps(value).encode()))
        for name, value in variants:
            with self.subTest(base=name):
                path.write_bytes(value)
                before = self.snapshot()
                result = t.close()
                self.assertNotEqual(result.returncode, 0, 'F2 invalid baseline accepted: ' + name)
                self.assertIn('postmerge', result.stdout + result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertEqual(before, self.snapshot())
        path.unlink()
        t.assert_close_rejected('postmerge')
        path.write_bytes(original)
        # A typed PASS is never used instead of a target run.
        t.load()['mediciones_destino'] = [{'status': 'PASS', 'exit': 0}]
        t.save()
        result = t.close()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        measured = t.load()['mediciones_destino']
        self.assertEqual(len(measured), 3)
        self.assertEqual(result.stdout.count('[i] postmerge destino '), 3)
        for receipt, row in zip(measured, t.manifest['repos']):
            self.assertEqual(receipt['integration'], row)
            self.assertEqual(receipt['command'], 'go test -tags integration -count=1 -json ./...')
            self.assertTrue(receipt['results'])
            self.assertTrue(receipt['runner_sha256'])
            self.assertEqual(set(receipt['execution']['exits'].values()), {0})

    def test_F2_disappeared_skipped_and_zero_exit_without_tests_reject(self):
        for variant in ('removed', 'skip', 'exit0'):
            with self.subTest(variant=variant):
                if variant != 'removed':
                    self.t.doCleanups()
                    self.setUp()
                t = self.t
                row = t.manifest['repos'][1]
                repo = Path(row['repo'])
                if variant == 'removed':
                    content = 'package contract\nimport "testing"\nfunc TestOther(t *testing.T) {}\n'
                elif variant == 'skip':
                    content = 'package contract\nimport "testing"\nfunc TestBaseContract(t *testing.T) { t.Skip("fixture") }\nfunc TestOther(t *testing.T) {}\n'
                else:
                    content = 'package contract\nimport ("testing"; "os")\nfunc TestMain(m *testing.M) { os.Exit(0) }\nfunc TestBaseContract(t *testing.T) {}\n'
                (repo / 'contract_test.go').write_text(content)
                t.git(repo, 'add', 'contract_test.go')
                t.git(repo, 'commit', '-m', 'fixture: missing measurements')
                row['target_sha'] = t.git(repo, 'rev-parse', 'HEAD')
                t.write_manifest()
                t.register()
                t.seal()
                t.assert_close_rejected('postmerge')

    def test_F1_late_history_failure_rolls_back_existing_documents(self):
        t = self.t
        t.ok('documentacion.py', 'sync')
        t.register()
        t.seal()
        before = self.snapshot()
        real = gate.bitacora
        written = []
        def fail_after_history(p, message):
            real(p, message)
            written.append(message)
            raise OSError('fixture: history write failed after bytes reached disk')
        with mock.patch.object(gate, 'bitacora', side_effect=fail_after_history):
            code, output = self.invoke()
        self.assertEqual(code, 1, output)
        self.assertEqual(len(written), 1, output)
        self.assertEqual(before, self.snapshot(), 'F1 late history failure persisted done')

    def test_F4_registered_snapshot_does_not_allow_marker_or_manual_edits(self):
        t = self.t
        t.ok('documentacion.py', 'sync')
        t.register()
        t.seal()
        prd = t.root / 'docs/prd/PRD-master.md'
        original = prd.read_bytes()
        mutations = [original.replace(documentacion.INICIO.encode(), b''),
                     original.replace(documentacion.INICIO.encode(), b'').replace(documentacion.FIN.encode(), b''),
                     original + documentacion.FIN.encode(), b'\n' + original,
                     original.replace(b'features:start', b'features:broken')]
        for content in mutations:
            prd.write_bytes(content)
            before = self.snapshot()
            t.assert_close_rejected('protegidas')
            result = t.cli('worktree.py', 'register', '--feature', '7', '--manifest', str(t.manifest_path))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(before, self.snapshot())
        prd.write_bytes(original)

    def test_F2_new_skipped_test_is_not_complete_measurement(self):
        t = self.t
        row = t.manifest['repos'][0]
        repo = Path(row['repo'])
        path = repo / 'contract_test.go'
        path.write_text(path.read_text() + '\nfunc TestNewSkipped(t *testing.T) { t.Skip("fixture") }\n')
        t.git(repo, 'add', 'contract_test.go')
        t.git(repo, 'commit', '-m', 'fixture: new skipped test')
        row['target_sha'] = t.git(repo, 'rev-parse', 'HEAD')
        t.write_manifest()
        t.register()
        t.seal()
        t.assert_close_rejected('skip')

    def test_F1_sync_command_history_failure_is_atomic(self):
        t = self.t
        before = self.snapshot()
        p = gate.paths(t.root)
        real = documentacion.bitacora
        def fail_after_history(paths, message):
            real(paths, message)
            raise OSError('fixture: sync history failed')
        with mock.patch.object(documentacion, 'paths', return_value=p), \
                mock.patch.object(documentacion, 'bitacora', side_effect=fail_after_history):
            with self.assertRaises(OSError):
                documentacion.cmd_sync(None)
        self.assertEqual(before, self.snapshot(), 'F1 sync command left partial history/documents')

    def test_F1_atlassian_failure_restores_documents_and_history(self):
        t = self.t
        t.register()
        t.seal()
        (t.root / 'harness' / 'atlassian.json').write_text('{}')
        before = self.snapshot()
        def partial_publication(args):
            # Real local outbox write, no HTTP, tokens or user credentials.
            atlassian._intent(gate.paths(t.root), 'fixture-close', {'status': 'done'})
            raise SystemExit('fixture remote failed')
        with mock.patch.object(atlassian, 'cmd_push', side_effect=partial_publication):
            code, output = self.invoke(publish=True)
        self.assertEqual(code, 1, output)
        self.assertEqual(before, self.snapshot(), 'F1 remote failure left false local history')
