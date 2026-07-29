---
name: estimate
description: >-
  Assess the complexity of a spec before building (advisory). Use when asked to "estimate" /
  "size" a feature, or to decide whether a design step is warranted.
---

# Estimate complexity

Provide an advisory complexity assessment for the current (or described) work. This does not block
anything.

## Workflow

1. Read `.agents/CONTEXT.json` for current state.
2. Read `requirements.md` (or `spec.md`) thoroughly.
3. Read the codebase to understand the current state and blast radius.
4. Skim relevant past-work memory (`.agents/specs/*/memory.md`, prior specs) for similar efforts.

## Output

Write `estimate.md` in the spec folder with:

- **T-shirt size**: S / M / L / XL
- **Breakdown**: new files (~N), modified files (~N), estimated tasks (~N), key risks.
- **Confidence**: High / Medium / Low
- **Recommendation**:
  - S: skip design, go straight to `/tasks`.
  - M: consider `/design`.
  - L/XL: `/design` recommended; consider splitting into smaller specs.
- **Similar past work**: reference relevant memory/specs.

## Next

- `/design` — for M+ work.
- `/tasks` — for small work, go straight to tasks.
