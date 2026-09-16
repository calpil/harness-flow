"""Cierre real en Git FIXTURE aislado, sin instalar/cerrar ADR."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import test_frontend_runner as frontend
from test_frontend_runner import SCRIPTS, NODE_FILES


class FrontendCloseTests(unittest.TestCase):
    def setUp(self):
        t = frontend.FrontendFixture('runTest')
        t.setUp()
        self.addCleanup(t.doCleanups)
        self.t = t
        self.root = t.home / 'project'
        (self.root / 'docs').mkdir(parents=True)
        (self.root / 'harness/progress').mkdir(parents=True)
        repo = self.root / 'front'
        t.repo.rename(repo)
        t.repo = repo
        t.env['HARNESS_SKILLS_DIR'] = str(t.home / 'skills')
        lesson = t.home / 'skills/closure-contract/SKILL.md'
        lesson.parent.mkdir(parents=True)
        lesson.write_text('---\nname: closure-contract\ndescription: Fixture\n---\n')
        self.base_sha = t.git('rev-parse', 'HEAD')
        t.measured_base()
        t.write('feature.txt', 'feature fixture\n')
        tip = t.commit('feature integrated fixture')
        self.row = dict(microservicio='front', repo=str(repo), worktree=str(repo),
                        base_sha=self.base_sha, source_sha=tip, target_sha=tip, target_branch='develop')
        self.manifest = t.home / 'manifest.json'
        self.map = t.home / 'postmerge.json'
        self.map.write_text(json.dumps(dict(version=1, feature='7', bases={'front': str(t.base)})))
        self.backlog = self.root / 'harness/feature_list.json'
        self.backlog.write_text(json.dumps(dict(project='fixture', rules={'rutas_protegidas':['docs/constitution.md','docs/prd/**']},
                features=[dict(id=7, name='Frontend fixture', status='in_progress', microservicios=['front'])])))
        (self.root / 'docs/spec-feature-7-frontend-fixture.md').write_text('Estado: draft\n- AC-1: Given frontend When integrated Then measured\nComando: `git -C front merge-base --is-ancestor HEAD HEAD`\n')
        for name in ('impl-7.md', 'review-7.md'):
            (self.root / 'docs' / name).write_text('## AC-1\nfront/feature.txt:1\n')
        (self.root / 'docs/constitution.md').write_text('User contract\n')
        (self.root / 'harness/progress/current-7.md').write_text('Fixture progress\n')
        self.ok('gate.py', 'approve-spec', '--feature', '7', '--yes', '--por', 'Fixture')

    def command(self, script, *args):
        argv = [sys.executable, '-B', str(SCRIPTS / script), *args]
        r = subprocess.run(argv, cwd=self.root, env=self.t.env, capture_output=True, text=True, timeout=120)
        directory = os.environ.get('HARNESS_TEST_FRONTEND_LOGS')
        if directory:
            p = Path(directory); p.mkdir(parents=True, exist_ok=True)
            with (p / (self.id() + '.jsonl')).open('a') as f:
                f.write(json.dumps(dict(argv=argv, exit=r.returncode, stdout=r.stdout, stderr=r.stderr)) + '\n')
            for artifact in self.t.home.glob('*.evidence.json'):
                shutil.copy2(artifact, p / (self.id() + '.' + artifact.name))
        return r

    def ok(self, script, *args):
        r = self.command(script, *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def register(self, rows=None):
        self.manifest.write_text(json.dumps(dict(version=1, feature='7', repos=rows or [self.row])))
        self.ok('worktree.py', 'register', '--feature', '7', '--manifest', str(self.manifest))
        self.ok('gate.py', 'verify', '--feature', '7')
        self.ok('gate.py', 'revision', '--feature', '7', '--veredicto', 'approved', '--por', 'Fixture reviewer')

    def close(self):
        return self.command('gate.py', 'close', '--feature', '7', '--status', 'done', '--to', 'develop',
                            '--integrated', '--leccion', 'closure-contract', '--postmerge', str(self.map))

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for base in (self.root/'docs', self.root/'harness')
                for p in base.rglob('*') if p.is_file()}

    def test_close_runs_frontend_and_binds_real_measurement_to_target(self):
        self.register()
        r = self.close()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        f = json.loads(self.backlog.read_text())['features'][0]
        self.assertEqual(f['status'], 'done')
        receipts = f['mediciones_destino']
        self.assertEqual(len(receipts), 1)
        receipt = receipts[0]
        self.assertEqual(receipt['integration'], self.row)
        self.assertEqual(receipt['measurement']['sha'], self.row['target_sha'])
        self.assertEqual(len(receipt['measurement']['results']), 3)
        self.assertEqual(set(receipt['measurement']['execution']), {'node:test', 'angular:app'})

    def test_new_red_on_target_blocks_close_and_preserves_documents(self):
        self.t.write(NODE_FILES[0], (self.t.repo / NODE_FILES[0]).read_text().replace('equal(1, 1)', 'equal(1, 2)'))
        self.row['target_sha'] = self.t.commit('target regression')
        self.register()
        before = self.snapshot()
        r = self.close()
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('rojos nuevos', r.stdout + r.stderr)
        self.assertNotIn('Traceback', r.stderr)
        self.assertEqual(self.snapshot(), before)
        artifacts = list(self.t.home.glob('*.close.evidence.json'))
        self.assertEqual(len(artifacts), 1)
        trace = json.loads(artifacts[0].read_text())
        self.assertEqual(trace['exit'], 1)
        self.assertTrue(trace['execution']['node:test']['stdout'])

    def test_mixed_frontend_and_go_destinations_are_both_measured(self):
        backend = self.root / 'backend'
        backend.mkdir()
        self.t.env.update(GOPROXY='off', GOSUMDB='off', GOTOOLCHAIN='local', GOWORK='off',
                          GOCACHE=os.environ.get('HARNESS_TEST_GOCACHE', str(self.t.home / 'go-cache')))
        def git(*args):
            r = subprocess.run(['git', '-C', str(backend), *args], env=self.t.env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stdout.strip()
        git('init', '-b', 'develop')
        (backend / 'go.mod').write_text('module fixture.invalid/backend\n\ngo 1.22\n')
        (backend / 'contract_test.go').write_text('package contract\nimport "testing"\nfunc TestHealthy(t *testing.T) {}\n')
        git('add', '.'); git('commit', '-m', 'fixture base')
        base = git('rev-parse', 'HEAD')
        base_path = self.t.home / 'backend-base.json'
        self.ok('postmerge_medido.py', 'base', '--repo', str(backend), '--cmd',
                'go test -tags integration -count=1 -json ./...', '--guardar', str(base_path))
        (backend / 'feature.txt').write_text('fixture delta\n')
        git('add', '.'); git('commit', '-m', 'fixture feature')
        tip = git('rev-parse', 'HEAD')
        row = dict(microservicio='backend', repo=str(backend), worktree=str(backend), base_sha=base,
                   source_sha=tip, target_sha=tip, target_branch='develop')
        data = json.loads(self.backlog.read_text())
        data['features'][0]['microservicios'].append('backend')
        self.backlog.write_text(json.dumps(data))
        self.map.write_text(json.dumps(dict(version=1, feature='7', bases={'front':str(self.t.base), 'backend':str(base_path)})))
        self.register([self.row, row])
        r = self.close()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        receipts = json.loads(self.backlog.read_text())['features'][0]['mediciones_destino']
        self.assertEqual(len(receipts), 2)
        self.assertEqual(len(receipts[0]['measurement']['results']), 3)
        self.assertEqual(receipts[1]['command'], 'go test -tags integration -count=1 -json ./...')
        self.assertEqual(len(receipts[1]['results']), 1)
        self.assertEqual(set(receipts[1]['execution']['exits'].values()), {0})

    def test_stale_base_cannot_close_without_running(self):
        self.register()
        value = json.loads(self.t.base.read_text())
        value['sha'] = self.row['target_sha']
        self.t.base.write_text(json.dumps(value))
        before = self.snapshot()
        r = self.close()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('stale', r.stdout + r.stderr)
        self.assertNotIn('$ [', r.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_protected_root_rejects_before_frontend(self):
        self.register()
        (self.root / 'docs/constitution.md').write_text('mutation\n')
        before = self.snapshot()
        r = self.close()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('protegidas', r.stdout + r.stderr)
        self.assertNotIn('$ [', r.stdout)
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
