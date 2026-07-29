---
name: analyse
description: >-
  Analyse the codebase and propose updates to the steering docs. Use when asked to "analyse the
  codebase", audit tech debt/risks, or bring .agents/steering up to date with the actual code.
---

# Analyse codebase & update steering

Assess the codebase against the recorded standards and propose concrete steering updates.

## Workflow

1. Read `.agents/CONTEXT.json` for current state and spec summary.
2. Analyse the codebase: structure, tech stack, patterns, conventions actually in use.
3. Review `.agents/steering/*.md` and compare against reality.
4. Identify risks, tech debt, and improvement areas.

## Output

A clear analysis report, plus **specific proposed edits** to `.agents/steering/*.md` where the docs
drift from the code (e.g. a pattern the code follows that isn't documented, or a documented rule the
code no longer honors). Get confirmation before writing steering changes.

## Next

- `/spec` — turn an improvement into a tracked spec.
- `/review` — review a specific change in depth.
