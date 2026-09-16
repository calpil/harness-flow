"""Contratos FIXTURE: Git local real; no repos, datos ni cuentas del proyecto."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(os.environ.get("HARNESS_TEST_SCRIPTS", Path(__file__).resolve().parents[1] / "scripts"))


class MultiRepoCloseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.root = self.home / "project"
        (self.root / "harness" / "progress").mkdir(parents=True)
        (self.root / "docs").mkdir()
        self.env = {"PATH": os.environ["PATH"], "HOME": str(self.home),
                    "USERPROFILE": str(self.home), "CI": "1", "PYTHONDONTWRITEBYTECODE": "1",
                    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                    "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
                    "HARNESS_SKILLS_DIR": str(self.home / "skills")}
        lesson = self.home / "skills" / "closure-contract"
        lesson.mkdir(parents=True)
        (lesson / "SKILL.md").write_text("---\nname: closure-contract\ndescription: Fixture\n---\n")
        self.backlog = self.root / "harness" / "feature_list.json"
        self.spec = self.root / "docs" / "spec-feature-7-closure-fixture.md"
        self.spec.write_text('Estado: draft\n- AC-1: Given repos When closed Then integrated\n'
                             'Comando: `git -C alpha merge-base --is-ancestor HEAD HEAD`\n')
        (self.root / "docs" / "impl-7.md").write_text("## AC-1\nalpha/feature.txt:1\n")
        (self.root / "docs" / "review-7.md").write_text("## AC-1\nalpha/feature.txt:1\n")
        (self.root / "docs" / "constitution.md").write_text("User contract\n")
        (self.root / "harness" / "progress" / "current-7.md").write_text("Fixture progress\n")
        self.data = {"project": "fixture", "rules": {}, "features": [
            {"id": 7, "name": "Closure fixture", "status": "in_progress",
             "microservicios": ["alpha", "beta", "gamma"]}]}
        self.save()
        self.manifest = {"version": 1, "feature": "7", "repos": []}
        self.postmerge_path = self.home / "postmerge-map.json"
        measurement = {"version": 1, "feature": "7", "bases": {}}
        # Real Go, network disabled, cache isolated from the user's HOME.
        self.env.update(GOPROXY="off", GOSUMDB="off", GOTOOLCHAIN="local", GOWORK="off",
                        GOCACHE=os.environ.get("HARNESS_TEST_GOCACHE", str(self.home / "go-cache")))
        for name in self.data["features"][0]["microservicios"]:
            repo = self.root / name
            repo.mkdir()
            self.git(repo, "init", "-b", "develop")
            (repo / "base.txt").write_text("base\n")
            (repo / ".gitignore").write_text("build/\n")
            (repo / "go.mod").write_text(f"module fixture.invalid/{name}\n\ngo 1.22\n")
            (repo / "contract_test.go").write_text(
                'package contract\nimport ("os"; "testing")\n'
                'func TestBaseContract(t *testing.T) { b, e := os.ReadFile("base.txt"); '
                'if e != nil || string(b) != "base\\n" { t.Fatalf("base contract: %q %v", b, e) } }\n')
            self.git(repo, "add", ".")
            self.git(repo, "commit", "-m", "fixture: baseline")
            base = self.git(repo, "rev-parse", "HEAD")
            measurement["bases"][name] = str(self.home / f"base-{name}.json")
            self.ok("postmerge_medido.py", "base", "--repo", str(repo), "--cmd",
                    "go test -tags integration -count=1 -json ./...",
                    "--guardar", measurement["bases"][name])
            wt = self.home / "worktrees" / name
            self.git(repo, "worktree", "add", "--detach", str(wt))
            (wt / "feature.txt").write_text("fixture feature\n")
            self.git(wt, "add", "feature.txt")
            self.git(wt, "commit", "-m", "fixture: feature")
            source = self.git(wt, "rev-parse", "HEAD")
            self.git(repo, "merge", "--ff-only", source)
            # Caso ya integrado: no rama nueva; fuente puede ser ancestro del HEAD.
            if name == "gamma":
                (repo / "later.txt").write_text("later\n")
                self.git(repo, "add", "later.txt")
                self.git(repo, "commit", "-m", "fixture: later")
                wt = repo
            self.manifest["repos"].append({"microservicio": name, "repo": str(repo),
                "worktree": str(wt), "base_sha": base, "source_sha": source,
                "target_branch": "develop", "target_sha": self.git(repo, "rev-parse", "HEAD")})
        self.postmerge_path.write_text(json.dumps(measurement))
        self.manifest_path = self.home / "manifest.json"
        self.write_manifest()
        self.ok("gate.py", "approve-spec", "--feature", "7", "--yes", "--por", "Fixture")

    def save(self):
        self.backlog.write_text(json.dumps(self.data, indent=2) + "\n")

    def load(self):
        self.data = json.loads(self.backlog.read_text())
        return self.data["features"][0]

    def write_manifest(self):
        self.manifest_path.write_text(json.dumps(self.manifest))

    def git(self, path, *args):
        r = subprocess.run(["git", "-C", str(path), *args], env=self.env,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout.strip()

    def cli(self, script, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=self.root,
                              env=self.env, capture_output=True, text=True)

    def ok(self, script, *args):
        r = self.cli(script, *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def register(self):
        return self.ok("worktree.py", "register", "--feature", "7", "--manifest", str(self.manifest_path))

    def seal(self):
        self.ok("gate.py", "verify", "--feature", "7")
        self.ok("gate.py", "revision", "--feature", "7", "--veredicto", "approved", "--por", "Fixture reviewer")

    def close(self):
        return self.cli("gate.py", "close", "--feature", "7", "--status", "done", "--to", "develop",
                        "--integrated", "--leccion", "closure-contract", "--postmerge", str(self.postmerge_path))

    def assert_close_rejected(self, reason):
        before = {str(p): p.read_bytes() for base in (self.root / "docs", self.root / "harness")
                  for p in base.rglob("*") if p.is_file()}
        r = self.close()
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(reason, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        after = {str(p): p.read_bytes() for base in (self.root / "docs", self.root / "harness")
                 for p in base.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_close_revalidates_every_repo_and_current_target_tip(self):
        self.register()
        self.seal()
        self.load()["multi_repo"]["repos"].pop()
        self.save()
        self.assert_close_rejected("multi-repo")
        self.load()["multi_repo"] = copy.deepcopy(self.manifest)
        self.save()
        repo = self.root / "beta"
        (repo / "other.txt").write_text("tip moved\n")
        self.git(repo, "add", "other.txt")
        self.git(repo, "commit", "-m", "fixture: new tip")
        self.assert_close_rejected("tip destino")

    def test_close_rejects_source_not_integrated(self):
        row = self.manifest["repos"][0]
        wt = Path(row["worktree"])
        (wt / "pending.txt").write_text("not integrated\n")
        self.git(wt, "add", "pending.txt")
        self.git(wt, "commit", "-m", "fixture: pending")
        row["source_sha"] = self.git(wt, "rev-parse", "HEAD")
        self.write_manifest()
        self.register()
        self.seal()
        self.assert_close_rejected("fuente no integrada")

    def test_dirty_trees_are_not_hidden_by_receipt_or_git_index_flags(self):
        self.register()
        self.seal()
        for root in (Path(self.manifest["repos"][0]["repo"]), Path(self.manifest["repos"][0]["worktree"])):
            for name in ("base.txt", "untracked.txt"):
                path = root / name
                old = path.read_bytes() if path.exists() else None
                path.write_text("dirty\n")
                try:
                    self.assert_close_rejected("sucio")
                finally:
                    if old is None:
                        path.unlink()
                    else:
                        path.write_bytes(old)
            self.git(root, "update-index", "--assume-unchanged", "base.txt")
            try:
                self.assert_close_rejected("indice oculta")
            finally:
                self.git(root, "update-index", "--no-assume-unchanged", "base.txt")
        self.ok("gate.py", "check")

    def test_registration_rejects_dirty_and_committed_protected_edits(self):
        wt = Path(self.manifest["repos"][0]["worktree"])
        dirty = wt / "unknown.txt"
        dirty.write_text("untracked\n")
        r = self.cli("worktree.py", "register", "--feature", "7", "--manifest", str(self.manifest_path))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("sucio", r.stdout + r.stderr)
        dirty.unlink()
        (wt / "docs").mkdir()
        (wt / "docs" / "constitution.md").write_text("forbidden edit\n")
        self.git(wt, "add", "docs/constitution.md")
        self.git(wt, "commit", "-m", "fixture: protected mutant")
        self.manifest["repos"][0]["source_sha"] = self.git(wt, "rev-parse", "HEAD")
        self.write_manifest()
        r = self.cli("worktree.py", "register", "--feature", "7", "--manifest", str(self.manifest_path))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("protegidas", r.stdout + r.stderr)
        self.assertNotIn("multi_repo", self.load())

    def test_close_rejects_protected_root_edits(self):
        self.register()
        self.seal()
        (self.root / "docs" / "constitution.md").write_text("forbidden mutation\n")
        self.assert_close_rejected("protegidas")

    def test_ignored_build_artifacts_are_not_untracked_work(self):
        for row in self.manifest["repos"]:
            for key in ("repo", "worktree"):
                build = Path(row[key]) / "build"
                build.mkdir(exist_ok=True)
                (build / "output.txt").write_text("ignored fixture artifact\n")
        self.register()
        self.seal()
        r = self.close()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_receipt_never_turns_missing_red_or_stale_process_gates_green(self):
        self.register()
        self.seal()
        self.load()
        original = copy.deepcopy(self.data)
        changes = [
            ("verify ausente", lambda f: f.pop("last_verify")),
            ("verify vacio", lambda f: f.update(last_verify={"at": "fixture", "total": 0, "fallos": 0})),
            ("verify rojo", lambda f: f["last_verify"].update(fallos=1)),
            ("verify desconocido", lambda f: f["last_verify"].pop("fallos")),
            ("review stale", lambda f: f.pop("last_review_sig")),
            ("spec stale", lambda f: f.pop("last_spec_sig")),
        ]
        for name, change in changes:
            with self.subTest(case=name):
                self.data = copy.deepcopy(original)
                change(self.data["features"][0])
                self.save()
                self.assert_close_rejected(name.split()[0])
        self.data = original
        self.save()
        for filename, reason in (("review-7.md", "review"), ("impl-7.md", "evidencia"), ("verify-7.md", "verify")):
            path = self.root / "docs" / filename
            old = path.read_bytes()
            path.write_text("No AC and no valid seal\n")
            try:
                self.assert_close_rejected(reason)
            finally:
                path.write_bytes(old)
        self.ok("gate.py", "revision", "--feature", "7", "--veredicto", "changes_requested")
        self.assert_close_rejected("review")

    def test_reregistering_new_tip_does_not_reuse_old_review_or_verify(self):
        self.register()
        self.seal()
        repo = self.root / "alpha"
        (repo / "other.txt").write_text("later\n")
        self.git(repo, "add", "other.txt")
        self.git(repo, "commit", "-m", "fixture: new validated candidate")
        self.manifest["repos"][0]["target_sha"] = self.git(repo, "rev-parse", "HEAD")
        self.write_manifest()
        self.register()
        self.assert_close_rejected("review")
        self.ok("gate.py", "revision", "--feature", "7", "--veredicto", "approved")
        self.assert_close_rejected("verify")
        self.ok("gate.py", "verify", "--feature", "7")
        self.assertEqual(self.close().returncode, 0)

    def test_receipt_does_not_authorize_missing_lesson_or_rule_bypass(self):
        self.register()
        self.seal()
        (self.home / "absent").mkdir()
        self.env["HARNESS_SKILLS_DIR"] = str(self.home / "absent")
        self.assert_close_rejected("leccion")
        self.load().pop("last_verify")
        self.data["rules"]["require_verify_green"] = False
        self.save()
        self.env["HARNESS_SKILLS_DIR"] = str(self.home / "skills")
        self.assert_close_rejected("verify")

    def test_isolation_requires_complete_real_worktree_map_and_keeps_other_blockers(self):
        self.register()
        self.seal()
        f = self.load()
        other = copy.deepcopy(f)
        other.update(id=8, status="blocked", worktree="/not/a/worktree")
        other.pop("multi_repo")
        self.data["features"].append(other)
        self.save()
        self.assert_close_rejected("aislamiento")
        self.assertEqual(self.load()["status"], "in_progress")
        self.assertEqual(self.data["features"][1]["status"], "blocked")

    def test_complete_detached_map_is_isolation_and_shared_map_is_not(self):
        self.manifest["repos"][2]["worktree"] = str(self.home / "worktrees" / "gamma")
        self.write_manifest()
        self.register()
        self.seal()
        other = copy.deepcopy(self.load())
        other.update(id=8, status="in_progress")
        other.pop("multi_repo")
        self.data["features"].append(other)
        self.save()
        (self.root / "docs" / "spec-feature-8-closure-fixture.md").write_bytes(self.spec.read_bytes())
        self.ok("gate.py", "check")
        self.load()
        self.data["features"][1]["multi_repo"] = dict(copy.deepcopy(self.manifest), feature="8")
        self.save()
        r = self.cli("gate.py", "check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("compartido", r.stdout + r.stderr)

    def test_ignored_protected_files_in_repos_are_not_build_artifacts(self):
        row = self.manifest["repos"][0]
        exclude = Path(self.git(row["repo"], "rev-parse", "--path-format=absolute", "--git-path", "info/exclude"))
        exclude.write_text(".env\n")
        for key in ("repo", "worktree"):
            (Path(row[key]) / ".env").write_text("fixture-not-a-secret\n")
        self.register()
        self.seal()
        (Path(row["worktree"]) / ".env").write_text("protected mutant, not build output\n")
        self.assert_close_rejected("protegidas")

    def test_review_briefing_identifies_every_repo_and_pinned_revision(self):
        self.register()
        before = self.backlog.read_bytes()
        r = self.ok("revision.py", "--feature", "7", "--briefing")
        for row in self.manifest["repos"]:
            for key in ("repo", "worktree", "base_sha", "source_sha", "target_sha"):
                self.assertIn(row[key], r.stdout)
        self.assertIn("feature.txt", r.stdout)
        self.assertEqual(self.backlog.read_bytes(), before)

    def test_rejected_revision_does_not_modify_review_or_backlog(self):
        self.register()
        before = (self.root / "docs" / "review-7.md").read_bytes(), self.backlog.read_bytes()
        (self.root / "beta" / "unexpected.txt").write_text("dirty\n")
        r = self.cli("gate.py", "revision", "--feature", "7", "--veredicto", "approved")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("sucio", r.stdout + r.stderr)
        self.assertEqual(before, ((self.root / "docs" / "review-7.md").read_bytes(), self.backlog.read_bytes()))

    def test_receipt_cannot_redirect_generated_docs_outside_root(self):
        self.register()
        self.seal()
        outside = self.home / "foreign.md"
        outside.write_text("foreign user document\n")
        (self.root / "docs" / "sdd.md").symlink_to(outside)
        self.assert_close_rejected("fuera")
        self.assertEqual(outside.read_text(), "foreign user document\n")

    def test_drop_cannot_remove_registered_existing_worktrees_via_legacy_field(self):
        self.register()
        self.load()["worktree"] = self.manifest["repos"][0]["worktree"]
        self.save()
        before = self.backlog.read_bytes()
        r = self.cli("worktree.py", "drop", "--feature", "7")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("multi-repo", r.stdout + r.stderr)
        self.assertEqual(self.backlog.read_bytes(), before)
        self.assertTrue(Path(self.manifest["repos"][0]["worktree"]).is_dir())

    def test_legacy_monorepo_still_performs_real_merge(self):
        self.git(self.root, "init", "-b", "develop")
        (self.root / ".gitignore").write_text("/alpha/\n/beta/\n/gamma/\n")
        self.git(self.root, "add", ".gitignore", "docs", "harness")
        self.git(self.root, "commit", "-m", "fixture: mono base")
        self.git(self.root, "checkout", "-b", "feature/fixture")
        (self.root / "mono.txt").write_text("feature\n")
        self.git(self.root, "add", "mono.txt")
        self.git(self.root, "commit", "-m", "fixture: mono feature")
        source = self.git(self.root, "rev-parse", "HEAD")
        self.git(self.root, "checkout", "develop")
        self.load()["branch"] = "feature/fixture"
        self.save()
        self.seal()
        self.git(self.root, "add", "docs", "harness")
        self.git(self.root, "commit", "-m", "fixture: process evidence")
        self.ok("gate.py", "close", "--feature", "7", "--status", "done", "--to", "develop",
                "--leccion", "closure-contract")
        f = self.load()
        self.assertEqual(f["status"], "done")
        self.assertEqual(f["merge_commit"], self.git(self.root, "rev-parse", "--short", "HEAD"))
        self.assertEqual(len(self.git(self.root, "rev-list", "--parents", "-n", "1", "HEAD").split()), 3)
        self.git(self.root, "merge-base", "--is-ancestor", source, "develop")

    def test_generated_sdd_names_each_real_source_and_target_without_fake_merge(self):
        self.register()
        self.seal()
        r = self.close()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        sdd = (self.root / "docs" / "sdd.md").read_text()
        for row in self.manifest["repos"]:
            self.assertIn(row["source_sha"], sdd)
            self.assertIn(row["target_sha"], sdd)
        self.assertNotIn("Merge commit:", sdd)

    def test_registration_rejects_invalid_or_incomplete_declaration_without_writes(self):
        original = copy.deepcopy(self.manifest)
        alias = self.root / "alpha-alias"
        alias.symlink_to(self.root / "alpha", target_is_directory=True)
        variants = []
        def variant(label, edit):
            m = copy.deepcopy(original)
            edit(m)
            variants.append((label, m))
        variant("omitted repo", lambda m: m["repos"].pop())
        variant("empty repos", lambda m: m.update(repos=[]))
        variant("wrong feature", lambda m: m.update(feature="8"))
        variant("unknown field", lambda m: m.update(permitir_sucio=True))
        variant("duplicate", lambda m: m["repos"].append(m["repos"][0]))
        variant("symlink duplicate", lambda m: m["repos"][1].update(repo=str(alias)))
        variant("undeclared path", lambda m: m["repos"][0].update(repo=str(self.home)))
        variant("not worktree root", lambda m: m["repos"][0].update(worktree=str(Path(m["repos"][0]["worktree"]) / ".git")))
        variant("foreign worktree", lambda m: m["repos"][0].update(worktree=m["repos"][1]["worktree"]))
        variant("empty path", lambda m: m["repos"][0].update(repo=""))
        variant("option branch", lambda m: m["repos"][0].update(target_branch="--help"))
        variant("foreign branch", lambda m: m["repos"][0].update(target_branch="other"))
        variant("abbrev SHA", lambda m: m["repos"][0].update(source_sha=m["repos"][0]["source_sha"][:7]))
        variant("missing SHA", lambda m: m["repos"][0].update(source_sha="0" * 40))
        variant("wrong source HEAD", lambda m: m["repos"][0].update(source_sha=m["repos"][0]["base_sha"]))
        variant("no feature delta", lambda m: m["repos"][0].update(base_sha=m["repos"][0]["source_sha"]))
        variant("stale target", lambda m: m["repos"][0].update(target_sha=m["repos"][0]["base_sha"]))
        before = self.backlog.read_bytes()
        for label, manifest in variants:
            with self.subTest(case=label):
                self.manifest = manifest
                self.write_manifest()
                r = self.cli("worktree.py", "register", "--feature", "7", "--manifest", str(self.manifest_path))
                self.assertNotEqual(r.returncode, 0, label)
                self.assertIn("multi-repo", r.stdout + r.stderr)
                self.assertNotIn("Traceback", r.stderr)
                self.assertEqual(self.backlog.read_bytes(), before)

    def test_root_without_git_closes_actual_integrated_repos_without_merging(self):
        self.register()
        self.seal()
        heads = [(self.git(x["repo"], "rev-parse", "HEAD"), self.git(x["worktree"], "rev-parse", "HEAD"))
                 for x in self.manifest["repos"]]
        r = self.close()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        f = self.load()
        self.assertEqual(f["status"], "done")
        self.assertNotIn("merge_commit", f)
        self.assertEqual(f["integraciones"], self.manifest["repos"])
        self.assertFalse((self.root / ".git").exists())
        self.assertEqual(heads, [(self.git(x["repo"], "rev-parse", "HEAD"), self.git(x["worktree"], "rev-parse", "HEAD"))
                                for x in self.manifest["repos"]])
        self.assertTrue((self.root / f["progress_archive"]).exists())


if __name__ == "__main__":
    unittest.main()
