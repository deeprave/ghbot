---
name: bugfix
specle_group: Alternatives
description: >-
  Fix bounded defects with abbreviated test-first work.
usage: >-
  Use for a clear, bounded defect that needs a reproduction and regression test; use change when the work introduces new behaviour or broader scope.
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
        kind: bugfix
      to:
        status: building
        kind: bugfix
      next: verify
---

# Bugfix (abbreviated TDD)

Resolve a defect with a lightweight, reproduce-first flow without displacing unrelated active work.

## Workflow

Before applying or recording a lifecycle transition, consult this skill's `lifecycle` frontmatter declaration.

1. Read `.specle/current-change` when present and preserve its selected change; this workflow must not replace it.
2. Read the relevant authoritative `.agents/project/` documents, then understand the bug from the description and inspect the codebase to find the relevant area.
   If the user names an existing active bugfix, locate its matching `status.json` and read its `spec.md` and `tasks.md`; reuse those artifacts and skip directly to step 6. Do not create another directory or status record.
3. Create a change folder `.specle/changes/<slug>/` with a short `spec.md`, using a slug unique across active and archived changes, containing:
   - Bug description.
   - Expected behaviour and actual behaviour.
   - Steps to reproduce, if inferable.
   - Root-cause analysis and fix approach.
   - Regression-test evidence to establish during the work.
4. Add a matching versioned `status.json` with `kind: "bugfix"`, `status: "defined"`, `created_at` set to current Unix seconds as a JSON number, `activated_at: null`, empty progress, `not-run` verification/review, `delivery: null`, and empty relationships/dependencies. Do not change `.specle/current-change`.
   When selected parent work exists and the user intends concurrent delivery, record a reciprocal relationship in both records as one recoverable mutation: the parent names this change with `type: "bugfix"` and `delivery: "with-related-change"`; this sidecar names the parent with `type: "origin"` and the same delivery value. If both records cannot be updated, stop with an actionable diagnostic; do not execute a half-linked sidecar. Otherwise, do not execute unlinked abbreviated work in that worktree and direct the user to `prepare` it for later named execution in a separate worktree.
5. Create `tasks.md` (test-first):
   - Write a failing test that reproduces the bug.
   - Implement the fix.
   - Confirm existing tests still pass.
6. Before implementation while active work exists, require the user to establish the explicit relationship in step 4; otherwise prepare the bugfix without implementation and direct later named execution in a separate worktree.
7. If the user asks to prepare the bugfix without implementation, update only the matching status to `planned` with current Unix-second `updated_at`, then report its generated change name and stop. Later `bugfix` and `verify` requests must name that bugfix explicitly.
8. Otherwise, execute the linked tasks immediately (TDD); mark them `- [x]` as you go. Update only the matching status to `building` with current Unix-second `updated_at` when implementation starts.

## Critical

- Write the failing test **first**, then fix. A bug fix without a regression test is incomplete.
- Run the regression test and the project's documented quality gates.
- A bugfix is non-selected work. Never replace `.specle/current-change`.

## Next

- `bugfix <change-name>` — resume a prepared named bugfix.
- `verify` — verify the named bugfix against this abbreviated contract and update its status without selecting it.

After successful execution, read `.agents/project/automation.md`. In `decision-gated` mode, invoke `verify <change-name>`; otherwise report it and wait.
