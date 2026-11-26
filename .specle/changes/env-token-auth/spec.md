# Environment API token authentication

## Problem

ghbot requires the GitHub CLI to obtain an API token. Automation may instead have a dedicated API token in its process environment.

## Goal

Add global `-e` / `--env` and `--no-env` flags plus an `env = true` configuration setting. They select `GITHUB_API_TOKEN` or explicitly return to `gh auth token`, without falling back to or invoking `gh` in environment-token mode.

## Design boundaries

- `GITHUB_API_TOKEN` is intentionally distinct from `GITHUB_TOKEN`; `env = true` selects its source but never stores a token value, and `--no-env` overrides it per invocation.
- Missing or whitespace-only values raise `AuthError` without exposing token content.
- Cache tokens independently by source so an explicit source selection cannot reuse the other source's token.
- No token is added to config files, `.env` files, or logs.

## Verification

Unit, config, and CLI tests cover source selection, absent/empty values, whitespace trimming, no-`gh` behaviour in environment-token mode, source-isolated caching, and unchanged default authentication. Run the repository Python gates through `uv run`.
