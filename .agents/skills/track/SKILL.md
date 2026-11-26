---
name: track
specle_group: Integration
requires:
  - define
description: >-
  Link Specle work to configured external sources and destinations.
usage: >-
  Use for explicitly named external imports, source checks, or authorised destination publishing; never write to a source.
---

# External work-source integration

Bridge a Specle change with external work sources and an optional delivery destination
configured for this project. A source supplies incoming work; a destination receives published
work information. They are separate roles, even when the same external system serves both.

Read `.agents/project/tracking.md` before selecting a connector, identifier convention, link format, or permitted operation. Do not infer configuration from available tools or from a user mentioning a generic issue.

If the requested source, destination, or required connection is not configured, explain that clearly and stop before reading or writing externally.

## Capabilities

When the configured connection supports the requested operation:

1. **Import sources:** fetch one or more explicitly named source items and consolidate their summary, description, acceptance criteria, and relevant discussion into the chosen change, preserving source links.
2. **Check sources:** fetch recorded source items and present a change report. Never modify a change until the user confirms the proposed changes.
3. **Publish destination:** create or update only the configured destination record, and only when the user explicitly requests the permitted publish action.

## Workflow

1. Read `.agents/project/tracking.md`, `.specle/current-change` when present, and the target `status.json`. Default the target to the selected normal change. A `bugfix` or `refactor` is a valid target only when the user explicitly names it; never select a sidecar implicitly.
2. Identify the requested operation: import, check sources, or publish destination. Identify the configured source item or destination record by its project-guidance convention.
3. For an import, use the selected existing target change. If the user asks to establish a new change and no unfinished active change would be displaced, use `define` to create it before importing. Otherwise, ask which existing or new change should receive the imported material.
4. Use only the connector or tool named by the project's tracking guidance. Source operations are read-only.
5. Record links in `.specle/changes/<change>/tracker-links.json`:
   - `$schema` is `specle://schemas/tracker-links/1.0`.
   - `sources` is an array of objects with `system`, `kind`, `id`, and canonical `url`.
   - `destination` is either `null` or an object with the same identifying fields.
   - Preserve existing links and do not invent identifiers or URLs.
6. Report the items read or published, including canonical links. State whether any proposed change change still needs user confirmation.

## Boundaries

- Do not write to a source. Do not write to a destination without explicit user authorisation.
- Do not configure or infer external systems; project tracking guidance is authoritative.
- Do not attach a source or destination link to an unselected bugfix or refactor unless the user explicitly names that target.
- Preserve source and destination links in the per-change JSON record; do not use a shared runtime cache or invent generic identifiers.
- Use `define` to establish a new import target, `revise` for confirmed changes to an existing normal change, and `verify` after implementation.
