# Versioned report schemas

## Problem

JSON report consumers cannot tell whether a ghbot document is compatible, and no package-shipped schema describes its structure.

## Goal

Version every `security`, `issues`, `drift`, and combined JSON document; ship a JSON Schema for each; validate real output against those schemas; and document semantic-version compatibility.

## Design boundaries

- Each document has `schema_version` and `mode`; the combined wrapper and nested reports are independently versioned.
- Initial versions are `1.0`, describing the report contracts implemented at delivery time.
- Schemas are package data accessible with `importlib.resources`, permit additive properties, and document `null` as unavailable where applicable.
- Plain and table formats remain unchanged.

## Verification

Validate current, partial, and unavailable documents for every report against the shipped schemas, verify package-data access from built distributions, and run repository Python gates through `uv run`.
