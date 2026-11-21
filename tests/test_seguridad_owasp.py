#!/usr/bin/env python3
"""Pruebas de regresion OWASP y paridad Multi-LLM (Claude, Gemini, AGY, Grok)."""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "scripts"
sys.path.insert(0, str(SCRIPTS))

import comun  # noqa: E402
import contexto  # noqa: E402
import normas  # noqa: E402
import producto  # noqa: E402
import seguridad  # noqa: E402
import stack  # noqa: E402


def escribir(ruta: Path, texto: str) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


def correr(script: str, *args: str, cwd: Path, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ, HARNESS_SIN_CONTEXTO="1", HARNESS_SIN_HUB="1", HARNESS_SIN_CBM="1")
    for k in ("CLAUDECODE", "CLAUDE_CONFIG_DIR", "GROK_AGENT", "ANTIGRAVITY_AGENT", "GEMINI_CLI", "HARNESS_HOST"):
        env.pop(k, None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          cwd=str(cwd), capture_output=True, text=True, env=env)


class SemverYVersionMinimaTests(unittest.TestCase):
    def test_comparacion_semver_no_es_lexicografica(self):
        # Regresion: en Go '1.9' < '1.23' era False por comparacion de strings.
        self.assertTrue(seguridad.version_menor("1.9", "1.23.0"))
        self.assertTrue(seguridad.version_menor("1.9.4", "1.23.0"))
        self.assertFalse(seguridad.version_menor("1.23", "1.23.0"))
        self.assertFalse(seguridad.version_menor("1.24.2", "1.23.0"))
        self.assertFalse(seguridad.version_menor("8.0", "8.0.0"))
        self.assertTrue(seguridad.version_menor("^18.2.0", "19.0.0"))
        self.assertFalse(seguridad.version_menor("^19.0.1", "19.0.0"))
        self.assertTrue(seguridad.version_menor(">=3.10", "3.11"))
        self.assertFalse(seguridad.version_menor(">=3.12", "3.11"))

    def test_todos_los_doce_stacks_declaran_minimum_version_y_sin_fallback_muerto(self):
        manifests = stack.listar_stacks_disponibles()
        self.assertEqual(12, len(manifests))
        for m in manifests:
            sa = m.get("security_audit") or {}
            with self.subTest(stack=m["id"]):
                self.assertTrue(sa.get("minimum_version"), f"{m['id']} sin minimum_version")
                self.assertNotIn("fallback_command", sa)

    def test_auditar_avisa_version_minima_en_go_angular_nextjs_nestjs_python_y_springboot(self):
        tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, tmp, True)

        # Go 1.9 (< 1.23.0): antes pasaba sin aviso por comparacion lexicografica.
        go_repo = tmp / "go-viejo"
        escribir(go_repo / "go.mod", "module demo\n\ngo 1.9\n")
        res_go = stack.auditar_seguridad_y_versiones(go_repo, "golang-hexagonal")
        self.assertTrue(any("1.9" in w and "1.23.0" in w for w in res_go["warnings"]), res_go["warnings"])

        # Angular 18 (< 19.0.0)
        ng_repo = tmp / "ng-viejo"
        escribir(ng_repo / "package.json", json.dumps({"dependencies": {"@angular/core": "^18.2.0"}}))
        res_ng = stack.auditar_seguridad_y_versiones(ng_repo, "angular-product")
        self.assertTrue(any("Angular" in w and "19.0.0" in w for w in res_ng["warnings"]), res_ng["warnings"])

        # Next.js 14 (< 15.0.0)
        nx_repo = tmp / "nx-viejo"
        escribir(nx_repo / "package.json", json.dumps({"dependencies": {"next": "14.2.5"}}))
        res_nx = stack.auditar_seguridad_y_versiones(nx_repo, "nextjs-product")
        self.assertTrue(any("Next.js" in w and "15.0.0" in w for w in res_nx["warnings"]), res_nx["warnings"])

        # NestJS 9 (< 10.0.0)
        nest_repo = tmp / "nest-viejo"
        escribir(nest_repo / "package.json", json.dumps({"dependencies": {"@nestjs/core": "^9.4.0"}}))
        res_nest = stack.auditar_seguridad_y_versiones(nest_repo, "nestjs-hexagonal")
        self.assertTrue(any("NestJS" in w and "10.0.0" in w for w in res_nest["warnings"]), res_nest["warnings"])

        # Python 3.10 (< 3.11)
        py_repo = tmp / "py-viejo"
        escribir(py_repo / "pyproject.toml", '[project]\nname = "demo"\nrequires-python = ">=3.10"\n')
        res_py = stack.auditar_seguridad_y_versiones(py_repo, "python-dataproduct")
        self.assertTrue(any("Python" in w and "3.11" in w for w in res_py["warnings"]), res_py["warnings"])

        # Spring Boot 3.1.5 (< 3.2.0)
        sb_repo = tmp / "sb-viejo"
        escribir(sb_repo / "pom.xml",
                 "<project><parent><artifactId>spring-boot-starter-parent</artifactId>"
                 "<version>3.1.5</version></parent></project>\n")
        res_sb = stack.auditar_seguridad_y_versiones(sb_repo, "springboot-hexagonal")
        self.assertTrue(any("Spring Boot" in w and "3.2.0" in w for w in res_sb["warnings"]), res_sb["warnings"])


class OwaspZapDastTests(unittest.TestCase):
    def test_reescribir_url_docker_en_macos_y_windows(self):
        self.assertEqual("http://host.docker.internal:8080/api",
                         seguridad.reescribir_url_docker("http://localhost:8080/api", plataforma="darwin"))
        self.assertEqual("http://host.docker.internal:3000",
                         seguridad.reescribir_url_docker("http://127.0.0.1:3000", plataforma="win32"))
        self.assertEqual("http://localhost:8080",
                         seguridad.reescribir_url_docker("http://localhost:8080", plataforma="linux"))
        self.assertEqual("https://staging.example.com",
                         seguridad.reescribir_url_docker("https://staging.example.com", plataforma="darwin"))

    def test_evaluar_dast_high_marca_failed_y_medium_marca_warnings(self):
        rep_high = {
            "site": [{"alerts": [
                {"name": "SQL Injection", "riskcode": "3", "cweid": "89", "count": "2"},
                {"name": "Missing CSP", "riskcode": "2", "cweid": "693", "count": "1"},
            ]}]
        }
        ev_high = seguridad.evaluar_dast_zap(2, "", rep_high)
        self.assertEqual("failed", ev_high["status"])
        self.assertEqual(1, ev_high["alerts"]["High"])
        self.assertEqual("SQL Injection", ev_high["high_alerts"][0]["name"])

        rep_med = {"site": [{"alerts": [{"name": "Missing CSP", "riskcode": "2", "count": "1"}]}]}
        ev_med = seguridad.evaluar_dast_zap(2, "", rep_med)
        self.assertEqual("warnings", ev_med["status"])
        self.assertEqual(0, ev_med["alerts"]["High"])
        self.assertEqual(1, ev_med["alerts"]["Medium"])

        ev_err = seguridad.evaluar_dast_zap(125, "docker: Error response from daemon", None)
        self.assertEqual("error", ev_err["status"])

        ev_ok = seguridad.evaluar_dast_zap(0, "PASS: 50\nWARN-NEW: 0\nFAIL-NEW: 0\n", None)
        self.assertEqual("passed", ev_ok["status"])

    def test_auditar_dast_con_alerta_high_eleva_estado_a_hallazgos_y_no_ensucia_repo(self):
        tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, tmp, True)
        repo = tmp / "ms-java"
        escribir(repo / "pom.xml",
                 "<project><parent><artifactId>spring-boot-starter-parent</artifactId>"
                 "<version>3.3.0</version></parent></project>\n")
        escribir(repo / "docs" / "openapi.yaml", "openapi: 3.0.3\ninfo:\n  title: Demo\n  version: 1.0.0\n")
        mvnw = repo / "mvnw"
        mvnw.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        mvnw.chmod(mvnw.stat().st_mode | stat.S_IXUSR)

        capturado: dict[str, list[str]] = {}

        def fake_run(cmd, cwd=None, timeout=60):
            if cmd[:2] == ["docker", "info"]:
                return 0, "ok"
            if cmd[0] == "docker" and cmd[1] == "run":
                capturado["cmd"] = list(cmd)
                # Escribir reporte JSON simulado en el volumen temporal montado en /zap/wrk
                vol = next(a for a in cmd if ":/zap/wrk/" in a)
                host_dir = Path(vol.split(":/zap/wrk/", 1)[0])
                (host_dir / "zap-report.json").write_text(json.dumps({
                    "site": [{"alerts": [{"name": "SQL Injection", "riskcode": "3", "cweid": "89", "count": "1"}]}]
                }), encoding="utf-8")
                return 2, "FAIL-NEW: 1"
            return 0, "clean"

        with mock.patch.object(shutil, "which", side_effect=lambda x: "/usr/bin/docker" if x == "docker" else None), \
             mock.patch.object(stack, "_run_cmd", side_effect=fake_run):
            res = stack.auditar_seguridad_y_versiones(
                repo, "springboot-hexagonal", dast=True, target_url="http://localhost:8080"
            )

        self.assertEqual(stack.AUDITORIA_CON_HALLAZGOS, res["estado"])
        self.assertEqual("failed", res["dast"]["status"])
        self.assertEqual(1, res["dast"]["alerts"]["High"])
        self.assertTrue(any("SQL Injection" in f for f in res["findings"]), res["findings"])
        self.assertIn("-O", capturado["cmd"])
        self.assertFalse((repo / "zap-report.json").exists(), "DAST no debe dejar archivos sin seguimiento en el repo")

    def test_auditar_dast_sin_docker_sugiere_ruta_relativa_de_openapi(self):
        tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, tmp, True)
        repo = tmp / "api"
        escribir(repo / "go.mod", "module demo\n\ngo 1.23.0\n")
        escribir(repo / "docs" / "openapi.yaml", "openapi: 3.0.3\n")
        with mock.patch.object(shutil, "which", return_value=None):
            res = stack.auditar_seguridad_y_versiones(
                repo, "golang-hexagonal", dast=True, target_url="http://localhost:9000"
            )
        self.assertEqual("skipped", res["dast"]["status"])
        self.assertIn("/zap/wrk/docs/openapi.yaml", res["dast"]["command"])
        self.assertIn("-O ", res["dast"]["command"])


class AcNegativoYProductoSeguridadTests(unittest.TestCase):
    def test_ac_negativo_admite_variantes_y_costuras_ampliadas(self):
        spec_gql = "## Criterios de aceptacion\n\n- AC-1 [costura: graphql]: consulta ordenes.\n"
        self.assertEqual(1, len([a for a in comun.avisos_vertical_spec(spec_gql) if a.startswith("seguridad:")]))

        spec_paren = spec_gql + "- AC-2 [costura: graphql] (negativo): sin token responde 401.\n"
        self.assertEqual(["AC-2"], comun.ac_negativos(spec_paren))
        self.assertEqual([], [a for a in comun.avisos_vertical_spec(spec_paren) if a.startswith("seguridad:")])

        spec_hijo = spec_gql + "- AC-2 [costura: bff]: rechaza rol invalido.\n  Tipo: negativo\n"
        self.assertEqual(["AC-2"], comun.ac_negativos(spec_hijo))
        self.assertEqual([], [a for a in comun.avisos_vertical_spec(spec_hijo) if a.startswith("seguridad:")])

    def test_fuera_de_alcance_puede_eximir_ac_negativo(self):
        spec = (
            "## Criterios de aceptacion\n\n"
            "- AC-1 [costura: endpoint]: devuelve healthcheck publico.\n\n"
            "## Fuera de alcance\n\n"
            "Endpoint publico sin autenticacion; no aplica AC negativo de permisos.\n"
        )
        self.assertEqual([], [a for a in comun.avisos_vertical_spec(spec) if a.startswith("seguridad:")])

    def test_avisos_seguridad_producto_prd_y_sdd(self):
        prd_sin = "# PRD\n\n## Resumen\nHoy: manual.\nDespues: automatico.\n"
        self.assertEqual(1, len(producto.avisos_seguridad_producto(prd_sin, "prd")))
        prd_con = prd_sin + "\n## La historia\nCaso de abuso: un usuario sin permisos intenta ver otra cuenta.\n"
        self.assertEqual([], producto.avisos_seguridad_producto(prd_con, "prd"))

        sdd_sin = "# SDD\n\n## Componentes\n```mermaid\ngraph TD; A-->B;\n```\n"
        self.assertEqual(1, len(producto.avisos_seguridad_producto(sdd_sin, "sdd")))
        sdd_con = sdd_sin + "\nFronteras de confianza entre BFF y API con autenticacion JWT.\n"
        self.assertEqual([], producto.avisos_seguridad_producto(sdd_con, "sdd"))


class ParidadMultiLlmYAssetsOwaspTests(unittest.TestCase):
    def test_normas_y_agentes_cubren_top_10_completo(self):
        seg = next(n for n in normas.NORMAS if n["id"] == "seguridad")
        texto_c = " ".join(seg["construye"])
        texto_a = " ".join(t for _, t in seg["audita"])
        for esperado in ("innerHTML", "dangerouslySetInnerHTML", "JWT", "pickle.loads", "PII", "metadata de la nube"):
            with self.subTest(construye=esperado):
                self.assertIn(esperado, texto_c)
        for esperado in ("A01", "A02", "A03", "A07", "A08", "A09", "A10", "A05"):
            with self.subTest(audita=esperado):
                self.assertIn(esperado, texto_a)

        impl = (RAIZ / "agents" / "implementer.md").read_text(encoding="utf-8")
        rev = (RAIZ / "agents" / "revisor.md").read_text(encoding="utf-8")
        self.assertIn("OWASP Top 10", impl)
        self.assertIn("pickle.loads", impl)
        self.assertIn("A07", rev)
        self.assertIn("A08", rev)
        self.assertIn("A09", rev)

    def test_ningun_stack_exige_x_xss_protection_ni_filtra_solo_claude(self):
        for m in stack.listar_stacks_disponibles():
            headers = ((m.get("normative") or {}).get("architecture_constraints") or {}).get(
                "security_headers_and_errors", {}
            ).get("security_headers", [])
            with self.subTest(manifest=m["id"]):
                self.assertNotIn("X-XSS-Protection", headers)

        for ruta in sorted(stack.STACKS_DIR.glob("*/rules/security.md")) + sorted(
            stack.STACKS_DIR.glob("*/skills/security-review/SKILL.md")
        ):
            txt = ruta.read_text(encoding="utf-8")
            with self.subTest(archivo=str(ruta.relative_to(stack.STACKS_DIR))):
                self.assertNotIn("X-XSS-Protection: 1", txt)
                self.assertNotIn("x-xss-protection: 1", txt)
                if ".claude/" in txt:
                    self.assertIn(".agents/", txt)
                    self.assertIn(".gemini/", txt)
                    self.assertIn(".grok/", txt)

    def test_paridad_multi_llm_en_brief_y_briefing_para_claude_gemini_agy_y_grok(self):
        tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, tmp, True)
        escribir(tmp / "go.mod", "module demo\n\ngo 1.23.0\n")
        escribir(tmp / "docs" / "spec-feature-1-auth.md",
                 "# Spec - Feature #1: auth\n\nEstado: draft\n\n## Criterios de aceptacion\n\n"
                 "- AC-1 [costura: endpoint] [negativo]: sin token responde 401. `verificar: true`\n")
        escribir(tmp / "harness" / "feature_list.json", json.dumps({
            "project": "demo",
            "rules": {"require_docs_al_dia": False},
            "features": [{"id": 1, "name": "auth", "status": "in_progress"}],
        }))

        # Normalizar deja security.md + security-review en .claude, .agents (AGY) y .gemini (Gemini CLI)
        stack.normalizar_repositorio(tmp, "golang-hexagonal", rules={})
        for carpeta in (".claude", ".agents", ".gemini"):
            self.assertTrue((tmp / carpeta / "rules" / "security.md").is_file())
            self.assertTrue((tmp / carpeta / "skills" / "security-review" / "SKILL.md").is_file())

        for host in ("claude", "gemini", "grok"):
            env = {"HARNESS_HOST": host}
            r_brief = correr("contexto.py", "brief", "--feature", "1", cwd=tmp, env_extra=env)
            r_rev = correr("revision.py", "--feature", "1", "--briefing", cwd=tmp, env_extra=env)
            with self.subTest(host=host):
                self.assertEqual(0, r_brief.returncode, r_brief.stderr)
                self.assertEqual(0, r_rev.returncode, r_rev.stderr)
                for marcador in ("[seguridad]", "pickle.loads", "dangerouslySetInnerHTML", "security.md", "security-review"):
                    self.assertIn(marcador, r_brief.stdout)
                for marcador in ("autenticacion rota (A07)", "deserializacion insegura (A08)", "fuga en logs (A09)",
                                 "security.md", "security-review"):
                    self.assertIn(marcador, r_rev.stdout)

        # En Grok, ademas publica .grok/rules/golang-hexagonal--security.md y .grok/skills/golang-hexagonal--security-review
        self.assertTrue((tmp / ".grok" / "rules" / "golang-hexagonal--security.md").is_file())
        self.assertTrue((tmp / ".grok" / "skills" / "golang-hexagonal--security-review" / "SKILL.md").is_file())


class DiffSecretosYDependenciasGateTests(unittest.TestCase):
    def test_escanear_diff_detecta_secretos_sin_exponer_valor_y_respeta_placeholders(self):
        fake_aws = "AKIA" + "9K8L7M6N5P4Q3R2S"
        fake_gh = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
        diff = (
            "diff --git a/src/config.py b/src/config.py\n"
            "+++ b/src/config.py\n"
            "@@ -1,0 +1,6 @@\n"
            f"+AWS_KEY = \"{fake_aws}\"\n"
            f"+GH_TOKEN = \"{fake_gh}\"\n"
            "+DB_URL = \"postgres://app:Sup3rPr0dP4ssw0rd@prod-db.internal:5432/app\"\n"
            "+LOCAL_DB = \"postgres://postgres:postgres12345@localhost:5432/dev\"\n"
            "+EXAMPLE_KEY = \"api_key_example_placeholder_value\"\n"
            f"+IGNORED = \"{fake_aws}\"  # harness-ignore-secret\n"
            "diff --git a/go.mod b/go.mod\n"
            "+++ b/go.mod\n"
            "@@ -1,0 +1,1 @@\n"
            "+require example.com/pkg v1.2.3\n"
        )
        res = seguridad.escanear_diff_seguridad(diff)
        self.assertEqual(3, len(res["secrets"]), res["secrets"])
        self.assertEqual(["go.mod"], res["dep_files"])
        # Jamas incluye el valor real del secreto en la salida estructurada.
        dumped = json.dumps(res)
        self.assertNotIn(fake_aws, dumped)
        self.assertNotIn(fake_gh, dumped)
        self.assertNotIn("Sup3rPr0dP4ssw0rd", dumped)

    def test_gate_close_bloquea_por_secreto_en_diff_y_avisa_por_dependencias(self):
        tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, tmp, True)

        def git(*args: str, cwd: Path = tmp) -> None:
            r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
            self.assertEqual(0, r.returncode, f"git {args}: {r.stderr}")

        git("init", "-b", "develop")
        git("config", "user.email", "test@example.com")
        git("config", "user.name", "Tester")

        escribir(tmp / "go.mod", "module demo\n\ngo 1.23.0\n")
        escribir(tmp / "main.go", "package main\nfunc main() {}\n")
        escribir(tmp / "docs" / "spec-feature-1-demo.md",
                 "# Spec - Feature #1: demo\n\nEstado: draft\n\n## Criterios de aceptacion\n\n"
                 "- AC-1 [costura: servicio]: compila. `verificar: true`\n")
        escribir(tmp / "harness" / "feature_list.json", json.dumps({
            "project": "demo",
            "rules": {
                "rama_base": "develop",
                "require_spec_approved": True,
                "require_review": False,
                "require_verify_green": False,
                "require_leccion": False,
                "require_docs_al_dia": False,
            },
            "features": [{"id": 1, "name": "demo", "status": "todo"}],
        }))
        git("add", ".")
        git("commit", "-m", "init")

        # Aprobar spec y arrancar worktree en modo delegado para no exigir lista de tests
        self.assertEqual(0, correr("gate.py", "approve-spec", "--feature", "1", "--yes", "--por", "T", cwd=tmp).returncode)
        self.assertEqual(0, correr("worktree.py", "start", "--feature", "1", "--delegado", "--yes", cwd=tmp).returncode)

        data = json.loads((tmp / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        wt = Path(data["features"][0]["worktree"])
        fake_secret = "AKIA" + "8Z7Y6X5W4V3U2T1S"
        escribir(wt / "main.go", f'package main\nconst key = "{fake_secret}"\nfunc main() {{}}\n')
        escribir(wt / "go.mod", "module demo\n\ngo 1.23.0\n// cambio de dependencia\n")
        git("add", "main.go", "go.mod", cwd=wt)
        git("commit", "-m", "feat: secreto y dep", cwd=wt)

        escribir(tmp / "docs" / "impl-1.md", "## AC-1\n\nmain.go:2\n")
        git("add", "docs/", "harness/")
        git("commit", "-m", "docs: spec y evidencia")

        # revision.py --briefing debe mostrar alertas automaticas de secreto y dependencias
        r_br = correr("revision.py", "--feature", "1", "--briefing", cwd=tmp)
        self.assertEqual(0, r_br.returncode, r_br.stderr)
        self.assertIn("ALERTAS AUTOMATICAS DE SEGURIDAD (OWASP)", r_br.stdout)
        self.assertIn("AWS Access Key ID", r_br.stdout)
        self.assertIn("DEPENDENCIAS TOCADAS (A06)", r_br.stdout)
        # La alerta automatica no debe imprimir el valor del secreto (el diff crudo va debajo)
        bloque_alertas = r_br.stdout.split("DIFF DE LA FEATURE", 1)[0]
        self.assertNotIn(fake_secret, bloque_alertas)

        # gate.py close debe BLOQUEAR por el secreto sin imprimir su valor
        r_fail = correr("gate.py", "close", "--feature", "1", "--status", "done", "--to", "develop", cwd=tmp)
        self.assertEqual(1, r_fail.returncode, r_fail.stdout + r_fail.stderr)
        self.assertIn("seguridad (OWASP A02)", r_fail.stdout)
        self.assertNotIn(fake_secret, r_fail.stdout)

        # Al retirar el secreto (manteniendo el cambio en go.mod), close pasa y avisa A06
        escribir(wt / "main.go", "package main\nfunc main() {}\n")
        git("add", "main.go", cwd=wt)
        git("commit", "-m", "fix: retirar secreto", cwd=wt)
        r_ok = correr("gate.py", "close", "--feature", "1", "--status", "done", "--to", "develop", cwd=tmp)
        self.assertEqual(0, r_ok.returncode, r_ok.stdout + r_ok.stderr)
        self.assertIn("seguridad (OWASP A06)", r_ok.stdout)
        self.assertIn("stack.py auditar", r_ok.stdout)


if __name__ == "__main__":
    unittest.main()
