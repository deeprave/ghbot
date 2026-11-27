# Design: Command-line command refactor

## Overview

Replace the non-scanning `schema` subcommand with a leading root invocation and make help text for
all processor-backed commands use the compact `Scan for …` form. Schema resource selection and
output remain owned by `ghbot.schema`.

## Architecture

```text
argv[1] == "--schema"
    │
    ├── SchemaDispatchGroup removes the leading marker
    ├── invokes the existing schema Click command with argv[2:]
    └── exits without root configuration or processor dispatch

otherwise
    │
    └── existing root Click group → discovered mode or combo command → processors
```

`SchemaDispatchGroup`, a small `click.Group` subclass in `__main__.py`, will recognise only a
literal leading `--schema`. It will convert that route to a private sentinel command, which its
own command lookup resolves only when the dispatch marker is present. Its invocation path then
passes the preserved remaining arguments to the existing `schema` command with a schema-specific
program name. This lets Click retain its supported no-command handling without reading its private
argument state. Schema retrieval must bypass the root group callback so it does not load
configuration, configure logging, authenticate, scan, or invoke a processor.

The root command will no longer register `schema` with `add_command`. Its help formatter will
document the three leading schema forms alongside normal global options, while the commands section
contains scan commands only.

## CLI contract

| Invocation | Behaviour |
| --- | --- |
| `ghbot --schema issues` | Print the current `issues` schema. |
| `ghbot --schema --id ID` | Print the schema identified by canonical ID. |
| `ghbot --schema --list` | Print installed schema names and IDs. |
| `ghbot schema issues` | Fail as an unknown command. |
| `ghbot --id ID` / `ghbot --list` | Fail as unknown root options. |
| `ghbot info --schema` | Fail as an unknown mode option. |

The existing schema command remains the sole selector validator: exactly one of report identity,
`--id`, and `--list` is required, and unknown report names or IDs remain usage errors. The leading
marker itself is not a global Click option; this preserves the specified leading-token boundary.

## Help descriptions

The scan commands will use these descriptions:

- combo: `Scan for every reportable mode.`
- info: `Scan for repository summary statistics.`
- drift: `Scan for commits since the latest stable release.`
- issues: `Scan for open issues and pull requests.`
- security: `Scan for open security alerts.`

## Error handling

- Schema parsing and selection errors remain `click.UsageError` from `ghbot.schema`.
- A missing selector or conflicting selectors retains the existing exactly-one error.
- No dispatcher-specific recovery is needed: non-leading schema tokens proceed through ordinary
  Click parsing and are rejected there.

## Documentation and output

Update README examples and pending change requirements to the three `ghbot --schema …` forms.
Schema JSON content, IDs, registry ordering, and library APIs are unchanged. Help output gains a
concise schema-invocation note while its command list excludes `schema`.

## Test strategy

- Adapt schema-command tests to cover all three leading forms, output preservation, selector
  validation, and no authentication or repository scanning.
- Add root CLI tests for removed `schema`, ungated `--id` and `--list`, and non-leading
  `--schema` rejection.
- Assert root help excludes `schema` from commands, documents schema retrieval, and gives every
  scan command its exact consistent description.
- Run the repository's full pytest, Ruff, ty, and format gates through `uv run`.
