---
name: observability-change
description: Add or modify backend logging, correlation, health, metrics or tracing in this CALPIL NestJS service.
---

# Observability Change

Follow `AGENTS.md`. Every telemetry change should answer an operational question; avoid telemetry for telemetry's sake.

## Start with the question

Identify what an operator needs to know: request tracing, dependency latency/failure, readiness, business-operation failure rate, queue/backlog, etc. Choose the smallest signal that answers it.

## Logging

- Use the approved structured logger/platform mechanism; no production `console.log` scatter.
- Preserve correlation/request context across supported boundaries.
- Log stable event names/fields rather than prose-only messages where possible.
- Never log access tokens, secrets, credentials, authorization headers or unnecessary personal data.
- Expected domain failures are not automatically error-level incidents.

## Health

- Liveness proves the process can run and stays independent of downstream dependencies.
- Readiness may check dependencies required to serve traffic, with bounded timeouts.
- Keep health contracts stable for Kubernetes/platform probes.

## Metrics/tracing

Add metrics or spans only for a concrete SLO, capacity or diagnostic question. Avoid high-cardinality labels such as user IDs, request bodies or arbitrary URLs. Bound external dependency timeouts/retries and ensure tracing does not leak sensitive payloads.

## Tests

Test stable behavior/configuration boundaries, not the internals of a logging SDK. Health behavior, correlation propagation and redaction rules should have focused tests when changed.
