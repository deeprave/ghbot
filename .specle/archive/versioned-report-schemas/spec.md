# Versioned report schemas

## Problem

JSON report consumers cannot tell which contract a ghbot document promises to satisfy, and no package-shipped registry resolves versioned report schemas.

## Goal

Ship versioned schemas for `security`, `issues`, `drift`, and combined JSON with a public library registry; validate real output through its report identity; and document compatibility policy.

## Design boundaries

- Schema resources carry canonical `ghbot:` `$id` values. Report documents retain their established shapes and do not carry schema IDs.
- Initial IDs use `ghbot://schemas/<report>/1.0.json`, describing the report contracts implemented at delivery time.
- A public ghbot library registry resolves schema IDs, discovers a report's current schema, and exposes packaged schema documents without callers depending on package-file paths or generic URI-scheme dereferencing.
- `schema_ids()` enables consumers to preload local resources for combined-schema validation; malformed installed resources raise a distinct package-data error rather than `ValueError`.
- Schemas permit additive properties and document `null` as unavailable where applicable.
- Plain and table formats remain unchanged.
- Security metrics preserve absent/`null`/zero semantics for failed, unavailable, and clean scans.

## Verification

Validate real current, partial, and unavailable documents for every report against the schema resolved by report identity; verify library-registry access from built distributions; and run repository Python gates through `uv run`.
