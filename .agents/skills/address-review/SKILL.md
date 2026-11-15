---
name: address-review
description: >-
  Collate accepted review decisions and route them through the right existing workflow. Use after
  triage to revise the current spec, fix defects, improve tests, refactor, or explicitly defer work.
---

# Address reviewed feedback

Turn a completed review triage into a coherent delivery plan and run the smallest workflow that
fully addresses each accepted decision. The triage decision is authoritative: this skill does not
reopen accepted, declined, varied, deferred, or stale items.

## Workflow

1. Read the decision record and its source feedback. This may be a pull-request review, an
   independent-agent review, user feedback, or a durable triage record. Confirm every relevant
   item has a disposition before acting; return undecided items to `triage-items` or `triage-pr`.
2. Collate decisions by affected change and prioritise accepted or varied work by correctness and
   safety first, then contract/architecture, then test coverage, then maintainability or docs.
   Keep related findings together when they share a cause or require the same planning revision.
3. Route each group deliberately:
   - Use `revise` when a current change's requirements, design, assumptions, or task plan are
     wrong or incomplete. Revise the existing spec in place, then use `build`.
   - Use `fix` for a bounded defect whose existing specification and design remain correct.
   - Use `refactor` only for a behaviour-preserving structural improvement.
   - For a test-only gap in the current change, use `revise` when its task/test strategy needs
     correction, then `build`; do not create a separate test-only change by default.
   - Use another local skill only when its stated scope better matches the accepted work.
4. Preserve non-action decisions:
   - **decline** and **stale**: record no action.
   - **defer**: retain the rationale and revisit condition; do not implement it.
   - Create a new spec for a deferred item only when the user explicitly chooses that outcome.
     A deferred review item never creates a new change automatically.
5. Invocation of this skill after triage authorises execution of the selected workflow(s) in
   priority order. Keep corrections to the active change in its existing spec rather than creating
   a review-fix spec.
6. Report the decision inventory, selected workflow for each accepted group, deferred work, and
   resulting next step. Where the feedback is on a pull request, record the completed disposition
   and handle the corresponding reviewer response or thread resolution as part of delivery.

## Boundaries

- Do not use this skill to triage raw feedback; use `triage-items` or `triage-pr` first.
- Do not create a new spec merely because feedback arrived after implementation. `revise` is the
  default for a defect in the current change's planning artifacts.
- Preserve the review source and its decisions in the existing durable record when one exists.

## Next

- `revise` then `build` — for accepted planning or architectural corrections to the current change.
- `fix` — for a bounded defect with a still-valid plan.
- `spec` — only after the user explicitly promotes deferred work into an independent change.
