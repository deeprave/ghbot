# Technical Design: explicit repository selection

## Overview

Add a global repeatable `--repo` option and single-use `--repos FILE` option to the application Click group. The shell resolves their input into an explicit, ordered, deduplicated sequence of `(owner, repo)` candidates and stores that sequence in the merged configuration. `runner.run_processor()` and `runner.run_mode()` continue to call one shared discovery entry point; that entry point lists configured owners when no explicit selection is present, or validates the explicit candidates when one is present.

The change does not alter authentication, processors, report rendering, mode-owned command options, or `TaskPool` behavior. Mode modules receive the same `DiscoveredRepository` information as today.

## Architecture

```text
ghbot --owner acme --repo widget --repos selected.txt security
  -> cli() merges defaults, TOML, and global options
  -> resolve explicit entries into ordered (owner, repo) candidates
  -> cfg["explicit_repositories"] is a tuple, or None when no explicit option was supplied
  -> security command calls run_mode(cfg, MODE, options)
  -> runner calls scan_repositories(owners, gh, explicit_repositories=...)
       -> None: list repositories for each owner (existing path)
       -> tuple: GET /repos/{owner}/{repo} for each candidate (new path)
  -> DiscoveredRepository reaches the existing processor and report collection paths
```

`__main__.py` remains the owner of global Click options, config merge, file-input errors, and construction of `cfg`. `runner.py` remains selection-agnostic: it forwards the optional explicit candidate sequence to `scan_repositories()`. `github/repos.py` owns both discovery implementations and the shared archive-filter policy.

## CLI and configuration

Add `--repo` with `multiple=True` and a single optional `--repos FILE` value to `cli`. Their values are not mode options and are therefore accepted before every registered command, including `info`.

After defaults, TOML, and CLI owner overrides are merged, the shell resolves selection input as follows:

1. Split each `--repo` occurrence on commas, preserving occurrence and entry order.
2. Read the optional `--repos` file. Ignore an empty entry and a line whose first non-whitespace character is `#`; split every other line on commas without treating inline `#` as a comment.
3. Process all inline entries before file entries.
4. A qualified entry must contain exactly one non-empty owner and repository component and produces one candidate. A bare entry expands to one candidate for each configured owner, in configured owner order. A bare entry with no configured owner raises `click.UsageError`.
5. Insert candidates into a normal insertion-ordered dictionary keyed by `f"{owner}/{repo}".casefold()`, retaining the first original `(owner, repo)` pair. A later matching key logs a warning and is skipped.

The shell stores `None` in `cfg["explicit_repositories"]` when neither option is supplied. It stores the resolved tuple, including an empty tuple for an explicitly supplied but empty/comment-only source, when either option is supplied. This distinction makes explicit mode suppress owner listing even when it has no candidates.

Click rejects repeated `--repos` use. An unreadable repository file and malformed repository specifications raise `click.UsageError` with the supplied path or entry in the message. No shell, file, or repository input is evaluated.

## Discovery API and data flow

Define a local `RepositoryReference` type alias for `(str, str)` in `github/repos.py`. Extend the scanner boundary without creating a second runner:

```python
async def scan_repositories(
    owners: Sequence[str],
    gh: GitHubAPI,
    *,
    explicit_repositories: Sequence[RepositoryReference] | None = None,
) -> AsyncGenerator[DiscoveredRepository]:
```

When `explicit_repositories is None`, retain the current owner-listing implementation and warning for an empty owner list. Otherwise, do not call `list_repos()` or the owner-classification endpoint. Validate each candidate via `GET /repos/{owner}/{repo}` using `github_api_call()` and `url_vars`.

Successful metadata creates `DiscoveredRepository(owner, metadata, owner_type)`. `owner_type` comes from `metadata["owner"]["type"]` when it is `User` or `Organization`; an unknown or absent type logs a warning and uses `None`, matching existing discovery semantics. The supplied candidate owner remains the record owner; metadata preserves GitHub's canonical owner data. Apply the existing archived-repository debug skip after a successful response.

`runner.run_processor()` and `runner.run_mode()` both pass `cfg["explicit_repositories"]` to the scanner. They do not parse repositories, branch on selection mode, or otherwise alter their processor/collection behavior.

## Error handling

| Event | Behavior |
| --- | --- |
| Bare entry with no configured owners | Shell raises `click.UsageError` before authentication or scanning. |
| Malformed entry or unreadable file | Shell raises `click.UsageError` naming the entry or file. |
| Duplicate candidate (case-insensitive) | Shell logs a warning and skips the later candidate before any API call. |
| Explicit repository is missing or inaccessible | Scanner logs a warning and skips that candidate. |
| Explicit repository returns `GitHubApiError` | Scanner retries once, then logs an error and skips that candidate, matching `list_repos()`. |
| Primary or secondary rate limit | Scanner re-raises; existing `TaskPool`/command fatal-error policy applies. |
| Valid explicit repository is archived | Scanner emits its existing debug skip and does not yield it. |
| Explicit option supplied with no candidates | Scanner yields nothing and never lists owners. |

All GitHub calls remain wrapped in `github_api_call()` and pass owner and repository through `url_vars`; access-denied responses retain the client's not-found translation and do not disclose private-resource details.

## Output compatibility

Explicit selection changes only which `DiscoveredRepository` records enter a scan. Processors, mode collections, report styles, JSON schemas, human output, and output-file handling are unchanged. Empty explicit selection produces the existing report behavior for zero scanned repositories.

## Test strategy

1. Add application-shell tests for repeated/comma-separated `--repo`, repeated-`--repos` rejection, qualified-only selection without owners, bare expansion across owner lists from CLI and TOML, bare-without-owner usage failure, inline-before-file ordering, comments/commas/empty file entries, unreadable files, malformed entries, and case-insensitive duplicate warning/skipping.
2. Add repository-discovery tests for explicit validation URL variables and metadata/owner type, no owner endpoint or owner listing in explicit mode, not-found/access-denied skipping, retry-once behavior, rate-limit propagation, unknown owner type, and archived filtering.
3. Extend runner tests to prove both `run_processor()` and `run_mode()` pass the configured explicit selection unchanged to the scanner.
4. Retain owner-list discovery regression tests to prove the absent-selection path is unchanged.
5. Run `uv run pytest -v -Werror -Walways`, `uv run ruff check`, `uv run ty check src/`, and `uv run ruff format --check` during verification.
