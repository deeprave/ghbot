---
name: fix
description: >-
  Fix a bug with an abbreviated, test-first pipeline (no full spec/design/tasks cycle). Use when
  asked to "fix" a bug or when there's a clear defect to resolve.
---

# Fix a bug (abbreviated TDD)

Resolve a defect with a lightweight, reproduce-first flow — no full spec cycle.

## Workflow

1. Read `.agents/CONTEXT.json` for current state.
2. Understand the bug from the description; read the codebase to find the relevant area.
3. Create a spec folder `.agents/specs/YYYY-MM-DD-{slug}/` with a short `spec.md`:
   - Bug description, steps to reproduce (if inferable), expected vs actual, root-cause analysis,
     fix approach.
4. Create `tasks.md` (test-first):
   - Write a failing test that reproduces the bug.
   - Implement the fix.
   - Confirm existing tests still pass.
5. Execute the tasks immediately (TDD); mark them `- [x]` as you go.

## Critical

- Write the failing test **first**, then fix. A bug fix without a regression test is incomplete.
- Run the gates via `uv run` (`pytest -Werror -Walways`, `ruff check`, `ty check src/`, `ruff format`).

## Next

- `/verify` — confirm the fix and that nothing regressed.
