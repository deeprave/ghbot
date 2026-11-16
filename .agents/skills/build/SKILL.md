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

1. Read `.agents/CONTEXT.json` (current spec + progress), `.agents/.current` (spec folder path),
   `.agents/steering/lifecycle.md`, and the relevant authoritative `.agents/project/` documents.
   Confirm the two current-spec
   paths agree before continuing.
2. Run a lifecycle preflight before reading or changing `tasks.md`:
   - `defined` — stop and advise `estimate`, or `design`/`tasks` only for small, understood work.
   - `estimated` — stop and advise `design`.
   - `designed` — stop and advise `tasks`.
   - `planned`, `building`, or `review-findings` — continue only when `tasks.md` exists and has an
     uncompleted task.
   - `verified` — stop and advise `review`.
   - `complete` — stop and report that no build work remains.
   - Any missing, inconsistent, or unrecognised lifecycle state — stop and advise `context`.
   If `review-findings` has no uncompleted task, advise `address-review` so the reviewed decisions
   can be routed and recorded. If `planned` or `building` has no uncompleted task, advise `verify`.
3. Read `tasks.md`; find the first uncompleted task (`- [ ]`).
4. For each task, in order:
   a. Write the test(s) first (TDD).
   b. Implement the minimum code to pass — no speculative code.
   c. Run the focused test and any project checks needed to keep the change safe.
   d. Mark the task complete: change `- [ ]` to `- [x]` in `tasks.md`.
   e. Update `.agents/CONTEXT.json` with the new progress and the `building` transition. Invalidate
      prior verification and review evidence as `stale` when this task changes implementation.
## Critical

- Do not implement, create tasks, or change lifecycle state when the preflight says another skill
  is required.
- Always update `tasks.md` and `.agents/CONTEXT.json` after each task.
- Use the project's documented command runner and non-interactive flags.
- Never delete the `.agents/` folder or its contents.

## Next

- When all tasks are complete: use `verify` to confirm the implementation against the spec.
- Use `review` for a quality pass on the diff.
