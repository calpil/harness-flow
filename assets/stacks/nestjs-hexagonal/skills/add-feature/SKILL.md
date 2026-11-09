---
name: add-feature
description: Implement a scoped business capability in this CALPIL NestJS backend while preserving capability-oriented hexagonal architecture.
---

# Add Feature

Follow `AGENTS.md`. Build the smallest complete vertical slice that satisfies the requested business behavior.

## Workflow

1. Identify the owning business capability and inspect the closest analogous feature before creating structure.
2. Write down the behavior, inputs, outputs, business rules, errors and external dependencies implied by the request.
3. Choose only the layers the behavior actually needs:
   - `domain/` for real invariants/state/value behavior;
   - `application/ports/in` for the use-case contract when an explicit contract is useful;
   - `application/services` for orchestration;
   - `application/ports/out` for external dependencies;
   - `adapter/in` for HTTP/transport concerns;
   - `adapter/out` for persistence/integrations.
4. Implement inward-out: domain/application contracts before adapters where practical.
5. Wire the capability through its Nest module. Keep framework wiring at the edge.
6. Add tests at every changed behavior boundary, using `write-tests` guidance.
7. Run focused validation, including `npm run architecture` whenever the change touches dependencies, modules, ports, adapters, persistence, controllers or capability structure; then broaden only if multiple boundaries changed.

## Design rules

- Dependency direction is non-negotiable: `adapter/in -> application -> domain`; outbound adapters implement `application/ports/out`. Application/domain never import adapters.
- Nest module wiring is the composition root. It may know concrete adapters; the use case must depend on port tokens/contracts rather than concrete repositories/SDK clients.
- Prefer a modular monolith organized by capability. Do not create a new microservice because the feature is new.
- Do not manufacture DDD objects, ports or interfaces for CRUD ceremony. Use domain modeling when business rules justify it.
- Controllers do not contain business rules or call repositories directly.
- Application services do not depend on HTTP/Nest transport types or Prisma/ORM persistence records.
- Cross-capability access must be explicit. Do not reach into another capability's adapter internals.
- External calls and persistence stay behind outbound ports when they participate in application behavior.
- Keep public contracts stable unless changing them is part of the request.
- Do not introduce generic `common`, `helpers` or `utils` abstractions without a clear owner and repeated need.

## Error handling

Define errors where the rule is owned. Domain invariant errors belong in domain; application coordination/not-found errors may belong in application/domain depending on the established pattern. Transport adapters map those errors to the shared Problem Details contract; they do not invent alternate envelopes.

## Definition of done

The feature is complete when the requested behavior works end-to-end through the required boundaries, tests prove success and meaningful negative paths, module wiring is explicit, no framework/persistence concern leaked inward, and focused validation is green.
