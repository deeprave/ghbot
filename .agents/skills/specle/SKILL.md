---
name: specle
specle_group: Reference
description: >-
  Describe the installed Specle workflow and skill inventory.
usage: >-
  Use when a user asks what Specle does, which skills are available, what a skill does, or where to begin.
---

# Describe Specle

Produce a read-only presentation of the installed Specle skill index. Do not update changes, context, source files, or the index.

## Workflow

1. Read the installed Specle skill-index resource. For a filesystem installation it is `<skills-location>/specle/index.json`; another provider, such as MCP, may expose the same logical resource by URI.
2. If the index is unavailable, explain that the installed Specle distribution must be initialised, updated, or indexed; do not scan arbitrary skill directories as a fallback.
3. Read each group's `name`, then each indexed skill's `name`, `description`, and `usage`.
4. Choose the presentation for the user's request: use concise descriptions for a navigation overview, include usage when the user asks which skill to choose or how one applies, and include both when that improves a comparison. Present grouped skills in the index's defined order.
5. Do not describe a skill as a slash command or list skills absent from the index.

Keep the result concise: this is a navigation aid, not a replacement for reading the selected
skill before using it.
