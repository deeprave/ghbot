---
name: wrapup
specle_group: Integration
requires:
  - complete
  - triage
description: >-
  Merge a recorded archival completion PR and synchronise delivery.
usage: >-
  Use after complete has archived a change and recorded a completion PR; merge that PR or synchronise an externally merged one without changing the archive.
lifecycle:
  accepts:
    - complete
---

# Wrap up archival delivery

Finish the externally delivered archival finalisation for one archived completed change. This workflow never changes the archived record.

## Workflow

1. Read `.specle/current-change` when present, `.agents/policies/{lifecycle,delivery}.md`, applicable project delivery guidance, and the named or selected archived change's `status.json`.
2. Resolve the target under `.specle/archive/`. Require `status: "complete"` and a `delivery.completion` object containing the completion PR reference, head branch, and target branch. Do not infer a completion PR.
3. Inspect the recorded completion PR. If it has unresolved external feedback, report `triage <change-name>` and stop. If it is open but cannot merge or lacks required checks, report that external state and stop. If it is already merged, do not attempt another merge.
4. Before an authorised merge or synchronisation, preserve tracked staged and unstaged work in one named recoverable `git stash`. If stashing fails, stop. Do not stash untracked or ignored generated files; accept the rare ignored-file collision risk.
5. With explicit delivery authority, merge the open completion PR when necessary, switch to the recorded completion target branch, and fast-forward it from upstream without reset or force operations.
6. Restore the stash. If restoration fails, retain it and report recovery steps; do not remove `.specle/current-change`.
7. After successful merge, synchronisation, and restoration, remove `.specle/current-change` only when its current contents still name this archived parent change. A completion PR that also contains reciprocal sidecars finalises the whole delivery set; do not run wrapup separately for those sidecars. Do not write `status.json`, summary files, archive contents, commits, or pull requests.

## Boundaries

- Do not generate summaries, move change directories, alter archived records, or create a completion PR.
- Do not merge unresolved or failing completion PRs.
- Do not discard a failed stash restoration.

## Next

No lifecycle step remains after successful wrapup.
