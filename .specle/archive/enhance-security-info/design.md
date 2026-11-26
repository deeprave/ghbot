# Design Document: enhance-security-info

## Overview

Extend `SecurityRepoProcessor` with Dependabot pull request remediation counts:

```text
dependabot_open_pull_requests
dependabot_ready_pull_requests
```

The processor will list open pull requests, filter to Dependabot-authored PRs, and inspect each
Dependabot PR head commit's statuses and check runs. Report rendering will include the two new
counts in plain, table, and JSON formats.

"Ready" means ready from automated checks and mergeability signals, while deliberately ignoring
approval requirements. A PR blocked only by required reviews still counts as ready.

## Architecture

```text
SecurityRepoProcessor.run()
  ├─ _fetch_dependabot_alerts()
  ├─ _fetch_code_scanning_alerts()
  ├─ _fetch_secret_scanning_alerts()
  └─ _fetch_dependabot_pull_requests()
       ├─ list open PRs
       ├─ filter Dependabot-authored PRs
       └─ inspect each Dependabot PR head SHA
            ├─ combined commit status
            └─ check runs

report module
  ├─ summary totals include Dependabot PR counts
  ├─ plain per-repo output includes Dependabot PR counts
  ├─ table columns include Dependabot PR counts
  └─ JSON includes counts in summary and repositories
```

## GitHub API

Use existing `github_api_call(self._gh)` for every request.

### List Open Pull Requests

```text
GET /repos/{owner}/{repo}/pulls?state=open
```

Use `getiter` and `url_vars={"owner": self._owner, "repo": self._repo}`.

Dependabot filtering:

```python
def _is_dependabot_pr(pr: dict) -> bool:
    user = pr.get("user") or {}
    login = user.get("login")
    return login == "dependabot[bot]"
```

The implementation may also accept equivalent Dependabot bot identities if the payload clearly
identifies Dependabot, but the tests should anchor the canonical `dependabot[bot]` case.

### Combined Commit Status

```text
GET /repos/{owner}/{repo}/commits/{ref}/status
```

Use the PR head SHA as `{ref}`. The response's top-level `state` is ready only when it is
`"success"`. If there are no status contexts, GitHub may report `"success"`; that is acceptable.

### Check Runs

```text
GET /repos/{owner}/{repo}/commits/{ref}/check-runs
```

Use `getitem` and read the `"check_runs"` array. A check run is passing when:

- `status == "completed"`
- `conclusion in {"success", "neutral", "skipped"}`

Any non-completed status or any other conclusion means the PR is not ready.

## Readiness Predicate

One helper should own the policy:

```python
async def _dependabot_pr_is_ready(self, pr: dict, result: RepoResult) -> bool:
    if pr.get("draft"):
        return False
    if pr.get("mergeable") is False:
        return False

    sha = (pr.get("head") or {}).get("sha")
    if not sha:
        result.errors.append("dependabot pull request readiness: missing head sha")
        return False

    status_ready = await self._commit_status_is_ready(sha)
    checks_ready = await self._check_runs_are_ready(sha)
    return status_ready and checks_ready
```

Approval and review data are intentionally absent from this predicate.

If GitHub returns `mergeable: null`, do not block readiness. GitHub often computes mergeability
asynchronously, and this feature should not add extra polling.

## Result Keys

Add keys to `RepoResult.results`:

```python
result.results["dependabot_open_pull_requests"] = open_count_or_none
result.results["dependabot_ready_pull_requests"] = ready_count_or_none
```

When the PR list endpoint is unavailable, both values should be `None`.

When listing PRs succeeds but readiness inspection fails for one PR, preserve the open PR count and
record a partial error; the ready count should include only PRs whose readiness was successfully
confirmed.

## Report Rendering

Update `_summary` to include totals:

```json
{
  "dependabot_open_pull_requests": 7,
  "dependabot_ready_pull_requests": 3
}
```

Plain summary labels:

```text
Dependabot PRs:
Dependabot PRs ready:
```

Plain per-repository labels:

```text
  Dependabot PRs:
  Dependabot PRs ready:
```

Table columns should stay compact. Suggested headers:

```text
Repository | Dependabot | Scanning | Secrets | Dep PRs | Ready
```

JSON repository objects add the two new keys and continue to include all scanned repositories.

## Error Handling

Follow the current security processor policy:

| Condition | Handling |
|---|---|
| PR list 403/404 | set both PR counts to `None`, emit deferred debug event |
| PR list `GitHubApiError` | set both PR counts to `None`, emit error, append error, status partial |
| Status/check 403/404 for one PR | do not count that PR as ready, emit deferred debug event |
| Status/check `GitHubApiError` for one PR | do not count that PR as ready, append error, status partial |
| Fatal rate limit errors | re-raise |
| Unexpected exception | existing `run()` containment sets result failed |

## Test Strategy

- Unit tests for Dependabot PR filtering.
- Processor tests for open Dependabot PR count.
- Processor tests for ready count when all statuses and check runs pass.
- Processor tests for draft PRs, failing statuses, pending statuses, failing check runs, and
  pending check runs not counting as ready.
- Processor test proving approval/review data does not block readiness.
- Processor tests for PR endpoint 403/404 and `GitHubApiError`.
- Processor tests for per-PR status/check inspection failures.
- Report tests for plain, table, JSON, `None` display, and repository inclusion.
- Run full verification:
  - `uv run pytest -v -Werror -Walways`
  - `uv run ruff check`
  - `uv run ty check src/`
  - `uv run ruff format --check`
