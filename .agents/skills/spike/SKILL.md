---
name: spike
description: >-
  Run a time-boxed investigation and produce a findings report — no implementation. Use when asked
  to "spike" / "investigate" / "research" a question before committing to building.
---

# Spike (investigate, don't implement)

Research a question and report findings for decision-making. **Do not implement anything.**

## Workflow

1. Read `.agents/CONTEXT.json` for current state.
2. Research the question/problem (read code, docs, run read-only experiments).
3. Create a spec folder `.agents/specs/YYYY-MM-DD-{slug}/` with `spec.md` as a **findings report**:
   - Question / hypothesis.
   - Investigation approach.
   - Findings (with code examples where relevant).
   - Recommendations.
   - Risks identified.
   - Estimated implementation effort (S / M / L / XL).
4. Capture key learnings in `memory.md` in the spec folder.

Research only — no production code changes.

## Next

- `/spec` — turn the recommendation into a real feature spec.
- Archive the learnings and move on.
