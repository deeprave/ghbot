---
name: onboard
description: >-
  Establish or refresh a repository's project guidance overlay. Use when adopting the spec workflow
  in a repository, or when its documented tools, standards, architecture, or tracker are missing.
---

# Onboard a project overlay

Create or refresh `.agents/project/` from the shared templates in
`~/.agents/project-templates/`. The resulting repository-local documents are authoritative project
facts for reusable skills; templates are only onboarding inputs.

## Workflow

1. Read `AGENTS.md`, `.agents/AGENTS.md`, `.agents/steering/*.md`, every existing
   `.agents/project/` document, and every template in `~/.agents/project-templates/`.
2. Inspect the repository's manifest, configuration, source layout, CI configuration, and existing
   developer documentation. Prepare evidence-backed defaults, but do not treat inference as fact.
3. Before writing, ask the user targeted, grouped questions for each template topic. Confirm or
   correct the observed defaults for:
   - product purpose, users, scope, and durable constraints;
   - languages, versions, frameworks, package/build management, architecture, dependencies, and
     implementation conventions;
   - issue tracking, connector, authentication, identifiers, links, and project scope;
   - test frameworks, organisation, methods, quality gates, and coverage expectations;
   - credentials, tokens, secret handling, sensitive code, and application-security requirements;
   - logging format, destinations, levels, PII, redaction, and retention; and
   - inbound and outbound APIs, authentication, validation, pagination, rate limits, retries,
     error policy, and data handling.
4. Create or refresh all template-backed documents in `.agents/project/`: `README.md`,
   `product.md`, `tech.md`, `tracking.md`, `testing.md`, `security.md`, `logging.md`, and
   `api-standards.md`. Replace template prompts with user-confirmed or source-supported facts. If a
   fact remains unknown, say that it is not established rather than inventing it.
5. Ensure the README identifies these documents as authoritative and maps each one.
6. Keep the portable `.agents/steering/` policy generic. Move repository facts out of steering
   rather than copying them into both locations.
7. Ensure the root `AGENTS.md` has a concise durable pointer to `.agents/AGENTS.md`; do not
   restate workflow or project documents in the root file.
8. After the project overlay exists and its README maps every project document it creates, remove
   only the `<!-- agents-onboard:start -->` through `<!-- agents-onboard:end -->` bootstrap block
   from the root `AGENTS.md`. Keep the durable `.agents/AGENTS.md` pointer.
9. Ensure the repository tracks `.agents/steering/` and `.agents/project/` rather than ignoring
   them. Validate that all eight documents exist, the README maps them, and no copied document
   retains a template prompt.

## Boundaries

- Do not invent standards, external integrations, or tracker configuration.
- Do not alter application code, dependencies, CI, or project configuration as part of onboarding.
- Project guidance documents describe durable repository facts; individual feature requirements
  belong in `.agents/specs/`.
- Preserve supported local content when refreshing an existing overlay. Do not replace established
  facts with generic template text.

## Next

- `analyse` — compare the overlay with the codebase when conventions may have drifted.
- `spec` — begin a feature once the project context is established.
