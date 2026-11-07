---
name: prisma-migrate
description: Create and maintain PostgreSQL schema migrations in this CALPIL NestJS template using Prisma Migrate as the single schema owner.
---

# Prisma Migrate

Follow `AGENTS.md` first.

This skill governs PostgreSQL schema evolution for this repository.

## Use this skill when

Apply this skill whenever a change:

- creates or drops a table;
- adds, removes or alters a column;
- adds or changes indexes;
- adds or changes constraints;
- adds or changes PostgreSQL enums/types;
- changes defaults required at database level;
- requires data backfill tightly coupled to schema evolution.

## Do not use this skill for

Do not use this skill for changes that are purely:

- domain logic with no schema impact;
- application orchestration;
- HTTP contract/DTO updates with no persistence schema changes;
- in-memory testing setup.

## Non-negotiable ownership rule

- Prisma Migrate is the only owner of PostgreSQL DDL.
- Prisma Client is runtime persistence only.
- Never use `prisma db push` as replacement for versioned migrations.
- Never reintroduce legacy ORM migration flows (`runMigrations`, `migration:run`, `migration:generate`, `schema:sync`).

## Repository paths

- Prisma schema: `prisma/schema.prisma`.
- Prisma migrations: `prisma/migrations`.
- Migration startup runner: `src/platform/database/migration-runner.ts`.
- Shared DB config: `src/platform/database/database.config.ts`.
- CLI wrapper: `scripts/db/run-prisma-migrate.mjs`.

## Migration authoring rules

- Use descriptive names (`create-users`, `add-work-item-priority-index`).
- Do not edit already applied migrations.
- For follow-up changes, create a new migration.
- Keep SQL deterministic and idempotent for deployment workflows.

Workflow:

```bash
npm run migrate:dev -- --name <migration-name>
npm run migrate:deploy
```

## Startup and runtime behavior

- Migrations run before Nest bootstrap.
- If migration fails, app must not start.
- Do not log passwords, full connection strings with credentials, tokens or secrets.

## Commands

Use repository scripts:

```bash
npm run migrate:dev -- --name add-new-column
npm run migrate:deploy
npm run migrate:status
```

## Testing and validation

Run focused validation first:

1. migration command/status relevant to the change;
2. related tests (domain/application/controller as applicable);
3. architecture gate for schema ownership guardrails:

```bash
npm run architecture
```

4. broaden to lint/build/test as needed for cross-boundary or release-sensitive changes.

When tests do not require a real database, set:

- `DB_MIGRATIONS_ENABLED=false`

Do not weaken schema ownership rules to make tests pass.

## Definition of done

A schema change is complete only when:

- a new migration exists in `prisma/migrations`;
- migration naming is descriptive;
- startup semantics remain `MIGRATE -> NEST -> READY`;
- Prisma migration flow remains `migrate deploy` before Nest startup;
- architecture checks pass;
- relevant tests/build are green.

