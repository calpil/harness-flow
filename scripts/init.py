#!/usr/bin/env python3
"""Inicializa harness-flow en una raiz multi-repo. Idempotente.

  init.py --project ADR [--root .] [--atlassian-site x --jira-project K --confluence-space S]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import DEFAULT_RULES, now_iso  # noqa: E402

GITIGNORE = """# harness-flow
/graphify-out*
.harness.env
.env
"""

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="nombre del proyecto (raiz multi-repo)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--atlassian-site"); ap.add_argument("--jira-project")
    ap.add_argument("--confluence-space")
    ap.add_argument("--jira-issue-type", default="Story")
    a = ap.parse_args()

    root = Path(a.root).resolve()
    h = root / "harness"
    for d in (h / "progress", root / "docs" / "prd",
              root / "docs" / "vault"):
        d.mkdir(parents=True, exist_ok=True)

    backlog = h / "feature_list.json"
    if backlog.exists():
        print(f"[i]  {backlog} ya existe, no se toca")
    else:
        backlog.write_text(json.dumps(
            {"project": a.project, "rules": DEFAULT_RULES, "features": []},
            ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[ok] {backlog}")

    hist = h / "progress" / "history.md"
    if not hist.exists():
        hist.write_text(f"# Bitacora - {a.project}\n\n- {now_iso()} · proyecto inicializado\n",
                        encoding="utf-8")
        print(f"[ok] {hist}")

    if a.atlassian_site or a.jira_project or a.confluence_space:
        (h / "atlassian.json").write_text(json.dumps({
            "site": a.atlassian_site, "jira_project": a.jira_project,
            "confluence_space": a.confluence_space, "issue_type": a.jira_issue_type,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[ok] {h/'atlassian.json'} (sin credenciales, versionable)")

    gi = root / ".gitignore"
    prev = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if "graphify-out" not in prev:
        gi.write_text(prev + ("\n" if prev and not prev.endswith("\n") else "") + GITIGNORE,
                      encoding="utf-8")
        print(f"[ok] .gitignore actualizado")

    print(f"\n[ok] harness-flow listo en {root}")
    print("     Siguiente: agrega una feature con  add.py --name '<nombre>'")


if __name__ == "__main__":
    main()
