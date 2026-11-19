# Technical Design: combo reports

## Overview

Add a `combo` coordinator command which discovers the current reportable mode set through
`combinable_modes()`, scans each repository once, and feeds each keyed mode's result into its own
collection. It reuses `CombinedCollectionReport` to render those existing collections as labelled
plain/table sections or a JSON object keyed by canonical mode name.

`combo` is a coordinator, not a discoverable scanner mode. It therefore lives outside the public
`ghbot.modes` package and is registered explicitly by the application shell alongside the
dynamically registered scanner commands. This does not reintroduce a mode registry: the command
imports no individual mode implementation and obtains its complete scan set only from discovery.

## Architecture

```text
Click CLI
  ├─ discovers and registers public scanner MODE.command values
  └─ registers combo command
       ├─ combinable_modes() -> combine-key-ordered ReportableModeDefinition tuple
       ├─ options-by-mode (issues receives labels; all receive format)
       └─ run_combo(cfg, modes, options_by_mode)
            ├─ construct each mode collection
            ├─ authenticate and create one GitHub client
            ├─ scan_repositories(...) once
            └─ TaskPool task per repository
                 └─ construct and await every selected processor using the same
                    owner, repository, GitHub client, monitor, options, and owner type
                 └─ retain completed RepoResults across a retry; add them once every selected
                    mode completes, or retain them when a later mode has an ordinary failure
       └─ CombinedCollectionReport(...).render(format) -> write_report(...)
```

`run_combo` belongs in `runner.py`, next to `run_mode`, because it owns the shared asynchronous
repository scan, authentication, client, and TaskPool lifecycle. The Click command belongs in a
new top-level `ghbot.combo` module because it owns its own CLI-only flags and synchronous
`FatalError` boundary.

Before any runner starts discovery, the application shell normalises configured owners through an
insertion-ordered mapping keyed by `owner.casefold()`. The mapping retains the first spelling,
logs subsequent case-insensitive duplicates as skipped, and supplies its values to both bare
repository expansion and owner-based discovery. This ensures all commands, including `combo`,
make at most one scan per owner without losing deterministic ordering.

## API and data

`runner.run_combo` accepts the merged configuration, an ordered tuple of
`ReportableModeDefinition` values, and options keyed by canonical mode name. It returns a
`CombinedCollectionReport` constructed from ordered `ReportSection` records.

Every selected mode receives its own options mapping. All modes receive `{"format": format}`;
the `issues` mapping additionally receives `{"labels": show_labels}`. No other mode sees the
issues-specific option.

Every reportable mode has a unique three-digit `combine_key`. The current dynamically discovered
sequence is security `010`, issues `020`, and drift `030`. Future keyed modes automatically obtain
a collection and section through the same loop; inserting a mode requires only its own key. `info`
is excluded before execution because it has no `combine_key`. `discover_modes()` remains
alphabetical for CLI registration; only `combinable_modes()` applies report ordering.

`CombinedCollectionReport.document()` already produces the required JSON shape:

```json
{
  "security": {"summary": {}, "repositories": []},
  "issues": {"summary": {}, "repositories": []},
  "drift": {"summary": {}, "repositories": []}
}
```

Each nested value comes directly from the respective collection's `document()` and therefore
retains its standalone schema. Plain and table output similarly reuse the collection `render()`
methods, with the existing composition class adding only section labels and blank-line separation.

## Error handling

- Token acquisition, repository discovery, `TaskPool`, and GitHub-client lifecycle follow the
  existing runner policy unchanged.
- `FatalError`, including primary and secondary rate limits, escapes `run_combo` and reaches the
  synchronous `combo` command, which logs its safe message and exits with its established code.
- A secondary rate limit is retried by `TaskPool` at repository-task scope. The task retains
  completed results in a mapping shared by its retry attempts, skips those modes on retry, and
  adds each result only after every selected mode has completed; a retry cannot duplicate earlier
  successful mode results.
- `TaskPool` retains a non-rate-limit `FatalError` object when a task raises it, including from a
  secondary-rate-limit retry, and re-raises that same object from its exit boundary after in-flight
  work completes. This preserves its safe message and exit code for `combo`'s existing CLI
  handler. Primary/secondary rate-limit classification and retry behaviour are unchanged and
  remain separate from this correction.
- A processor's normal partial or failed `RepoResult` is added only to that mode's collection;
  successful results from other modes for the same repository remain available. If a later mode
  raises a non-fatal ordinary exception, the task adds its already-completed mode results before
  re-raising the error for `TaskPool`'s established ordinary-error handling. Fatal and rate-limit
  errors do not take this partial-commit path.
- The command uses `output_format()` for the established mutually exclusive format validation and
  `write_report()` for standard stdout/file and file-write error behaviour.

## Report and CLI behaviour

The new command surface is:

```text
ghbot [global options] combo [--plain | --table | --json] [--labels] [--output FILE]
```

`--plain` remains the default. `--labels` affects only the nested/rendered issues collection. The
command is explicitly registered in `__main__.py`; discovery continues to register all public
scanner commands and never attempts to import the coordinator as a scanner definition.

The README gains a user-facing `combo` command description and examples. CONTRIBUTING documents
that coordinator commands must remain outside the discoverable scanner-mode package unless they
satisfy the scanner `MODE` contract.

## Test strategy

1. Extend runner tests with a fake discovered repository and fake reportable modes to prove one
   `scan_repositories()` pass, one TaskPool repository task, owner-type/context propagation to
   every processor, isolated result collection, `FatalError` propagation, retention of
   completed-mode results after an ordinary later-mode failure, and no duplicate collection
   entries after a secondary-rate-limit retry.
2. Add combo command tests covering default/selected formats, mutually exclusive format failure,
   `--labels` option routing only to issues, output writing, and fatal exit handling.
3. Extend CLI registration coverage to prove `combo` is available without becoming a discovered
   scanner mode.
4. Extend discovery and composition tests to assert `combine_key` validation and ordering is
   preserved in text and JSON keys and that mode collection documents are nested unchanged.
5. Run the full project quality gates through `uv run`: pytest with warnings as errors, Ruff,
   ty, and format check.
6. Add regression tests for preserving a non-rate-limit `FatalError` through the real `TaskPool`
   and for case-insensitive duplicate CLI/config owners being scanned only once in first-seen
   order.
7. Cover a non-rate-limit `FatalError` raised on the retry following a secondary rate limit.
