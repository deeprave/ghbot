---
name: cancel
specle_group: Integration
description: >-
  Archive one explicitly named active change as cancelled without claiming delivery.
usage: >-
  Use with a stable active change name to end it after required dependency and in-flight cleanup decisions.
lifecycle:
  accepts:
    - defined
    - estimated
    - designed
    - planned
    - spiking
    - building
    - verified
    - approved
    - committed
    - review-findings
    - triaged
  transitions:
    - from: defined
      to: cancelled
    - from: estimated
      to: cancelled
    - from: designed
      to: cancelled
    - from: planned
      to: cancelled
    - from: spiking
      to: cancelled
    - from: building
      to: cancelled
    - from: verified
      to: cancelled
    - from: approved
      to: cancelled
    - from: committed
      to: cancelled
    - from: review-findings
      to: cancelled
    - from: triaged
      to: cancelled
  terminal:
    - cancelled
---

# Cancel a change

Cancel one explicitly named active change when its intended work should end without claiming delivery. Cancellation archives durable history as `cancelled`; it is not a delivery method and does not replace `complete`.

## Workflow

Before applying or recording a lifecycle transition, consult this skill's `lifecycle` frontmatter declaration.

1. Require an explicit stable change name. Read `.specle/current-change` when present, relevant lifecycle and delivery policy, applicable steering and project delivery guidance, and the named target's current active `status.json`. Never default to or infer a target from `.specle/current-change`; cancel the selected change only when it is explicitly named. Reject a missing target, an archived target, or a target already in `complete` or `cancelled` without changing durable state.
2. Re-read every active `status.json` and identify only records whose explicit `dependencies` arrays name the target. Stop before durable mutation if an active record is unreadable or malformed. When dependents exist, report each dependent name and lifecycle status. Separately inspect active relationships for explicit `delivery: "with-related-change"` declarations in either direction between the target and an active partner. Report each distinct partner and tolerate a missing declaration in the other direction. Require explicit confirmation to remove the target from dependency arrays and separate explicit confirmation before removing a matching concurrent-delivery relationship that exists on a surviving partner. If the named target is a committed normal change with a committed concurrent-delivery sidecar, stop before mutation and explain the required order: handle the shared PR as directed, explicitly cancel each sidecar first, then retry cancellation of the parent. If the user declines or gives another direction, stop without durable changes.
3. For a selected target or one with recorded delivery evidence, inspect and present the current checkout facts before any lifecycle write: `git status --short --untracked-files=all`, current branch, and commits on any recorded delivery branch that are not on its recorded target branch. When direct/local delivery records `delivery.branch` and `delivery.commit`, report that already-landed commit and request direction for its branch. Present every pre-existing staged, unstaged, and untracked worktree entry separately from the planned cancellation mutation. Treat all such content as user-owned and unattributed; current selection, a path, or a branch name never proves it belongs to the target. For a non-selected target without recorded delivery-branch evidence, do not infer that checkout content belongs to it.
4. If worktree changes, relevant branch commits, direct-delivery evidence, or a recorded PR exist, explain their concrete consequence and request the user's cleanup direction before recording cancellation. The user may direct preservation, stashing or discarding local content, retaining or removing a branch, closing an open PR, or another action. Do not reset, stash, restore, switch, clean, stage, commit, push, revert, rewrite, remove a branch, or make an external change unless the user explicitly requests and authorises that separate action.
5. When delivery evidence has a PR reference, inspect only that recorded PR. An open PR must not merge: report it and require user direction for closure or other handling. For a merged PR, report that its delivered changes remain in the target branch and request direction for any remediation. If PR inspection is unavailable, report that fact and request direction; do not infer its state.
6. After every required confirmation and cleanup direction is resolved, re-read the target `status.json`, each confirmed dependent `status.json`, and each confirmed relationship-bearing partner immediately before writing. Remove only the target name from confirmed dependency arrays and only the matching concurrent-delivery relationship that exists on each surviving partner; preserve all other fields, including lifecycle status and timestamps. Update the target with `status: "cancelled"`, current numeric Unix-second `updated_at`, and `cancelled_at`; retain every other field and do not add completion or delivery evidence.
7. Move only the target directory to `.specle/archive/<name>/` without staging or committing it. Remove `.specle/current-change` only when it still exactly names the target. Leave all other worktree content untouched. Report the archive mutation and any cleanup action separately; committing, pushing, and external delivery remain user-directed actions.

## Boundaries

- Do not infer sidecars or change relationships beyond explicit declarations. A missing declaration in the other direction is tolerated.
- Do not change a record that does not explicitly depend on the target or contain an exact concurrent-delivery relationship with it.
- Do not create a pull request, tracker item, delivery event, completion record, summary, or background watcher.
- Do not claim that cancellation undoes an existing commit, branch, pull request, merge, or published work.
- Archived cancelled records are immutable. Read-only workflows may explain them by name; lifecycle work requires a new change when later work is needed.

## Next

- No lifecycle action remains for the cancelled record.
- Follow only the user-directed cleanup action, if one was requested.
