---
name: build
description: >-
  Execute the current spec's tasks with TDD, one at a time, updating tasks.md and CONTEXT.json
  as you go. Use when asked to "build" / "implement" the current spec.
---

# Build the current spec (TDD)

Work through the active spec's tasks one at a time, test-first, keeping the spec's tracking files
in sync.

## Workflow

1. Read `.agents/CONTEXT.json` (current spec + progress) and `.agents/.current` (spec folder path).
2. Read `tasks.md`; find the first uncompleted task (`- [ ]`).
3. For each task, in order:
   a. Write the test(s) first (TDD).
   b. Implement the minimum code to pass — no speculative code.
   c. Run `uv run pytest -v -Werror -Walways` (plus `uv run ruff check`, `uv run ty check src/`,
      `uv run ruff format` as appropriate).
   d. Mark the task complete: change `- [ ]` to `- [x]` in `tasks.md`.
   e. Update `.agents/CONTEXT.json` with the new progress.
4. Follow the repo commit policy (see `.agents/CONTEXT.json` → `commit_policy`): direct commits to
   `main` are acceptable once tests and the Python quality checks pass. Commit only when the user
   asks, with a descriptive message.

## Critical

- Always update `tasks.md` and `.agents/CONTEXT.json` after each task.
- Run all commands through `uv run`; use non-interactive flags.
- Never delete the `.agents/` folder or its contents.

## Next

- When all tasks are complete: `/verify` to confirm the implementation against the spec.
- `/review` for a quality pass on the diff.
