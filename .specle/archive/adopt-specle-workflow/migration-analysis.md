# Migration analysis: adopt Specle workflow

## Current state

ghbot stores portable workflow assets and project-specific guidance under `.agents/`, while change records and durable lifecycle state belong in `.specle/changes/<slug>/`. The project overlay and change history are ghbot-owned; the reusable skills and policies are the migration target.

## Migration approach

1. Inventory portable workflow assets versus ghbot-owned project guidance and change records.
2. Install the supported Specle portable workflow using its supported mechanism.
3. Retain the project overlay and compatibly migrate change records, the active selector, and compact context into `status.json` records.
4. Validate skill discovery, root instructions, lifecycle coherence, and unchanged product files.

## Risks

- Replacing `.agents/` wholesale could discard project guidance or active change state.
- A migration that changes product files would exceed the workflow-only scope.
