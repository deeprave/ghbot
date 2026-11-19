# Contributing

## Development

Use `uv run` for every repository command. The project checks are:

```bash
uv run pytest -v -Werror -Walways
uv run ruff check
uv run ty check src/
uv run ruff format --check
```

Follow the repository's spec-driven workflow in [AGENTS.md](AGENTS.md). Contributions are made on
feature branches and proposed through pull requests.

## Architecture

`src/ghbot/processor.py` owns the shared scanning contracts:

- `RepoProcessor` is the runtime-checkable protocol for a repository scanner. It exposes `owner`,
  `repo`, and `async run() -> RepoResult`.
- `RepoResult` carries the repository identity, processing status, errors, and mode-owned result
  data.
- `Monitor` accepts `FeedbackEvent` instances for progress and errors.
- `GitHubClient` is the narrow GitHub API protocol used by processors, providing REST item/list
  calls and `graphql()` for bulk GraphQL queries.
- `InfoRepoProcessor` is the only built-in non-reporting processor.

Each reportable capability is a self-contained mode module under `src/ghbot/modes/`:

```text
modes/
  security.py   processor + collection report + mode unit
  issues.py     processor + collection report + mode unit
  drift.py      processor + collection report + mode unit
  info.py       non-reporting processor + mode unit
```

`src/ghbot/report_style.py` contains only reusable output mechanics: `ReportStyle`, plain, JSON,
and Markdown-table styles, table helpers, report composition, and the output writer. Mode modules
own result interpretation, summaries, filtering, JSON documents, and report layout.

## Adding a processor

Choose the appropriate shape first:

- Add a non-reporting processor when its results are only logged or consumed by the engine.
- Add a reportable mode when users need a collection-level plain, table, or JSON report.

Every processor constructor accepts `(owner, repo, gh, monitor, options=None, *,
owner_type=None)`. Validate `owner` and `repo`; retain `owner_type` even when it is not yet needed.
Discovery supplies `owner_type` as `"User"`, `"Organization"`, or `None` so a processor can later
select owner-specific endpoints without changing its construction contract.

Use `github_api_call` with `url_vars` for REST GitHub requests, or with `gh.graphql()` for a
GraphQL query. Prefer a paginated GraphQL connection when one query can replace per-resource REST
lookups. Treat unavailable 403/404 data as a mode-appropriate unavailable value, record non-fatal
`GitHubApiError` failures as partial results, and re-raise rate-limit and other `FatalError`
failures for `TaskPool` to handle. Send progress or fetch feedback through the injected `Monitor`.

Put processor tests beside their owner, for example `tests/unit/test_tags_processor.py`. Exercise
the processor with a mocked `GitHubClient` and assert its result data, status, error policy, and
feedback events.

## Adding a reportable mode

Create `src/ghbot/modes/<name>.py`. Keep these elements together:

- `<Name>RepoProcessor`, implementing `RepoProcessor`.
- `<Name>CollectionReport`, with `add(result)`, `document()`, and `render(format)`.
- A named `MODE` unit exposing a non-empty canonical `name`, a `click.Command` whose name matches
  it, and `new_processor(...)`.
- A reportable `MODE` also exposes `new_collection(options)` and a unique three-digit
  `combine_key`, such as `"040"`. The key both opts the mode into coordinator reports and places
  it between adjacent keys without changing existing mode definitions. Non-reporting modes, such
  as `info`, omit `combine_key` and do not need a collection factory.
- The module's decorated Click command owns its mode-specific options and invokes the appropriate
  shared runner.

The collection receives completed `RepoResult` objects during the shared scan. It owns summary
calculation, filtering, ordering, plain/table layout, and its JSON document. Resolve supported
formats through `ReportStyle.from_format()`; use `PlainReportStyle`, `TableReportStyle`, and
`JSONReportStyle` helpers rather than recreating shared formatting or file-output behavior.

Built-in public modules under `src/ghbot/modes/` are discovered and their commands registered
automatically; do not add central CLI wiring. Keep private support modules prefixed with `_` so
discovery does not treat them as modes. Keep mode-specific processor, report, and report-contract
tests together under
`tests/unit/test_<name>_processor.py`, `tests/unit/test_<name>_report.py`, and
`tests/unit/test_<name>_report_mode.py`. Test output contracts against explicit expectations;
reserve mode-unit tests for construction, option forwarding, and collection integration.

## Coordinator commands

A command that coordinates multiple modes, such as `combo`, is not itself a scanner mode. Keep it
outside the public `ghbot.modes` package and register it explicitly in `__main__.py`; it must use
`combinable_modes()` rather than importing or maintaining a list of individual modes. This keeps
future reportable modes automatically available to the coordinator while preventing the coordinator
from being discovered as a scanner.
