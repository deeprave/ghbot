---
name: onboard
description: >-
  Establish or refresh a repository's project guidance overlay. Use when adopting the spec workflow
  in a repository, or when its documented tools, standards, architecture, or tracker are missing.
---

# Onboard a project overlay

Create or refresh `.agents/project/` so reusable skills can load project facts without embedding
them in portable steering or workflow instructions.

## Workflow

1. Read `AGENTS.md`, `.agents/AGENTS.md`, `.agents/steering/*.md`, and any existing
   `.agents/project/` files.
2. Inspect the repository's manifest, configuration, source layout, CI configuration, and existing
   developer documentation. Record only facts supported by those sources.
3. Ask targeted questions for material facts that cannot be derived safely: product purpose,
   required quality gates, security or API invariants, and the issue tracker in use.
4. Create or update `.agents/project/README.md` as a directory map. Add only the topical files the
   repository needs, such as `product.md`, `tech.md`, `testing.md`, `security.md`,
   `api-standards.md`, and `tracking.md`.
5. Keep the portable `.agents/steering/` policy generic. Move repository facts out of steering
   rather than copying them into both locations.
6. Ensure the root `AGENTS.md` has a concise durable pointer to `.agents/AGENTS.md`; do not
   restate workflow or project documents in the root file.
7. After the project overlay exists and its README maps every project document it creates, remove
   only the `<!-- agents-onboard:start -->` through `<!-- agents-onboard:end -->` bootstrap block
   from the root `AGENTS.md`. Keep the durable `.agents/AGENTS.md` pointer.
8. Ensure the repository tracks `.agents/steering/` and `.agents/project/` rather than ignoring
   them, then validate that no workflow skill requires a project document which does not exist.

## Boundaries

- Do not invent standards, external integrations, or tracker configuration.
- Do not alter application code, dependencies, CI, or project configuration as part of onboarding.
- Project guidance documents describe durable repository facts; individual feature requirements
  belong in `.agents/specs/`.

## Next

- `analyse` — compare the overlay with the codebase when conventions may have drifted.
- `spec` — begin a feature once the project context is established.
