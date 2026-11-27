# Add activity processor

## Problem

Current reports explain repository posture and release drift but not maintenance activity. A
repository may have no release drift while inactive, or many issues while still being actively
maintained.

## Outcome

Add a reportable `activity` mode backed by `ActivityRepoProcessor`. It will provide lifecycle,
recency, contributor, Dependabot, and workflow-health metrics in plain, table, and JSON formats.

## Scope

- Default-branch and repository-wide commit recency, default-branch commit total, release, merged
  pull-request, and contributor metrics.
- Pull-request and issue lifecycle totals, open-backlog age, and stale-pull-request metrics.
- Dependabot open, merged, ignored, and abandonment-notice signals.
- Bounded workflow recency, conclusion, retry, success-rate, and failure-window metrics.
- `--since` activity window, defaulting to 30 days; `--stale-days`, defaulting to 30.
- Mode discovery, `combo` composition, packaged JSON schema, and documentation.

## Boundaries

- Activity is distinct from release-relative drift, issue posture, and security posture.
- Commit totals apply only to the default branch.
- Workflow and Dependabot comment retrieval is bounded and never includes logs, secrets, or
  unrelated comment text.
- No GitHub mutation or compliance judgement.

## Assumptions

- A 30-day default activity window is useful for routine scans; 60- and 90-day views are obtained
  by supplying a corresponding `--since` timestamp.
- Workflow success rate over 20 completed runs provides a stable bounded health signal.

## Verification

Unit tests will cover each lifecycle classification, bot exclusion, date boundaries, stale
threshold, Dependabot abandonment detection and redaction, bounded workflow aggregation,
partial-result handling, all output formats, `combo`, and JSON-schema validation.
