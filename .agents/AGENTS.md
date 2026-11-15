# Shared Agent Workflow

This is the portable entrypoint for the repository's spec-driven workflow. A repository-root `AGENTS.md` should direct agents here while retaining only genuinely local execution or tool instructions.

## Start here

1. Read `.agents/steering/*.md`. These are reusable policy: context state, lifecycle, and testing principles.
2. If `.agents/project/README.md` is absent, use the `onboard` skill before relying on project architecture, commands, security rules, API conventions, or tracker configuration.
3. If the project overlay exists, read its README and only the documents relevant to the task.
4. Read the matching skill in `.agents/skills/` before performing a workflow stage.
5. For spec work, keep `.agents/.current` and `.agents/CONTEXT.json` aligned with the lifecycle and context schema.

## Workflow

Use the local skills in the following order for feature work:

`spec` → optional `estimate` → `design` → `tasks` → `build` → `verify` → `review`.

A clean verification result is `verified`, not `complete`; only a subsequent passing review completes a spec. After triaged review feedback, use `address-review` to route accepted decisions; it uses `revise` for corrections to the current spec's requirements, design, or plan. Use `context` after major progress or context compaction, and `status` to inspect recorded lifecycle state.

Alternative paths are `fix` for a bounded defect, `refactor` for behaviour-preserving work, and `spike` for an investigation that does not implement changes.

## Root bootstrap block

When adding this framework to a repository without a project overlay, add the following temporary block to the root `AGENTS.md` immediately after its pointer to this file. The `onboard` skill removes the marked block only after it has created and validated the overlay; the durable pointer to this file remains.

```md
<!-- agents-onboard:start -->
This repository has not yet established `.agents/project/` guidance. Use the `onboard` skill
before feature work, then remove this marked bootstrap block.
<!-- agents-onboard:end -->
```
