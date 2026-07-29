---
name: spec
description: >-
  Create a new feature specification under .agents/specs/. Use when starting new work,
  capturing requirements, or when asked to "write a spec" / "spec out" a feature. Produces
  requirements.md + spec-lite.md and sets the spec as current.
---

# Write a feature spec

Create a structured specification for a new piece of work, matching the conventions of the
existing specs in `.agents/specs/`.

## Workflow

1. Read `.agents/steering/*.md` for project context and standards.
2. Ask (or infer) the feature intent. If it is underspecified, ask 2–4 targeted clarifying
   questions before writing — propose sensible defaults so the user can confirm quickly.
3. Create the spec folder: `.agents/specs/YYYY-MM-DD-{feature-slug}/` (today's date, a 2–4 word
   slug).
4. Write `requirements.md` with:
   - **Introduction** — problem/context.
   - **Glossary** — key terms.
   - **Requirements** — numbered, each with a user story and EARS-style **Acceptance Criteria**
     (`THE … SHALL …`, `IF … THEN … SHALL …`). These are the conformance checklist `/verify` uses.
   - **Non-Functional Requirements** — dependencies, API-access rules, `uv run`, unchanged behavior.
5. Write `spec-lite.md` (concise, well under 500 words) — the condensed intent for context
   retention after compression: problem, goal, key result keys, output, design sketch, verification.
6. Set the active spec: write the folder path to `.agents/.current` (format
   `.agents/specs/YYYY-MM-DD-slug`) and update `.agents/CONTEXT.json` (current spec name, path,
   status `defined`, progress).

Do not advance `.current` past an unfinished spec unless the user intends it.

## Next

- `/design` — add a technical design (recommended for L/XL work).
- `/tasks` — generate the implementation task list.
- `/verify` — sanity-check the spec's acceptance criteria before building.
