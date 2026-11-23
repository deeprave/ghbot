"""Tests for the public packaged-schema registry."""

import pytest

from ghbot import schemas
from ghbot.schemas import (
    SchemaPackageError,
    current_schema,
    current_schema_id,
    schema_for_id,
    schema_ids,
)


@pytest.mark.parametrize(
    ("report", "schema_id"),
    [
        ("security", "ghbot://schemas/security/1.0.json"),
        ("issues", "ghbot://schemas/issues/1.0.json"),
        ("drift", "ghbot://schemas/drift/1.0.json"),
        ("combined", "ghbot://schemas/combined/1.0.json"),
    ],
)
def test_current_schema_resolves_each_report_identity(report, schema_id):
    assert current_schema_id(report) == schema_id
    assert current_schema(report)["$id"] == schema_id
    assert schema_for_id(schema_id)["$id"] == schema_id


def test_schema_for_id_returns_a_fresh_document():
    first = schema_for_id("ghbot://schemas/security/1.0.json")
    second = schema_for_id("ghbot://schemas/security/1.0.json")

    first["title"] = "mutated"

    assert second["title"] == "ghbot security report 1.0"


@pytest.mark.parametrize("value", ["info", "unknown"])
def test_current_schema_rejects_unknown_report_identity(value):
    with pytest.raises(ValueError, match=value):
        current_schema_id(value)


def test_schema_for_id_rejects_unknown_identifier():
    unknown_id = "ghbot://schemas/info/1.0.json"

    with pytest.raises(ValueError, match=unknown_id):
        schema_for_id(unknown_id)


def test_schema_ids_lists_the_current_packaged_resources():
    assert schema_ids() == (
        "ghbot://schemas/security/1.0.json",
        "ghbot://schemas/issues/1.0.json",
        "ghbot://schemas/drift/1.0.json",
        "ghbot://schemas/combined/1.0.json",
    )


@pytest.mark.parametrize(
    "content", ["not json", "[]", '{"$id": "ghbot://schemas/issues/1.0.json"}']
)
def test_schema_for_id_wraps_invalid_package_data(monkeypatch, content):
    class Resource:
        def read_text(self, *, encoding):
            return content

    class Package:
        def joinpath(self, resource):
            return Resource()

    monkeypatch.setattr(schemas, "files", lambda package: Package())

    with pytest.raises(SchemaPackageError, match="ghbot://schemas/security/1.0.json"):
        schema_for_id("ghbot://schemas/security/1.0.json")


def test_schema_for_id_wraps_unreadable_package_data(monkeypatch):
    class Resource:
        def read_text(self, *, encoding):
            raise OSError("unreadable")

    class Package:
        def joinpath(self, resource):
            return Resource()

    monkeypatch.setattr(schemas, "files", lambda package: Package())

    with pytest.raises(SchemaPackageError, match="ghbot://schemas/security/1.0.json"):
        schema_for_id("ghbot://schemas/security/1.0.json")
