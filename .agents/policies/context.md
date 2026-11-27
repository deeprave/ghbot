---
specle_policy: true
---

# Hand-off context

`.specle/context.json` is an optional, ignored, worktree-local hand-off document. It transfers concise current status, recent relevant activity, material milestones, informal todos, directives, and an agent's own material actions between sessions, subagents, and reviewers. It is not a permanent record, lifecycle source, verification log, command log, diary, authoritative backlog, delivery artefact, or Git content.

## Project selection

Hand-off maintenance is enabled by default. A project may record its choices in `.agents/project/context.md`:

- whether to maintain `context.json` at all; and
- whether reviewing agents may update it.

When maintenance is disabled, agents do not create or update the document. A reviewing agent is one that neither built nor participated in the feature's design. Reviewing agents may always read it. They may write it only when the project policy explicitly allows review updates; an absent or unestablished choice does not grant that authority.

## Contents

The portable `context/1.0` shape sets `"$schema": "specle://schemas/context/1.0"`. For milestones and todos, use a non-empty human-readable local date-and-time string in `date_added`. Prefer local ISO 8601 with an explicit numeric offset, such as `2026-11-26T10:26:00+11:00`, because it remains clear between agents; this is guidance, not a workflow or schema gate.

All recognised entries may carry additional fields with values of any JSON type when they are useful to the hand-off.

- `todos` are short follow-ups with `date_added`, `subject`, optional `change`, and optional `detail`. Remove or mark one transferred when a defined change takes ownership; prune obsolete, completed, and irrelevant items.
- `directives` are current user-provided defaults, denials, or other instructions with `subject` and optional `detail`. They never override repository policy, durable change artefacts, or explicit current user instructions.
- `milestones` are additive, reverse-chronological records with `date_added`, `subject`, optional `change`, and optional `detail`. Keep a small set of milestones that remain relevant to current work. A major event, such as completing a change, may add its own milestone and prune older context that no longer matters. When hand-off maintenance is enabled, activation, first commit, and completion MUST be recorded as milestones at a minimum. Other stages, relevant decisions, and non-lifecycle work SHOULD also be recorded when their significance makes them useful to a future hand-off.

Read context at useful hand-off boundaries and refresh it only when project policy permits. Never commit, merge, or copy it between worktrees.
