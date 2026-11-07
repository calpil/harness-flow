---
name: write-tests
description: Design, add or repair tests for domain, application, HTTP, persistence or end-to-end behavior in this CALPIL NestJS backend.
---

# Write Tests

Follow `AGENTS.md`. Treat tests as executable behavioral contracts, not as a coverage exercise.

## 1. Start from the behavior

Before writing a test, identify:

- the behavior or defect being proved;
- the owning boundary: domain, application, HTTP, persistence, integration or e2e;
- the observable result;
- the meaningful failure modes;
- the lowest-cost test that can prove those facts.

Do not start by mocking classes or copying an existing spec. If the requested behavior is already fully proven by an existing test, extend it only when the new case adds information.

For bug fixes, reproduce the defect with a failing regression test first when practical, then make the smallest production change that makes it pass.

## 2. Choose the correct test boundary

Tests must reinforce the hexagon rather than bypass it. A test setup that requires domain/application code to import NestJS, TypeORM or adapters is evidence of a boundary problem, not a reason to weaken the architecture. HTTP tests stub inbound application ports; application tests fake outbound ports; persistence tests exercise outbound adapters.

### Domain unit test
Use for invariants, state transitions, value rules and deterministic business behavior.

- Instantiate domain objects directly; no Nest testing module.
- Do not mock the entity/value object under test.
- Prove allowed behavior and prohibited behavior.
- Assert the domain-specific error type when one exists; do not assert only `toThrow()` if the error contract matters.
- Include idempotency/boundary values where they are part of the rule.

### Application unit test
Use for use-case orchestration and interaction with outbound ports.

- Instantiate the application service directly whenever Nest DI is not the behavior under test.
- Replace outbound ports with small typed fakes/stubs/mocks.
- Verify returned behavior/errors and only the dependency interactions that are part of the use-case contract.
- Do not mock domain behavior just to make orchestration easier.
- Cover not-found/conflict/authorization branches when the use case owns them.

### HTTP/API test
Use for routing, request validation, transport mapping, authorization boundary, status code, headers and Problem Details.

- Use Nest testing utilities plus `supertest` against an `INestApplication`.
- Configure the test application through the same shared app configuration used by production bootstrap. Do not hand-create a weaker ValidationPipe/filter setup.
- Stub the inbound use-case port, not the controller internals.
- Exercise the real route including the global `/api/v1` prefix when applicable.
- Assert status plus the stable response fields that are part of the API contract.
- Test validation for path/query/body, including unknown fields when the global contract forbids them.
- Test relevant `401`, `403`, `404`, `409`, `422` or other Problem Details mappings when the endpoint can produce them.
- Do not snapshot entire error payloads if a few stable contract fields prove the behavior better.
- If the change affects the public HTTP contract, include/adjust OpenAPI contract verification (for example via `npm run openapi:check` or focused structural OpenAPI tests) in the same change.

### Persistence integration test
Use when correctness depends on PostgreSQL/TypeORM behavior: mappings, SQL semantics, constraints, transactions, locking, migrations or query shape.

- Exercise the real persistence adapter against PostgreSQL using the repository's existing integration-test harness.
- Do not replace PostgreSQL with SQLite when PostgreSQL semantics are material.
- Do not mock TypeORM in a test whose purpose is to prove a TypeORM mapping/query.
- Isolate test data and clean it deterministically.
- Prove both mapping directions when custom mapping exists.
- Include relevant uniqueness/foreign-key/transaction rollback behavior.
- Never point automated tests at shared `sb`, `np` or production databases.
- Do not add Testcontainers or another infrastructure dependency unless the repository/platform has chosen that pattern or the user explicitly requests it.

### End-to-end test
Use sparingly for behavior that genuinely crosses runtime boundaries and is not already proven more cheaply.

- Prefer a small set of critical journeys over duplicating every unit/API case.
- Use real module wiring for the behavior being proven.
- Keep external systems controlled through approved test doubles or dedicated test dependencies.
- Never use e2e as a substitute for missing domain/application tests.

## 3. Minimum case selection

For changed behavior, consider this matrix and include only applicable cases:

1. one representative success path;
2. boundary values and state transitions;
3. invalid/malformed input;
4. missing resource;
5. conflict/invariant violation;
6. missing identity and forbidden identity for protected operations;
7. outbound dependency failure only when the application owns a defined response to it;
8. regression case for the bug being fixed.

Do not mechanically test every permutation. Prefer cases that distinguish one business or contract rule from another.

## 4. Test design rules

- Use Arrange / Act / Assert structure, visually separated when the test is non-trivial.
- Name tests after behavior: `rejects TODO -> DONE`, not `test changeStatus`.
- Keep one primary reason to fail per test.
- Prefer typed fixture builders/factories once setup becomes repetitive; do not create a generic testing framework for two tests.
- Keep tests deterministic. Do not depend on wall-clock timing, test order, random data or network availability.
- For time-sensitive behavior, inject/control time if the production design supports it; otherwise assert ranges/relative behavior rather than sleeping.
- For generated IDs, assert contract/shape or use rehydrated fixed objects when the exact ID is not the behavior.
- Always `await` async expectations. Do not leave unresolved promises or fire-and-forget calls.
- Restore fake timers/spies/environment mutations in teardown.
- Never log secrets, access tokens or real credentials in fixtures.
- Avoid `any` in test doubles where the real port type is available.
- Prefer explicit objects over giant fixtures containing irrelevant fields.

## 5. Mocking policy

Mock only at a boundary that the test intentionally does not exercise.

Good examples:

- application test -> mock/fake outbound repository port;
- HTTP test -> mock/fake inbound use-case port;
- external API adapter test -> stub the external HTTP client boundary.

Bad examples:

- mocking the domain entity in a domain test;
- mocking `ValidationPipe` in an HTTP contract test;
- mocking TypeORM in a PostgreSQL mapping test;
- mocking so many collaborators that no production behavior remains.

Prefer a small in-memory fake when stateful behavior makes assertions clearer than a collection of `jest.fn()` calls. Use `jest.fn()` when call/argument verification itself is meaningful and simple.

## 6. Assertions and contracts

Assert the smallest stable surface that proves the behavior.

- Domain: resulting state, returned value, domain error type.
- Application: result/error and meaningful port calls/arguments.
- HTTP: status, response contract, relevant headers, Problem Details fields.
- Persistence: persisted/reloaded state, query semantics, constraints/transaction outcome.

Do not couple tests to private methods, local variable names, Nest implementation internals, SQL generated text or incidental call ordering unless that ordering is itself required behavior.

Coverage percentage is a signal, not the goal. Never add meaningless assertions or tests only to raise coverage.

## 7. Validation workflow

Run progressively:

1. the single changed spec/test name;
2. the related spec file;
3. the affected boundary/feature test set;
4. if the testing task also changes architecture-relevant production files (dependencies, modules, ports, adapters, persistence, controllers or capability structure), run `npm run architecture` before finalizing;
5. `npm run validate` only for cross-cutting/final-gate work or when requested.

Typical commands:

```bash
npm test -- test/work-item.domain.spec.ts
npm test -- test/work-item.controller.spec.ts -t "rejects unknown fields"
npm run validate
```

If a required integration dependency is unavailable, do not silently replace it with a weaker test. Report what could be run and the exact command/environment needed to complete validation.

## 8. Definition of done

A testing task is complete when:

- the intended behavior is proven at the correct boundary;
- meaningful negative/regression paths are covered;
- the test would fail for the defect or contract break it is intended to catch;
- the test does not depend on implementation details unnecessarily;
- focused validation passes;
- no unrelated production refactor or new dependency was introduced just to make testing convenient.
