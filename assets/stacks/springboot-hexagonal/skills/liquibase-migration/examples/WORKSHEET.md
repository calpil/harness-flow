# Expand-Contract Release Worksheet


| Release | DB schema | Old app reads | New app reads | Rollback app | Backfill | Evidence |
|---|---|---|---|---|---|---|
| R1 expand | new nullable columns | yes | yes | yes | pending | clean+old DB |
| R2 dual-write | both representations | yes | yes | yes | batches | replay + counts |
| R3 switch | both representations | maybe | yes | conditional | complete | data validation |
| R4 contract | old columns removed | no | yes | no unless prepared | complete | backup verified |

## SQL checks to adapt to real table

```sql
-- Only templates: replace table/column/transaction context.
SELECT count(*) AS total_rows FROM <table>;
SELECT count(*) AS missing_values FROM <table> WHERE <new_column> IS NULL;
-- Verify duplicate candidate keys before UNIQUE; avoid scanning unbounded logs with PII.
```

Before declaring rollback, identify which releases can still run against the newly migrated schema, and which SQL changes irreversibly discarded data.
