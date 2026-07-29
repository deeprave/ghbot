---
name: refresh
description: >-
  Regenerate a spec's spec-lite.md as a concise AI summary of its requirements. Use when the full
  spec has changed and its condensed version is stale, or when asked to "refresh the spec-lite".
---

# Refresh spec-lite

Generate a concise, AI-summarized `spec-lite.md` from the full spec — a real summary, not a
truncation.

## Workflow

1. Read `.agents/.current` to get the current spec folder.
2. Read `requirements.md` (or `spec.md`) thoroughly.
3. Write `spec-lite.md` in that folder capturing:
   - Core objective (1–2 sentences).
   - Key requirements (bullets) and result keys.
   - Technical constraints.
   - Output/success criteria.

Keep it well under 2000 characters — focused on what's needed for implementation and for context
retention after compression.

## Next

- `/tasks` or `/build` — continue the workflow.
- `/context` — refresh `.agents/CONTEXT.json` if progress also changed.
