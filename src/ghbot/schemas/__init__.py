"""Public access to ghbot's packaged report schemas."""

from __future__ import annotations

import json
from importlib.resources import files

__all__ = [
    "SchemaPackageError",
    "current_schema",
    "current_schema_id",
    "schema_entries",
    "schema_for_id",
    "schema_ids",
]

_SCHEMA_PATHS = {
    "security": "security/1.0.json",
    "issues": "issues/1.0.json",
    "drift": "drift/1.0.json",
    "combined": "combined/1.0.json",
}
_CURRENT_IDS = {
    report: f"ghbot://schemas/{path}" for report, path in _SCHEMA_PATHS.items()
}
_RESOURCE_BY_ID = {
    schema_id: _SCHEMA_PATHS[report] for report, schema_id in _CURRENT_IDS.items()
}


class SchemaPackageError(RuntimeError):
    """A packaged schema resource is absent or invalid."""


def schema_ids() -> tuple[str, ...]:
    """Return the canonical identifiers of all current packaged schemas."""
    return tuple(_RESOURCE_BY_ID)


def schema_entries() -> tuple[tuple[str, str], ...]:
    """Return the current report identities and canonical schema identifiers."""
    return tuple(_CURRENT_IDS.items())


def current_schema_id(report: str) -> str:
    """Return the current canonical schema identifier for *report*."""
    try:
        return _CURRENT_IDS[report]
    except KeyError as error:
        raise ValueError(f"unknown report identity: {report}") from error


def schema_for_id(schema_id: str) -> dict[str, object]:
    """Load the packaged schema identified by *schema_id*."""
    try:
        resource = _RESOURCE_BY_ID[schema_id]
    except KeyError as error:
        raise ValueError(f"unknown schema identifier: {schema_id}") from error
    try:
        document = json.loads(
            files(__package__).joinpath(resource).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SchemaPackageError(
            f"could not load packaged schema: {schema_id}"
        ) from error
    if not isinstance(document, dict):
        raise SchemaPackageError(f"packaged schema is not an object: {schema_id}")
    if document.get("$id") != schema_id:
        raise SchemaPackageError(f"packaged schema has mismatched ID: {schema_id}")
    return document


def current_schema(report: str) -> dict[str, object]:
    """Load the current packaged schema for *report*."""
    return schema_for_id(current_schema_id(report))
