# Add schema to CLI

## Problem

The package ships report schemas but CLI users cannot retrieve them without Python code.

## Goal

Add a read-only `ghbot schema` command that prints a packaged schema by either report identity or
canonical schema ID.

## Interface

```text
ghbot schema issues
ghbot schema --id ghbot://schemas/issues/1.0.json
```

Exactly one selector is required. The command prints newline-terminated JSON from the public
`ghbot.schemas` registry and makes no authentication, scan, or network request.

## Errors and boundaries

Unsupported identities and IDs become clear Click usage errors containing the supplied value.
Existing report commands and their JSON payloads are unchanged; schemas remain package-local
resources rather than URI endpoints.

## Verification

Test both successful forms, selection validation, unknown values, valid JSON output, and the
absence of scanner/authentication calls. Document both forms in README.
