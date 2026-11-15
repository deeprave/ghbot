---
name: status
description: >-
  List defined repository specs that still need planning, implementation, or lifecycle work.
  Use when asked what specs remain, which specs are unfinished, or to inventory pending work.
---

# List pending specs

Produce a read-only inventory of actionable specs under `.agents/specs/`. Do not change `.current`,
`CONTEXT.json`, spec files, or the working tree.

## Workflow

1. Read `.agents/.current`, `.agents/CONTEXT.json`, and `.agents/steering/lifecycle.md` first.
   Include the active spec whenever its recorded lifecycle status is not `complete`.
2. Enumerate immediate directories under `.agents/specs/`, ordered by their directory name.
3. For each spec, inspect `tasks.md` when present. Count Markdown task boxes at any indentation
   level:
   - no `tasks.md` — report its recorded lifecycle state when available, otherwise **defined**;
   - use checkbox counts only as progress; never infer lifecycle status or completion from them.
4. Report a compact table headed **Pending specs** with **Status**, **Spec**, **Size**,
   **Depends on**, **Progress**, and **Next** columns:
   - display the spec's slug without its leading `YYYY-MM-DD-` directory prefix;
   - read the T-shirt size from `estimate.md` when present, otherwise display `—`;
   - read explicit dependencies from the queued-spec context record or an `## Dependencies`
     section in `estimate.md`, listing their short spec slugs, otherwise display `—`;
   - use the recorded lifecycle state as the status;
   - report checkbox progress only when `tasks.md` exists; and
   - derive the next skill from the recorded lifecycle status using `lifecycle.md`.
5. After the table, state the count and identify the current spec and its recorded lifecycle status.
   If there are no pending entries, say so directly.

Also include any completed spec that is an explicit dependency of a pending spec, with `Next` shown
as `—`. Do not count that dependency-context row as pending work.

Task completion alone is not proof that an older spec was verified, reviewed, or committed. If the
user asks for a full audit, add a separate **Task-complete specs** section for omitted entries and
label them as requiring historical verification rather than calling them complete.

## Boundaries

- This is an inventory command, not a substitute for `verify`.
- Never activate, archive, edit, or delete a spec while listing it.
