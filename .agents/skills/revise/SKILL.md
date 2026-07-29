---
name: revise
description: >-
  Revise an existing spec from new feedback, and reconcile the task list. Use when requirements
  change mid-flight or when asked to "revise the spec" / "update requirements".
---

# Revise a spec

Update the current spec for changed requirements and keep tasks consistent.

## Workflow

1. Read `.agents/CONTEXT.json` for current state.
2. Read the current `requirements.md` (or `spec.md`), and `tasks.md` if it exists.
3. Establish what feedback/changes are needed (ask if unclear).
4. Update the spec with the changes.
5. If `tasks.md` exists, reconcile it:
   - Mark affected completed tasks for **re-verification**.
   - Add new tasks for new requirements.
   - Note removed requirements (and any now-obsolete tasks).
6. Regenerate `spec-lite.md` (`/refresh`) and update `.agents/CONTEXT.json` (`/context`).

## Important

Show a **diff summary** of what changed and confirm before writing.

## Next

- `/verify` — re-check the revised spec's acceptance criteria.
- `/tasks` — regenerate tasks if the change was large.
