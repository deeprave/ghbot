---
name: spike
specle_group: Discovery
description: >-
  Investigate a question within a time-box, without implementation.
usage: >-
  Use before committing to a solution when a bounded investigation is needed; produce findings and recommendations, not production changes.
lifecycle:
  accepts:
    - defined
    - spiking
  creates:
    - defined
  transitions:
    - from:
        status: defined
        kind: spike
      to:
        status: spiking
        kind: spike
      next: spike
    - from:
        status: spiking
        kind: spike
      to:
        status: complete
        kind: spike
  terminal:
    - complete
---

# Spike an investigation (don't implement)

Research a question for decision-making as active work. **Do not implement anything.**

## Workflow

Before applying or recording a lifecycle transition, consult this skill's `lifecycle` frontmatter declaration.

1. Read `.specle/current-change` when present, relevant policies, steering, and project guidance. Create the spike unselected; only `activate <change-name>` may select and commence it.
2. Establish the investigation question, hypothesis, scope, and an S/M/L/XL effort budget. The budget bounds research effort; it is not a delivery estimate or due date.
3. Create `.specle/changes/<slug>/findings.json`, using a slug unique across active and archived changes, with `"$schema": "specle://schemas/findings/1.0"`, `question`, `hypothesis`, `effort`, `scope`, `status: "defined"`, `findings`, `recommendations`, `risks`, and `outcome_change: null`.
4. Initialise the new change's versioned `status.json` with `kind: "spike"`, `status: "defined"`, `created_at` set to current Unix seconds as a JSON number, `activated_at: null`, empty progress and relationships/dependencies, `delivery: null`, and verification/review both `not-applicable`. Do not select or commence it.
5. When invoked by `activate`, set the selected spike status to `spiking` with current Unix-second `updated_at`, then research the question using code, documentation, and read-only experiments only. Update `findings.json` with concrete evidence, recommendations, and risks.
6. On completion, set `findings.json.status` and the spike `status.json.status` to `complete` with current Unix-second `updated_at`. If a resulting normal change, bugfix, or refactor exists, set `outcome_change` to its stable change name; otherwise leave it `null`.

Research only — no production code, tests, task plans, or implementation changes.

## Next

- `define` — create an outcome feature change when the findings recommend one, then record its stable name in `outcome_change`.
- Move on — when the spike recommends no follow-up work.
