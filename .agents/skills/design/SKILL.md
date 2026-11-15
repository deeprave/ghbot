---
name: design
description: >-
  Create a technical design (design.md) from a spec's requirements. Use after a spec exists
  and before generating tasks, or when asked to "design" an implementation approach.
---

# Create a technical design

Turn the current spec's requirements into an actionable technical design, matching the `design.md`
files already in `.agents/specs/`.

## Workflow

1. Read `.agents/CONTEXT.json` and `.agents/.current` to locate the active spec.
2. Read `requirements.md` (or `spec.md`) and `spec-lite.md` from that folder.
3. Read `.agents/steering/*.md` and the project documents relevant to the change so the design
   follows the repository's architecture, API, security, and testing conventions.
4. Write `design.md` in the spec folder with:
   - **Overview** — what changes, at a glance.
   - **Architecture** — component/call flow (a text diagram is fine).
   - **API / data** — applicable endpoints, result keys, and record shapes.
   - **Error handling** — map each failure to its documented policy.
   - **Report/output rendering** — if the feature has output, show relevant output shapes.
   - **Test strategy** — the behavioural tests and project quality gates to run.
5. Update `.agents/CONTEXT.json` according to `context.md` and `lifecycle.md`: record that design
   is present and set the active spec status to `designed`.

Keep the design faithful to every requirement — `verify` later checks design coverage.

## Next

- `tasks` — generate the implementation tasks from this design.
- `verify` — confirm the design covers all requirements before building.
