---
name: review
specle_group: Quality
requires:
  - verify
description: >-
  Review verified implementations for quality and policy compliance.
usage: >-
  Use only after verification passes to assess implementation quality, guidance compliance, coverage, and security; it records approval or findings but does not implement fixes.
lifecycle:
  accepts:
    - verified
  transitions:
    - from: verified
      to: approved
      next: commit
    - from: verified
      to: review-findings
      next: triage
---

# Review a verified implementation

Review a verified Specle target against the repository's standards. This is a distinct quality
gate, not a substitute for verification or a client-specific pull-request workflow.

## Workflow

Before applying or recording a lifecycle transition, consult this skill's `lifecycle` frontmatter declaration.

1. Read `.specle/current-change` when present, the selected target's `status.json`, `.agents/policies/{lifecycle,testing,review,delivery,context}.md`, applicable `.agents/steering/` overrides, and the relevant authoritative `.agents/project/` documents. A reviewing agent is one that neither built nor participated in design; it may read local hand-off context but updates it only when project policy explicitly permits them.
2. Select the target. By default it is the locally selected change, which must have `status: "verified"`. A non-selected target must be explicitly named and have `status: "verified"`; it never replaces the local selection. Reject archived targets: they are immutable, and a later defect uses independent work. A spike does not enter review; report its findings and optional outcome change instead. If the selected implementation target is not verified, stop and direct the user to `verify` (or `verify <change-name>`); do not run verification implicitly.
3. Read the target's `spec.md` and `tasks.md`, plus `requirements.md` and `design.md` when present. For abbreviated work, use its abbreviated verification contract in `spec.md`.
4. Get the target changes with `git diff` and `git diff --staged`. Scope the review to files named by the target's task plan or explicitly named by the user; do not treat unrelated working-tree changes as part of the target.
5. Check compliance with the portable policy, applicable steering overrides, and project architecture, API, security, and test guidance. Evaluate correctness, readability, test coverage, security, and performance.

## Output

`APPROVE` or `REQUEST_CHANGES`, with specific, actionable findings (cite `file:line`) and a P1–P6 severity. Keep findings concrete; separate must-fix from nice-to-have.

After reporting, record raw findings in `.specle/changes/<target>/review-findings.json`. Add a source record for this review with a stable local identifier and revision or diff fingerprint. Each raw finding records its source ID, severity, description, evidence, state `new`, and empty decision and route fields. Then record the review outcome and current Unix-second `updated_at` in the target `status.json` as required by `lifecycle.md`:

- `APPROVE` records review `pass` and changes the selected target to `approved`. `REQUEST_CHANGES` records the finding count and changes it to `review-findings`.
- For a named non-selected target, update only its matching status and never change the local selection. A re-reviewed committed target must retain its delivery reference for the later `commit` update.

## Next

After an `APPROVE`, stop for commit authorisation. After `REQUEST_CHANGES`, read `.agents/project/automation.md`; in `decision-gated` mode invoke `triage <change-name>`, which collects user decisions and stops at its final summary.

- `triage` — decide how to handle review findings before addressing them.
- `commit` — deliver an approved change according to the project policy.
