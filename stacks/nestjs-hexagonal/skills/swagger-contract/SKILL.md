---

name: swagger-contract
description: Maintain the NestJS Swagger/OpenAPI contract whenever creating or changing controllers, HTTP endpoints, request/response DTOs, parameters, status codes, errors, authentication, authorization, or API versioning. Apply automatically to every public HTTP API contract change.
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Swagger Contract

Follow `AGENTS.md` first.

This skill ensures that every public HTTP API change keeps the generated Swagger/OpenAPI contract accurate.

Swagger/OpenAPI is part of the implementation.

It is not optional documentation.

An endpoint change is incomplete until its OpenAPI contract is correct and validated.

## Use this skill when

Apply this skill whenever a change:

* creates an HTTP endpoint;
* removes an HTTP endpoint;
* modifies a controller;
* changes an HTTP method;
* changes a route/path;
* changes a request DTO;
* changes a response DTO;
* adds/removes/changes a path parameter;
* adds/removes/changes a query parameter;
* changes a request body;
* changes a response body;
* changes an HTTP status code;
* changes a public error response;
* changes authentication requirements;
* changes authorization exposure;
* changes API versioning;
* changes upload/download behavior.

Also apply this skill whenever `add-api-endpoint` is used.

## Do not use this skill for

Do not apply Swagger concerns to changes that are purely:

* domain logic;
* application use cases with no HTTP contract impact;
* persistence;
* outbound adapters;
* internal refactoring that leaves the public HTTP contract unchanged.

Do not add Swagger dependencies to non-HTTP layers.

## Architecture boundary

`@nestjs/swagger` may appear only in HTTP/delivery/bootstrap code.

Allowed conceptually:

```text
adapter/in/http
controllers
HTTP request DTOs
HTTP response DTOs
bootstrap
Swagger configuration
```

Forbidden:

```text
domain
application
application ports
adapter/out
persistence
external-service adapters
```

Never decorate domain entities with Swagger decorators.

Never make application-layer models depend on Swagger.

Map application/domain results into HTTP response DTOs where needed.

## First inspect the contract

Before editing documentation, inspect the actual implementation:

1. controller;
2. route;
3. HTTP method;
4. guards;
5. request DTO;
6. response DTO;
7. status code;
8. exception mapping;
9. global API prefix/version;
10. analogous existing endpoint.

Swagger must describe reality.

Never modify runtime behavior merely to make documentation convenient.

## Controller requirements

Every public controller should have an appropriate:

`@ApiTags(...)`

Protected controllers/endpoints must document the configured bearer security scheme.

Use the repository's existing security-scheme name.

Do not invent a second Bearer scheme.

## Operation requirements

Every public operation must have enough information for a consumer to understand it.

Use:

`@ApiOperation(...)`

when the operation cannot be clearly represented by generated metadata alone.

Use concise action-oriented summaries.

Good:

```text
Create work item
Get work item status
List managed groups
Assign user to group
```

Bad:

```text
Get data
Endpoint
API operation
Process request
```

## Request DTOs

Request DTOs remain normal NestJS/class-validator DTOs.

The repository uses the Nest Swagger CLI plugin.

Do not add `@ApiProperty()` mechanically to every field.

Let the plugin infer ordinary properties from:

* TypeScript types;
* optional markers;
* arrays;
* enums where supported;
* class-validator metadata.

Use explicit Swagger property decorators only when needed for information the plugin cannot infer adequately.

Examples:

* description;
* meaningful example;
* format;
* polymorphism;
* ambiguous type;
* special enum representation.

Runtime validation still requires the appropriate `class-validator` decorators.

Swagger is not validation.

## Mapped types

When an HTTP Swagger DTO uses:

* `PartialType`
* `PickType`
* `OmitType`
* `IntersectionType`

use the Swagger-compatible mapped type from:

`@nestjs/swagger`

when required by repository conventions.

Do not import a variant that causes the generated OpenAPI schema to lose metadata.

## Path parameters

Ensure path parameters appear correctly in OpenAPI.

Use explicit `@ApiParam()` where metadata/description is insufficient.

Verify:

* name;
* type;
* required behavior;
* description;
* enum where relevant.

The documented parameter name must match the actual route exactly.

## Query parameters

Ensure query parameters appear correctly.

Prefer typed query DTOs when that is the repository standard.

Verify:

* optional vs required;
* primitive type;
* enum;
* arrays;
* pagination;
* filtering;
* sorting.

Do not document query parameters that the implementation ignores.

## Request body

Ensure request body schema matches the actual accepted DTO.

Do not manually duplicate DTO schemas in `@ApiBody()` unless required.

When special content types are used, document them explicitly.

Examples:

* multipart/form-data;
* binary;
* text.

## Success response

Every endpoint must document its actual successful response.

Use appropriate response decorators such as:

```text
@ApiOkResponse
@ApiCreatedResponse
@ApiAcceptedResponse
@ApiNoContentResponse
```

Specify the actual response DTO when a body exists.

Do not use domain entities as Swagger models merely for convenience.

## Error responses

Document expected public errors.

Use the repository's standard HTTP error schema.

Common responses may include:

```text
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
422 Unprocessable Entity
429 Too Many Requests
500 Internal Server Error
502 Bad Gateway
503 Service Unavailable
504 Gateway Timeout
```

Only document statuses that can actually occur through the endpoint/application boundary.

Do not blindly copy every possible status onto every endpoint.

Do not expose infrastructure exception structures.

## Authentication

If an endpoint requires authentication, ensure OpenAPI indicates Bearer authentication.

Swagger documentation never replaces runtime guards.

Do not change:

* guards;
* issuer validation;
* audience validation;
* role checks;

solely for documentation.

## Authorization

If an endpoint has a meaningful authorization boundary, document it briefly.

Example:

```text
Requires application administrator role.
```

Do not leak internal policy implementation details.

Do not claim authorization rules that the application does not enforce.

## Empty responses

If the endpoint returns `204 No Content`, document exactly that.

Do not attach a response body schema to 204 responses.

## Collections

Document array response types correctly.

Do not let an array endpoint appear as a single object.

## Pagination

If pagination exists, ensure the OpenAPI contract reflects:

* page/cursor request;
* page size/limit;
* response metadata;
* collection type.

Reuse repository pagination contracts.

## Enums

Make public enums visible as actual OpenAPI enum constraints.

Do not document arbitrary strings when the API only accepts known values.

## Examples

Examples must be:

* synthetic;
* safe;
* representative.

Never put in Swagger examples:

* production user emails;
* real customer data;
* access tokens;
* tenant secrets;
* real credentials;
* sensitive IDs unnecessarily.

## Correlation ID

If the HTTP API exposes or accepts the repository's correlation ID header, keep Swagger consistent with that contract.

Do not invent another header.

## Files

For uploads/downloads verify:

* content type;
* `@ApiConsumes`;
* request body schema;
* binary response;
* `Content-Disposition` where relevant.

Do not force binary data through JSON schemas.

## Check generated contract

After modifying the API run the repository OpenAPI check.

Prefer:

```bash
npm run openapi:check
```

if available.

Otherwise use the repository's documented equivalent.

OpenAPI generation must succeed.

## Tests

For every changed API boundary, add/update tests that prove the contract where appropriate.

Do not snapshot the entire OpenAPI JSON unless the repository explicitly uses that strategy.

Prefer structural assertions.

Verify changed behavior such as:

* path exists;
* HTTP method exists;
* request schema exists;
* response schema exists;
* relevant status exists;
* security requirement exists;
* parameter exists;
* enum/schema constraint exists.

Apply the `write-tests` skill for behavior changes.

## Contract drift

If the repository commits generated OpenAPI output:

regenerate it.

The generated artifact must not remain stale.

If CI uses drift detection, ensure:

```text
OpenAPI source
    =
generated OpenAPI
```

before completing the task.

## Generated SDK impact

If the repository generates a client SDK from OpenAPI, an API contract change may require SDK regeneration.

Follow the repository SDK workflow.

Do not manually edit generated SDK models.

The correct direction is:

```text
HTTP contract
    ↓
OpenAPI
    ↓
generated client
```

Never:

```text
generated client
    ↓
manual backend contract
```

## Architecture validation

If Swagger imports or DTO placement changed architecture-sensitive code, run:

```bash
npm run architecture
```

or the repository's current architecture validation command.

No `@nestjs/swagger` import may leak into domain/application/outbound layers.

## Required validation

Before declaring an API change complete, run all applicable commands:

```text
format
lint
typecheck
relevant tests
OpenAPI generation/check
architecture validation when applicable
build
```

Use the repository's aggregate validation command when available.

Do not:

* skip failing tests;
* weaken TypeScript;
* suppress architecture failures;
* claim success without actual results.

## Definition of Done

An API change is complete only when:

* runtime implementation is correct;
* request DTO is correct;
* response DTO is correct;
* validation is correct;
* controller documentation is correct;
* success response is documented;
* relevant error responses are documented;
* authentication documentation matches runtime behavior;
* path/query parameters are documented;
* generated OpenAPI succeeds;
* affected OpenAPI tests pass;
* SDK is regenerated when applicable;
* architecture boundaries remain valid.

## Final report

When this skill is applied, include in the completion report:

```text
Swagger/OpenAPI:
- endpoints added/changed
- schemas added/changed
- security documentation
- responses documented
- OpenAPI validation result
- SDK regeneration result, if applicable
```

Never report the Swagger contract as updated unless generation/tests actually succeeded.
