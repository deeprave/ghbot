# Design Document: output-controls

## Overview

Add reusable final-output controls while keeping progress logging separate from result reporting.
The `security` subcommand exposes the first UI:

```text
ghbot --owner acme security                 # plain, stdout
ghbot --owner acme security --plain         # plain, stdout
ghbot --owner acme security --table         # table, stdout
ghbot --owner acme security --json          # json, stdout
ghbot --owner acme security --json --output results.json
```

The implementation should make the output controls generic:

- `_main(...)` accepts an `options: dict | None` parameter.
- Every processor constructor accepts `options: dict | None = None`.
- The selected format is represented as `{"format": "plain" | "table" | "json"}`.
- `--output` is handled by the command/reporting layer as the final report destination.

The processor may store options for future use, but final report rendering should remain in the
report module so processors stay focused on collecting `RepoResult` data.

## Architecture

```text
security command
  ├─ parse mutually exclusive --plain/--table/--json
  ├─ build options = {"format": selected_format}
  ├─ results = asyncio.run(_main(cfg, SecurityRepoProcessor, options=options))
  └─ render/write final report with format + optional output path

_main
  └─ processor_cls(owner, repo_name, gh, monitor, options=options)

SecurityRepoProcessor
  └─ run() returns RepoResult with structured counts

report module
  ├─ plain renderer
  ├─ table renderer
  ├─ json renderer
  └─ destination writer (stdout or UTF-8 file)
```

Progress logs continue to flow through `Monitor` and `LoggingMonitor`; final reports are produced
from accumulated `RepoResult` objects only after the task pool exits.

## CLI

Add security-only options:

```python
@cli.command()
@click.option("--plain", "format_plain", is_flag=True, default=False)
@click.option("--table", "format_table", is_flag=True, default=False)
@click.option("--json", "format_json", is_flag=True, default=False)
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path))
@click.pass_context
def security(...):
    ...
```

The three format flags are mutually exclusive. A small helper can compute the effective format:

```python
def _output_format(*, plain: bool, table: bool, json: bool) -> str:
    selected = [...]
    if len(selected) > 1:
        raise click.UsageError("choose only one of --plain, --table, or --json")
    return selected[0] if selected else "plain"
```

`--plain` is optional because `"plain"` is the default.

## Processor Options

Update the protocol and concrete processors to accept generic options:

```python
class InfoRepoProcessor:
    def __init__(self, owner, repo, gh, monitor, options: dict | None = None):
        self._options = dict(options or {})
```

Do the same for `SecurityRepoProcessor`. Existing tests that construct processors without options
should continue to pass.

Update `_main`:

```python
async def _main(cfg: dict, processor_cls: type, options: dict | None = None):
    ...
    processor = processor_cls(owner, repo["name"], gh, monitor, options=options)
```

This keeps the option path reusable and avoids hard-coding security-specific arguments into the
processor constructor.

## Report Rendering

Refactor `print_security_report(results)` into a renderer plus writer. One workable API:

```python
def render_security_report(results: list[RepoResult], *, format: str = "plain") -> str: ...

def write_report(text: str, output: Path | None = None) -> None: ...

def print_security_report(
    results: list[RepoResult],
    *,
    format: str = "plain",
    output: Path | None = None,
) -> None:
    write_report(render_security_report(results, format=format), output)
```

The existing `print_security_report(results)` call remains valid and defaults to plain output.

### Plain

Plain output is the previous stacked format:

```text
Repos scanned:           42
Repos with issues:       12
Dependabot alerts:       34
Code scanning alerts:     8
Secret scanning alerts:   3

owner/repo-name
  Dependabot alerts:       5
  Code scanning alerts:    2
  Secret scanning alerts:  0
```

### Table

Table output is the compact fixed-width Markdown format:

```text
Repos scanned:           42
Repos with issues:       12
Dependabot alerts:       34
Code scanning alerts:     8
Secret scanning alerts:   3

|Repository                            | Dependabot | Scanning | Secrets |
|--------------------------------------|------------|----------|---------|
|owner/repo-name                       |           5|         2|        0|
```

### JSON

JSON output:

```json
{
  "summary": {
    "repos_scanned": 42,
    "repos_with_issues": 12,
    "dependabot_alerts": 34,
    "code_scanning_alerts": 8,
    "secret_scanning_alerts": 3
  },
  "repositories": [
    {
      "owner": "owner",
      "repo": "repo-name",
      "repository": "owner/repo-name",
      "dependabot_alerts": 5,
      "code_scanning_alerts": 2,
      "secret_scanning_alerts": 0
    }
  ]
}
```

Unlike text output, JSON includes all scanned repositories so automation can distinguish a clean
repository from an omitted one.

## Error Handling

- Invalid combinations of format flags fail as Click usage errors before `_main` runs.
- Invalid format values passed internally to the renderer raise `ValueError`.
- Output file write failures should surface as `click.ClickException` with a concise message.
- Progress logging remains on stderr through the existing logging configuration.

## Test Strategy

- CLI tests for default format, each format flag, mutual exclusion, and `--output`.
- `_main` tests proving the options dict reaches processor constructors.
- Processor constructor tests proving omitted options still work.
- Report tests for plain, table, JSON, and file output.
- Regression tests that `info` does not accept security-only format flags.
