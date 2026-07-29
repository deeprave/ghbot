---
name: context
description: >-
  Regenerate .agents/CONTEXT.json for the current spec and state. Use after major changes or a
  context compaction, or when asked to "refresh context".
---

# Refresh CONTEXT.json

Regenerate `.agents/CONTEXT.json` so it reflects the current spec and progress. It is the structured
context other agents read first.

## Workflow

1. Read `.agents/.current` to get the current spec folder.
2. Read that folder's contents (`requirements.md`/`spec.md`, `tasks.md`, `design.md`, `spec-lite.md`).
3. Read `.agents/steering/*.md` for project rules.
4. Regenerate `.agents/CONTEXT.json`, keeping the existing structure. Include at least:
   - `current_spec` — name, path, status, progress (`tasks_completed`/`tasks_total`).
   - `verification` — last gate results if known.
   - `queued_specs` — any defined-but-not-started specs.
   - `python_checks`, `commit_policy` — carry forward unless they changed.
   - `current_diagnosis` / `requirements_summary` — condensed spec-lite content, not the full spec.
5. Write valid JSON. Keep it concise and actionable; do not paste whole specs.

Run this after `/compact` or major changes so the next agent starts with accurate context.

## Next

- `/build` — continue implementing.
- `/verify` — check the implementation against the spec.
