#!/usr/bin/env python3
"""Pruebas de regresion para los 3 mecanismos de autonomia y confianza en agentes:
  1. Feedback Loop + Feature Map (`scripts/feature_map.py`)
  2. Agent Evals de skills/lecciones (`scripts/evals.py`)
  3. Guardrails deterministas (`scripts/guardrails.py`)

Cubre tanto el bloqueo real ante incumplimientos como el cierre legitimo en verde,
validando que no existan falsos verdes (hash SHA-256 en evals, evidencia real de
reproduccion en bugs, exenciones auditadas en guardrails y errores de medicion).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "scripts"
sys.path.insert(0, str(SCRIPTS))

import comun  # noqa: E402
import evals  # noqa: E402
import feature_map  # noqa: E402
import guardrails  # noqa: E402


def escribir(ruta: Path, texto: str) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


def sh(*args: str, cwd: Path) -> str:
    r = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)
    assert r.returncode == 0, f"{args}: {r.stdout}\n{r.stderr}"
    return r.stdout.strip()


def correr(script: str, *args: str, cwd: Path, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ, HARNESS_SIN_CONTEXTO="1", HARNESS_SIN_HUB="1", HARNESS_SIN_CBM="1")
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=str(cwd), capture_output=True, text=True, env=env,
    )


def crear_repo_base(
    tmp: Path,
    *,
    feature: dict,
    spec_text: str,
    rules_extra: dict | None = None,
    archivo_inicial: tuple[str, str] = ("src/app.ts", "export const ok = true;\n"),
) -> Path:
    root = tmp / "proyecto"
    root.mkdir(parents=True, exist_ok=True)
    sh("git", "init", "-q", "-b", "develop", cwd=root)
    sh("git", "config", "user.email", "test@example.com", cwd=root)
    sh("git", "config", "user.name", "Tester", cwd=root)
    rules = {
        "rama_base": "develop",
        "require_docs_al_dia": False,
        "require_spec_approved": True,
        "require_review": False,
        "require_verify_green": False,
        "require_leccion": False,
    }
    if rules_extra:
        rules.update(rules_extra)
    escribir(root / archivo_inicial[0], archivo_inicial[1])
    escribir(
        root / "docs" / f"spec-feature-{feature['id']}-{comun.slugify(feature['name'])}.md",
        spec_text,
    )
    escribir(
        root / "harness" / "feature_list.json",
        json.dumps({"project": "demo", "rules": rules, "features": [feature]}, indent=2) + "\n",
    )
    sh("git", "add", "-A", cwd=root)
    sh("git", "commit", "-q", "-m", "init", cwd=root)
    return root


# ---------------------------------------------------------------------------
# Mecanismo 1: Feedback Loop + Feature Map
# ---------------------------------------------------------------------------

class FeatureMapYFeedbackLoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="harness-fmap-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_init_crea_feature_map_y_guardrails_con_require_feature_map_true(self):
        root = self.tmp / "nuevo"
        root.mkdir()
        r = correr("init.py", "--project", "demo", "--root", str(root), cwd=self.tmp)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertTrue((root / "harness" / "feature-map.json").is_file())
        self.assertTrue((root / "harness" / "guardrails.json").is_file())
        self.assertTrue((root / "harness" / "evals").is_dir())
        bl = json.loads((root / "harness" / "feature_list.json").read_text(encoding="utf-8"))
        self.assertTrue(bl["rules"]["require_feature_map"])
        self.assertFalse(bl["rules"]["require_skill_eval"])

    def test_close_bloquea_feature_ui_sin_feature_map_y_pasa_al_registrarlo(self):
        spec = (
            "# Spec - Feature #1: registro\n\nEstado: draft\n\n"
            "## Criterios de aceptacion\n\n"
            "- AC-1 [costura: ui]: el formulario crea la cuenta. `verificar: true`\n"
        )
        root = crear_repo_base(
            self.tmp,
            feature={"id": 1, "name": "registro", "kind": "feature", "status": "todo"},
            spec_text=spec,
        )
        self.assertEqual(0, correr("gate.py", "approve-spec", "--feature", "1", "--yes", "--por", "T", cwd=root).returncode)
        self.assertEqual(0, correr("worktree.py", "start", "--feature", "1", "--delegado", "--yes", cwd=root).returncode)
        wt = Path(json.loads((root / "harness" / "feature_list.json").read_text(encoding="utf-8"))["features"][0]["worktree"])
        escribir(wt / "src/app.ts", "export const ok = true;\nexport const registro = 1;\n")
        sh("git", "add", "src/app.ts", cwd=wt)
        sh("git", "commit", "-q", "-m", "feat: registro", cwd=wt)
        escribir(root / "docs" / "impl-1.md", "## AC-1\n\nsrc/app.ts:2\n")
        sh("git", "add", "docs/", "harness/", cwd=root)
        sh("git", "commit", "-q", "-m", "docs: impl", cwd=root)

        # brief y revision deben avisar la falta de Feature Map
        r_brief = correr("contexto.py", "brief", "--feature", "1", cwd=root)
        self.assertEqual(0, r_brief.returncode, r_brief.stderr)
        self.assertIn("FEATURE MAP Y FEEDBACK LOOP", r_brief.stdout)
        self.assertIn("feature_map.py registrar", r_brief.stdout)

        r_rev = correr("revision.py", "--feature", "1", "--briefing", cwd=root)
        self.assertEqual(0, r_rev.returncode, r_rev.stderr)
        self.assertIn("ALERTAS DE FEATURE MAP Y FEEDBACK LOOP", r_rev.stdout)

        # close DEBE bloquear por require_feature_map=True (default)
        r_fail = correr("gate.py", "close", "--feature", "1", "--status", "done", "--to", "develop", cwd=root)
        self.assertEqual(1, r_fail.returncode, r_fail.stdout + r_fail.stderr)
        self.assertIn("feature-map:", r_fail.stdout)

        # Registrar entrada valida en harness/feature-map.json
        r_reg = correr(
            "feature_map.py", "registrar",
            "--id", "registro",
            "--nombre", "Registro de usuarios",
            "--feature", "1",
            "--ruta-ui", "/registro",
            "--paso", "Abrir /registro y enviar el formulario",
            "--como-verificar", "npx playwright test e2e/registro.spec.ts",
            cwd=root,
        )
        self.assertEqual(0, r_reg.returncode, r_reg.stdout + r_reg.stderr)
        self.assertEqual(0, correr("feature_map.py", "buscar", "registro", cwd=root).returncode)
        self.assertEqual(0, correr("feature_map.py", "verificar", "--feature", "1", cwd=root).returncode)

        sh("git", "add", "harness/", cwd=root)
        sh("git", "commit", "-q", "-m", "docs: feature map", cwd=root)

        r_ok = correr("gate.py", "close", "--feature", "1", "--status", "done", "--to", "develop", cwd=root)
        self.assertEqual(0, r_ok.returncode, r_ok.stdout + r_ok.stderr)

    def test_close_bloquea_bug_sin_evidencia_verificable_de_reproduccion_y_pasa_con_ella(self):
        spec = (
            "# Spec - Feature #2: fix login\n\nEstado: draft\n\n"
            "## Criterios de aceptacion\n\n"
            "- AC-1 [costura: servicio]: no falla con email con espacios. `verificar: true`\n"
        )
        root = crear_repo_base(
            self.tmp,
            feature={"id": 2, "name": "fix login", "kind": "bug", "status": "todo"},
            spec_text=spec,
        )
        self.assertEqual(0, correr("gate.py", "approve-spec", "--feature", "2", "--yes", "--por", "T", cwd=root).returncode)
        self.assertEqual(0, correr("worktree.py", "start", "--feature", "2", "--delegado", "--yes", cwd=root).returncode)
        wt = Path(json.loads((root / "harness" / "feature_list.json").read_text(encoding="utf-8"))["features"][0]["worktree"])
        escribir(wt / "src/app.ts", "export const trimEmail = (s: string) => s.trim();\n")
        sh("git", "add", "src/app.ts", cwd=wt)
        sh("git", "commit", "-q", "-m", "fix: trim email", cwd=wt)

        # Evidencia con prosa vacia en Reproduccion NO debe pasar (anti-falso-verde)
        escribir(root / "docs" / "impl-2.md", "## AC-1\n\nsrc/app.ts:1\n\n## Reproduccion\n\nLo probe a mano y fallo.\n")
        sh("git", "add", "docs/", "harness/", cwd=root)
        sh("git", "commit", "-q", "-m", "docs: impl sin comando", cwd=root)

        r_fail = correr("gate.py", "close", "--feature", "2", "--status", "done", "--to", "develop", cwd=root)
        self.assertEqual(1, r_fail.returncode, r_fail.stdout + r_fail.stderr)
        self.assertIn("feedback-loop:", r_fail.stdout)
        self.assertIn("evidencia verificable", r_fail.stdout)

        # Con comando verificable en `## Reproduccion`, cierra limpio
        escribir(
            root / "docs" / "impl-2.md",
            "## AC-1\n\nsrc/app.ts:1\n\n## Reproduccion\n\n"
            "Reproducido en rojo con `npm test -- login.spec.ts` (fallo en `src/app.ts:1`); en verde tras el fix.\n",
        )
        sh("git", "add", "docs/", cwd=root)
        sh("git", "commit", "-q", "-m", "docs: repro real", cwd=root)

        r_ok = correr("gate.py", "close", "--feature", "2", "--status", "done", "--to", "develop", cwd=root)
        self.assertEqual(0, r_ok.returncode, r_ok.stdout + r_ok.stderr)

    def test_feature_interna_sin_costura_ui_ni_bug_no_exige_feature_map(self):
        spec = (
            "# Spec - Feature #3: cache interna\n\nEstado: draft\n\n"
            "## Criterios de aceptacion\n\n"
            "- AC-1 [costura: servicio]: memoriza el calculo. `verificar: true`\n"
        )
        root = crear_repo_base(
            self.tmp,
            feature={"id": 3, "name": "cache interna", "kind": "feature", "status": "todo"},
            spec_text=spec,
        )
        self.assertEqual(0, correr("gate.py", "approve-spec", "--feature", "3", "--yes", "--por", "T", cwd=root).returncode)
        self.assertEqual(0, correr("worktree.py", "start", "--feature", "3", "--delegado", "--yes", cwd=root).returncode)
        wt = Path(json.loads((root / "harness" / "feature_list.json").read_text(encoding="utf-8"))["features"][0]["worktree"])
        escribir(wt / "src/app.ts", "export const cache = new Map();\n")
        sh("git", "add", "src/app.ts", cwd=wt)
        sh("git", "commit", "-q", "-m", "feat: cache", cwd=wt)
        escribir(root / "docs" / "impl-3.md", "## AC-1\n\nsrc/app.ts:1\n")
        sh("git", "add", "docs/", "harness/", cwd=root)
        sh("git", "commit", "-q", "-m", "docs", cwd=root)
        r_ok = correr("gate.py", "close", "--feature", "3", "--status", "done", "--to", "develop", cwd=root)
        self.assertEqual(0, r_ok.returncode, r_ok.stdout + r_ok.stderr)

    def test_require_feature_map_false_convierte_bloqueo_en_aviso_y_estado_reporta_mecanismos(self):
        spec = (
            "# Spec - Feature #4: perfil\n\nEstado: draft\n\n"
            "## Criterios de aceptacion\n\n"
            "- AC-1 [costura: endpoint]: devuelve el perfil. `verificar: true`\n"
        )
        root = crear_repo_base(
            self.tmp,
            feature={"id": 4, "name": "perfil", "kind": "feature", "status": "todo"},
            spec_text=spec,
            rules_extra={"require_feature_map": False},
        )
        r_est = correr("estado.py", cwd=root)
        self.assertEqual(0, r_est.returncode, r_est.stdout + r_est.stderr)
        self.assertIn("feature-map:", r_est.stdout)
        self.assertIn("guardrails:", r_est.stdout)

        self.assertEqual(0, correr("gate.py", "approve-spec", "--feature", "4", "--yes", "--por", "T", cwd=root).returncode)
        self.assertEqual(0, correr("worktree.py", "start", "--feature", "4", "--delegado", "--yes", cwd=root).returncode)
        wt = Path(json.loads((root / "harness" / "feature_list.json").read_text(encoding="utf-8"))["features"][0]["worktree"])
        escribir(wt / "src/app.ts", "export const perfil = 1;\n")
        sh("git", "add", "src/app.ts", cwd=wt)
        sh("git", "commit", "-q", "-m", "feat: perfil", cwd=wt)
        escribir(root / "docs" / "impl-4.md", "## AC-1\n\nsrc/app.ts:1\n")
        sh("git", "add", "docs/", "harness/", cwd=root)
        sh("git", "commit", "-q", "-m", "docs", cwd=root)

        r_ok = correr("gate.py", "close", "--feature", "4", "--status", "done", "--to", "develop", cwd=root)
        self.assertEqual(0, r_ok.returncode, r_ok.stdout + r_ok.stderr)
        self.assertIn("feature-map:", r_ok.stdout)


# ---------------------------------------------------------------------------
# Mecanismo 2: Agent Evals de Skills / Lecciones
# ---------------------------------------------------------------------------

class AgentEvalsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="harness-evals-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.skills_dir = self.tmp / "skills"
        self.skills_dir.mkdir()
        self.env = {"HARNESS_SKILLS_DIR": str(self.skills_dir)}

        spec = (
            "# Spec - Feature #1: pagos\n\nEstado: draft\n\n"
            "## Criterios de aceptacion\n\n"
            "- AC-1 [costura: servicio]: cobra una vez. `verificar: true`\n"
        )
        self.root = crear_repo_base(
            self.tmp,
            feature={"id": 1, "name": "pagos", "kind": "feature", "status": "todo"},
            spec_text=spec,
            rules_extra={"require_leccion": True, "require_skill_eval": True},
        )
        self.skill_md = self.skills_dir / "pagos-idempotentes" / "SKILL.md"
        escribir(
            self.skill_md,
            "---\nname: pagos-idempotentes\n"
            "description: \"Use when implementing payment retries with idempotency keys.\"\n---\n\n"
            "# pagos-idempotentes\n\n## Reglas\n\n"
            "- Validar Idempotency-Key antes de cobrar.\n"
            "- Usar transaccion atomica para evitar doble cobro.\n",
        )

    def _preparar_suite_valida(self) -> Path:
        r = correr("evals.py", "init", "pagos-idempotentes", "--umbral", "0.85", "--corridas", "2",
                   cwd=self.root, env_extra=self.env)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        suite_p = self.root / "harness" / "evals" / "pagos-idempotentes.json"
        suite = json.loads(suite_p.read_text(encoding="utf-8"))
        suite["max_rondas_mejora"] = 2
        suite["casos"][0]["tarea"] = "Escribe un servicio de cobro que soporte reintentos idempotentes."
        suite["casos"][0]["senales_prohibidas"] = ["cobrar dos veces sin clave"]
        suite_p.write_text(json.dumps(suite, indent=2), encoding="utf-8")
        return suite_p

    def test_flujo_completo_briefings_registro_stale_y_gate_close_opt_in(self):
        # 1. Path traversal rechazado
        r_bad = correr("evals.py", "init", "../escape", cwd=self.root, env_extra=self.env)
        self.assertNotEqual(0, r_bad.returncode)

        # 2. Init + briefing sin rellenar placeholder se niega
        correr("evals.py", "init", "pagos-idempotentes", "--corridas", "2", cwd=self.root, env_extra=self.env)
        r_ph = correr("evals.py", "briefing", "pagos-idempotentes", cwd=self.root, env_extra=self.env)
        self.assertNotEqual(0, r_ph.returncode)
        self.assertIn("placeholder", r_ph.stdout + r_ph.stderr)

        # 3. Suite valida -> briefing ejecutor NO revela rubrica ni senales prohibidas; juez SI
        (self.root / "harness" / "evals" / "pagos-idempotentes.json").unlink()
        self._preparar_suite_valida()

        r_ej = correr("evals.py", "briefing", "pagos-idempotentes", "--fase", "ejecutar", cwd=self.root, env_extra=self.env)
        self.assertEqual(0, r_ej.returncode, r_ej.stderr)
        self.assertIn("EN PARALELO", r_ej.stdout)
        self.assertNotIn("cobrar dos veces sin clave", r_ej.stdout)

        r_jz = correr("evals.py", "briefing", "pagos-idempotentes", "--fase", "juez", cwd=self.root, env_extra=self.env)
        self.assertEqual(0, r_jz.returncode, r_jz.stderr)
        self.assertIn("RUBRICA POR CASO", r_jz.stdout)
        self.assertIn("cobrar dos veces sin clave", r_jz.stdout)

        # 4. Resultado incompleto (solo 1 corrida de 2 exigidas) -> rechazado
        res_incompleto = self.tmp / "r_incompleto.json"
        escribir(res_incompleto, json.dumps({
            "ronda": 1, "juez": "argon",
            "corridas": [{
                "caso_id": "E-1", "corrida": 1,
                "criterios": [
                    {"id": "C-1", "cumplido": True, "evidencia": "handler.go:10 valida key"},
                    {"id": "C-2", "cumplido": True, "evidencia": "repo.go:22 usa TX"},
                ],
                "senales_prohibidas_detectadas": [],
            }],
        }))
        r_inc = correr("evals.py", "registrar", "pagos-idempotentes", "--resultado", str(res_incompleto),
                       cwd=self.root, env_extra=self.env)
        self.assertNotEqual(0, r_inc.returncode)
        self.assertIn("al menos 2", r_inc.stdout + r_inc.stderr)

        # 5. Ronda 1 reprobada -> exit 1 y guia de bucle de mejora; Ronda 2 reprobada (tope) -> sugiere promover a guardrail
        res_fail = self.tmp / "r_fail.json"
        escribir(res_fail, json.dumps({
            "ronda": 1, "juez": "argon",
            "corridas": [
                {
                    "caso_id": "E-1", "corrida": 1,
                    "criterios": [
                        {"id": "C-1", "cumplido": False, "evidencia": "no valido la clave en handler.go:10"},
                        {"id": "C-2", "cumplido": True, "evidencia": "repo.go:22 usa TX"},
                    ],
                    "senales_prohibidas_detectadas": [],
                },
                {
                    "caso_id": "E-1", "corrida": 2,
                    "criterios": [
                        {"id": "C-1", "cumplido": True, "evidencia": "handler.go:12 valida key"},
                        {"id": "C-2", "cumplido": True, "evidencia": "repo.go:22 usa TX"},
                    ],
                    "senales_prohibidas_detectadas": [],
                },
            ],
        }))
        r_f1 = correr("evals.py", "registrar", "pagos-idempotentes", "--resultado", str(res_fail), "--ronda", "1",
                      cwd=self.root, env_extra=self.env)
        self.assertEqual(1, r_f1.returncode, r_f1.stdout + r_f1.stderr)
        self.assertIn("bucle de mejora", r_f1.stdout)

        r_f2 = correr("evals.py", "registrar", "pagos-idempotentes", "--resultado", str(res_fail), "--ronda", "2",
                      cwd=self.root, env_extra=self.env)
        self.assertEqual(1, r_f2.returncode, r_f2.stdout + r_f2.stderr)
        self.assertIn("guardrails.py promover", r_f2.stdout)

        # 6. Preparar feature para cierre: con eval FAIL, close bloquea (require_skill_eval=True)
        self.assertEqual(0, correr("gate.py", "approve-spec", "--feature", "1", "--yes", "--por", "T", cwd=self.root).returncode)
        self.assertEqual(0, correr("worktree.py", "start", "--feature", "1", "--delegado", "--yes", cwd=self.root).returncode)
        wt = Path(json.loads((self.root / "harness" / "feature_list.json").read_text(encoding="utf-8"))["features"][0]["worktree"])
        escribir(wt / "src/app.ts", "export const ok = true;\nexport const pago = 1;\n")
        sh("git", "add", "src/app.ts", cwd=wt)
        sh("git", "commit", "-q", "-m", "feat: pago", cwd=wt)
        escribir(self.root / "docs" / "impl-1.md", "## AC-1\n\nsrc/app.ts:2\n")
        sh("git", "add", "docs/", "harness/", cwd=self.root)
        sh("git", "commit", "-q", "-m", "docs: impl", cwd=self.root)

        r_blk = correr("gate.py", "close", "--feature", "1", "--status", "done", "--to", "develop",
                       "--leccion", "pagos-idempotentes", cwd=self.root, env_extra=self.env)
        self.assertEqual(1, r_blk.returncode, r_blk.stdout + r_blk.stderr)
        self.assertIn("evals:", r_blk.stdout)

        # 7. Registrar ronda aprobada -> PASS + insignia en leccion.py list
        res_pass = self.tmp / "r_pass.json"
        escribir(res_pass, json.dumps({
            "ronda": 3, "juez": "argon",
            "corridas": [
                {
                    "caso_id": "E-1", "corrida": c,
                    "criterios": [
                        {"id": "C-1", "cumplido": True, "evidencia": "handler.go:10 valida Idempotency-Key"},
                        {"id": "C-2", "cumplido": True, "evidencia": "repo.go:22 usa TX atomica"},
                    ],
                    "senales_prohibidas_detectadas": [],
                }
                for c in (1, 2)
            ],
        }))
        r_p = correr("evals.py", "registrar", "pagos-idempotentes", "--resultado", str(res_pass), "--ronda", "3",
                     cwd=self.root, env_extra=self.env)
        self.assertEqual(0, r_p.returncode, r_p.stdout + r_p.stderr)
        self.assertIn("PASS (100%", r_p.stdout)

        r_list = correr("leccion.py", "list", cwd=self.root, env_extra=self.env)
        self.assertEqual(0, r_list.returncode, r_list.stderr)
        self.assertIn("[eval: PASS 100%]", r_list.stdout)

        # 8. Anti-falso-verde: editar SKILL.md invalida la eval -> STALE -> close bloquea otra vez
        self.skill_md.write_text(self.skill_md.read_text(encoding="utf-8") + "\n- Regla extra.\n", encoding="utf-8")
        est = evals.estado_eval("pagos-idempotentes", comun.paths(self.root), skill_md=self.skill_md)
        self.assertEqual("stale_skill", est["estado"])

        sh("git", "add", "harness/", cwd=self.root)
        sh("git", "commit", "-q", "-m", "chore: evals", cwd=self.root)
        r_stale = correr("gate.py", "close", "--feature", "1", "--status", "done", "--to", "develop",
                         "--leccion", "pagos-idempotentes", cwd=self.root, env_extra=self.env)
        self.assertEqual(1, r_stale.returncode, r_stale.stdout + r_stale.stderr)
        self.assertIn("stale_skill", r_stale.stdout)

        # 9. Re-evaluar sobre la version nueva -> close pasa
        self.assertEqual(
            0,
            correr("evals.py", "registrar", "pagos-idempotentes", "--resultado", str(res_pass), "--ronda", "4",
                   cwd=self.root, env_extra=self.env).returncode,
        )
        sh("git", "add", "harness/", cwd=self.root)
        sh("git", "commit", "-q", "-m", "chore: eval vigente", cwd=self.root)
        r_ok = correr("gate.py", "close", "--feature", "1", "--status", "done", "--to", "develop",
                      "--leccion", "pagos-idempotentes", cwd=self.root, env_extra=self.env)
        self.assertEqual(0, r_ok.returncode, r_ok.stdout + r_ok.stderr)


# ---------------------------------------------------------------------------
# Mecanismo 3: Guardrails Deterministas
# ---------------------------------------------------------------------------

class GuardrailsDeterministasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="harness-guardrails-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_politica_comentarios_anti_ruido_vs_sin_comentarios_y_exencion_auditada(self):
        diff = (
            "diff --git a/src/pagos.ts b/src/pagos.ts\n"
            "+++ b/src/pagos.ts\n"
            "@@ -1,0 +1,5 @@\n"
            "+// Changed the payment logic to fix retry\n"
            "+// Invariante: el saldo nunca puede ser negativo tras debitar\n"
            "+// eslint-disable-next-line no-console\n"
            "+export const x = 1;\n"
            "+// Changed by agent // harness-ignore-guardrail: comentarios-anti-ruido motivo valido de auditoria\n"
        )
        # Modo estandar (anti-ruido): bloquea solo linea 1 (narracion de IA), permite linea 2 (invariante Ousterhout),
        # linea 3 (directiva eslint) y linea 5 (exencion auditada con id y motivo >= 10 chars).
        res_std = guardrails.escanear_diff_guardrails(diff, guardrails.config_default("estandar"))
        self.assertEqual(1, len(res_std["bloqueos"]), res_std["bloqueos"])
        self.assertEqual("comentarios-anti-ruido", res_std["bloqueos"][0]["id"])
        self.assertEqual(1, res_std["bloqueos"][0]["line"])

        # Modo SpaceX (sin-comentarios): bloquea linea 1, linea 2 Y linea 5 (porque la exencion nombraba otro id!)
        res_sx = guardrails.escanear_diff_guardrails(diff, guardrails.config_default("spacex"))
        self.assertEqual(3, len(res_sx["bloqueos"]), res_sx["bloqueos"])
        self.assertTrue(all(b["id"] == "comentarios-sin-comentarios" for b in res_sx["bloqueos"]))

        # Exencion sin motivo suficiente NO exime
        diff_trampa = (
            "diff --git a/src/a.ts b/src/a.ts\n"
            "+++ b/src/a.ts\n"
            "@@ -1,0 +1,1 @@\n"
            "+eval(userInput) // harness-ignore-guardrail: no-eval-dinamico ok\n"
        )
        res_trampa = guardrails.escanear_diff_guardrails(diff_trampa, guardrails.config_default("estandar"))
        self.assertEqual(1, len(res_trampa["bloqueos"]))

    def test_frontera_entre_features_bloquea_atajo_de_acoplamiento(self):
        diff = (
            "diff --git a/src/features/envios/application/enviar.ts b/src/features/envios/application/enviar.ts\n"
            "+++ b/src/features/envios/application/enviar.ts\n"
            "@@ -1,0 +1,2 @@\n"
            "+import { PagoRepo } from '../../features/pagos/infrastructure/repo';\n"
            "+import { Envio } from '../../features/envios/domain/envio';\n"
        )
        res = guardrails.escanear_diff_guardrails(diff, guardrails.config_default("estandar"))
        self.assertEqual(1, len(res["bloqueos"]), res["bloqueos"])
        self.assertEqual("aislamiento-entre-features", res["bloqueos"][0]["id"])
        self.assertEqual(1, res["bloqueos"][0]["line"])

    def test_promover_desde_skill_desactivar_con_yes_y_bloqueo_en_verify_briefing_y_close(self):
        skills_dir = self.tmp / "skills"
        escribir(
            skills_dir / "react-sin-effects" / "SKILL.md",
            "---\nname: react-sin-effects\ndescription: \"No usar useEffect\"\n---\n# react-sin-effects\n",
        )
        env = {"HARNESS_SKILLS_DIR": str(skills_dir)}

        spec = (
            "# Spec - Feature #1: vista\n\nEstado: draft\n\n"
            "## Criterios de aceptacion\n\n"
            "- AC-1 [costura: servicio]: calcula total. `verificar: true`\n"
        )
        root = crear_repo_base(
            self.tmp,
            feature={"id": 1, "name": "vista", "kind": "feature", "status": "todo"},
            spec_text=spec,
            archivo_inicial=("src/view.tsx", "export function View() { return null; }\n"),
        )
        self.assertEqual(0, correr("guardrails.py", "init", "--perfil", "estandar", cwd=root).returncode)

        # Promover regla desde skill -> bloqueante en harness/guardrails.json
        r_prom = correr(
            "guardrails.py", "promover",
            "--desde-skill", "react-sin-effects",
            "--id", "no-use-effect",
            "--patron", r"\b(?:React\.)?useEffect\s*\(",
            "--glob", "**/*.tsx",
            "--mensaje", "useEffect prohibido; deriva estado",
            cwd=root, env_extra=env,
        )
        self.assertEqual(0, r_prom.returncode, r_prom.stdout + r_prom.stderr)

        # Desactivar sin --yes se niega
        r_no = correr("guardrails.py", "desactivar", "--id", "no-debugger", "--motivo", "motivo largo valido", cwd=root)
        self.assertNotEqual(0, r_no.returncode)
        self.assertIn("--yes", r_no.stdout + r_no.stderr)

        sh("git", "add", "harness/", cwd=root)
        sh("git", "commit", "-q", "-m", "chore: guardrails", cwd=root)

        self.assertEqual(0, correr("gate.py", "approve-spec", "--feature", "1", "--yes", "--por", "T", cwd=root).returncode)
        self.assertEqual(0, correr("worktree.py", "start", "--feature", "1", "--delegado", "--yes", cwd=root).returncode)
        wt = Path(json.loads((root / "harness" / "feature_list.json").read_text(encoding="utf-8"))["features"][0]["worktree"])

        # Introducir violacion de guardrail promovido (`useEffect`) + comentario ruido IA
        escribir(
            wt / "src/view.tsx",
            "// Added effect to fetch data\nexport function View() { useEffect(() => {}, []); return null; }\n",
        )
        sh("git", "add", "src/view.tsx", cwd=wt)
        sh("git", "commit", "-q", "-m", "feat: viola guardrails", cwd=wt)
        escribir(root / "docs" / "impl-1.md", "## AC-1\n\nsrc/view.tsx:2\n")
        sh("git", "add", "docs/", "harness/", cwd=root)
        sh("git", "commit", "-q", "-m", "docs: impl", cwd=root)

        # 1. guardrails.py check falla con exit 1
        r_chk = correr("guardrails.py", "check", "--feature", "1", cwd=root)
        self.assertEqual(1, r_chk.returncode, r_chk.stdout + r_chk.stderr)
        self.assertIn("no-use-effect", r_chk.stdout)
        self.assertIn("comentarios-anti-ruido", r_chk.stdout)

        # 2. gate.py verify falla por guardrails aunque el AC pase (`verificar: true`)
        r_ver = correr("gate.py", "verify", "--feature", "1", cwd=root)
        self.assertEqual(1, r_ver.returncode, r_ver.stdout + r_ver.stderr)
        self.assertIn("guardrails deterministas:", r_ver.stdout)
        self.assertIn("## Guardrails deterministas — FAIL", (root / "docs" / "verify-1.md").read_text(encoding="utf-8"))

        # 3. revision.py --briefing muestra alertas automaticas de guardrails
        r_br = correr("revision.py", "--feature", "1", "--briefing", cwd=root)
        self.assertEqual(0, r_br.returncode, r_br.stderr)
        self.assertIn("ALERTAS AUTOMATICAS DE GUARDRAILS DETERMINISTAS", r_br.stdout)
        self.assertIn("no-use-effect", r_br.stdout)

        # 4. gate.py close BLOQUEA
        r_cls = correr("gate.py", "close", "--feature", "1", "--status", "done", "--to", "develop", cwd=root)
        self.assertEqual(1, r_cls.returncode, r_cls.stdout + r_cls.stderr)
        self.assertIn("guardrails [no-use-effect]", r_cls.stdout)

        # 5. Al corregir el codigo en el worktree, verify y close salen en VERDE
        escribir(wt / "src/view.tsx", "export function View() { return 1 + 1; }\n")
        sh("git", "add", "src/view.tsx", cwd=wt)
        sh("git", "commit", "-q", "-m", "fix: cumplir guardrails", cwd=wt)

        r_ver2 = correr("gate.py", "verify", "--feature", "1", cwd=root)
        self.assertEqual(0, r_ver2.returncode, r_ver2.stdout + r_ver2.stderr)
        sh("git", "add", "docs/", "harness/", cwd=root)
        sh("git", "commit", "-q", "-m", "docs: verify verde", cwd=root)

        r_cls2 = correr("gate.py", "close", "--feature", "1", "--status", "done", "--to", "develop", cwd=root)
        self.assertEqual(0, r_cls2.returncode, r_cls2.stdout + r_cls2.stderr)

    def test_comando_guardrail_ausente_no_devuelve_verde(self):
        spec = (
            "# Spec - Feature #1: cmd\n\nEstado: draft\n\n"
            "## Criterios de aceptacion\n\n- AC-1 [costura: servicio]: ok. `verificar: true`\n"
        )
        root = crear_repo_base(
            self.tmp,
            feature={"id": 1, "name": "cmd", "kind": "feature", "status": "in_progress"},
            spec_text=spec,
        )
        cfg = guardrails.config_default("estandar")
        cfg["comandos"] = [{"id": "linter-inexistente", "comando": "comando_que_no_existe_xyz_999", "severidad": "block"}]
        escribir(root / "harness" / "guardrails.json", json.dumps(cfg, indent=2))
        r = correr("guardrails.py", "check", "--feature", "1", cwd=root)
        self.assertEqual(2, r.returncode, r.stdout + r.stderr)
        self.assertIn("NO SE PUDO MEDIR", r.stdout)

    def test_perfil_spacex_activa_sin_comentarios_y_no_use_effect(self):
        spec = (
            "# Spec - Feature #1: ui\n\nEstado: draft\n\n"
            "## Criterios de aceptacion\n\n- AC-1 [costura: servicio]: ok. `verificar: true`\n"
        )
        root = crear_repo_base(
            self.tmp,
            feature={"id": 1, "name": "ui", "kind": "feature", "status": "in_progress"},
            spec_text=spec,
        )
        r = correr("guardrails.py", "init", "--perfil", "spacex", cwd=root)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        cfg = json.loads((root / "harness" / "guardrails.json").read_text(encoding="utf-8"))
        self.assertEqual("sin-comentarios", cfg["comentarios"])
        self.assertTrue(any(x["id"] == "no-use-effect" for x in cfg["reglas"]))

    def test_higiene_evals_detecta_solapamiento_entre_skills(self):
        skills_dir = self.tmp / "skills-higiene"
        escribir(
            skills_dir / "pagos-reintentos-a" / "SKILL.md",
            "---\nname: pagos-reintentos-a\ndescription: \"Validar idempotencia en pagos y reintentos HTTP\"\n---\n# a\n",
        )
        escribir(
            skills_dir / "pagos-reintentos-b" / "SKILL.md",
            "---\nname: pagos-reintentos-b\ndescription: \"Validar idempotencia en pagos y reintentos HTTP\"\n---\n# b\n",
        )
        r = correr("evals.py", "estado", "--json", cwd=RAIZ, env_extra={"HARNESS_SKILLS_DIR": str(skills_dir)})
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        rep = json.loads(r.stdout)
        self.assertTrue(any("solapamiento" in a for a in rep["avisos"]), rep["avisos"])


if __name__ == "__main__":
    unittest.main()
