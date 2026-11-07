# AKS / API Incident Runbook


## Identify blast radius

- Date/time and environment: ______
- Image digest / release: ______
- Namespace/cluster (authorized): ______
- Affected path/template and consumer: ______
- Symptom and SLO/SLI baseline: ______

## Triage sequence

1. Recent deployments and config change → compare actual image digest/chart values.
2. Readiness/liveness, restarts, CPU/memory/connection pools.
3. Logs by correlation ID (redacted), trace latency breakdown, 5xx/4xx classification.
4. PostgreSQL locks/pool pressure and external API errors/timeouts.
5. Mitigate: traffic switch/flag/scale/rollback/forward fix with owner approval.
6. Validate recovery against prior symptom and collect postmortem actions.

**Do not** rely on liveness failing because Postgres is temporarily unavailable; that causes cascading restarts.
