---
name: write-tests
description: Add focused pytest coverage for ingestion, validation, transformation, FastAPI serving or output persistence.
---

# Write Tests

Choose the lowest test level that proves the behavior.

- ingestion/validation/transformation -> `tests/unit`
- FastAPI -> `tests/api`
- DB repository -> `tests/integration`

Reuse existing fixtures/style. Keep tests deterministic. Do not weaken production behavior to simplify a test.

Run the affected test file first.

Tests are I3 evidence. When behavior changes, coordinate with a separate I4 local flow exercise instead of treating the test as a full substitute.
