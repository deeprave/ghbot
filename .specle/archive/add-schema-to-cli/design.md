# Technical Design: add schema to CLI

## Overview

Add a read-only `ghbot schema` subcommand that prints one installed JSON Schema resource. It accepts
either a report identity (`ghbot schema issues`) or an exact canonical ID
(`ghbot schema --id ghbot://schemas/issues/1.0.json`). The command delegates all resource lookup
to `ghbot.schemas`; it neither authenticates nor starts a repository scan.

## Architecture

```text
Click root group
    └── schema command
          ├── report identity ──> current_schema(report)
          └── --id value ──────> schema_for_id(schema_id)
                                     │
                                     └── packaged JSON resource
          └── json.dumps(..., indent=2) ──> stdout
```

Place the command in `src/ghbot/schema.py`, alongside the existing command modules, and register
it from `src/ghbot/__main__.py`. The command module imports only `click`, `json`, and the public
registry functions; it does not import runners, modes, or GitHub clients.

## CLI and output

```text
ghbot schema <report>
ghbot schema --id <canonical-schema-id>
```

The optional positional `report` and `--id` option are mutually exclusive and exactly one is
required. Successful lookup serializes the registry-returned dictionary with two-space indentation
and `click.echo`, producing valid JSON with exactly one terminating newline. Serialization retains
the packaged mapping's key order; this command does not add an envelope or identifier to a report
payload.

## Error handling

| Condition | Behaviour |
| --- | --- |
| neither selector or both selectors | `click.UsageError` explaining that exactly one selector is required |
| unknown report identity | convert registry `ValueError` to `click.UsageError` that includes the supplied identity |
| unknown canonical ID | convert registry `ValueError` to `click.UsageError` that includes the supplied ID |
| invalid packaged resource | preserve the registry's package-data failure rather than treating it as an unsupported user selector |

The root callback may still establish normal local configuration and logging, but schema lookup
does not request credentials, instantiate a runner, scan repositories, or make network calls.

## Documentation

Add both invocation forms to the README JSON-schema section, stating that the command reads
packaged resources through the installed library registry and never dereferences `ghbot:` IDs.

## Test strategy

1. Add command tests that invoke the root CLI for identity and `--id` lookups, parse stdout as
   JSON, and assert exactly one trailing newline.
2. Test missing and conflicting selectors, plus unsupported identity and ID errors; assert each
   unsupported value appears in the Click usage error.
3. Patch the command's registry functions and scan/auth boundaries to prove lookups use the public
   registry only and do not authenticate, invoke a runner, or make network calls.
4. Keep existing command registration and report-output tests green, then run all project gates
   through `uv run`.
