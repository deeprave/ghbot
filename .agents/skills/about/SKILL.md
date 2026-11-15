---
name: about
description: >-
  Describe the project-local skills and their lifecycle order. Use when asked what skills exist,
  what a skill does, or how the spec-driven workflow fits together.
---

# Describe the local skills

Produce a read-only inventory of `.agents/skills/`. Do not update specs, context, or source files.

## Workflow

1. Enumerate every immediate skill directory containing `SKILL.md` and read its frontmatter
   description.
2. Present one Markdown table with **Skill** and **Description** columns. In the description,
   combine the workflow point with the skill's purpose. Order rows as follows, retaining this
   order within a group:

   | Sequence | Skill |
   | --- | --- |
   | Reference, any time | `about` |
   | Set up a project overlay | `onboard` |
   | Choose work | `status` |
   | Investigate before specifying | `analyse`, `spike` |
   | Optional issue tracking | `track` |
   | 1. Specify | `spec` |
   | 2. Size (optional) | `estimate` |
   | 3. Design (normally M+) | `design` |
   | 4. Break down | `tasks` |
   | 5. Build | `build` |
   | 6. Verify | `verify` |
   | 7. Review | `review` |
   | After delivery, when useful | `demo` |
   | Between lifecycle stages when requirements change | `revise`, then `refresh`, `design`, and `tasks` as needed |
   | After major progress or context compaction | `context` |
   | Alternative bug path | `fix`, then `verify` |
   | Alternative behaviour-preserving path | `refactor`, then `verify` and `review` |

3. Use each skill's frontmatter description as the basis for a concise purpose. Do not describe a
   skill as a slash command.
4. Compare the discovered directory names with the ordered list. If a skill is not classified,
   add it in a final **Other local skills** section rather than omitting it. If a listed skill is
   absent, say so plainly.

Keep the result concise: this is a navigation aid, not a replacement for reading the selected
skill before using it.
