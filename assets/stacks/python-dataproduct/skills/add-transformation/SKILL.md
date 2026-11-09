---
name: add-transformation
description: Implement source-to-canonical mapping or replace the generic CanonicalTransformer with a typed Data Product transformer.
---

# Add Transformation

Keep source field semantics out of the canonical/domain model.

Transformation converts validated `RawRecord` data into governed canonical/domain entities.

Prefer a strongly typed transformer/entity for a concrete Data Product when business semantics justify it.

Do not couple the transformer to FastAPI, SQLAlchemy or a concrete source adapter.

Preserve idempotent identity semantics and explicit field mapping.

Validate mapping edge cases with focused unit tests.
