# Issues report: PR categories and CI counts

## Problem

The `issues` report combines all open pull requests and does not show which Dependabot or other PRs have passing CI.

## Goal

Report four metrics per repository and in the summary:

1. Dependabot PR total
2. Dependabot PRs with passing CI
3. Other PR total
4. Other PRs with passing CI

## Design

`IssuesRepoProcessor` classifies open PRs by author login and evaluates each head commit through the existing combined-status and check-run success criteria. The CI result is intentionally independent of drafts, mergeability, approval, and review state: a counted PR needs only non-CI requirements before it can merge.

On an individual status/check lookup failure, retain the total category count, exclude that PR from the CI-passing count, and mark the repository partial. Rate limits propagate unchanged.

Extend plain, table, and JSON issues reports with the four metrics while retaining existing issue counts and unavailable-data semantics.

## Verification

Test category classification, checks-only CI semantics, partial-result handling, and all three report formats. Run the Python quality gates through `uv run`.
