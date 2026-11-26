---
name: complete
specle_group: Integration
requires:
  - commit
  - triage
  - resolve
description: >-
  Finalise archival delivery for a committed Specle change.
usage: >-
  Use after any committed delivery to confirm its final event when needed, archive the durable change record, and create any required completion PR.
lifecycle:
  accepts:
    - committed
  transitions:
    - from: committed
      to: complete
  terminal:
    - complete
---

# Complete committed delivery

Complete archival finalisation for a committed delivery. A branch-and-pull-request delivery may still require its configured final event; only that model can merge and synchronise when both project policy and the user explicitly authorise the work.

## Workflow

Before applying or recording a lifecycle transition, consult this skill's `lifecycle` frontmatter declaration.

1. Read `.specle/current-change` when present, `.agents/policies/{lifecycle,delivery}.md`, applicable `.agents/steering/` overrides, `.agents/project/delivery.md`, and the selected target's `status.json` delivery evidence.
2. Select the locally selected delivery-complete target by default. A non-selected target must be explicitly named and never replaces `.specle/current-change`. Require the evidence appropriate to the configured delivery model. For branch-and-pull-request delivery, require a reference, head branch, and target branch. For a normal parent target, derive candidates only from its own concurrent-delivery relationships and require each active bugfix/refactor candidate to reciprocally name the parent, match the parent-declared kind, and be `committed` with consistent delivery evidence. Stop with an actionable diagnostic for any declared ineligible candidate; do not infer sidecars by scanning active changes.
3. For branch-and-pull-request delivery, check that the checkout is on the recorded delivery head branch. If it is on any other branch, including the delivery target branch, stop immediately and report the current and expected branches. Do not stash, switch, merge, pull, fetch, or otherwise modify the worktree.
4. Confirm that external findings are resolved and establish whether the final delivery event is already evidenced. A confirmed final event permits archival finalisation; it does not make a selected target with pending wrapup replaceable by `activate`.
5. If the delivery is not already final, describe the precise final action and require both project policy and explicit user authorisation before performing it. Without both, leave the target ready for delivery and provide the required human action.
6. Before an authorised merge, branch switch, or synchronisation, preserve tracked staged and unstaged work in one named, recoverable `git stash`. If creating the stash fails, stop before changing Git state. Retain it through every finalisation operation. Do not stash untracked or ignored generated files; accept the rare ignored-file collision risk.
7. Perform the authorised final delivery action. For branch-and-pull-request delivery, merge the reviewable delivery, switch to the configured delivery target branch, and fast-forward from upstream without reset or force operations. Do not restore the stash yet.
8. After the final delivery event, form the delivered-name set from the parent and every validated sidecar. Re-read each other active `status.json`; when its explicit `dependencies` array contains a delivered name, remove every such name and write only that array back, preserving unrelated dependencies, lifecycle status, timestamps including `updated_at`, and all other fields. Do not infer dependencies, mutate archives, or edit records with no matching declared dependency.
9. Generate the parent's `summary.md`, stage one complete directory move for the parent and every validated sidecar from `.specle/changes/` to `.specle/archive/`, and update every archived `status.json` with final delivery evidence, `status: "complete"`, and `archived_at`. Include every dependency-reconciled active `status.json` in the same finalisation change. Preserve every artifact, relationship, delivery field, and each sidecar's prior `updated_at`. Treat this as one recoverable operation: on failure, retain or restore every active directory and the parent selector.
10. Present the exact finalisation file list and obtain delivery authorisation before committing any archive mutation. For direct-main policy, commit finalisation on main and remove the matching selector. For a delivery branch already merged into main, create or reuse `<delivery-branch>-completion` from the retained delivery head, commit and push the archival finalisation, then open or identify one completion PR to main. Add its `delivery.completion` reference, head branch, target branch, and archival commit to every jointly archived record in a follow-up commit pushed to that same completion branch. Do not synchronise local main: retain the selected archived record and direct it to `wrapup` until that PR merges. Resume after interruption from the next missing branch, PR, or evidence-commit step without duplication.
11. Restore the retained stash only after finalisation succeeds or stops safely. If restoration conflicts or fails, retain the stash, report recovery steps, and do not remove the selector.
12. A named non-selected target remains non-selected throughout.

## Boundaries

- Never act when the branch guard fails.
- Never discard staged or unstaged work; retain the stash if restoration is incomplete. Do not shuffle untracked or ignored generated files merely to guard against a rare branch-switch collision.
- For a branch-and-pull-request delivery that has not reached its final event, do not direct the user to merge manually; `complete` owns the authorised merge and archival finalisation sequence.
- Lack of merge authority does not prevent preparing archive finalisation for an already evidenced external merge.
- Remove `.specle/current-change` only for direct delivery with no completion PR. `wrapup` owns selector removal after completion-PR delivery.
- A jointly archived sidecar has no separate `complete` or `wrapup` cycle; its parent owns the shared finalisation delivery.

## Next

- `wrapup <change-name>` — merge the recorded completion PR and clear the retained selector after successful delivery.
- `triage <change-name>` — when new external feedback arrives before the final event.
