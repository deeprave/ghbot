# Implementation Tasks

- [x] 1. Extend patch-update eligibility in the auto-merge workflow (`.github/workflows/dependabot-automerge.yml`)
  - [x] 1.1 Change the shared token-generation and auto-merge conditions to permit `github_actions` alongside `uv` when Dependabot metadata reports a patch update.
  - [x] 1.2 Rename the merge step to describe both eligible ecosystems without changing authentication, grouping, or action references.
- [x] 2. Verify workflow policy and update tracking
  - [x] 2.1 Inspect the YAML to confirm both eligible steps share the patch-and-allowed-ecosystem condition, with no minor/major or grouping-policy changes.
  - [x] 2.2 Update `spec-lite.md` and `CONTEXT.json`; no static workflow tests are added per project direction.
