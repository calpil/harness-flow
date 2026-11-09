"""Regresion del indice de skills de Hermes.

Hermes recorre `~/.hermes/skills` entero y registra como skill propia cada
`SKILL.md` que encuentra. Dentro de una skill solo poda `references/`,
`templates/`, `assets/` y `scripts/` (`agent/skill_utils.py`,
`iter_skill_index_files`). Con `stacks/` en la raiz, las 153 plantillas de los
stacks entraban al indice: `hermes skills list` mostraba `auto-git-commit`,
`springboot` o `adr` como skills del usuario, y 132 mas con la ruta por nombre.

No hay exit!=0 que avise: la skill sigue cargando y el indice solo crece.
"""
import os
from pathlib import Path
import sys
import unittest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import stack  # noqa: E402

# Copia de las constantes de Hermes. Si Hermes las cambia, este test deja de
# medir lo que dice: contrastalo con `hermes skills list`.
EXCLUIDOS = frozenset((
    ".git", ".github", ".hub", ".archive", ".curator_backups", ".locks",
    ".venv", "venv", "node_modules", "site-packages", "__pycache__",
    ".tox", ".nox", ".pytest_cache", ".mypy_cache", ".ruff_cache",
))
SOPORTE = frozenset(("references", "templates", "assets", "scripts"))


def skills_que_ve_hermes(raiz: Path) -> list[Path]:
    """El recorrido de `iter_skill_index_files`, con la misma poda."""
    vistas = []
    for actual, dirs, archivos in os.walk(str(raiz), followlinks=True):
        es_skill = "SKILL.md" in archivos
        dirs[:] = [d for d in dirs if d not in EXCLUIDOS and not (es_skill and d in SOPORTE)]
        if es_skill:
            vistas.append(Path(actual, "SKILL.md").relative_to(raiz))
    return sorted(vistas)


class IndiceHermesTests(unittest.TestCase):
    def test_hermes_solo_indexa_la_skill_raiz(self):
        self.assertEqual([Path("SKILL.md")], skills_que_ve_hermes(RAIZ))

    def test_las_plantillas_de_stack_siguen_en_el_repo(self):
        """Que no las vea Hermes no puede ser porque se perdieron al moverlas."""
        plantillas = list(stack.STACKS_DIR.glob("*/skills/*/SKILL.md"))
        self.assertGreater(len(plantillas), 100)
        self.assertTrue(stack.STACKS_DIR.is_relative_to(RAIZ / "assets"))


if __name__ == "__main__":
    unittest.main()
