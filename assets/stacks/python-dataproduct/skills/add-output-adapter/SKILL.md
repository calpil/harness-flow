---
name: add-output-adapter
description: Add a new output persistence adapter such as PostgreSQL, MongoDB or another governed store behind EntityRepository.
---

# Add Output Adapter

Implement the existing repository port where possible.

Keep persistence models, clients and sessions inside the outbound adapter.

Map explicitly between persisted representation and canonical/domain entity.

Do not alter the ingestion pipeline or serving API merely because the database technology changes.

Keep credentials in environment/secret configuration.

Validate repository behavior with the smallest relevant integration test.
