# Technical Design: combo reports

## Overview

Add a `combo` coordinator command which discovers the current reportable mode set through
`combinable_modes()`, scans each repository once, and feeds each mode's result into its own
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
       ├─ combinable_modes() -> ReportableModeDefinition tuple
       ├─ options-by-mode (issues receives labels; all receive format)
       └─ run_combo(cfg, modes, options_by_mode)
            ├─ construct each mode collection
            ├─ authenticate and create one GitHub client
            ├─ scan_repositories(...) once
            └─ TaskPool task per repository
                 └─ construct and await every selected processor using the same
                    owner, repository, GitHub client, monitor, options, and owner type
                 └─ stage each RepoResult locally, then add all results to their corresponding
                    collections only after every selected mode completes
       └─ CombinedCollectionReport(...).render(format) -> write_report(...)
```

`run_combo` belongs in `runner.py`, next to `run_mode`, because it owns the shared asynchronous
repository scan, authentication, client, and TaskPool lifecycle. The Click command belongs in a
new top-level `ghbot.combo` module because it owns its own CLI-only flags and synchronous
`FatalError` boundary.

## API and data

`runner.run_combo` accepts the merged configuration, an ordered tuple of
`ReportableModeDefinition` values, and options keyed by canonical mode name. It returns a
`CombinedCollectionReport` constructed from ordered `ReportSection` records.

Every selected mode receives its own options mapping. All modes receive `{"format": format}`;
the `issues` mapping additionally receives `{"labels": show_labels}`. No other mode sees the
issues-specific option.

The current dynamically discovered sequence is `drift`, `issues`, and `security`. Future
combinable modes automatically obtain a collection and section through the same loop. `info` is
excluded before execution because `combinable_modes()` returns only reportable combinable modes.

`CombinedCollectionReport.document()` already produces the required JSON shape:

```json
{
  "drift": {"summary": {}, "repositories": []},
  "issues": {"summary": {}, "repositories": []},
  "security": {"summary": {}, "repositories": []}
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
- A secondary rate limit is retried by `TaskPool` at repository-task scope. The task therefore
  stages results in a local mapping and adds them to mode collections only after every mode has
  completed; a retry cannot duplicate earlier successful mode results.
- A processor's normal partial or failed `RepoResult` is added only to that mode's collection;
  successful results from other modes for the same repository remain available.
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
   every processor, isolated result collection, `FatalError` propagation, and no duplicate
   collection entries after a secondary-rate-limit retry.
2. Add combo command tests covering default/selected formats, mutually exclusive format failure,
   `--labels` option routing only to issues, output writing, and fatal exit handling.
3. Extend CLI registration coverage to prove `combo` is available without becoming a discovered
   scanner mode.
4. Extend composition tests to assert discovery/canonical ordering is preserved in text and JSON
   keys and that mode collection documents are nested unchanged.
5. Run the full project quality gates through `uv run`: pytest with warnings as errors, Ruff,
   ty, and format check.
