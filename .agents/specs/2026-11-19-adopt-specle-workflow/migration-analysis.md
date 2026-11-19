# Migration analysis: adopt Specle workflow

## Current state

ghbot stores portable workflow assets, project-specific guidance, local specifications, and compact lifecycle state under `.agents/`. The project overlay and specification history are ghbot-owned; the reusable skills and steering are the migration target.

## Migration approach

1. Inventory portable workflow assets versus ghbot-owned project guidance and state.
2. Install the supported Specle portable workflow using its supported mechanism.
3. Retain or compatibly migrate the project overlay, specifications, active pointer, and compact context.
4. Validate skill discovery, root instructions, lifecycle coherence, and unchanged product files.

## Risks

- Replacing `.agents/` wholesale could discard project guidance or active specification state.
- A migration that changes product files would exceed the workflow-only scope.
