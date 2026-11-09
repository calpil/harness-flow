---
name: security-review
description: Review a scoped security concern in this CALPIL NestJS web backend, including identity, authorization, input, secrets, persistence and disclosure boundaries.
---

# Security Review

Follow `AGENTS.md`. Scope the attack surface and trust boundaries first; report evidence rather than generic checklist findings.

## Review as applicable

- server-side access-token/session validation and trust boundaries;
- issuer/audience/expiry handling through the approved identity mechanism;
- explicit authorization for protected operations and resource ownership;
- path/query/body validation, unknown-field behavior and mass assignment;
- secret/token/credential handling and configuration injection;
- logs/errors for sensitive-data or stack/internal disclosure;
- CORS, cookie/session/CSRF behavior for BFF scenarios;
- parameterized database access and injection risk;
- outbound URL/input handling and SSRF-like trust issues when external calls are user-influenced;
- file upload/content handling when present;
- dependency risk relevant to the requested scope;
- security negative-path tests.

## Rules

Never invent Entra tenant/client IDs, roles, scopes, groups, secrets or Key Vault names. Do not treat authentication as authorization. Do not weaken a security gate or validation rule to make tests/build pass. Avoid logging sensitive payloads as proof.

## Output

For each finding: evidence, affected boundary, realistic impact, smallest remediation and test needed to prevent regression. Separate confirmed issues from hypotheses requiring environment/platform verification.
