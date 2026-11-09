---
name: add-api-endpoint
description: Add or modify a FastAPI serving endpoint for transformed Data Product output while preserving hexagonal boundaries.
---

# Add API Endpoint

Start from the closest existing router operation.

Inspect only the relevant HTTP schema, application query behavior, repository port and test.

HTTP/Pydantic schemas stay in the inbound HTTP adapter.

Expose canonical/transformed output data; never call an external source API directly from a serving endpoint unless the architecture explicitly requires a separate use case.

Route handlers do not access SQLAlchemy models/sessions directly.

Run the narrowest API test first.

If endpoint behavior changed, run the endpoint locally as well; tests do not replace I4 flow exercise.
