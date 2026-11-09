---
name: dependency-review
description: Evaluate, add, remove or update an npm dependency in this CALPIL NestJS backend.
---

# Dependency Review

Follow `AGENTS.md`. Dependencies are an architecture and supply-chain decision, not just a package.json edit.

## Before adding

State the concrete capability missing today. Check whether Node 24, NestJS, an existing package or an approved platform capability already solves it. Prefer no new dependency when the local implementation is small, obvious and safer.

## Evaluate

- exact use and owning boundary;
- runtime vs dev-only placement;
- Node 24 / NestJS / TypeScript compatibility;
- maintenance/release posture and known security concerns from available project tooling;
- transitive/runtime footprint;
- licensing/organizational policy when relevant;
- whether it leaks framework/vendor types into domain/application contracts;
- whether it duplicates an existing capability;
- lockfile/install reproducibility.

## Change rules

Make the smallest dependency change. Do not bundle unrelated upgrades or mass-refresh the lockfile. Never add a package solely to avoid writing a few clear lines of code or tests. Do not install global tools as part of repository behavior.

After changing dependencies, update the lockfile intentionally, run the relevant tests/build and verify a clean `npm ci` path when practical. Security or compatibility failures are reported; do not suppress them to land the package.
