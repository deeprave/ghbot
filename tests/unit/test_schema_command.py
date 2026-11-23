"""Tests for the local packaged-schema CLI command."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

_SCHEMA = {"$id": "ghbot://schemas/issues/1.0.json", "type": "object"}
_SCHEMA_ENTRIES = (
    ("security", "ghbot://schemas/security/1.0.json"),
    ("issues", "ghbot://schemas/issues/1.0.json"),
)


def test_schema_command_resolves_a_report_identity_without_scanning():
    from ghbot.__main__ import cli

    with (
        patch("ghbot.schema.current_schema", return_value=_SCHEMA) as current_schema,
        patch("ghbot.runner.get_auth_token", new=AsyncMock()) as get_auth_token,
        patch("ghbot.runner.scan_repositories") as scan_repositories,
    ):
        result = CliRunner().invoke(cli, ["schema", "issues"])

    assert result.exit_code == 0
    assert result.output == json.dumps(_SCHEMA, indent=2) + "\n"
    assert json.loads(result.output) == _SCHEMA
    current_schema.assert_called_once_with("issues")
    get_auth_token.assert_not_awaited()
    scan_repositories.assert_not_called()


def test_schema_command_resolves_a_canonical_id():
    from ghbot.__main__ import cli

    schema_id = "ghbot://schemas/issues/1.0.json"
    with patch("ghbot.schema.schema_for_id", return_value=_SCHEMA) as schema_for_id:
        result = CliRunner().invoke(cli, ["schema", "--id", schema_id])

    assert result.exit_code == 0
    assert json.loads(result.output) == _SCHEMA
    schema_for_id.assert_called_once_with(schema_id)


def test_schema_command_lists_names_and_ids_without_scanning():
    from ghbot.__main__ import cli

    with (
        patch("ghbot.schema.schema_entries", return_value=_SCHEMA_ENTRIES) as entries,
        patch("ghbot.schema.current_schema") as current_schema,
        patch("ghbot.schema.schema_for_id") as schema_for_id,
        patch("ghbot.runner.get_auth_token", new=AsyncMock()) as get_auth_token,
        patch("ghbot.runner.scan_repositories") as scan_repositories,
    ):
        result = CliRunner().invoke(cli, ["schema", "--list"])

    assert result.exit_code == 0
    assert json.loads(result.output) == [
        {"name": name, "id": schema_id} for name, schema_id in _SCHEMA_ENTRIES
    ]
    entries.assert_called_once_with()
    current_schema.assert_not_called()
    schema_for_id.assert_not_called()
    get_auth_token.assert_not_awaited()
    scan_repositories.assert_not_called()


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["issues", "--id", "ghbot://schemas/issues/1.0.json"],
        ["issues", "--list"],
        ["--id", "ghbot://schemas/issues/1.0.json", "--list"],
    ],
)
def test_schema_command_requires_exactly_one_selector(arguments):
    from ghbot.__main__ import cli

    result = CliRunner().invoke(cli, ["schema", *arguments])

    assert result.exit_code == 2
    assert "exactly one" in result.output


@pytest.mark.parametrize(
    ("arguments", "value"),
    [
        (["unknown"], "unknown"),
        (["--id", "ghbot://schemas/unknown/1.0.json"], "unknown"),
    ],
)
def test_schema_command_reports_unsupported_selectors(arguments, value):
    from ghbot.__main__ import cli

    with (
        patch("ghbot.schema.current_schema", side_effect=ValueError("unknown")),
        patch("ghbot.schema.schema_for_id", side_effect=ValueError("unknown")),
    ):
        result = CliRunner().invoke(cli, ["schema", *arguments])

    assert result.exit_code == 2
    assert value in result.output
