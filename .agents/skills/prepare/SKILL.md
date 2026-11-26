---
name: prepare
specle_group: Alternatives
requires:
  - bugfix
  - refactor
description: >-
  Prepare non-active bugfixes or refactors for later work.
usage: >-
  Use to create an explicitly named unselected repair or behaviour-preserving restructure without implementation changes.
lifecycle:
  creates:
    - planned
---

# Prepare abbreviated side work

Create a named, implementation-ready bugfix or refactor without executing its tasks or changing the local selection.

## Workflow

Before creating or recording lifecycle state, consult this skill's `lifecycle` frontmatter declaration.

1. Read `.specle/current-change` when present, the relevant policies and steering, and applicable authoritative `.agents/project/` documents.
2. Determine the work kind. Use `bugfix` for a bounded defect whose intended behaviour is known. Use `refactor` for a behaviour-preserving structural change. Ask the user if that distinction is unclear.
3. Invoke the selected owning workflow in prepare mode. It must create the uniquely named change directory, write the abbreviated `spec.md` and `tasks.md`, and create the matching status record without executing any task.
4. Confirm the status record has the selected `kind` and `status: "planned"`. Preserve `.specle/current-change`.
5. Report the exact generated change name. Later invocation must name that item's owning `bugfix` or `refactor` skill; `verify <change-name>` verifies it after those tasks are complete.

## Critical

- Never implement code, tests, or task steps in this workflow.
- Do not use this skill for a normal feature, documentation change, or release; use the normal `define` workflow instead.
- Do not choose an existing abbreviated item implicitly.

## Next

- `bugfix <change-name>` or `refactor <change-name>` — resume prepared abbreviated work.
