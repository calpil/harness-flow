# API Authorization / Threat-Model Worksheet


| Trust boundary | Asset | Threat | Control verified here | Negative test | Residual |
|---|---|---|---|---|---|
| Gateway → API | auth token | spoofed token/header | signature, iss, aud | invalid signature/issuer | TBD |
| API → domain use case | tenant data | IDOR/BOLA | resource ownership from trusted context | tenant crossing | TBD |
| API → vendor | API key | credential leakage | Key Vault, rotation, scope | revoked/expired | TBD |
| API → logs | PII | sensitive logging | redaction | synthetic payload | TBD |
| DB layer | records | injection/mass assignment | parameterization and allowlists | malicious filter | TBD |

## Finding ticket

```yaml
finding: SEC-<number>
severity: BLOCKER|HIGH|MEDIUM|LOW
endpoint: <method path>
proof: <sanitized request and observed response>
impact: <data/exposure>
owner: <real owner or pending>
remediation: <minimum code/config change>
negative_test: <test id>
verification_status: NOT_RUN
```

Never insert live tokens or actual personal data in this document.
