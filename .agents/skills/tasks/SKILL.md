---
name: tasks
description: >-
  Generate an implementation task list (tasks.md) from a spec and its design. Use when asked to
  "generate tasks" / "break down" a spec into ordered TDD steps.
---

# Generate implementation tasks

Produce a `tasks.md` of atomic, independently verifiable, test-first tasks for the current spec,
matching the existing `tasks.md` files in `.agents/specs/`.

## Workflow

1. Read `.agents/CONTEXT.json` and `.agents/.current` to locate the active spec.
2. Read `requirements.md` (or `spec.md`), `spec-lite.md`, and `design.md` if present (for
   architecture and dependency ordering).
3. Write `tasks.md` in the spec folder:
   - Checkbox format: `- [ ] N. <task>` with nested `- [ ] N.M` subtasks.
   - **TDD**: each implementation slice is "add tests" then "implement", never implementation first.
   - Logical ordering (data/records → processor → report/output → CLI wiring → verification).
   - Note the files each task touches.
   - A final task group for verification: update `spec-lite.md`, then run the four `uv run` gates.
4. Update `.agents/CONTEXT.json` with the task count (`0/N`).

Tasks must be atomic and independently verifiable — one behavior per cycle.

## Next

- `/build` — start executing the tasks with TDD.
- `/verify` — confirm the tasks cover every acceptance criterion.
