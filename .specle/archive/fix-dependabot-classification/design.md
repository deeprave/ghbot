# Design: Fix Dependabot classification

## Overview

Replace endpoint-specific literal comparisons with one shared predicate for Dependabot login values. Both modes will pass the login supplied by their existing API payloads to that predicate; report data and rendering stay unchanged.

## Architecture

```text
GraphQL author.login ─┐
                      ├─> processor.is_dependabot_login(login) ─> issues metrics and list
REST user.login ──────┘                                      └─> security PR metrics
```

The shared processor module will own an immutable set of the two exact accepted logins: `dependabot` and `dependabot[bot]`. The predicate will return false for missing, non-string, or any other login.

## API and data

- Keep the current GraphQL pull-request query and REST pull-request endpoint unchanged.
- Preserve all issues and security result keys, JSON schema fields, table columns, and human-readable labels.
- Issues mode continues to determine merge readiness only from `mergeStateStatus == "CLEAN"`; the shared identity decision selects the Dependabot or other metric family.

## Error handling

The predicate is pure and treats malformed or absent login values as non-Dependabot. Security mode validates that a REST `user` payload is a mapping before reading its login, so a malformed value cannot fail a repository scan. Existing API error and partial-result handling remains unchanged.

## Test strategy

- Add focused predicate coverage for both accepted forms, plus representative prefix, suffix, case, whitespace, and empty-string near misses.
- Extend issues-processor coverage with GraphQL `author.login: "dependabot"`, asserting Dependabot counts, CLEAN readiness, oldest date, and listed PR data.
- Extend security-processor coverage with the unsuffixed representation to ensure both API paths use the same rule.
- Patch `github_api_call` at the security module import site in all security-processor tests so the test suite isolates its API wrapper consistently.
- Cover null and non-mapping REST user payloads as non-Dependabot values.
- Remove the unused check-conclusion constant left behind when security processing moved out of the shared processor module.
- Run the required pytest, Ruff, ty, and formatting gates during verification.
