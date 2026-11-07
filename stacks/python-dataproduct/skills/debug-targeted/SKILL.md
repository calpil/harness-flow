---
name: debug-targeted
description: Diagnose a specific test, import, ingestion, API, source or persistence failure with minimal evidence-driven investigation.
---

# Targeted Debugging

1. Read the exact failure.
2. Identify the first relevant repository frame/symbol.
3. Inspect that implementation and its closest caller/dependency.
4. Reproduce with the smallest command.
5. Apply the smallest root-cause fix.
6. Re-run the reproducer; broaden validation only if required.

If the fix changes runtime behavior, exercise the real local flow separately after the focused reproducer passes.

Do not begin with repository-wide exploration or unrelated refactoring.
