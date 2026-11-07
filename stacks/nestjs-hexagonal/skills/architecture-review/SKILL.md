---
name: architecture-review
description: Review this CALPIL NestJS backend for concrete architecture, modularity and boundary violations without changing code unless requested.
---

# Architecture Review

Follow `AGENTS.md`. Review evidence, not aesthetics. Inspect only enough code to prove or disprove each concern.

## Review sequence

1. Identify capabilities/modules and their public dependencies.
2. Trace representative inbound flows: controller -> use case -> domain/outbound port -> adapter.
3. Search for dependency-direction violations and cross-capability shortcuts.
4. Review platform/shared code for accidental business ownership.
5. Check whether complexity (microservices, events, CQRS, generic abstraction) has a concrete requirement.
6. Review tests to see whether architecture boundaries are actually protected by behavior.
7. When the review includes architecture-relevant code changes or executable verification, run `npm run architecture`; treat each failing dependency as review evidence, not as a tool false positive to waive away.

## Findings to look for

Treat dependency-direction violations as architecture defects even when runtime behavior is correct. The expected direction is `adapter/in -> application -> domain`, while `adapter/out` implements contracts owned by `application/ports/out`; Nest module wiring is the composition root.

- NestJS/HTTP/Express/class-validator leakage into domain/application;
- TypeORM entities/repositories imported inward;
- controllers calling persistence/external SDKs directly;
- domain rules implemented in controllers/repositories;
- DTO/ORM models crossing boundaries as universal models;
- capabilities reaching into another capability's adapter internals;
- generic `common/utils` dumping grounds with unclear ownership;
- cross-cutting platform concerns duplicated in features;
- unbounded repository/API reads;
- hidden transaction/concurrency assumptions;
- unjustified microservice/event/CQRS abstractions.

## Output

Classify only evidence-backed findings as `BLOCKER`, `IMPORTANT` or `IMPROVEMENT`. For each finding provide file/symbol evidence, why the boundary matters and the smallest corrective direction. Do not grade formatting/naming taste as architecture. Note strengths only when they materially explain why a suspected issue is not a violation.

Do not rewrite code during a review unless explicitly asked.
