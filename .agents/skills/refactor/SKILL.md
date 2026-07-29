---
name: refactor
description: >-
  Restructure code with no behavior change, guarded by the existing tests. Use when asked to
  "refactor" / "clean up" / "restructure" code without changing what it does.
---

# Refactor (no behavior change)

Improve structure while keeping behavior identical, with tests as the guardrail.

## Workflow

1. Read `.agents/CONTEXT.json` for current state.
2. Read the codebase area being refactored.
3. Create a spec folder `.agents/specs/YYYY-MM-DD-{slug}/` with `spec.md`:
   - Current state (what exists), target state (what it should look like), constraints
     (**behavior must not change**), refactor approach.
4. Create `tasks.md` with incremental refactor steps.
5. Execute:
   - Confirm the existing tests pass **before** starting.
   - Restructure in small steps.
   - Run the full suite after **each** change.

## Critical

- Run existing tests before AND after each change. No behavior changes, no new features.
- If a test needs to change to pass, that's a behavior change — stop and reconsider.

## Next

- `/verify` — confirm behavior is unchanged and gates pass.
- `/review` — quality pass on the restructure.
