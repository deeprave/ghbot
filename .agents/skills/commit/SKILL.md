---
name: commit
specle_group: Integration
requires:
  - review
description: >-
  Deliver approved Specle work according to project policy.
usage: >-
  Use after local review approves a change, bugfix, or refactor to prepare or perform its configured commit, push, and pull-request delivery actions.
lifecycle:
  accepts:
    - approved
    - complete
  transitions:
    - from: approved
      to: committed
      next: complete
---

# Commit approved work

Prepare or perform delivery for an approved target, or deliver post-triage related work to a selected archived completion PR. This skill distinguishes local approval from final external delivery.

## Workflow

Before applying or recording a lifecycle transition, consult this skill's `lifecycle` frontmatter declaration.

1. Read `.specle/current-change` when present, the selected target's `status.json`, `.agents/policies/{lifecycle,delivery,testing}.md`, applicable `.agents/steering/` overrides, and `.agents/project/{delivery,security,testing}.md`.
2. Select the locally selected approved target by default. A non-selected ordinary target must be explicitly named, have `status: "approved"`, and must not replace `.specle/current-change`. A selected archived `complete` target is valid only for the narrow completion-review delivery in step 7. Stop if delivery policy is missing or incomplete; direct the user to `onboard`.
3. Read the target's tasks, review evidence, and, where present, its `delivery` field in its `status.json`. Do not infer a delivery reference from a branch or pull request.
4. For a normal parent target, derive candidate sidecars only from its own `relationships` entries with `delivery: "with-related-change"`. Require every candidate to be an active `bugfix` or `refactor` with matching parent name, matching parent-declared kind, one reciprocal declaration, and `status: "approved"`. Stop with an actionable diagnostic for a missing, duplicate, mismatched, or unready candidate. Include every validated sidecar and no inferred or unrelated work. Run project-required pre-delivery checks, including any configured secret check.
5. Explain the exact planned action and obtain explicit user authorisation before any external write. If authority or policy is absent, provide exact instructions and leave the target approved.
6. Apply the selected model:
   - **Local-only Git:** create the authorised local commit, record identical applicable evidence with current Unix-second `updated_at` on the parent and each validated sidecar, and move every delivered member to `committed` for joint archive finalisation.
   - **Direct shared upstream:** create the authorised delivery-branch commit and push it. Record identical applicable evidence with current Unix-second `updated_at` on every delivered member, then move them to `committed` for joint archive finalisation.
   - **Branch and pull request:** create or update the approved branch delivery, push it, and create or update the reviewable change request. Record its delivery reference, head branch, target branch, current delivery event, and Unix-second `updated_at` in each delivered member's `status.json`, then move every delivered member to `committed`.
7. For a selected archived complete target with recorded `delivery.completion` identity, require completed explicit archived triage. Stage only that archive's `review-findings.json` and resolved related bugfix/refactor work, commit and push them to the recorded completion branch, and thereby update the existing completion PR. Do not change the archived status, timestamps, delivery evidence, summary, or any other archived artifact.
8. Preserve `.specle/current-change` whenever the selected target is non-selected. Report the delivery members, evidence recorded, and next delivery action. For branch-and-pull-request delivery, state: `Next: complete` to merge and finalise delivery, or `triage <change-name>` to address external reviews. For completion-review delivery, state: `Next: wrapup <change-name>`.

When a local-only or direct-delivery operation completes an included abbreviated sidecar, retain its relationship and delivery evidence in its own status before completion finalisation archives it.

## Boundaries

- Never make an external write without explicit user authorisation and applicable project policy.
- Never stage unrelated files or infer a branch, destination, pull-request format, or secret-scanning policy.
- Completion-review delivery may include only the recorded archive's `review-findings.json` and its resolved related corrective work.
- Do not merge a pull request; `complete` owns final branch-and-pull-request delivery.
- Do not create a separate delivery record or depend on queued future schema work.

## Next

- `complete` — to merge and finalise a committed branch-and-pull-request delivery.
- `complete` — after a recorded final local-only or direct-delivery event, to archive the completed change.
- `triage <change-name>` — when external review feedback arrives for a committed target.
