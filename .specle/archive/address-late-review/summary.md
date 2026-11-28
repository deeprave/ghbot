# Summary: Address late PR #71 review

## Summary

Resolved accepted late-review findings from the repository settings collector and clarified
security product-gating diagnostics.

## Outcome

Settings and issues reports now preserve partial-data availability accurately, and security
diagnostics distinguish features that are not enabled from inaccessible repositories.

## What changed

- Preserved usable settings data when GraphQL fields or independent REST data are unavailable.
- Added bounded ruleset provenance and truncation reporting, plus curated security configuration.
- Normalised recognised Code Security, secret-scanning, and Dependabot feature-gating messages.

## Key decisions and limits

The unreleased settings 1.0 schema retains `rulesets_truncated` as a required field. Raw GitHub
error details remain structured metadata while human diagnostics use canonical wording.
