---
name: onboard
specle_group: Setup
description: >-
  Establish or refresh a repository's project guidance overlay.
usage: >-
  Use when project guidance is missing or incomplete; inventory it, ask one question at a time, then write the completed overlay.
---

# Onboard a project overlay

Create or refresh `.agents/project/`. These repository-local Markdown documents are authoritative project facts for reusable skills and are managed by the user after onboarding.

## Workflow

1. Read `AGENTS.md`, `.agents/AGENTS.md`, `.agents/policies/*.md`, `.agents/steering/*.md`, and every existing `.agents/project/` document. Inventory the required project documents: `README.md`, `product.md`, `tech.md`, `tracking.md`, `testing.md`, `language.md`, `security.md`, `logging.md`, `api-standards.md`, `review.md`, `delivery.md`, `automation.md`, and `context.md`. Mark each as **present and complete**, **present but incomplete**, or **missing**. Treat placeholders, unsupported assumptions, and absent required facts as incomplete.
2. Inspect the repository's manifest, configuration, source layout, CI configuration, and existing developer documentation. Prepare evidence-backed defaults, but do not treat inference as fact.
3. Report the inventory and evidence-backed defaults to the user. Ask one focused question at a
   time for every missing or incomplete document. Wait for the answer before asking the next
   question, and retain each answer in the conversation until the overlay is written. Confirm or
   correct the observed defaults for:
   - product purpose, users, scope, and durable constraints;
   - languages, versions, frameworks, package/build management, architecture, dependencies, and implementation conventions;
   - issue tracking, connector, authentication, identifiers, links, and project scope;
   - test frameworks, organisation, methods, quality gates, and coverage expectations;
   - human language, spelling locale, and accepted terminology exceptions;
   - credentials, tokens, secret handling, sensitive code, and application-security requirements;
   - logging format, destinations, levels, PII, redaction, and retention; and
   - inbound and outbound APIs, authentication, validation, pagination, rate limits, retries, error policy, and data handling; and
   - review-finding presentation mode, any override of the policy presentation layouts, and whether any finding classes may be accepted or addressed automatically.
   - selected delivery model, delivery branch, branch naming, commit title and message format, required checks, secret scanning, pull-request format or templates, final delivery event, and authority for agent-performed external writes.
   - workflow progression mode (`manual` or `decision-gated`) and any supported local exceptions.
   - whether to maintain the optional `.specle/context.json` hand-off document and whether reviewing agents may update it.
   Do not create or modify `.agents/project/` while collecting answers. Continue until every
   required topic is answered or explicitly recorded as not established.
4. After all answers are collected, create or refresh the project documents needed by the workflow:
   `README.md`, `product.md`, `tech.md`, `tracking.md`, `testing.md`, `language.md`, `security.md`, `logging.md`,
   `api-standards.md`, `review.md`, `delivery.md`, `automation.md`, and `context.md`. In `language.md`, record the human language, spelling locale, and accepted terminology exceptions. In `review.md`, record the presentation mode, any policy-layout override, and automated-decision policy; severity and default layouts are defined by package policy. In `delivery.md`, record the selected delivery model and confirmed delivery conventions. In `automation.md`, record the selected progression mode and confirmed exceptions. In `context.md`, record whether optional hand-off context is maintained and whether reviewing agents may update it. Write only user-confirmed or source-supported facts. If a fact remains
   unknown, say that it is not established rather than inventing it.
5. Ensure the README identifies these documents as authoritative and maps each one.
6. Keep package-owned `.agents/policies/` generic and unmodified. `.agents/steering/` is project-owned generic guidance; move repository-specific facts to `.agents/project/` rather than duplicating them in either layer.
7. Ensure the root `AGENTS.md` has a concise durable pointer to `.agents/AGENTS.md`; do not restate workflow or project documents in the root file.
8. After the project overlay exists and its README maps every project document it creates, remove only the `<!-- agents-onboard:start -->` through `<!-- agents-onboard:end -->` bootstrap block from the root `AGENTS.md`. Keep the durable `.agents/AGENTS.md` pointer.
9. Ensure the repository tracks `.agents/policies/`, `.agents/steering/`, and `.agents/project/`. Establish the repository's separate commit policy for `.specle/`. Validate that the README maps every project document it creates.

## Boundaries

- Do not invent standards, external integrations, or tracker configuration.
- Do not alter application code, dependencies, CI, or project configuration as part of onboarding.
- Project guidance documents describe durable repository facts; individual feature requirements belong in `.specle/changes/`.
- Preserve supported local content when refreshing an existing overlay. Do not replace established facts with generic template text.

## Next

- `analyse` — compare the overlay with the codebase when conventions may have drifted.
- `define` — describe a feature change once the project context is established.
