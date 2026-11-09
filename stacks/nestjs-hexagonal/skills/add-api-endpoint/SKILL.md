---
name: add-api-endpoint
description: Add or modify a REST endpoint in this CALPIL NestJS backend, including HTTP DTOs, validation, response mapping, errors and endpoint tests.
---

# Add API Endpoint

Follow `AGENTS.md`. Treat the endpoint as a transport contract over an application use case, not as the place to implement business behavior.

## Contract first

Before editing the controller, identify:

- HTTP method and versioned path;
- path/query/body fields and validation constraints;
- success status and response shape;
- pagination semantics when applicable;
- authorization requirement;
- expected domain/application errors and their Problem Details mapping;
- idempotency expectations for commands when relevant.

Preserve an existing public contract unless the request explicitly changes it.

## Implementation

Hexagonal boundary: the controller is an **inbound adapter**. It may depend on an inbound application port/use-case contract, but it must never call `adapter/out`, Prisma repositories/adapters or external SDKs directly.

1. Inspect the nearest endpoint and existing use-case contract.
2. Reuse an existing use case when it already represents the behavior. Do not push orchestration into the controller.
3. Keep request DTOs transport-only and validate untrusted path/query/body input.
4. Use the repository's shared global app configuration; do not add endpoint-local validation conventions that conflict with it.
5. Map application/domain results explicitly to stable response DTOs/objects. Never return ORM entities.
6. Keep controllers thin: translate request -> invoke one use case -> map response.
7. Route errors through the shared Problem Details mechanism. Do not catch broad exceptions in controllers to manufacture `200`/custom error payloads.
8. Keep collection reads bounded. Do not add unbounded `findAll` HTTP endpoints.

## Security

- Authentication extraction belongs at inbound/platform boundaries.
- Authorization must be explicit when required; authentication alone is not authorization.
- Never trust identity/role fields supplied in request bodies when they should come from the authenticated principal.
- Do not expose secrets, internal exception details or unnecessary personal data in responses/errors.

## Tests

Use `INestApplication` + `supertest` and the same shared app configuration as production. Test the representative success path and applicable invalid UUID/query/body, unknown fields, unauthorized/forbidden, not-found, conflict or invariant-error mappings. Stub the inbound use-case port, not controller internals.

## Definition of done

Apply `swagger-contract skill (.agents/skills/swagger-contract/ o .claude/skills/swagger-contract/)` before considering the endpoint complete.

The endpoint has an explicit contract, thin controller, validated input, explicit response mapping, shared error behavior, required authz, focused HTTP tests, updated OpenAPI contract checks and green focused validation. When the change touches controllers, ports, adapters, use-case wiring or module composition, run `npm run architecture` and treat any violation as blocking.
