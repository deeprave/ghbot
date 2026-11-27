---
name: resolve
specle_group: Quality
requires:
  - triage
  - revise
  - prepare
  - bugfix
  - refactor
  - define
description: >-
  Dispatch accepted review decisions to follow-up workflows.
usage: >-
  Use only after triage has recorded decisions for all current findings; route accepted work without implementing it directly.
lifecycle:
  accepts:
    - triaged
  transitions:
    - from: triaged
      to: planned
      next: build
    - from: triaged
      to: approved
      next: commit
    - from: triaged
      to: committed
      next: complete
---

# Resolve triaged review findings

Before applying or recording a lifecycle transition, consult this skill's `lifecycle` frontmatter declaration.

Dispatch recorded review decisions without revisiting the triage or silently implementing work outside the selected workflows.

## Workflow

1. Read `.specle/current-change` when present, the target `status.json`, `.agents/policies/{lifecycle,review}.md`, applicable `.agents/steering/` overrides, `.agents/project/review.md`, and the target's `review-findings.json`.
2. Select the target. Default to the locally selected normal change. A non-selected target must be explicitly named. A committed normal change, bugfix, or refactor never replaces `.specle/current-change`. Require an active target with `status: "triaged"` and a decision for every current finding; otherwise, stop and direct the user to `triage`.
3. Reconcile existing accepted or varied-action dispatches before dispatching new work. For each recorded resulting work item, determine whether it is complete, incomplete, or failed. Record completed outcomes and do not dispatch them again. Incomplete or failed follow-up work keeps the target `triaged`; report that work item's next step and `resolve <target>` as the reconciliation step after it completes.
4. Identify accepted or varied findings without a completed dispatch. Group ordinary follow-up routes by their recorded route and process groups in P1–P6 order. Keep an independent `define` route pending until every other current finding is terminally no-action or has a completed follow-up. Do not reopen declined, skipped, deferred, duplicate, or completed-dispatch findings.
5. Dispatch each pending accepted or varied group according to its recorded route. Preserve whether its decision was `accept` or `vary`:
   - `revise` — revise the target normal change or explicitly named abbreviated target in place.
   - `prepare-bugfix` or `prepare-refactor` — create a named prepared sidecar; this is the default for new bounded follow-up work.
   - `bugfix` or `refactor` with `execution: "execute"` — execute the selected abbreviated workflow only when the user decision or automatic policy explicitly authorises it.
   - `define` — only after every other current finding is settled, create the independent normal change as unselected `defined` work. Do not complete the origin: restore it to `approved` when it has only local review history or `committed` when it has a submitted delivery, then direct it to its own delivery step. Until then, leave the route pending and report the remaining work. A named non-selected target must preserve the unrelated local selection.
6. Update each dispatched finding in `review-findings.json` with its dispatch state, selected workflow, execution mode, resulting change name when applicable, and any failure or deferred reason. Preserve all source history and decisions.
7. Let each downstream workflow own its lifecycle transition. Do not mark the originating review target complete merely because accepted or varied decisions were dispatched. A committed normal change with accepted or varied implementation work returns through build, verification, review, approval, and commit. For active targets, when every current finding is terminally no-action (`decline`, `skip`, `defer`, or `duplicate`) or has a completed dispatched follow-up, record `review.status: "resolved"` with `findings: 0` and current Unix-second `updated_at`. Restore a previously committed target to `committed` and direct the user to `complete`; restore a locally reviewed target to `approved` and direct the user to `commit`. Only a target whose configured delivery outcome is already evidenced may become `complete`. Never change `.specle/current-change` for a named non-selected target. Report the terminal dispositions and every resulting work item.

## Boundaries

- Do not re-triage, alter decisions, or downgrade severity.
- Do not implement code, tests, or task steps directly; only the selected downstream workflow may do so.
- Do not write to external review sources, pull-request threads, or tracker records.
- Do not dispatch a direct execution route without explicit recorded authorisation.

## Next

After explicit invocation and successful dispatch, read `.agents/project/automation.md`. In `decision-gated` mode, continue through the selected downstream local workflow with its explicit target name; never bypass a downstream preflight or delivery boundary.

- If a dispatched accepted or varied follow-up remains incomplete, follow its reported next step, then invoke `resolve <target>` to reconcile it.
- When Resolve completes the selected target, no lifecycle step remains.
