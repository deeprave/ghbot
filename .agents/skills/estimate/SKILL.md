---
name: estimate
specle_group: Planning
description: >-
  Estimate Specle work complexity and planning depth.
usage: >-
  Use before implementation to size an active change and decide whether design is warranted; it is advisory and performs no implementation.
lifecycle:
  accepts:
    - defined
  transitions:
    - from: defined
      to: estimated
      next: design
---

# Estimate complexity

Provide an advisory complexity assessment for the current (or described) work. This does not block
anything.

## Change independence

Changes are independent by default. A queued or future change must not create a dependency through ordering, conceptual overlap, or anticipated functionality. Record a dependency only for an obvious, already-implemented technical prerequisite or an explicit user decision, and make it visible in the estimate and affected change artifacts. Constraints, features, expectations, and functionality from a future change must not constrain this change until that future change is implemented.

## Workflow

Before applying or recording a lifecycle transition, consult this skill's `lifecycle` frontmatter declaration.

1. Read `.specle/current-change` when present and the target's `status.json`. Default to the selected normal change. A named unselected normal change is valid for advisory estimation only; it must remain unselected.
2. Read `requirements.md` (or `spec.md`) thoroughly.
3. Read the relevant authoritative `.agents/project/` documents and the codebase to understand the
   current state, project constraints, and blast radius.
4. Skim relevant archived changes under `.specle/archive/` for similar efforts.
5. Read `.agents/policies/lifecycle.md` and any applicable `.agents/steering/` override before recording state.

## Output

Write `estimate.md` in the change folder with:

- **T-shirt size**: S / M / L / XL
- **Breakdown**: new files (~N), modified files (~N), estimated tasks (~N), key risks.
- **Confidence**: High / Medium / Low
- **Recommendation**: describe the planning risks and any reason to split the work. Active normal work always continues through design before tasks.
- **Similar past work**: reference relevant memory/changes.

If estimating the selected change, update its lifecycle status to `estimated` and write `updated_at` as current Unix seconds. A named unselected
estimate records only that change's artifact; it does not change `.specle/current-change`.

## Next

After recording a successful estimate for the selected change, read `.agents/project/automation.md`. In `decision-gated` mode, invoke `design <change-name>`; otherwise report it and wait. For a named unselected change, stop and report `activate <change-name>` regardless of progression policy.

- `design` — required before tasks for active normal work.
