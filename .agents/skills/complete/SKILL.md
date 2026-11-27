---
name: complete
specle_group: Integration
requires:
  - commit
  - triage
  - resolve
description: >-
  Finalise or resume archival delivery for a committed Specle change.
usage: >-
  Use after committed delivery to archive it on its existing delivery path, request final merge where applicable, or resume the missing finalisation phase.
lifecycle:
  accepts:
    - committed
    - complete
  transitions:
    - from: committed
      to: complete
  terminal:
    - complete
---

# Complete delivery

`complete` is the sole normal finalisation workflow. A branch-and-pull-request delivery archive-finalises on its original open PR, pushes that archival update, and requests auto-merge. It creates a `<delivery-branch>-complete` recovery PR only when the original PR has already merged before archival delivery.

## Workflow

Before applying or recording a lifecycle transition, consult this skill's `lifecycle` frontmatter declaration.

1. Read `.specle/current-change` when present, `.agents/policies/{lifecycle,delivery,context}.md`, applicable `.agents/steering/` overrides, `.agents/project/{delivery,context}.md`, and the target's current `status.json` delivery evidence. Context remains optional and never blocks completion. Re-read every state file immediately before changing its precise fields.
2. Select a locally selected or explicitly named target. An active target must be `committed`; an archived target must be a normal parent with `status: "complete"` and branch-delivery evidence. A named non-selected target never replaces `.specle/current-change`. Archived sidecars and direct-delivery archives are not resumable. For an active normal parent, derive sidecars only from its own reciprocal concurrent-delivery declarations and require them to be `committed` with consistent delivery evidence.
3. Determine the delivery model and current phase. A branch target uses its recorded original PR and head branch until recovery begins; a recovery target uses its recorded `<delivery-branch>-complete` branch and PR. Require the checkout to equal that phase branch. On mismatch, report the current and expected branches and stop; do not stash, switch, or infer why the branches differ. If the original PR is closed without merge, stop and report that it cannot be finalised on that delivery path. Confirm every current external finding is terminally resolved before archive finalisation.
4. For an active direct delivery, retain the implementation commit and branch already recorded by `commit`. Form the delivered-name set, re-read every other active `status.json`, remove only matching explicit dependencies, generate the parent summary, set `status: "complete"` and `archived_at`, and archive the delivery set as one recoverable mutation. Do not add `delivery.completion` or fabricate PR evidence. Stage only those archive files and the changed, Git-tracked dependency records, then commit and push the finalisation before clearing the matching selector.
5. For an active branch delivery whose original PR is open, form the delivered-name set, re-read every other active `status.json`, remove only matching explicit dependencies, generate the parent summary, add `delivery.completion` containing only the original PR `reference`, `head_branch`, and `target_branch`, set `status: "complete"` and `archived_at`, and archive the delivery set as one recoverable mutation. Preserve `updated_at` and unrelated fields. Stage only those archive files and the changed, Git-tracked dependency records, then commit and push this archival update to the same PR. The original delivery authority covers that update. Do not write an archival commit SHA or completion event.
6. If the original PR has already merged before archival delivery, synchronise the recorded target branch, then create or reuse `<delivery-branch>-complete`. Archive and commit the delivery set there, push it, and open the recovery PR under the additional delivery-authority boundary. This is the only permitted second PR. It only delivers the missed archive commit: do not add recovery identity to, or otherwise rewrite, the archive.
7. After an archival update reaches its current PR, request auto-merge when the repository permits it. If CI, review, merge eligibility, or auto-merge enablement is outstanding, report that exact condition and retain the selector. Do not poll or subscribe for external updates.
8. On explicit resumption, determine and perform only the first missing phase: archive mutation, archival commit, push, PR update or recovery PR, auto-merge request, merge confirmation, or target synchronisation. After the relevant original or recovery PR merges, synchronise its target branch without reset or force operations and remove only the matching selector. Do not change the archive during synchronisation.
9. A named non-selected target remains non-selected throughout.

## Boundaries

- Never act when the current-phase branch guard fails.
- Never discard staged or unstaged work. If tracked changes prevent the exceptional recovery branch switch, stop and let the user decide how to preserve them; untracked files do not require preservation.
- Do not merge a PR before its archival finalisation reaches that PR; request auto-merge instead.
- Do not add a delivery-tracking store, notification service, polling loop, inferred branch relationship, automatic branch deletion, mutable completion event, or completion commit SHA.
- A jointly archived sidecar has no separate completion cycle; its parent owns shared finalisation delivery.

## Next

- `complete <change-name>` — resume only the missing finalisation phase or synchronise after the relevant external merge.
- `triage <change-name>` — when external feedback arrives before archive finalisation.
