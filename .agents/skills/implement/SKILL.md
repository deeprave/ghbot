---
name: implement
description: >-
  Advance an existing spec through its missing planning stages and build its tasks. Use when asked
  to take a spec through implementation without repeating already completed lifecycle work.
---

# Implement a spec

Take an existing specification through the missing lifecycle stages up to and including `build`.
Reuse valid estimates, designs, and task plans; do not recreate them merely because this skill was
invoked.

## Workflow

1. Select the target spec. Use the active spec by default, or an existing explicitly named spec.
   A named target is authority to make that spec current when necessary. Do not replace a different
   unfinished active spec unless the user explicitly named the target.
2. Read `.agents/.current`, `.agents/CONTEXT.json`, the target requirements (`requirements.md` or
   `spec.md`), `spec-lite.md`, any `estimate.md`, `design.md`, and `tasks.md`, plus the lifecycle
   and applicable authoritative `.agents/project/` documents. Confirm the artifact set and recorded status agree; use
   `context` if they do not.
3. Advance only the missing stages, following the selected skill's full instructions:
   - If no valid estimate exists, use `estimate`. Treat its sizing recommendation as advisory:
     design is normally needed for M/L/XL work; small, understood work may proceed to tasks.
   - If design is needed and `design.md` is absent or invalidated, use `design`.
   - If `tasks.md` is absent, incomplete as a plan, or invalidated by the requirements/design, use
     `tasks` to produce or reconcile the implementation plan.
   - When an unchecked, buildable task list exists, use `build` and continue until every planned
     task is complete.
4. Stop rather than inventing a decision when requirements are ambiguous, a material design choice
   needs user direction, or untriaged review feedback affects the target. Route completed review
   decisions through `address-review`; it may in turn use `revise`, `fix`, or `refactor` before
   this skill resumes the build path.
5. Do not repeat completed stages. If all tasks are already complete, do not rebuild; report
   `verify` as the next step. If the spec is already `verified`, report `review`; if it is
   `complete`, report that no implementation work remains.

## Boundaries

- This skill operates on an existing spec; use `spec` to create a new one.
- Preserve the target spec's directory and history. Corrections to its requirements, design, or
  plan stay in that spec through `revise`, rather than becoming a separate review-fix change.
- Delegate stage-specific state updates to the selected skills. Do not silently skip their
  required tests, lifecycle updates, or decision points.
- Stop after `build`; verification, review, delivery, and pull-request operations remain their own
  explicit stages.

## Next

- `verify` — when all build tasks are complete.
- `review` — when verification has already passed.
