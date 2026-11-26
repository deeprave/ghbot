# Auto-merge GitHub Actions patch updates

## Problem

The Dependabot auto-merge workflow restricts eligibility to `uv` patch updates. Grouped GitHub Actions patch PRs are recognised but never receive the token or auto-merge steps.

## Goal

Extend patch-only auto-merge eligibility to the `github_actions` package ecosystem while retaining the current GitHub App token flow.

## Design

Use the existing Dependabot metadata condition with an allowed ecosystem set: `uv` or `github_actions`. Apply that condition consistently to token generation and `gh pr merge --auto --merge`. Rename the step to describe both Python dependency and GitHub Actions patch updates.

## Boundaries

- Minor and major GitHub Actions updates remain manual.
- Dependabot grouping and existing version-tag references remain unchanged.
- No workflow-YAML tests are added; inspect the YAML and its conditions directly.

## Verification

Confirm both eligible steps share the patch-and-allowed-ecosystem condition and that no group or pinning configuration changed.

## Outcome

Both conditions now allow `uv` and `github_actions` patch updates only; the workflow retains its GitHub App token flow and existing action references.
