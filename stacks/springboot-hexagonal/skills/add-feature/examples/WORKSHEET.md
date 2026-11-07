# Vertical Slice — Definition Card


## Input card (complete before implementing)

```yaml
feature: <bounded-context>/<capability>
actor: <user-or-system>
trigger: <api-event-or-job>
preconditions: []
invariants: []
operations:
  - name: <use-case>
    command_fields: []
    result_fields: []
side_effects: [database, domain_event]
tenant_rule: <source-of-truth>
api_contract: <route-status-errors>
persistence: <tables-indexes-migrations>
rollback: <old-app-compatibility>
```

## Scenario contract

| Given | When | Then | Evidence |
|---|---|---|---|
| valid input | execute use case | persisted + domain response | unit + integration |
| invalid transition | execute update | domain exception, state unchanged | domain test |
| duplicate request | repeat same operation | idempotency behavior defined | E2E |
| tenant mismatch | request another resource | reject before data leakage | security E2E |

This is a template; each placeholder must be resolved against the story or marked assumption before implementing.
