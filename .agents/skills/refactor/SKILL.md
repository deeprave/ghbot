---
name: refactor
specle_group: Alternatives
description: >-
  Restructure code without changing observable behaviour.
usage: >-
  Use for structural cleanup protected by documented invariants and tests; use change when new behaviour is needed.
lifecycle:
  accepts:
    - defined
    - planned
    - building
  creates:
    - defined
    - planned
  transitions:
    - from:
        status: planned
        kind: refactor
      to:
        status: building
        kind: refactor
      next: verify
---

# Refactor (no behaviour change)

Improve structure while keeping behaviour identical, with explicit invariants and tests as the guardrail, without displacing unrelated active work.

## Workflow

Before applying or recording a lifecycle transition, consult this skill's `lifecycle` frontmatter declaration.

1. Read `.specle/current-change` when present. Preserve the local selected change; this workflow must not replace it.
2. Read the relevant authoritative `.agents/project/` documents and the codebase area being refactored.
   If the user names an existing refactor, locate its matching `kind: "refactor"` status record and read its `spec.md` and `tasks.md`; reuse those artifacts and skip directly to step 6. Do not create another directory or status record.
3. Create a change folder `.specle/changes/<slug>/` with a short `spec.md`, using a slug unique across active and archived changes, containing:
   - Current state and target state.
   - Behavioural invariants that must remain true.
   - Baseline or characterisation evidence to establish before restructuring.
   - Refactor approach.
4. Add a matching versioned `status.json` with `kind: "refactor"`, `status: "defined"`, `created_at` set to current Unix seconds as a JSON number, `activated_at: null`, empty progress, `not-run` verification/review, `delivery: null`, and empty relationships/dependencies. Do not change `.specle/current-change`.
   When selected parent work exists and the user intends concurrent delivery, record a reciprocal relationship in both records as one recoverable mutation: the parent names this change with `type: "refactor"` and `delivery: "with-related-change"`; this sidecar names the parent with `type: "origin"` and the same delivery value. If both records cannot be updated, stop with an actionable diagnostic; do not execute a half-linked sidecar. Otherwise, do not execute unlinked abbreviated work in that worktree and direct the user to `prepare` it for later named execution in a separate worktree.
5. Create `tasks.md` with incremental steps:
   - Confirm the relevant baseline tests pass or add focused characterisation coverage.
   - Record the behaviour-preserving invariants for each affected area.
   - Make one small cohesive production-code or test-code restructure at a time.
   - Run focused checks after every cycle, then repeat until the target structure is reached.
   - Run the documented quality gates before verification.
6. Before implementation while active work exists, require the user to establish the explicit relationship in step 4; otherwise prepare the refactor without implementation and direct later named execution in a separate worktree.
7. If the user asks to prepare the refactor without implementation, update only the matching status to `planned` with current Unix-second `updated_at`, then report its generated name and stop. Later `refactor` and `verify` requests must name that refactor explicitly.
8. Otherwise, execute the linked tasks immediately; mark them `- [x]` as you go. Update only the matching status to `building` with current Unix-second `updated_at` when implementation starts.

## Critical

- Do not intentionally change observable behaviour or add features. If that becomes necessary, stop and use the normal `define` workflow.
- Tests may be restructured alongside production code, including renaming fixtures, helpers, and test cases that expose renamed internals, when their coverage remains equivalent or stronger for the recorded invariants.
- A refactor is non-selected work. Never replace `.specle/current-change`.

## Next

- `refactor <change-name>` — resume a prepared named refactor.
- `verify` — verify the named refactor against its abbreviated contract and update its status without selecting it.

After successful execution, read `.agents/project/automation.md`. In `decision-gated` mode, invoke `verify <change-name>`; otherwise report it and wait.
