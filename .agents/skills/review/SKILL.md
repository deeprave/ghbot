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

1. Read `.agents/CONTEXT.json`, `.agents/steering/{context,lifecycle,testing}.md`, and the
   relevant project guidance. Review an active spec only after it is `verified` for the current
   implementation.
2. Get the changes: `git diff` (and `git diff --staged`), or the files the user names.
3. Check compliance with the portable steering policy and applicable project architecture, API,
   security, and test guidance.
4. Evaluate: correctness, readability, test coverage, security, performance.

## Output

`APPROVE` or `REQUEST_CHANGES`, with specific, actionable findings (cite `file:line`). Keep
findings concrete; separate must-fix from nice-to-have.

After reporting, record the review outcome in `CONTEXT.json` as required by `lifecycle.md`:
`APPROVE` changes a verified spec to `complete`; `REQUEST_CHANGES` records the finding count and
changes it to `review-findings`.

## Next

- `build` — fix the issues raised.
- `verify` — confirm the implementation against the spec once changes settle.
