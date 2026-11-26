# Technical Design: organisation private repository discovery

## Overview

Extend `list_repos()` in `src/ghbot/github/repos.py` with an owner-account lookup before its existing paginated listing. The lookup's `type` controls the listing path. Add a frozen, slotted `DiscoveredRepository` record with `owner`, `metadata`, and `owner_type`, then have `scan_repositories()` yield that record after archive filtering.

## Architecture

```text
configured owner
  -> GET /users/{owner}
     -> type == Organization: GET /orgs/{owner}/repos?type=all
     -> type == User or unknown: GET /users/{owner}/repos?type=all
  -> scan_repositories(): skip archived -> DiscoveredRepository(owner, metadata, owner_type)
  -> _main(): invoke processor with owner_type=discovered.owner_type
```

`list_repos()` keeps its two-attempt loop and returns enough information for the scanner to build discovery records. Each attempt encompasses both metadata and listing, so a transient failure in either part restarts discovery cleanly. The lookup is not separately cached: the current scanner invokes `list_repos()` once per supplied owner, and retaining this simple boundary avoids new shared state.

`owner_type` is explicit rather than inferred from `metadata["owner"]["type"]`: it represents the account classification used to choose the list endpoint and stays available even if a listing payload is incomplete. It is `None` for unknown or missing account types; that case still lists through the user endpoint for compatibility. `_main()` passes it as a keyword-only `owner_type` argument. Built-in and custom processor constructors used with `_main()` accept `*, owner_type: str | None = None`; it remains optional discovery context rather than a required `RepoProcessor` protocol property.

Create `CHANGELOG.md` at the repository root. Use a concise versioned format with a `0.10.0` entry for the `drift` command and an Unreleased breaking-change entry explaining the `owner_type` processor keyword and its default.

## API and error handling

| Operation | Endpoint | Success policy | Failure policy |
| --- | --- | --- | --- |
| Owner classification | `GET /users/{owner}` | read `type` | not-found/access denied: warn and skip; API failure: retry full attempt |
| User listing | `GET /users/{owner}/repos?type=all` | async-paginate repositories | existing retry/skip policy |
| Organisation listing | `GET /orgs/{owner}/repos?type=all` | async-paginate repositories including token-accessible private repositories | existing retry/skip policy |

All paths use parameterized URL templates and `url_vars={"owner": owner, "type": "all"}`. Both API calls are enclosed in `github_api_call()`. `GitHubPrimaryRateLimitError` and `GitHubSecondaryRateLimitError` must be re-raised rather than swallowed by the existing broad `GitHubApiError` retry handling; a documented secondary-rate-limit 403 is classified before generic access-denied 403 handling. An absent or unfamiliar account type emits a warning and selects the user endpoint, preserving historical behaviour while making malformed metadata visible. A discovery attempt buffers its listing before yielding repositories, so a transient later-page failure cannot submit duplicate processors on retry.

## Test strategy

- Write failing async unit tests for user and organisation endpoint selection, asserting templates and `url_vars`.
- Verify an organisation result marked `private` reaches `scan_repositories()` with `owner_type == "Organization"`, and an archived result still does not.
- Add a CLI-loop test that proves the discovered owner type is supplied through the keyword-only processor argument while command options remain unchanged.
- Add constructor/protocol tests for the default `owner_type=None` across built-in processors.
- Assert changelog entries for `0.10.0` drift support and the Unreleased processor API change.
- Cover not-found lookup skip, transient lookup failure retry, transient listing failure retry, rate-limit propagation, and unknown-type fallback.
- Run `uv run pytest -v -Werror -Walways`, `uv run ruff check`, `uv run ty check src/`, and `uv run ruff format --check`.
