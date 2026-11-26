# Technical Design: versioned report schemas

## Overview

Ship Draft 2020-12 schemas and a package-local registry for the `security`, `issues`, `drift`,
and combined report identities. Schema `$id` values identify schema resources only; emitted report
documents preserve their existing JSON shapes. Consumers select a schema through
`ghbot.schemas.current_schema(report)` or `schema_for_id(id)`. The separately queued CLI-schema
change will expose those same resources to shell users.

## Architecture

```text
collection.document() -> established report mapping -> JSONReportStyle

ghbot.schemas
  report identity -> current canonical ID -> packaged JSON Schema resource
  canonical ID -> packaged JSON Schema resource

tests
  real collection document + report identity -> registry schema -> Draft202012Validator
```

`src/ghbot/schemas/` remains a package under the module root. `schema_for_id()` parses a fresh
document from package resources; `current_schema_id()` and `current_schema()` are the public
identity-based lookup surface. Unknown identities or IDs raise `ValueError`; malformed trusted
package data raises `SchemaPackageError`, a non-`ValueError` exception containing the requested
schema ID. `schema_ids()` returns every current packaged canonical ID, letting callers preload
resources into their own validator registry without introducing a runtime validator dependency.
No registry operation performs network I/O.

## Schema contracts

Each resource declares its own canonical ID:

| Report | Schema `$id` |
| --- | --- |
| `security` | `ghbot://schemas/security/1.0.json` |
| `issues` | `ghbot://schemas/issues/1.0.json` |
| `drift` | `ghbot://schemas/drift/1.0.json` |
| `combined` | `ghbot://schemas/combined/1.0.json` |

Standalone schemas fully model their emitted `summary` and `repositories` structures, including
all current repository result fields, item metadata, pull-request metrics, Dependabot details, and
nullable unavailable values. They permit additional properties for future additive compatibility.
The combined schema retains external `$ref` values to the three standalone schemas, resolved from
a locally preloaded resource registry; its instance shape remains the existing three keyed nested
documents with no wrapper identifier property.

Schema files use `$schema` and `$id`, but schemas do not require an instance `$id`. Collection and
combined-report code does not import the registry merely to render an ordinary report.

The combined schema's external references require caller-managed preloading. Documentation shows
`schema_ids()` paired with `schema_for_id()` and a `referencing.Registry`. Security repository
metrics remain optional only because an unexpected failed scan can produce no metrics: absent means
not produced, `null` means attempted but unavailable, and `0` means successfully found none.

## Output and compatibility

Plain and table output do not change. JSON output does not gain `$id`, `schema`, or another
envelope property. README documents the four schema IDs, the public registry, and the rule that
additive changes increment MINOR while breaking changes increment MAJOR. Consumers reject
unsupported major versions after selecting a schema by known report identity or canonical ID.

## Test strategy

1. Keep registry tests for identity/ID lookup, fresh documents, invalid values, package-data
   failures, and installed artifact access.
2. Extend each collection test fixture to construct real complete, partial, and unavailable report
   documents, then validate each against `current_schema(report)`. Assert rendered JSON remains
   identical to its collection document and has no schema-identification property.
3. Validate combined populated and partial output with every packaged resource preloaded; assert
   external `$ref` resolution stays local and invalid nested documents fail validation.
4. Check each packaged resource against the Draft 2020-12 meta-schema, preserve JSON-render/
   document parity, and prove additive properties remain valid.
5. Run registry checks from isolated wheel and sdist installations with checkout paths excluded.
6. Run the project gates through `uv run`.
