---
name: analyse
description: >-
  Analyse the codebase and propose updates to the steering docs. Use when asked to "analyse the
  codebase", audit tech debt/risks, or bring the project documentation up to date with the actual code.
---

# Analyse codebase & update project guidance

Assess the codebase against its recorded project guidance and propose concrete updates.

## Workflow

1. Read `.agents/CONTEXT.json` for current state and spec summary.
2. Analyse the codebase: structure, tech stack, patterns, conventions actually in use.
3. Review `.agents/steering/*.md` and the relevant authoritative `.agents/project/*.md` files,
   then compare the project guidance against reality.
4. Identify risks, tech debt, and improvement areas.

## Output

A clear analysis report, plus **specific proposed edits** to `.agents/project/*.md` where project
facts or conventions drift from the code. Amend steering only when the reusable workflow itself is
wrong. Get confirmation before writing either kind of guidance change.

## Next

- `spec` — turn an improvement into a tracked spec.
- `review` — review a specific change in depth.
