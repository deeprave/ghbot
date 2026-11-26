# Design: Adopt Specle workflow

## Overview

Replace ghbot's copied portable workflow with the pinned Specle distribution, retain repository-specific guidance in `.agents/project/`, and move every legacy dated specification into `.specle/changes/<slug>/`. Convert the available lifecycle ledger into schema-valid `status.json` records without changing product code or report behaviour.

## Architecture

```text
legacy .agents/{skills,steering,specs,.current,CONTEXT.json}
                │
                ├─ portable inventory ──> Specle init --force ──> .agents/{skills,policies}
                ├─ project facts ───────────────────────────────> .agents/project/
                └─ dated change records ──> .specle/changes/<slug>/{spec.md,status.json,...}
                                                               │
                                                        .specle/current-change
```

Specle owns the managed skills, policy inventory, skill index, lifecycle schema, and local selector semantics. ghbot owns its project overlay, change content, delivery conventions, and historical evidence. The root `AGENTS.md` retains only local execution and trusted-tool instructions and delegates workflow to `.agents/AGENTS.md`.

## Data and lifecycle migration

- Rename each dated change directory to its slug and preserve its content under `.specle/changes/`.
- Rename each concise summary to the canonical specification name when no detailed specification already exists. Where both existed, retain the detailed specification and remove the redundant summary.
- Replace internal legacy paths and date-prefixed change references with current slugs and local filenames.
- Create one `status.json` per active change with the `specle://schemas/change-status/1.0` schema. Preserve recorded completion and available verification/review evidence; use `not-recorded` where the legacy compact context has no evidence.
- Derive each migrated record's task progress from its preserved `tasks.md` checkbox plan.
- Select `adopt-specle-workflow` through `.specle/current-change` and retain all completed records in `.specle/changes/` for later, deliberate archival.

## Delivery convention

Record the branch convention unambiguously in the project overlay: normal `kind: "change"` records use `feature/<slug>`, while `bugfix`, `refactor`, and maintenance work use their matching prefixes.

## Error handling and boundaries

- Run the Specle installer without `--force` first to detect managed-path conflicts; use `--force` only for the explicit portable-inventory replacement.
- Do not overwrite `.agents/project/` or change content during installation.
- A failed Specle validation is a migration failure and must be corrected before review.
- No application source, tests, report schemas, dependency declarations, or GitHub Issues are changed by this workflow migration.

## Test strategy

- Validate the managed skill inventory, lifecycle graph, all active status records, and local selection with `specle validate . --verbose`.
- Check the migrated tree for dated directories, legacy state paths, and obsolete summary-file references.
- Run `git diff --check` and confirm the migration has no changes under `src/` or `tests/`.
- Confirm the project overlay contains every document required by the Specle `onboard` skill.
- Confirm every migrated status record's task progress matches its preserved task plan and that the delivery policy names the normal-change branch prefix.
