---
name: debug-targeted
description: Diagnose and fix a specific failing test, runtime exception, build failure or backend bug in this CALPIL NestJS repository.
---

# Debug Targeted

Follow `AGENTS.md`. Debug from evidence and keep the patch narrower than the investigation.

## Workflow

1. Capture the exact failing command/request, error and first relevant project frame.
2. Reproduce with the smallest deterministic case available.
3. Classify the failure boundary: HTTP/bootstrap, application, domain, persistence, external integration, configuration or delivery.
4. Maintain one primary hypothesis at a time and inspect only direct evidence needed to test it.
5. Find the earliest point where actual behavior diverges from expected behavior; fix the owner of that behavior.
6. Add a regression test that fails for the original defect when practical.
7. Rerun the reproduction first, then affected tests/build; broaden only if the fix crosses boundaries.

## Rules

- Do not patch symptoms in a downstream layer when the root cause is upstream.
- Do not add retries/timeouts/null catches without understanding the failure mode.
- Do not weaken validation, authorization, type checks or security gates to make a failure disappear.
- Do not install tools or upgrade unrelated dependencies while debugging.
- Distinguish code defects from environment/configuration failures. Never invent missing Azure/Entra/DB values.
- For intermittent failures, look for shared mutable state, uncontrolled time/randomness, async races, DB isolation and external dependencies before adding sleeps.

Report the root cause, evidence, patch and validation actually performed.
