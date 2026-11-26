---
name: tasks
specle_group: Planning
description: >-
  Generate task plans from normal changes and designs.
usage: >-
  Use after normal requirements and any necessary design exist to create or reconcile an ordered TDD task plan; do not infer completed work from a diff.
lifecycle:
  accepts:
    - designed
  transitions:
    - from: designed
      to: planned
      next: build
---

# Generate implementation tasks

Produce a `tasks.md` of atomic, independently verifiable, test-first tasks for a normal change,
matching the existing `tasks.md` files in `.specle/changes/`.

## Change independence

Changes are independent by default. A queued or future change must not create a dependency through ordering, conceptual overlap, or anticipated functionality. Record a dependency only for an obvious, already-implemented technical prerequisite or an explicit user decision, and make it visible in the affected tasks and change artifacts. Constraints, features, expectations, and functionality from a future change must not constrain this change until that future change is implemented.

## Workflow

Before applying or recording a lifecycle transition, consult this skill's `lifecycle` frontmatter declaration.

1. Read `.specle/current-change` when present and the target `status.json` to locate the selected change. A named unselected normal change is also valid for explicit planning; it must remain unselected.
2. Require and read `requirements.md`, `spec.md`, and `design.md` (for architecture and dependency ordering). Stop if the target has no design.
   Read applicable authoritative `.agents/project/` documents for project constraints that the
   implementation tasks must preserve.
3. Inspect relevant repository changes before planning: use `git status --short`, staged and unstaged diffs, and recent commits for the code affected by the change. Account for relevant existing implementation or partial work, but ignore unrelated changes.
4. Write or reconcile `tasks.md` in the change folder:
   - Checkbox format: `- [ ] N. <task>` with nested `- [ ] N.M` subtasks.
   - **TDD**: each implementation slice is "add tests" then "implement", never implementation first.
   - Logical ordering (data/records → processor → report/output → CLI wiring).
   - Note the files each task touches.
   - Do not mark a task complete solely because a diff or existing code appears to satisfy it; reconcile that evidence into the plan and leave completion to `build` and `verify`.
5. For a selected target, update its `status.json` with the top-level task count (`0/N`), set its status to `planned` according to `lifecycle.md`, and write `updated_at` as current Unix seconds. For a named unselected target, write only its task plan and retain `status: "defined"`.

Tasks must be atomic and independently verifiable — one behaviour per cycle.

## Next

After recording a complete plan for the selected target, read `.agents/project/automation.md`. In `decision-gated` mode, invoke `build <change-name>`; otherwise report it and wait. For a named unselected target, stop and report `activate <change-name>`.

- `build` — start executing the tasks with TDD.
- `verify` — confirm the tasks cover every acceptance criterion.
