---
name: add-source-adapter
description: Add a new file, database, API, object-storage or other ingestion source while preserving the source-agnostic ingestion pipeline.
---

# Add Source Adapter

Implement only acquisition/transport concerns in `adapters/inbound/sources`.

The adapter must implement the `DataSource` contract and emit `RawRecord` values.

Do not add canonical mapping, business validation or output persistence to the adapter.

Reuse an existing source implementation pattern before creating new abstractions.

Add a dependency only if the protocol genuinely requires it.

Validate with a targeted source/ingestion test first.
