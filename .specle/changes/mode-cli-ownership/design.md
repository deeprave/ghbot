# Technical Design: mode CLI ownership

## Overview

Move the standalone Click command for each reportable mode into its owning module. The application
shell remains responsible for common configuration and the non-reporting `info` operation, but it
registers reportable commands through one `ghbot.modes` package export. Extract the existing async
scan loops from `__main__.py` into a dependency-neutral runner module so mode commands can invoke
the shared scan path without importing the application shell.

No command syntax, output contract, API call, or processor policy changes.

## Architecture

```text
src/ghbot/
  __main__.py             Click group, global options, info command, built-in registration
  runner.py               async run_processor() and run_mode() scan paths
  modes/
    __init__.py           BUILTIN_COMMANDS registration boundary
    security.py           MODE, collection, processor, security Click command
    issues.py             MODE, collection, processor, issues Click command
    drift.py              MODE, collection, processor, drift Click command
  report_style.py         shared report-style factory and output writer
```

```text
ghbot --global-options <mode> --mode-options
  -> cli() merges configuration and stores cfg on Click context
  -> command selected from modes.BUILTIN_COMMANDS
  -> mode command parses its own flags and builds its options mapping
  -> asyncio.run(run_mode(cfg, MODE, options))
  -> mode collection.render(format) -> write_report(text, output)
```

`info` remains `cli`'s locally registered non-reporting command and enters
`asyncio.run(run_processor(cfg, InfoRepoProcessor))`. Both runner functions use the same existing
authentication, discovery, `LoggingMonitor`, and `TaskPool` sequence. Neither receives CLI format,
labels, or output-destination state except the opaque mode `options` mapping needed by a processor
or collection.

## Command registration and ownership

Each reportable mode module defines one `@click.command` object with its established command name
and help text. It owns all of its options:

| Command | Owned options | Options mapping |
| --- | --- | --- |
| `security` | `--plain`, `--table`, `--json`, `--output` | `{"format": format}` |
| `issues` | `--plain`, `--table`, `--json`, `--labels`, `--output` | `{"format": format, "labels": labels}` |
| `drift` | `--plain`, `--table`, `--json`, `--output` | `{"format": format}` |

The three modules use the shared report-style format-selection helper to translate the mutually
exclusive flags into `plain`, `table`, or `json`. The helper continues to raise
`click.UsageError("choose only one of --plain, --table, or --json")`, preserving the current
error message and exit behaviour. It is not an application-shell concern and is not a mode
registry.

`ghbot.modes.__init__` imports the three command objects and exports an ordered, static
`BUILTIN_COMMANDS` tuple. `__main__.py` imports that tuple once and calls `cli.add_command(command)`
for each member after defining the group. It does not import individual mode units, declare mode
flags, or construct mode option mappings. This is a static boundary only: it neither discovers
plugins nor implements `combo`.

## Runner contract

`runner.py` receives the configuration mapping already merged by the Click group.

- `run_processor(cfg, processor_cls, options=None)` is the extracted existing processor-only loop
  used by `info`; it returns `list[RepoResult]`.
- `run_mode(cfg, mode, options=None)` is the extracted reportable loop; it creates the collection,
  constructs one mode processor per discovered repository with `owner_type`, and adds completed
  results inside the submitted pool task before returning the collection.

The runner does not render output or inspect option keys. The command catches `FatalError` at the
synchronous boundary, logs its message, and exits with its existing exit code. `write_report`
continues to turn output-file `OSError` failures into `click.ClickException`.

## Error handling

| Event | Owner | Behaviour |
| --- | --- | --- |
| Multiple format flags | mode command | raise the established `click.UsageError` before scanning |
| Invalid mode option use | Click | retain Click's existing option parsing and help behaviour |
| `FatalError` from authentication, discovery, or a processor | mode or info command | log and exit at the synchronous command boundary |
| Recoverable GitHub API error | processor | unchanged: partial result and mode-defined rendering |
| Output write failure | shared writer | unchanged: `click.ClickException` |

The refactor does not introduce endpoints, alter `github_api_call` use, bypass archive filtering,
or change authentication source selection.

## Output compatibility

Mode commands pass the selected format to their existing collection renderer and the requested
destination to `write_report`. Consequently plain, Markdown-table, JSON, labels, summaries,
filtering, ordering, unavailable-data markers, and JSON schemas remain exactly collection-owned.
`info` continues not to render a stdout report.

## Test strategy

1. Move the command-specific tests out of `test_main.py` to the owning security, issues, and drift
   mode test modules. Patch `run_mode` and `write_report` at each mode module's import site.
2. For every reportable command, assert the default and each `--plain`/`--table`/`--json` option
   produces the expected mode options; assert conflicting flags fail before scanning; and assert
   `--output` is passed only to the shared writer.
3. Assert `issues --labels` reaches only the issues collection options, including when combined
   with each output format.
4. Keep application-shell tests for global configuration, `info`, and registration of the three
   package-provided commands. Confirm global options work before a registered mode and are not
   declared by the mode itself.
5. Retain runner tests for owner-type propagation, TaskPool collection timing, authentication,
   discovery, and fatal-error propagation after their imports move from `__main__` to `runner`.
6. Run `uv run pytest -v -Werror -Walways`, `uv run ruff check`, `uv run ty check src/`, and
   `uv run ruff format --check` during verification.
