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
        self.dotnet_template = self.calpil_root / "calpil-dotnet-hexagonal-template"
        self.rust_template = self.calpil_root / "calpil-rust-hexagonal-template"
        self.next_template = self.calpil_root / "calpil-nextjs-product-template"
        self.sb_template = self.calpil_root / "calpil-springboot-hexagonal-template"
        self.nest_template = self.calpil_root / "calpil-nestjs-hexagonal-template"
        self.py_template = self.calpil_root / "calpil-python-dataproduct-template"
        self.ios_template = self.calpil_root / "calpil-ios-swiftui-template"
        self.android_template = self.calpil_root / "calpil-android-compose-template"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_listar_stacks_disponibles(self):
        stacks = stack.listar_stacks_disponibles()
        ids = [s["id"] for s in stacks]
        self.assertIn("golang-hexagonal", ids)
        self.assertIn("angular-product", ids)
        self.assertIn("dotnet-hexagonal", ids)
        self.assertIn("rust-hexagonal", ids)
        self.assertIn("nextjs-product", ids)
        self.assertIn("springboot-hexagonal", ids)
        self.assertIn("nestjs-hexagonal", ids)
        self.assertIn("python-dataproduct", ids)
        self.assertIn("ios-swiftui-clean", ids)
        self.assertIn("android-compose-clean", ids)

    def test_detectar_ios_swiftui_clean(self):
        if self.ios_template.exists():
            res = stack.detectar_stack_directorio(self.ios_template)
            self.assertEqual(res["stack"], "ios-swiftui-clean")
            self.assertGreaterEqual(res["confidence"], 80)
            self.assertIn("Package.swift", res["indicators"])

    def test_detectar_android_compose_clean(self):
        if self.android_template.exists():
            res = stack.detectar_stack_directorio(self.android_template)
            self.assertEqual(res["stack"], "android-compose-clean")
            self.assertGreaterEqual(res["confidence"], 80)
            self.assertTrue(any("gradle" in ind for ind in res["indicators"]))

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

    def test_detectar_dotnet_hexagonal(self):
        if self.dotnet_template.exists():
            res = stack.detectar_stack_directorio(self.dotnet_template)
            self.assertEqual(res["stack"], "dotnet-hexagonal")
            self.assertGreaterEqual(res["confidence"], 80)
            self.assertTrue(any(".sln" in ind or ".cs" in ind for ind in res["indicators"]))

    def test_detectar_rust_hexagonal(self):
        if self.rust_template.exists():
            res = stack.detectar_stack_directorio(self.rust_template)
            self.assertEqual(res["stack"], "rust-hexagonal")
            self.assertGreaterEqual(res["confidence"], 80)
            self.assertTrue(any("Cargo.toml" in ind or ".rs" in ind for ind in res["indicators"]))

    def test_detectar_custom_future_stack(self):
        # Simular la adición de un nuevo stack a futuro (ej. Elixir Phoenix)
        custom_stack_dir = stack.STACKS_DIR / "custom-elixir-stack"
        custom_stack_dir.mkdir(parents=True, exist_ok=True)
        try:
            custom_manifest = {
                "id": "custom-elixir-stack",
                "name": "Custom Elixir Stack",
                "detection": {
                    "files_any": ["mix.exs"],
                    "extensions": [".ex", ".exs"],
                    "content_matches": {
                        "mix.exs": ["phoenix", "ecto"]
                    },
                    "strong_indicators": ["lib"]
                }
            }
            (custom_stack_dir / "manifest.json").write_text(json.dumps(custom_manifest), encoding="utf-8")

            # Crear repo fixture de Elixir
            elixir_repo = self.tmpdir / "my-elixir-app"
            elixir_repo.mkdir()
            (elixir_repo / "mix.exs").write_text('defmodule App.MixProject do\n  use Mix.Project\n  def deps do\n    [{:phoenix, "~> 1.7"},\n     {:ecto, "~> 3.10"}]\n  end\nend\n', encoding="utf-8")
            (elixir_repo / "lib").mkdir()
            (elixir_repo / "lib" / "app.ex").write_text('defmodule App do\nend\n', encoding="utf-8")

            res = stack.detectar_stack_directorio(elixir_repo)
            self.assertEqual(res["stack"], "custom-elixir-stack")
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

        if self.dotnet_template.exists():
            diag_dotnet = stack.verificar_cumplimiento(self.dotnet_template)
            self.assertTrue(diag_dotnet["compliant"])
            self.assertTrue(diag_dotnet["architecture_ok"])
            self.assertTrue(diag_dotnet["rules_ok"])

        if self.rust_template.exists():
            diag_rust = stack.verificar_cumplimiento(self.rust_template)
            self.assertTrue(diag_rust["compliant"])
            self.assertTrue(diag_rust["architecture_ok"])
            self.assertTrue(diag_rust["rules_ok"])

        if self.next_template.exists():
            diag_next = stack.verificar_cumplimiento(self.next_template)
            self.assertTrue(diag_next["compliant"])
            self.assertTrue(diag_next["architecture_ok"])
            self.assertTrue(diag_next["rules_ok"])

        if self.sb_template.exists():
            diag_sb = stack.verificar_cumplimiento(self.sb_template)
            self.assertTrue(diag_sb["compliant"])
            self.assertTrue(diag_sb["architecture_ok"])
            self.assertTrue(diag_sb["rules_ok"])

        if self.nest_template.exists():
            diag_nest = stack.verificar_cumplimiento(self.nest_template)
            self.assertTrue(diag_nest["compliant"])
            self.assertTrue(diag_nest["architecture_ok"])
            self.assertTrue(diag_nest["rules_ok"])

        if self.py_template.exists():
            diag_py = stack.verificar_cumplimiento(self.py_template)
            self.assertTrue(diag_py["compliant"])
            self.assertTrue(diag_py["architecture_ok"])
            self.assertTrue(diag_py["rules_ok"])

        if self.ios_template.exists():
            diag_ios = stack.verificar_cumplimiento(self.ios_template)
            self.assertTrue(diag_ios["compliant"])
            self.assertTrue(diag_ios["architecture_ok"])
            self.assertTrue(diag_ios["rules_ok"])

        if self.android_template.exists():
            diag_android = stack.verificar_cumplimiento(self.android_template)
            self.assertTrue(diag_android["compliant"])
            self.assertTrue(diag_android["architecture_ok"])
            self.assertTrue(diag_android["rules_ok"])

    def test_check_architecture_ios_violations(self):
        # Probar que el checker detecta violaciones en iOS SwiftUI
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_ios",
            str(stack.STACKS_DIR / "ios-swiftui-clean" / "scripts" / "check-architecture.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        bad_repo = self.tmpdir / "bad-ios"
        bad_repo.mkdir()
        (bad_repo / "Sources" / "CalpilDomain").mkdir(parents=True)
        (bad_repo / "Sources" / "CalpilDomain" / "Entity.swift").write_text(
            'import SwiftUI\nimport CalpilData\npublic struct Entity {}',
            encoding="utf-8"
        )
        (bad_repo / "Sources" / "CalpilUI").mkdir(parents=True)
        (bad_repo / "Sources" / "CalpilUI" / "View.swift").write_text(
            'import CalpilData\npublic struct SomeView {}',
            encoding="utf-8"
        )
        (bad_repo / "Tests" / "CalpilTests").mkdir(parents=True)
        (bad_repo / "Tests" / "CalpilTests" / "AppTests.swift").write_text(
            'import Foundation\nfunc testSleep() { Thread.sleep(forTimeInterval: 1) }',
            encoding="utf-8"
        )

        errors, warnings = mod.check_ios_architecture(bad_repo)
        self.assertGreaterEqual(len(errors), 3)
        self.assertTrue(any("Composition Root ausente" in e for e in errors))
        self.assertTrue(any("SwiftUI" in e for e in errors))
        self.assertTrue(any("UI no debe importar la capa de datos directamente" in e for e in errors))
        self.assertTrue(any("sleep prohibido" in e for e in errors))

    def test_check_architecture_android_violations(self):
        # Probar que el checker detecta violaciones en Android Compose
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_android",
            str(stack.STACKS_DIR / "android-compose-clean" / "scripts" / "check-architecture.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        bad_repo = self.tmpdir / "bad-android"
        bad_repo.mkdir()
        (bad_repo / "features" / "sample" / "domain").mkdir(parents=True)
        (bad_repo / "features" / "sample" / "domain" / "Entity.kt").write_text(
            'package com.calpil.sample.domain\nimport androidx.compose.runtime.Composable\nimport com.calpil.sample.data.dto.SomeDto\nclass Entity',
            encoding="utf-8"
        )
        (bad_repo / "features" / "sample" / "presentation").mkdir(parents=True)
        (bad_repo / "features" / "sample" / "presentation" / "Screen.kt").write_text(
            'package com.calpil.sample.presentation\nimport com.calpil.sample.data.dto.SomeDto\nclass Screen',
            encoding="utf-8"
        )
        (bad_repo / "features" / "sample" / "src" / "test").mkdir(parents=True)
        (bad_repo / "features" / "sample" / "src" / "test" / "SampleTest.kt").write_text(
            'package com.calpil.sample\nclass SampleTest { fun test() { Thread.sleep(100) } }',
            encoding="utf-8"
        )

        errors, warnings = mod.check_android_architecture(bad_repo)
        self.assertGreaterEqual(len(errors), 3)
        self.assertTrue(any("Composition Root ausente" in e for e in errors))
        self.assertTrue(any("androidx.compose." in e for e in errors))
        self.assertTrue(any("Presentation no debe importar detalles de data directamente" in e for e in errors))
        self.assertTrue(any("sleep prohibido" in e for e in errors))

    def test_check_architecture_dotnet_violations(self):
        # Probar que el checker detecta violaciones en .NET
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_dotnet",
            str(stack.STACKS_DIR / "dotnet-hexagonal" / "scripts" / "check-architecture.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        bad_repo = self.tmpdir / "bad-dotnet"
        bad_repo.mkdir()
        (bad_repo / "src" / "Bad.Domain").mkdir(parents=True)
        (bad_repo / "src" / "Bad.Domain" / "Bad.Domain.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk">\n<ItemGroup><PackageReference Include="Dapper" Version="2.0" /></ItemGroup>\n</Project>',
            encoding="utf-8"
        )
        (bad_repo / "src" / "Bad.Domain" / "Entity.cs").write_text(
            'using Microsoft.AspNetCore.Mvc;\npublic class Entity {}',
            encoding="utf-8"
        )
        (bad_repo / "tests").mkdir()
        (bad_repo / "tests" / "EntityTest.cs").write_text(
            'using System.Threading;\npublic class EntityTest { void Test() { Thread.Sleep(100); } }',
            encoding="utf-8"
        )

        errors, warnings = mod.check_dotnet_architecture(bad_repo)
        self.assertGreaterEqual(len(errors), 2)
        self.assertTrue(any("Composition Root ausente" in e for e in errors))
        self.assertTrue(any("Domain no debe incluir el paquete externo 'dapper'" in e for e in errors))
        self.assertTrue(any("Thread.Sleep" in e for e in errors))

    def test_check_architecture_rust_violations(self):
        # Probar que el checker detecta violaciones en Rust
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_rust",
            str(stack.STACKS_DIR / "rust-hexagonal" / "scripts" / "check-architecture.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        bad_repo = self.tmpdir / "bad-rust"
        bad_repo.mkdir()
        (bad_repo / "crates" / "domain" / "src").mkdir(parents=True)
        (bad_repo / "crates" / "domain" / "Cargo.toml").write_text(
            '[package]\nname = "domain"\nversion = "0.1.0"\nedition = "2021"\n[dependencies]\naxum = "0.8"\n',
            encoding="utf-8"
        )
        (bad_repo / "crates" / "domain" / "src" / "lib.rs").write_text(
            'use axum::extract::State;\npub struct Entity;\n',
            encoding="utf-8"
        )
        (bad_repo / "tests").mkdir()
        (bad_repo / "tests" / "bad_test.rs").write_text(
            '#[test]\nfn test_sleep() {\n    std::thread::sleep(std::time::Duration::from_millis(100));\n}\n',
            encoding="utf-8"
        )

        errors, warnings = mod.check_rust_architecture(bad_repo)
        self.assertGreaterEqual(len(errors), 2)
        self.assertTrue(any("Composition Root ausente" in e for e in errors))
        self.assertTrue(any("Domain no debe incluir la dependencia externa 'axum'" in e for e in errors))
        self.assertTrue(any("sleep prohibido" in e for e in errors))

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
        self.assertTrue((mock_repo / ".agents" / "rules" / "architecture.md").exists())
        self.assertTrue((mock_repo / ".gemini" / "rules" / "architecture.md").exists())
        self.assertTrue((mock_repo / ".claude" / "skills" / "add-feature" / "SKILL.md").exists())
        self.assertTrue((mock_repo / ".agents" / "skills" / "add-feature" / "SKILL.md").exists())
        self.assertTrue((mock_repo / "AGENTS.md").exists())
        self.assertTrue((mock_repo / "scripts" / "check-architecture.py").exists())

        diag = stack.verificar_cumplimiento(mock_repo)
        self.assertTrue(diag["full_multi_llm_parity"])
        self.assertIn("claude-code", diag["hosts_active"])
        self.assertIn("openai-codex/hermes/grok/kimi", diag["hosts_active"])
        self.assertIn("gemini-cli/agy", diag["hosts_active"])

    def test_verificar_multi_llm_rules_ok(self):
        # Repositorio que solo tiene .agents/rules/ (ej. configurado para OpenAI Codex / Gemini sin .claude/)
        mock_repo = self.tmpdir / "agents-repo"
        mock_repo.mkdir()
        (mock_repo / "go.mod").write_text("module example.com/agents\n", encoding="utf-8")
        agents_rules = mock_repo / ".agents" / "rules"
        agents_rules.mkdir(parents=True, exist_ok=True)
        manifest = stack.cargar_manifest("golang-hexagonal")
        for r in manifest["normative"]["rules"]:
            (agents_rules / r).write_text("# regla\n", encoding="utf-8")

        diag = stack.verificar_cumplimiento(mock_repo, "golang-hexagonal")
        self.assertTrue(diag["rules_ok"])
        self.assertEqual(diag["missing_rules"], [])

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

        if self.dotnet_template.exists():
            res_dn = stack.auditar_seguridad_y_versiones(self.dotnet_template)
            self.assertEqual(res_dn["stack"], "dotnet-hexagonal")
            self.assertEqual(res_dn["context7_library"], "/dotnet/runtime")
            self.assertEqual(res_dn["minimum_version"], "8.0.0")
            self.assertIn("dotnet list package", res_dn["audit_command"])

        if self.rust_template.exists():
            res_rust = stack.auditar_seguridad_y_versiones(self.rust_template)
            self.assertEqual(res_rust["stack"], "rust-hexagonal")
            self.assertEqual(res_rust["context7_library"], "/tokio-rs/axum")
            self.assertEqual(res_rust["minimum_version"], "2021")
            self.assertIn("cargo audit", res_rust["audit_command"])

        if self.ios_template.exists():
            res_ios = stack.auditar_seguridad_y_versiones(self.ios_template)
            self.assertEqual(res_ios["stack"], "ios-swiftui-clean")
            self.assertEqual(res_ios["context7_library"], "/apple/swift")
            self.assertEqual(res_ios["minimum_version"], "6.0")
            self.assertIn("swift package audit", res_ios["audit_command"])

        if self.android_template.exists():
            res_and = stack.auditar_seguridad_y_versiones(self.android_template)
            self.assertEqual(res_and["stack"], "android-compose-clean")
            self.assertEqual(res_and["context7_library"], "/google/android")
            self.assertEqual(res_and["minimum_version"], "2.0.0")
            self.assertIn("./gradlew dependencyCheckAnalyze", res_and["audit_command"])

    def test_refactorizar_plan_y_scaffolding_ios(self):
        ios_repo = self.tmpdir / "unstructured-ios"
        ios_repo.mkdir()
        (ios_repo / "Package.swift").write_text('// swift-tools-version: 6.0\nimport PackageDescription\n', encoding="utf-8")

        plan = stack.generar_plan_refactor(ios_repo)
        self.assertTrue(plan["needed"])
        self.assertGreaterEqual(len(plan["steps"]), 1)
        self.assertTrue(any("Composition Root" in s["title"] for s in plan["steps"]))

        creados = stack.ejecutar_scaffolding(ios_repo)
        self.assertIn("Sources/CalpilApp/CalpilApp.swift", creados)
        self.assertTrue((ios_repo / "Sources" / "CalpilApp" / "CalpilApp.swift").exists())
        self.assertTrue((ios_repo / "Sources" / "CalpilDomain").exists())
        self.assertTrue((ios_repo / "Sources" / "CalpilData").exists())
        self.assertTrue((ios_repo / "Sources" / "CalpilUI").exists())
        self.assertTrue((ios_repo / "Tests" / "CalpilDomainTests").exists())

    def test_refactorizar_plan_y_scaffolding_android(self):
        and_repo = self.tmpdir / "unstructured-android"
        and_repo.mkdir()
        (and_repo / "settings.gradle.kts").write_text('rootProject.name = "MyAndroidApp"\n', encoding="utf-8")

        plan = stack.generar_plan_refactor(and_repo)
        self.assertTrue(plan["needed"])
        self.assertGreaterEqual(len(plan["steps"]), 1)
        self.assertTrue(any("Composition Root" in s["title"] for s in plan["steps"]))

        creados = stack.ejecutar_scaffolding(and_repo)
        self.assertIn("app/src/main/java/com/calpil/template/CalpilApplication.kt", creados)
        self.assertTrue((and_repo / "app" / "src" / "main" / "java" / "com" / "calpil" / "template" / "CalpilApplication.kt").exists())
        self.assertTrue((and_repo / "app" / "src" / "main" / "java" / "com" / "calpil" / "template" / "core").exists())
        self.assertTrue((and_repo / "app" / "src" / "main" / "java" / "com" / "calpil" / "template" / "features" / "workitems" / "domain").exists())
        self.assertTrue((and_repo / "app" / "src" / "main" / "java" / "com" / "calpil" / "template" / "features" / "workitems" / "data").exists())
        self.assertTrue((and_repo / "app" / "src" / "main" / "java" / "com" / "calpil" / "template" / "features" / "workitems" / "presentation").exists())

    def test_auditar_dast_zap(self):
        if self.go_template.exists():
            api_file = self.go_template / "openapi.json"
            created_mock = False
            if not api_file.exists():
                api_file.write_text('{"openapi": "3.0.0", "info": {"title": "Test API", "version": "1.0"}}', encoding="utf-8")
                created_mock = True
            try:
                res = stack.auditar_seguridad_y_versiones(self.go_template, dast=True)
                self.assertIsNotNone(res.get("dast"))
                dast_info = res["dast"]
                self.assertTrue(dast_info["enabled"])
                self.assertEqual(dast_info["mode"], "openapi")
                self.assertIn("zap", dast_info["tool"].lower())
                self.assertIn(dast_info["status"], ["passed", "warnings", "skipped"])
            finally:
                if created_mock and api_file.exists():
                    api_file.unlink()

    def test_refactorizar_plan_y_scaffolding_rust(self):
        rust_repo = self.tmpdir / "unstructured-rust"
        rust_repo.mkdir()
        (rust_repo / "Cargo.toml").write_text('[package]\nname = "my_rust"\nversion = "0.1.0"\nedition = "2021"\n[dependencies]\naxum = "0.8"\n', encoding="utf-8")

        plan = stack.generar_plan_refactor(rust_repo)
        self.assertTrue(plan["needed"])
        self.assertGreaterEqual(len(plan["steps"]), 1)
        self.assertTrue(any("Composition Root" in s["title"] for s in plan["steps"]))

        creados = stack.ejecutar_scaffolding(rust_repo)
        self.assertIn("src/main.rs", creados)
        self.assertTrue((rust_repo / "src" / "main.rs").exists())
        self.assertTrue((rust_repo / "src" / "domain").exists())
        self.assertTrue((rust_repo / "src" / "application").exists())
        self.assertTrue((rust_repo / "src" / "infrastructure").exists())

    def test_auto_normalizar_nivel_1(self):
        mock_repo = self.tmpdir / "auto-norm-repo"
        mock_repo.mkdir()
        (mock_repo / "go.mod").write_text("module example.com/autonorm\n", encoding="utf-8")

        res = stack.auto_normalizar_y_asegurar_cumplimiento(mock_repo, auto_normalizar_nivel_1=True)
        self.assertGreater(len(res["nivel_1_acciones"]), 0)
        self.assertTrue((mock_repo / ".claude" / "rules" / "architecture.md").exists())
        self.assertTrue((mock_repo / ".claude" / "skills" / "add-feature" / "SKILL.md").exists())
        self.assertTrue((mock_repo / "AGENTS.md").exists())

    def test_auto_normalizar_nivel_2_crea_f0_y_bloquea(self):
        project_root = self.tmpdir / "proj-with-violations"
        project_root.mkdir()
        harness_dir = project_root / "harness"
        harness_dir.mkdir()
        docs_dir = project_root / "docs"
        docs_dir.mkdir()

        # Crear repo dotnet con violaciones de arquitectura en src
        (project_root / "App.sln").write_text("Microsoft Visual Studio Solution File", encoding="utf-8")
        domain_dir = project_root / "src" / "App.Domain"
        domain_dir.mkdir(parents=True)
        (domain_dir / "App.Domain.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk">\n<ItemGroup><PackageReference Include="Dapper" Version="2.0" /></ItemGroup>\n</Project>',
            encoding="utf-8"
        )
        (domain_dir / "Entity.cs").write_text('using Dapper;\npublic class Entity {}', encoding="utf-8")

        backlog_data = {
            "project": "proj-with-violations",
            "rules": {"require_spec_approved": True},
            "features": [
                {"id": 1, "name": "feat-checkout", "status": "todo"}
            ]
        }
        (harness_dir / "feature_list.json").write_text(json.dumps(backlog_data), encoding="utf-8")

        res = stack.auto_normalizar_y_asegurar_cumplimiento(project_root, backlog_data)
        self.assertTrue(res["f0_creada"])
        self.assertEqual(res["f0_id"], 0)
        self.assertTrue(res["bloqueos_activados"])
        self.assertGreater(len(res["nivel_2_violaciones"]), 0)

        # Verificar que F0 se insertó al inicio del backlog
        features = backlog_data["features"]
        self.assertEqual(features[0]["id"], 0)
        self.assertEqual(features[0]["status"], "todo")
        self.assertIn("normalizacion-arquitectura", features[0]["name"])

        # Verificar que F1 quedó bloqueada requiriendo 0
        self.assertIn(0, features[1]["requiere"])

        # Verificar que se generó el spec de F0
        spec_f0 = docs_dir / "spec-feature-0-normalizacion-arquitectura-dotnet-hexagonal.md"
        self.assertTrue(spec_f0.exists())
        self.assertIn("AC-1 [costura: integracion]", spec_f0.read_text(encoding="utf-8"))

        # Preparar spec de F1 para probar gate
        (docs_dir / "spec-feature-1-feat-checkout.md").write_text("# Spec 1\n\n- AC-1: Given When Then\n", encoding="utf-8")

        import os
        import gate
        import worktree
        import argparse

        cwd_prev = os.getcwd()
        os.chdir(project_root)
        try:
            # Probar bloqueo en gate.py approve-spec
            args_approve = argparse.Namespace(feature="1", yes=True, por="test")
            with self.assertRaises(SystemExit) as cm:
                gate.cmd_approve_spec(args_approve)
            self.assertIn("require_stack_normativo", str(cm.exception))

            # Probar bloqueo en worktree.py start
            args_start = argparse.Namespace(feature="1", sin_worktree=True, base="main")
            with self.assertRaises(SystemExit) as cm_wt:
                worktree.cmd_start(args_start)
            self.assertIn("require_stack_normativo", str(cm_wt.exception))
        finally:
            os.chdir(cwd_prev)


if __name__ == "__main__":
    unittest.main()
