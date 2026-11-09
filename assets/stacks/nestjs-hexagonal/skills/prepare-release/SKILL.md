---
name: prepare-release
description: Run final release readiness checks for this CALPIL NestJS backend without deploying it.
---

# Prepare Release

Follow `AGENTS.md`. Use only for explicit release/final-gate work. This skill validates readiness; it does not deploy, tag, publish, commit or push unless separately requested.

## Release gate

1. Identify the intended release scope and changed capabilities/contracts.
2. Run `npm run validate` (which must include `npm run architecture`) and required integration/e2e checks for the changed boundaries; any architecture-gate failure is a release blocker.
3. Verify `package-lock.json` consistency and reproducible dependency install.
4. Build the production artifact/image through the repository-supported path when available.
5. Check that no secrets, tokens, real `.env` values, debug logging or local-only switches are committed.
6. Confirm TypeORM schema synchronization is not enabled for shared environments and required migrations exist.
7. Confirm public API changes are intentional/backward-compatible or have an explicit migration/version plan.
8. Confirm health endpoints, runtime configuration and workload metadata remain valid.
9. Treat SAST/SCA/image/deployment gates as authoritative; report failures rather than bypassing them.
10. Summarize blockers, warnings and evidence actually validated.

Do not claim release readiness for checks that could not be run; identify the exact missing platform/environment validation.
