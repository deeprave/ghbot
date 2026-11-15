---
name: track
description: >-
  Integrate specs with the project-configured issue tracker. Use when asked to import tracked
  requirements, synchronize a spec, or create tracked work items and subtasks.
---

# Project-tracker integration

Bridge specs and the issue tracker configured for this project. Read
`.agents/project/tracking.md` before selecting a tracker, connector, identifier convention, or
link format. Do not infer a tracker from available tools or from a user mentioning a generic issue.

If the project tracking guidance does not configure a tracker or its required connection, explain
that clearly and stop before reading from or writing to any external tracker.

## Capabilities

When the configured tracker and its connection support the requested operation:

1. **Import requirements:** fetch named work items; consolidate their summary, description,
   acceptance criteria, and relevant discussion into the active or new spec, with source links.
2. **Check for updates:** fetch the linked work items and present a change report. Never modify a
   spec until the user confirms the proposed changes.
3. **Synchronize outward:** create or update a technical-specification work item only when the
   user explicitly requests it.
4. **Create subtasks:** create tracker subtasks from `tasks.md` only when the user explicitly
   requests it.

## Workflow

1. Read `.agents/project/tracking.md`, `.agents/CONTEXT.json`, and the active spec as relevant.
2. Identify the configured tracker and the requested operation.
3. Use only the connector or tool named by the project's tracking guidance.
4. Record linked items in `tracker-links.json`, including the tracker name, item identifiers, and
   canonical URLs. Reflect concise link state in `.agents/CONTEXT.json`.
5. Report the items read, created, or updated, including links.

## Boundaries

- Do not make external tracker changes without explicit user authorization.
- Preserve source links and tracker-specific identifiers; do not invent generic identifiers.
- Use `spec` or `verify` after importing requirements, and `tasks` before creating subtasks.
