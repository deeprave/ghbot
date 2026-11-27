---
name: changes
specle_group: Coordination
description: >-
  List pending and active Specle changes with next stages.
usage: >-
  Use to inventory unfinished, selected, unselected, or dependent changes and report their recorded next steps; it never changes lifecycle state.
---

# Show changes

Produce a read-only inventory of actionable changes under `.specle/changes/`. Terminal archives are historical evidence, not pending delivery. Do not change
`.specle/current-change`, per-change `status.json` files, change files, or the working tree.

## Workflow

1. Read `.specle/current-change` when present and `.agents/policies/lifecycle.md` first, then any applicable steering override.
   Include the selected change whenever its recorded lifecycle status is not terminal.
2. Enumerate immediate directories under `.specle/changes/`, ordered by their directory name, and read each `status.json`. Exclude a record already marked terminal from pending output unless it is explicit dependency context; terminal archival owns moving it out of the active location.
   Do not treat archived complete or cancelled records as pending work. An archived complete record's original PR is checked only by an explicitly invoked `complete`.
3. For each change, inspect `tasks.md` when present. Count Markdown task boxes at any indentation
   level:
   - no `tasks.md` — report its recorded lifecycle state when available, otherwise **defined**;
   - use checkbox counts only as progress; never infer lifecycle status or completion from them.
4. Report a compact table headed **Pending changes** with **Kind**, **Status**, **Change**, **Size**,
   **Depends on**, **Progress**, and **Next** columns:
   - read `kind` from the matching status record;
   - display the change's directory slug;
   - read the T-shirt size from `estimate.md` when present, otherwise display `—`;
   - read explicit dependencies from the target status record or an `## Dependencies`
     section in `estimate.md`, listing their short change slugs, otherwise display `—`;
   - use the recorded lifecycle state as the status;
   - report checkbox progress only when `tasks.md` exists; and
   - derive the next skill from recorded lifecycle status and kind using `lifecycle.md`.
5. After the table, state the count and identify the locally selected change and its recorded lifecycle status.
   If there are no pending entries, say so directly.

For a selected normal parent, also list only sidecars declared by the parent's own `relationships` entries with `delivery: "with-related-change"`. Show each named sidecar's declared kind, reciprocal-link validity, status, and next step. Report missing, mismatched, duplicate, or unready declarations rather than inferring sidecars from shared files, ordering, or worktree state.

Also include any terminal archived change that is an explicit dependency of a pending change, with `Next` shown
as `—`. Do not count that dependency-context row as pending work.

Task completion alone is not proof that an older change was verified, reviewed, or committed. If the
user asks for a full audit, add a separate **Task-complete changes** section for omitted entries and
label them as requiring historical verification rather than calling them complete.

## Boundaries

- This is an inventory command, not a substitute for `verify`.
- Never activate, archive, edit, or delete a change while listing it.
