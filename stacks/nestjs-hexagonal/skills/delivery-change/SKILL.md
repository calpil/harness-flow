---
name: delivery-change
description: Modify Docker, Azure DevOps pipeline or CALPIL workload metadata for this NestJS backend.
---

# Delivery Change

Follow `AGENTS.md`. Delivery files are platform contracts; application repositories should consume shared platform capabilities rather than reimplement them.

## Before changing

Identify which concern owns the requested change: build, test/security gate, image creation, registry/promotion, deployment metadata, runtime configuration or environment wiring. Inspect the existing shared-template usage first.

## Rules

- Target the repository-supported Node 24 runtime.
- Use `npm ci` with the committed lockfile.
- Prefer approved CALPIL base images and shared Azure DevOps templates when already available.
- Keep SAST/SCA/dependency scanning before build/promotion according to platform policy; never add a bypass by assumption.
- Build immutable OCI images. Keep runtime images minimal and non-root when the base/platform supports it.
- Do not bake environment configuration, secrets or credentials into source/image layers.
- Do not invent ACR, subscription, resource group, service connection, DNS, Key Vault, identity, namespace or environment values.
- Keep application pipeline logic independent of one developer workstation; do not require local Azure CLI/Terraform assumptions.
- Preserve artifact traceability from source/build to promoted image.
- Environment promotion should reuse the same built artifact rather than rebuild different bits per environment when the platform template supports that model.

## Validation

Validate the changed YAML/Docker contract, dependency install reproducibility and application build/test surface needed to prove it. Report platform-dependent checks that cannot be executed locally rather than replacing them with guessed values.
