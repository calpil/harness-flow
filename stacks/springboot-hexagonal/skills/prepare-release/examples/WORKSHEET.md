# Release Go/No-Go Checklist


```yaml
source_sha: PENDING
release_version: PENDING
docker_image_digest: PENDING
change_owner: PENDING
target_environment: PENDING
quality_gates:
  maven_verify: NOT_RUN
  archunit: NOT_RUN
  jacoco: NOT_RUN
  spotless: NOT_RUN
  security_sast_sca_iac: NOT_RUN
  postgres_integration: NOT_RUN
operational:
  rollback_app: PENDING
  db_rollback_or_forward_fix: PENDING
  feature_flags: []
  alerts: PENDING
  smoke_api_authenticated: NOT_RUN
  go_no_go_approver: PENDING
```

No-go if critical gates are blocked or failures are unmitigated. A release checklist is not authorization to deploy.
