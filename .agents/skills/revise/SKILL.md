---
name: revise
specle_group: Planning
description: >-
  Revise changes and plans after accepted feedback.
usage: >-
  Use when accepted feedback changes requirements, design, or tasks; do not use it for an implementation-only defect.
lifecycle:
  accepts:
    - triaged
    - committed
  transitions:
    - from: triaged
      to: planned
      next: build
    - from: committed
      to: planned
      next: build
---

# Revise a change

Before applying or recording a lifecycle transition, consult this skill's `lifecycle` frontmatter declaration.

Preserve one change's history when accepted feedback exposes an error in its requirements,
architecture, or assumptions. Revise the existing planning artifacts in place so that the next
implementation work remains part of the same change.

Use this skill after feedback has been triaged and accepted (or varied) by the user. It is not the
path for an implementation-only defect whose requirements, design, and task plan remain valid;
use `bugfix` for that case.

## Change independence

Changes are independent by default. A queued or future change must not create a dependency through ordering, conceptual overlap, or anticipated functionality. Record a dependency only for an obvious, already-implemented technical prerequisite or an explicit user decision, and make it visible in the affected change artifacts and context. Constraints, features, expectations, and functionality from a future change must not constrain this change until that future change is implemented.

## Workflow

1. Identify the target from `.specle/current-change` and per-change `status.json`. Default to the selected normal change. A `bugfix` or `refactor`, or a committed normal change, is valid only when the user explicitly names it; preserve the local selection throughout that non-selected revision. Reject archived targets: they are immutable except for explicitly named triage updating `review-findings.json`. Do not create a new change, switch to an unrelated one, or split accepted review feedback into a separate change.
2. Read the feedback and its accepted disposition. For a normal target, read `requirements.md`, `spec.md`, `design.md`, and `tasks.md` when present. For an abbreviated target, read its `spec.md` and `tasks.md`.
   Read the applicable lifecycle and authoritative `.agents/project/` documents before revising architecture or contracts.
3. Classify each accepted finding:
   - **Requirements impact** — the user-facing behaviour, contract, acceptance criteria, or
     constraints are wrong or incomplete. Revise the requirements/change.
   - **Design impact** — the requirement remains valid but the architecture, API choice,
     assumption, error policy, or data flow is wrong. Revise `design.md`.
   - **Task impact** — the implementation plan no longer reaches the corrected requirements and
     design. Revise `tasks.md`.
   - **Abbreviated-contract impact** — for a bugfix, the defect description, expected behaviour, root cause, or fix approach is wrong or incomplete; for a refactor, the target state, behavioural invariants, baseline evidence, or approach is wrong or incomplete. Revise the abbreviated `spec.md`.
   A finding may affect more than one artifact. Ask only when its intended contract cannot be
   determined from the accepted disposition and repository evidence.
4. Revise every affected artifact in place:
   - Update the requirements/change only when the contract needs correction; do not rewrite it for
     an implementation-only repair.
   - Update the design whenever an accepted finding invalidates its architecture or assumptions.
     Keep interfaces, data flow, failure policy, and test strategy aligned with the corrected
     contract.
   - Reconcile tasks after requirements/design changes. Preserve completed work as history, reopen
     tasks whose claimed outcome is invalidated, and add precise unchecked tasks for new work.
     Remove only tasks made genuinely obsolete, noting why when that would otherwise be unclear.
   - For an abbreviated target, revise only its `spec.md` and `tasks.md`. Preserve valid completed tasks, reopen invalidated tasks, and add precise unchecked tasks for accepted changes.
5. Regenerate a normal target's `spec.md` if the requirements changed. Update only its `status.json` with a concise revision note and current Unix-second `updated_at`. For a selected normal target, invalidate prior verification and review, then set the lifecycle status according to the revised artifacts. When requirements, design, and tasks are all reconciled, the target is `planned`. For a named committed normal target, update only its matching status to `planned`, retain its delivery reference, and preserve the local selection. For an abbreviated target, update only its `spec.md`, `tasks.md`, and status to `planned`; do not alter `.specle/current-change`.
6. Report the accepted feedback, which artifacts changed, any reopened or added tasks, and the
   resulting next step.
7. After a successful revision, read `.agents/project/automation.md`. In `decision-gated` mode, invoke the recorded next local skill with the selected target name; otherwise report it and wait.

## Important

- Accepted review feedback authorises revision of the target change's planning artifacts; do not
  ask for a second confirmation merely to update them.
- Never create a new change, a separate review-fix change, or replacement design solely to address
  accepted feedback for the target change.
- Retain the original change directory and its Git history. Keep revision notes concise; link the
  accepted finding or review source when that materially explains the correction.
- Do not implement code, reply to reviewers, resolve threads, commit, or change external state
  during revision unless the user separately asks.

## Next

- `build` — implement the reconciled active normal plan.
- `bugfix <change-name>` or `refactor <change-name>` — resume reconciled abbreviated work.
