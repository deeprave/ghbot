# Bug Fix: list schema names and IDs

## Defect

`ghbot schema` can retrieve a schema only when the caller already knows a report name or canonical
ID. The command lacks a discovery form, so shell users cannot enumerate installed schemas before
selecting one.

## Reproduction

Run `ghbot schema --list`. The option is not supported, even though the installed public registry
already knows every current schema ID.

## Expected behaviour

`ghbot schema --list` returns every current schema's report name and canonical ID as a deterministic,
newline-terminated JSON list. It is local-only, does not read schema documents, and cannot be
combined with a report selector or `--id`.

## Root cause

The public registry exposes schema IDs but not the corresponding report names, and the CLI has no
listing selection path.

## Fix approach

Expose current name/ID pairs from the public registry, then add a mutually exclusive `--list`
path that serializes those pairs. Preserve the existing identity and exact-ID retrieval forms.
