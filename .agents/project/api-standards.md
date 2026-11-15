# GitHub API Standards

## Client boundary

Wrap every GitHub request with `github_api_call(gh)` from `src/ghbot/github/client.py`. Do not
call the client directly outside that context manager.

```python
async with github_api_call(self._gh):
    data = await self._gh.getitem("/repos/{owner}/{repo}", url_vars={...})
```

## Requests

- Use `url_vars` for all URL parameters; never interpolate owner or repository values into paths.
- Use `getiter` for paginated list endpoints rather than manual page loops.
- Keep API access in `src/ghbot/github/` or a processor helper with the project error policy.

## Error policy

- `GitHubNotFoundError` means unavailable or inaccessible data: use the mode's documented default
  and, where appropriate, emit a debug monitor event.
- Re-raise `GitHubPrimaryRateLimitError`, `GitHubSecondaryRateLimitError`, and any `FatalError`.
- A recoverable `GitHubApiError` records a fetch-error monitor event and a result error, then makes
  the repository result partial rather than claiming a successful empty value.

Repository discovery classifies owners through `GET /users/{owner}` and selects the user or
organisation repository endpoint from that type.
