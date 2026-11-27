# Summary: Correct Dependabot classification

## Summary

ghbot now recognises both GitHub Dependabot identities consistently in issues and security reports.

## Outcome

Dependabot pull requests reported as `dependabot` are no longer counted as other pull requests.

## What changed

- Centralised exact Dependabot identity recognition for both report modes.
- Safely ignores malformed REST author payloads.
- Removed stale processor-module code left by the earlier mode refactor.

## Key decisions and limits

Only `dependabot` and `dependabot[bot]` are recognised; near-match logins remain other pull requests.
