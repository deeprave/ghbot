---
name: define
specle_group: Planning
description: >-
  Create evidence-led, unselected normal change definitions under `.specle/changes/`.
usage: >-
  Use when scoping potential normal work: investigate evidence, resolve material uncertainty, and define the change without activating it.
lifecycle:
  creates:
    - defined
---

# Define a change

Create a useful, evidence-led definition for a normal change without selecting or commencing it.

## Change independence

Changes are independent by default. A queued or future change must not create a dependency through ordering, conceptual overlap, or anticipated functionality. Record a dependency only for an obvious, already-implemented technical prerequisite or an explicit user decision, and make it visible in the affected change artifacts and context. Constraints, features, expectations, and functionality from a future change must not constrain this change until that future change is implemented.

## Workflow

Before creating or recording lifecycle state, consult this skill's `lifecycle` frontmatter declaration.

1. Read the request, `.agents/policies/*.md`, relevant steering and project guidance, and available repository evidence: code, tests, documentation, configuration, and active and archived changes.
2. Separate established current behaviour, the requested outcome, affected boundaries, and implementation details that remain undecided. Check whether existing work already covers or partially overlaps the request. If it fully covers the request, report the evidence and stop without creating a duplicate change. For partial overlap, explain the boundary rather than silently duplicating, absorbing, or constraining either change.
3. Identify material uncertainty: a question whose answer would change scope, observable behaviour, compatibility, acceptance criteria, or change type. Ask focused questions only for that uncertainty, stating the decision each question unblocks and an evidence-based default when available. Do not ask for facts the evidence establishes.
4. Infer minor details only when they do not materially alter the request. Record them as assumptions or boundaries in the change artifacts.
5. Draft substantive requirements and specification content. Requirements explain why the work matters now and its desired observable outcome; state the capabilities or behaviour to add, modify, or remove; identify known affected systems and compatibility impact; state boundaries and non-goals; and provide numbered user stories with clear, testable EARS-style acceptance criteria. The concise specification retains motivation, intended outcome, key scope and impact, evidence expected for verification, and any unresolved material question or recorded assumption. Use helpful headings, not a prescribed proposal format.
6. Select a concise 2–4 word slug and check it is unique across `.specle/changes/` and `.specle/archive/`. If it conflicts, identify the existing change and stop before writing a durable record; let the user choose a new slug or investigate whether that change already covers the request.
7. Create `.specle/changes/<change-slug>/`, then write `requirements.md` and `spec.md`.
8. Add versioned `status.json` with `kind: "change"`, `status: "defined"`, `created_at` set to current Unix seconds as a JSON number, `activated_at: null`, empty progress, `not-run` verification/review, `delivery: null`, and empty `relationships` and `dependencies`. Do not select it in `.specle/current-change`, invoke planning, or commence implementation.
9. Present a concise definition summary covering the problem, intended outcome, scope, boundaries, assumptions or unresolved material questions, and verification direction. This reports the newly defined change; it does not require confirmation or imply that the user must activate it next.

If the user identifies a completed spike as the source of this change, update that spike's `findings.json` `outcome_change` with this change's stable name.

Do not replace an unfinished local selection in `.specle/current-change`.

## Next

- `activate <change-name>` — explicitly commence the unselected normal change.
