---
name: review
description: >-
  Review working-tree code changes for quality, steering compliance, test coverage, and security.
  Use when asked to "review" the current changes/diff (for a GitHub PR, use the built-in PR review
  instead).
---

# Review current code changes

Review the working-tree diff (or specified files) against the repo's standards.

## Workflow

1. Read `.agents/CONTEXT.json` for the current spec context.
2. Get the changes: `git diff` (and `git diff --staged`), or the files the user names.
3. Check compliance with `.agents/steering/*.md`:
   - `tech.md` — async-first, protocols over ABCs, single `cfg` source of truth.
   - `api-standards.md` — all GitHub calls via `github_api_call`, `url_vars` not f-strings,
     per-step error handling (403/404 → `None`; `GitHubApiError` → partial; fatal rate limits re-raised).
   - `security.md` — no secrets in logs/errors, no raw HTTP.
   - `testing.md` — `@pytest.mark.anyio`, `AsyncMock`, patch at the import site, `-Werror`.
4. Evaluate: correctness, readability, test coverage, security, performance.

## Output

`APPROVE` or `REQUEST_CHANGES`, with specific, actionable findings (cite `file:line`). Keep
findings concrete; separate must-fix from nice-to-have.

## Next

- `/build` — fix the issues raised.
- `/verify` — confirm the implementation against the spec once changes settle.
