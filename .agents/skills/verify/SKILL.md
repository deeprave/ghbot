---
name: verify
specle_group: Quality
description: >-
  Verify implementations against changes and quality gates.
usage: >-
  Use after implementation tasks are complete and before review; check every requirement and documented gate against current code and tests.
lifecycle:
  accepts:
    - building
  transitions:
    - from: building
      to: verified
      next: review
---

# Verify implementation against change

Verify that the current change implementation actually satisfies its requirements — matching
every acceptance criterion, closing gaps, adhering to the recorded guidance, and passing the
project quality gates.

Do **not** trust recorded status (checked `[x]` tasks or a `spec.md` that says "passing"). Re-verify
against the working tree every time.

Use the project's documented command runner for every command.

## Step 1 — Establish what to verify

Before applying or recording a lifecycle transition, consult this skill's `lifecycle` frontmatter declaration.

1. Read `.specle/current-change` when present and discover active changes by their `status.json`. Unless the user names an abbreviated change, verify the locally selected change. If the selected target has `kind: "spike"`, stop: spikes complete from recorded findings and do not enter verification.
2. Locate the target change and read its documents in full:
   - A normal selected change has `requirements.md`, whose **acceptance criteria** (`SHALL` clauses) and optional `## Contract` `checks[]` array are the conformance checklist. Read its `design.md`, `tasks.md`, and `spec.md` when present.
   - A named `bugfix` may omit `requirements.md` and `design.md`. Its `spec.md` must state the bug, expected and actual behaviour, reproduction when inferable, root cause, fix approach, and regression-test evidence.
   - A named `refactor` may omit `requirements.md` and `design.md`. Its `spec.md` must state the current and target state, behavioural invariants, baseline or characterisation evidence, and refactor approach.
   - Every target needs `tasks.md` and `spec.md`. Stop and report an incomplete abbreviated contract rather than treating it as a normal change.
3. Read the relevant policy and steering docs so you can check adherence:
   `.agents/policies/{lifecycle,testing}.md`, applicable `.agents/steering/` overrides, and all applicable authoritative
   `.agents/project/` documents.

Only `bugfix`, `refactor`, and `committed` normal changes may be verified as explicitly named non-selected work. Never choose a non-selected item implicitly; preserve `.specle/current-change` throughout such a verification.

## Step 2 — Run the project quality gates

Read the project's documented verification commands and run every required gate, recording
pass/fail and relevant failure output. A failure in any required gate means the implementation does
not pass verification, regardless of the acceptance-criteria review.

## Step 3 — Verify task completeness

- Confirm every task in `tasks.md` is marked `[x]`. List any that are not.
- For each completed task, confirm the claimed change actually exists in the code/tests (spot-check
  the files the task names). A checked box with no corresponding code is a gap, not a pass.

## Step 4 — Check the verification contract

For a normal selected change, go through each requirement's `SHALL` clauses (and each `Contract.checks[]` entry, if present) one by one. For each, find the concrete evidence:

- the code that implements it (cite `file:line`), and
- the test that exercises it (cite the test name/file).

For a named abbreviated change, check its documented contract instead:

- **Bugfix** — the reported defect no longer occurs, regression coverage demonstrates the expected behaviour, and the implementation remains a bounded repair.
- **Refactor** — every stated behavioural invariant remains true, the documented baseline or characterisation evidence passes, and no intentional feature behaviour was introduced.

Mark each criterion or abbreviated validation check **PASS / FAIL / PARTIAL**:

- **PASS** — implemented and covered by a test.
- **PARTIAL** — implemented but untested, or tested but the implementation diverges in a detail.
- **FAIL** — not implemented, or contradicted by the code.

Pay particular attention to the criteria the change identifies as easy to get wrong, including
boundary values, error handling, and external-interface details.

## Step 5 — Gaps, completeness, and change adherence

- **Coverage gaps** — any change requirement with no implementation and/or no test.
- **Scope creep** — implementation behaviour that is *not* in the change (flag it; it may need a change
  update or removal).
- **Guidance adherence** — confirm the implementation follows the portable policy, steering overrides, and all
  applicable project standards, including dependency, API, testing, and secret-handling rules.

## Step 6 — Report

Produce a clear verification report:

- **Overall: PASS / FAIL** (FAIL if any gate fails, any acceptance criterion is FAIL, or any task is
  incomplete).
- **Quality gates** — one line for each documented project gate.
- **Tasks** — `X/Y` complete; list incomplete ones.
- **Acceptance criteria or abbreviated validation checks** — a table of check → PASS/PARTIAL/FAIL → evidence (`file:line` / test).
- **Gaps & adherence** — bulleted list of coverage gaps, scope creep, and any policy or steering violations.
- **Next step** — if PASS, use `review`; if FAIL, list the specific fixes needed before
  re-verifying (use `build` to fix, then re-run `verify`).

After reporting, update only the target `status.json` according to `lifecycle.md`, writing current Unix-second `updated_at` with every status mutation. For a selected normal change, a PASS records verification as `pass`, resets a stale review to `not-run`, and sets status `verified`; a FAIL records verification as `fail` and sets status `building`. For a named committed normal target, a PASS sets only its matching status to `verified`; a FAIL leaves only that status `building`. For a named abbreviated change, a PASS sets only its status to `verified`; a FAIL leaves only that status `building`. Verification alone never marks a change complete.

Keep evidence concrete (cite files, lines, and test names). Do not report PASS on a criterion whose
only support is a checked task box or a claim in `spec.md`.

On PASS, read `.agents/project/automation.md`. In `decision-gated` mode, invoke `review <change-name>`; on FAIL, stop with the required remediation.
