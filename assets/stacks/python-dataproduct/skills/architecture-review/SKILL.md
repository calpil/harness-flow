---
name: architecture-review
description: Review the Data Product for concrete hexagonal boundary violations and technology leakage without modifying code unless requested.
---

# Architecture Review

Check:

- domain/framework independence
- application independence from adapters/frameworks
- source adapters emit raw records only
- transformations do not depend on concrete source technologies
- outbound DB adapters implement repository ports
- FastAPI/Pydantic and SQLAlchemy leakage
- serving API reads transformed/canonical output
- explicit boundary mappings
- secret/configuration boundaries

Review architecture, not cosmetic style. Report only meaningful findings with evidence, impact and smallest correction.
