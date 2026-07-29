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
3. Read `.agents/steering/*.md` — especially `tech.md` and `api-standards.md` — so the design
   follows repo patterns (async-first, `github_api_call`, `url_vars`, protocols over ABCs).
4. Write `design.md` in the spec folder with:
   - **Overview** — what changes, at a glance.
   - **Architecture** — component/call flow (a text diagram is fine).
   - **API / data** — GitHub endpoints, result keys, record shapes.
   - **Error handling** — map each failure to its policy (403/404 → `None`; `GitHubApiError` →
     partial; fatal rate limits re-raised).
   - **Report/output rendering** — if the feature has output, show plain/table/JSON shapes.
   - **Test strategy** — the unit/property tests to write, plus the four `uv run` gates.
5. Update `.agents/CONTEXT.json` to note design is present.

Keep the design faithful to every requirement — `/verify` later checks design coverage.

## Next

- `/tasks` — generate the implementation tasks from this design.
- `/verify` — confirm the design covers all requirements before building.
