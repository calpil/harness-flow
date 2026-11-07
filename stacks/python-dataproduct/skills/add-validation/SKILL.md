---
name: add-validation
description: Add deterministic ingestion validation or data-quality rules before canonical persistence.
---

# Add Validation

Validation executes before transformation/persistence.

Keep rules deterministic and independent from HTTP/ORM concerns.

Distinguish transport/schema validation from business/data-quality semantics when useful.

Rejected records must remain observable and must not be silently persisted as canonical output.

Add focused unit tests for valid, invalid and boundary cases.
