---
name: demo
description: >-
  Generate a stakeholder walkthrough (demo.md) of what a spec delivered, for human review. Use
  when asked to "demo" / "walk through" / "write up" completed work for non-AI reviewers.
---

# Demo walkthrough

Produce a human-facing walkthrough of what was built — for stakeholder review, not AI verification.

## Workflow

1. Read `.agents/CONTEXT.json` for current state.
2. Read `requirements.md` (or `spec.md`) for the requirements.
3. Read `tasks.md` for implementation status.
4. Examine the actual implementation in the codebase.
5. Write `demo.md` in the spec folder showing:
   - What was built, mapped to spec requirements.
   - How to test/verify each feature (concrete commands/examples).
   - What's working vs still pending.
   - Key decisions made during implementation.
   - Examples/sample output where applicable.
6. Highlight anything that needs stakeholder input.

## Next

- `/revise` — fold in stakeholder feedback.
- The work is ready to complete once feedback is addressed.
