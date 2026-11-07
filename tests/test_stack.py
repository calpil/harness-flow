import json
import shutil
import tempfile
import unittest
from pathlib import Path

import stack


class TestStackManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.calpil_root = Path("/Users/alan/Documents/Git/CALPIL")
        self.go_template = self.calpil_root / "calpil-golang-hexagonal-template"
        self.ng_template = self.calpil_root / "calpil-angular-product-template"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_listar_stacks_disponibles(self):
        stacks = stack.listar_stacks_disponibles()
        ids = [s["id"] for s in stacks]
        self.assertIn("golang-hexagonal", ids)
        self.assertIn("angular-product", ids)

    def test_detectar_golang_hexagonal(self):
        if self.go_template.exists():
            res = stack.detectar_stack_directorio(self.go_template)
            self.assertEqual(res["stack"], "golang-hexagonal")
            self.assertGreaterEqual(res["confidence"], 80)
            self.assertIn("go.mod", res["indicators"])

    def test_detectar_angular_product(self):
        if self.ng_template.exists():
            res = stack.detectar_stack_directorio(self.ng_template)
            self.assertEqual(res["stack"], "angular-product")
            self.assertGreaterEqual(res["confidence"], 80)
            self.assertIn("angular.json", res["indicators"])

    def test_detectar_nextjs_product(self):
        next_template = self.calpil_root / "calpil-nextjs-product-template"
        if next_template.exists():
            res = stack.detectar_stack_directorio(next_template)
            self.assertEqual(res["stack"], "nextjs-product")
            self.assertGreaterEqual(res["confidence"], 80)

    def test_detectar_springboot_hexagonal(self):
        sb_template = self.calpil_root / "calpil-springboot-hexagonal-template"
        if sb_template.exists():
            res = stack.detectar_stack_directorio(sb_template)
            self.assertEqual(res["stack"], "springboot-hexagonal")
            self.assertGreaterEqual(res["confidence"], 80)

    def test_detectar_nestjs_hexagonal(self):
        nest_template = self.calpil_root / "calpil-nestjs-hexagonal-template"
        if nest_template.exists():
            res = stack.detectar_stack_directorio(nest_template)
            self.assertEqual(res["stack"], "nestjs-hexagonal")
            self.assertGreaterEqual(res["confidence"], 80)

    def test_detectar_python_dataproduct(self):
        py_template = self.calpil_root / "calpil-python-dataproduct-template"
        if py_template.exists():
            res = stack.detectar_stack_directorio(py_template)
            self.assertEqual(res["stack"], "python-dataproduct")
            self.assertGreaterEqual(res["confidence"], 80)

    def test_detectar_custom_future_stack(self):
        # Simular la adición de un nuevo stack a futuro (ej. Rust Axum)
        custom_stack_dir = stack.STACKS_DIR / "custom-rust-stack"
        custom_stack_dir.mkdir(parents=True, exist_ok=True)
        try:
            custom_manifest = {
                "id": "custom-rust-stack",
                "name": "Custom Rust Stack",
                "detection": {
                    "files_any": ["Cargo.toml"],
                    "extensions": [".rs"],
                    "content_matches": {
                        "Cargo.toml": ["axum", "tokio"]
                    },
                    "strong_indicators": ["src/main.rs"]
                }
            }
            (custom_stack_dir / "manifest.json").write_text(json.dumps(custom_manifest), encoding="utf-8")

            # Crear repo fixture de Rust
            rust_repo = self.tmpdir / "my-rust-app"
            rust_repo.mkdir()
            (rust_repo / "Cargo.toml").write_text('[package]\nname = "app"\n[dependencies]\naxum = "0.7"\ntokio = "1"\n', encoding="utf-8")
            (rust_repo / "src").mkdir()
            (rust_repo / "src" / "main.rs").write_text('fn main() { println!("hi"); }\n', encoding="utf-8")

            res = stack.detectar_stack_directorio(rust_repo)
            self.assertEqual(res["stack"], "custom-rust-stack")
            self.assertGreaterEqual(res["confidence"], 80)
        finally:
            shutil.rmtree(custom_stack_dir, ignore_errors=True)

    def test_verificar_cumplimiento_templates_calpil(self):
        if self.go_template.exists():
            diag_go = stack.verificar_cumplimiento(self.go_template)
            self.assertTrue(diag_go["compliant"])
            self.assertTrue(diag_go["architecture_ok"])
            self.assertTrue(diag_go["rules_ok"])

        if self.ng_template.exists():
            diag_ng = stack.verificar_cumplimiento(self.ng_template)
            self.assertTrue(diag_ng["compliant"])
            self.assertTrue(diag_ng["architecture_ok"])
            self.assertTrue(diag_ng["rules_ok"])

    def test_verificar_non_compliant_repo(self):
        mock_repo = self.tmpdir / "legacy-repo"
        mock_repo.mkdir()
        (mock_repo / "go.mod").write_text("module example.com/legacy\n", encoding="utf-8")

        diag = stack.verificar_cumplimiento(mock_repo)
        self.assertFalse(diag["compliant"])
        self.assertFalse(diag["rules_ok"])
        self.assertFalse(diag["skills_ok"])
        self.assertGreater(len(diag["findings"]), 0)

    def test_normalizar_repositorio(self):
        mock_repo = self.tmpdir / "target-repo"
        mock_repo.mkdir()
        (mock_repo / "go.mod").write_text("module example.com/target\n", encoding="utf-8")

        res = stack.normalizar_repositorio(mock_repo)
        self.assertEqual(res["status"], "normalized")
        self.assertTrue((mock_repo / ".claude" / "rules" / "architecture.md").exists())
        self.assertTrue((mock_repo / ".claude" / "skills" / "add-feature" / "SKILL.md").exists())
        self.assertTrue((mock_repo / ".agents" / "skills" / "add-feature" / "SKILL.md").exists())
        self.assertTrue((mock_repo / "AGENTS.md").exists())
        self.assertTrue((mock_repo / "scripts" / "check-architecture.py").exists())

    def test_refactorizar_plan(self):
        mock_repo = self.tmpdir / "unstructured-repo"
        mock_repo.mkdir()
        (mock_repo / "go.mod").write_text("module example.com/target\n", encoding="utf-8")

        plan = stack.generar_plan_refactor(mock_repo)
        self.assertTrue(plan["needed"])
        self.assertGreaterEqual(len(plan["steps"]), 1)

    def test_auditar_seguridad_y_versiones(self):
        if self.go_template.exists():
            res = stack.auditar_seguridad_y_versiones(self.go_template)
            self.assertEqual(res["stack"], "golang-hexagonal")
            self.assertEqual(res["context7_library"], "/golang/go")
            self.assertEqual(res["official_docs"], "https://go.dev/doc/")
            self.assertEqual(res["minimum_version"], "1.23.0")
            self.assertIn("govulncheck", res["audit_command"])


if __name__ == "__main__":
    unittest.main()
