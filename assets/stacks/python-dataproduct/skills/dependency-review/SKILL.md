---
name: dependency-review
description: Evaluate a proposed Python dependency addition or upgrade before changing pyproject metadata.
---

# Dependency Review

Inspect `pyproject.toml` and only the code motivating the dependency.

Evaluate necessity, existing alternatives, Python 3.14 compatibility, maintenance maturity, license, security and runtime footprint.

All installs must remain compatible with the EA Corp Azure Artifacts policy.

Avoid opportunistic upgrades. Run targeted import/tests/type validation first.
