# Requirements Document

## Introduction

ghbot currently obtains its GitHub API token exclusively by invoking `gh auth token`. Operators running in automation may instead supply a dedicated API token through their process environment. This feature adds an explicit opt-in source without changing the existing default behaviour.

## Glossary

- **gh authentication**: The existing token source, obtained with `gh auth token`.
- **environment-token mode**: Token selection activated by the global `-e` / `--env` option or `env = true` in configuration.
- **API token variable**: The `GITHUB_API_TOKEN` environment variable, intentionally distinct from workflow-provided `GITHUB_TOKEN`.

## Requirements

### Requirement 1: Select environment-token mode explicitly

**User Story:** As an operator, I want an explicit CLI option to use an API token from the environment, so that automation need not install or authenticate the GitHub CLI.

#### Acceptance Criteria

1. THE CLI SHALL provide a global `-e` / `--env` flag that enables environment-token mode for every command.
2. THE CLI SHALL provide `--no-env` to disable environment-token mode, including when configuration sets `env = true`.
3. THE configuration file SHALL accept `env = true` to enable environment-token mode for every command.
4. IF environment-token mode is enabled, THEN THE application SHALL obtain its token from `GITHUB_API_TOKEN`.
5. IF environment-token mode is enabled, THEN THE application SHALL NOT invoke `gh`, including when the environment variable is absent or invalid.
6. IF environment-token mode is not enabled, THEN THE application SHALL retain the existing `gh auth token` behaviour.

### Requirement 2: Validate and protect environment tokens

**User Story:** As an operator, I want actionable failures without exposing credentials, so that configuration mistakes are safe to diagnose.

#### Acceptance Criteria

1. IF `GITHUB_API_TOKEN` is unset or empty in environment-token mode, THEN THE application SHALL raise `AuthError` with an actionable message naming the missing variable.
2. THE application SHALL strip surrounding whitespace from an environment token before use.
3. THE application SHALL NOT log, render, persist, or include the token value in an error message.
4. THE application SHALL use the selected token as the GitHub API client's OAuth token without changing API request behaviour.

### Requirement 3: Preserve token-source isolation

**User Story:** As a caller and test author, I want each authentication source to remain independent, so that a cached token cannot override an explicitly selected source.

#### Acceptance Criteria

1. IF environment-token mode is selected after a gh-derived token was cached, THEN THE application SHALL use `GITHUB_API_TOKEN`.
2. IF gh authentication is selected after an environment token was cached, THEN THE application SHALL use the gh-derived token.
3. THE implementation SHALL preserve concurrency-safe lazy token retrieval for each source.

## Non-Functional Requirements

- `GITHUB_API_TOKEN` is the sole environment variable introduced by this change; do not read or repurpose `GITHUB_TOKEN`.
- `env = true` may select the token source in `ghbot.toml`; do not add token values to configuration, `.env` files, or logs.
- Update authentication documentation and security steering to describe the explicit environment-token mode.
- Add focused unit and CLI tests using `uv run`; never use a real token in tests.
