"""Metadata OpenAI para invocacion automatica de la skill."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OpenAIMetadataTests(unittest.TestCase):
    def test_openai_yaml_habilita_invocacion_implicita(self):
        meta = ROOT / "agents" / "openai.yaml"
        texto = meta.read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: true", texto)
        self.assertIn("Harness Flow", texto)
        self.assertIn("PRD/SDD", texto)
        self.assertIn("Jira", texto)
        self.assertIn("Obsidian", texto)

    def test_referencia_openai_documenta_agents_skills(self):
        texto = (ROOT / "references" / "openai.md").read_text(encoding="utf-8")
        self.assertIn("~/.agents/skills/harness-flow", texto)
        self.assertIn("<repo>/.agents/skills/harness-flow", texto)
        self.assertIn("/etc/codex/skills", texto)


if __name__ == "__main__":
    unittest.main()
