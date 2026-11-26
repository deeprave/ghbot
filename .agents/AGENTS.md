# Shared Agent Workflow

This is the portable entrypoint for the repository's Specle change-driven workflow. The repository-root `AGENTS.md` directs agents here while retaining only local execution and tool instructions.

## Start here

1. Read `.agents/policies/*.md`. These are reusable Specle policy for lifecycle, delivery, review, and testing.
2. If `.agents/project/README.md` is absent, use the `onboard` skill before relying on project architecture, commands, security rules, API conventions, or tracker configuration.
3. If the project overlay exists, treat `.agents/project/*.md` as the authoritative project-specific facts. Read its README and only the documents relevant to the task.
4. Read the matching skill in `.agents/skills/` before performing a workflow stage.
5. For change work, read the selected slug from `.specle/current-change` when it exists and use that change's `status.json` as the durable lifecycle record.

## Workflow

Use the local skills in this order for feature work:

`define` → `activate` → `estimate` → `design` → `tasks` → `build` → `verify` → `review` → `commit`; use `complete` only for branch-and-pull-request delivery.

Before activation, an explicitly named normal change may be estimated, designed, or given tasks without becoming current. Tasks require a design. `activate` is the only operation that selects normal work and begins the required estimate → design → tasks chain before build.

A clean verification result is `verified`, not `complete`; a subsequent passing review makes the work `approved`. The selected delivery model determines whether `commit` completes the work or creates a `committed` branch-and-pull-request delivery for `complete` to finish. After review findings, use `triage` to record decisions, then `resolve` to route accepted decisions. Use `status` to orient selected work and `changes` to inspect pending lifecycle state.

Alternative paths are `bugfix` for a bounded defect, `refactor` for behaviour-preserving work, and `spike` for an investigation that does not implement changes. Use `prepare` to create an unselected bugfix or refactor for later implementation.

When the user explicitly says `next`, automatically invoke the previously suggested next step.

## Shell execution

In zsh shell snippets, do not use `path` as a variable name: it is the special array that backs `PATH`.
