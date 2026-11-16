---
name: revise
description: >-
  Revise an existing spec, design, and tasks in place after accepted feedback. Use when review
  findings expose a requirements or architectural/design error; do not create a separate change.
---

# Revise a spec

Preserve one change's history when accepted feedback exposes an error in its requirements,
architecture, or assumptions. Revise the existing planning artifacts in place so that the next
implementation work remains part of the same spec.

Use this skill after feedback has been triaged and accepted (or varied) by the user. It is not the
path for an implementation-only defect whose requirements, design, and task plan remain valid;
use `fix` for that case.

## Workflow

1. Identify the current spec from `.agents/.current` and `.agents/CONTEXT.json`, unless the user
   explicitly names another existing spec. Do not create a new spec, switch to an unrelated one,
   or split accepted review feedback into a separate change.
2. Read the feedback and its accepted disposition, then read the target's full requirements
   (`requirements.md` or `spec.md`), `design.md`, `tasks.md`, and `spec-lite.md` when present.
   Read the applicable lifecycle and authoritative `.agents/project/` documents before revising architecture or contracts.
3. Classify each accepted finding:
   - **Requirements impact** — the user-facing behaviour, contract, acceptance criteria, or
     constraints are wrong or incomplete. Revise the requirements/spec.
   - **Design impact** — the requirement remains valid but the architecture, API choice,
     assumption, error policy, or data flow is wrong. Revise `design.md`.
   - **Task impact** — the implementation plan no longer reaches the corrected requirements and
     design. Revise `tasks.md`.
   A finding may affect more than one artifact. Ask only when its intended contract cannot be
   determined from the accepted disposition and repository evidence.
4. Revise every affected artifact in place:
   - Update the requirements/spec only when the contract needs correction; do not rewrite it for
     an implementation-only repair.
   - Update the design whenever an accepted finding invalidates its architecture or assumptions.
     Keep interfaces, data flow, failure policy, and test strategy aligned with the corrected
     contract.
   - Reconcile tasks after requirements/design changes. Preserve completed work as history, reopen
     tasks whose claimed outcome is invalidated, and add precise unchecked tasks for new work.
     Remove only tasks made genuinely obsolete, noting why when that would otherwise be unclear.
5. Regenerate `spec-lite.md` if the full specification changed. Update `CONTEXT.json` to record a
   concise revision note, invalidate prior verification and review, and set the lifecycle status
   according to the revised artifacts. When requirements, design, and tasks are all reconciled,
   the target is `planned` and the next skill is `build`.
6. Report the accepted feedback, which artifacts changed, any reopened or added tasks, and the
   resulting next step.

## Important

- Accepted review feedback authorises revision of the current change's planning artifacts; do not
  ask for a second confirmation merely to update them.
- Never create a new spec, a separate review-fix change, or replacement design solely to address
  accepted feedback for the active change.
- Retain the original spec directory and its Git history. Keep revision notes concise; link the
  accepted finding or review source when that materially explains the correction.
- Do not implement code, reply to reviewers, resolve threads, commit, or change external state
  during revision unless the user separately asks.

## Next

- `build` — implement the reconciled plan.
