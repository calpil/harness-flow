---
name: add-persistence
description: Add or change PostgreSQL/Prisma persistence, repository ports, mappings, queries, transactions or schema evolution in this CALPIL NestJS backend.
---

# Add Persistence

Follow `AGENTS.md`. Persistence is an outbound adapter serving an application need; do not let the database schema become the domain model by accident.

Schema ownership policy:

- Prisma Migrate owns PostgreSQL schema evolution.
- Prisma Client is runtime persistence only.
- Never use `prisma db push` as the template standard for shared environments.

## Workflow

Hexagonal boundary: persistence is an **outbound adapter**. The application owns the outbound port; the platform adapter implements it with Prisma. Never define an application contract in terms of Prisma types, filters or database-specific exceptions.

1. Start from the use case and identify the persistence behavior actually required: save, lookup, bounded list, aggregate query, transaction, lock, etc.
2. Define/reuse the smallest outbound application port that expresses that need.
3. Implement Prisma details under `adapter/out/persistence`.
4. Keep explicit mapping between ORM records and domain/application models.
5. Add/modify migrations for schema evolution. Shared environments never rely on `synchronize`.
6. Add integration tests when correctness depends on PostgreSQL/Prisma semantics.
7. Validate query behavior and rollout implications before declaring the change complete. When the change touches dependencies, modules, ports, adapters or persistence structure, run `npm run architecture` and fail on any violation.

## Data rules

- PostgreSQL is the default transactional backend. MongoDB requires an explicit data/access-model reason.
- Use repository/query APIs with parameter binding; no string-concatenated SQL from untrusted input.
- Keep reads bounded and deterministic. Define pagination/order when result ordering matters.
- Avoid N+1 patterns; load only the relationships/data required by the use case.
- Add indexes for demonstrated access paths/constraints, not speculation.
- Use database constraints where they protect durable invariants that must hold across processes.
- Do not expose Prisma records/models beyond the persistence adapter.

## Transactions and concurrency

Place transaction boundaries around the business operation that must be atomic. Do not open transactions in controllers. When correctness depends on concurrent updates, make the concurrency strategy explicit (constraint, optimistic version, lock, idempotency, etc.) and test it at the database boundary.

## Schema changes

Prefer backward-compatible expand/migrate/contract changes for live systems. Destructive/renaming changes require an explicit rollout plan. Never silently drop columns/data or assume all environments can be rebuilt.

## Tests

Do not mock Prisma when the purpose is proving mappings, queries, constraints or transactions. Use PostgreSQL through the established integration harness; never point automated tests at shared `sb`, `np` or prod data.
