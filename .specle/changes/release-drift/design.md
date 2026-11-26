# Technical Design: drift

## Overview

Add a `drift` reporting command backed by `DriftRepoProcessor` and a dedicated report renderer. It reuses the existing token, `gidgethub` client, scanner, monitor, and bounded `TaskPool`. The processor is intentionally narrow: it determines the stable-release baseline, counts commits on the actual default branch since that baseline, and detects PyPI publication configuration from GitHub Actions workflows. It does not create releases, write to GitHub, or contact PyPI.

## Architecture

```text
click drift (--plain | --table | --json, --output)
  -> _main(cfg, DriftRepoProcessor, {format})
    -> get_auth_token() -> shared gidgethub GitHubAPI
    -> scan_repositories(owners, gh)
      -> TaskPool.submit(processor.run)
        -> releases/latest                         (stable baseline)
        -> repository metadata                     (default branch)
        -> compare/{tag}...{default_branch}        (ahead_by)
        -> git tree + workflow blobs (only if ahead_by > 0)
  -> print_release_drift_report(pool.results, format, output)
```

`_main` remains processor-agnostic. `DriftRepoProcessor` implements the existing constructor and `RepoProcessor` contract, returning `RepoResult`. That keeps repository discovery, authentication, concurrency, logging, and fatal-error handling shared with the existing commands.

Fetch repository metadata before comparison unless the scanner is extended to pass its already-present `default_branch` field to processors. The initial implementation should favor the existing processor boundary and fetch it itself; an explicit optimization can later pass immutable repository metadata without changing the report contract.

## API and result data

All GitHub calls are inside `github_api_call(self._gh)` and use `url_vars`.

| Purpose | Endpoint | Result use |
| --- | --- | --- |
| Release baseline | `GET /repos/{owner}/{repo}/releases/latest` | `tag_name`, `published_at` |
| Branch selection | `GET /repos/{owner}/{repo}` | `default_branch` |
| Drift count | `GET /repos/{owner}/{repo}/compare/{basehead}` | `ahead_by`, where `basehead` is `{tag_name}...{default_branch}` |
| Workflow inventory | `GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1` | workflow blob paths and SHAs |
| Workflow text | `GET /repos/{owner}/{repo}/git/blobs/{sha}` | decoded YAML, PyPI signal detection |

`releases/latest` is GitHub's latest published non-prerelease endpoint, so it expresses the agreed stable-release policy. The compare base is the release tag, not `target_commitish`: tags are immutable release identities, whereas a release's target commitish can name a moving branch.

The processor writes these public result keys:

```python
{
    "latest_release_tag": str | None,
    "latest_release_published_at": str | None,
    "default_branch": str | None,
    "commits_since_release": int | None,
    "pypi_publishing_configured": bool | None,
}
```

Private eligibility/filtering state is not required: a result is reportable when `commits_since_release` is a positive integer. This maintains the existing mutable `RepoResult.results` convention.

Workflow discovery filters tree blobs to `.github/workflows/*.yml` and `.github/workflows/*.yaml`. Decode Git blob content from Base64 and detect case-insensitive `pypi` in the filename, top-level/name text, or content, plus explicit `pypa/gh-action-pypi-publish` and `pypi.org` references. This is intentionally a configuration signal, not proof of a successful PyPI publication.

## Error handling

| Operation/outcome | Result policy |
| --- | --- |
| `releases/latest` returns 404/403 | set release values to `None`; successful, non-reportable skip |
| Release or metadata/compare `GitHubApiError` | append diagnostic; mark partial; set affected keys to `None`; non-reportable |
| Primary/secondary rate limit | re-raise for `TaskPool` policy |
| No commits ahead | set count to `0`; successful, non-reportable |
| Workflow tree/blob inaccessible | append diagnostic; set PyPI flag to `None`; retain a reportable entry |
| No workflow blobs or no signals | set PyPI flag to `False` |
| Unexpected processor failure | follow existing processor behavior: mark failed and emit an error event |

Defer routine progress events until positive drift is known, then emit an informational summary and flush the deferred events; API failures emit fetch-error events immediately. This matches the security processor's low-noise reporting approach.

## Output rendering

Implement `render_drift_report()` and `print_drift_report()` in `report.py`, following the security and issues report pattern. The renderer filters and sorts reportable results; JSON must also omit non-reportable repositories.

Plain example:

```text
Repos scanned:                    12
Released repos:                    8
Repos with drift:                  3
Commits since release:            19

acme/widgets
  Latest release:            v1.4.0
  Release published:  2026-11-01T00:00:00Z
  Default branch:               main
  Commits since release:           7
  PyPI configured:               yes
```

Table columns: `Repository`, `Release`, `Published`, `Branch`, `Commits`, and `PyPI`. Use `yes`, `no`, and `N/A` for the final column. JSON has a `summary` object and a `repositories` array with `owner`, `repo`, `repository`, and the public keys above; unknown PyPI configuration is `null`.

Add the `drift` CLI command with the existing shared `_output_format()` validation and `--output` behavior. It invokes `_main`, then its report printer exactly as the `security` and `issues` commands do.

## Test strategy

- Unit-test protocol conformance, constructor validation, successful stable-release flow, default-branch use, and `ahead_by` handling.
- Test no-release 404, zero drift, compare failure, rate-limit propagation, and PyPI workflow-tree/blob failure policies.
- Test PyPI detection for filename, workflow name/content, explicit action, and no signal; ensure no PyPI probing occurs.
- Test report filtering, deterministic sort, summary values, plain/table/JSON shapes, and `None`/N/A handling.
- Test CLI processor routing, output format validation, and output-file handoff.
- Run `uv run pytest -v -Werror -Walways`, `uv run ruff check`, `uv run ty check src/`, and `uv run ruff format --check` during verification.
