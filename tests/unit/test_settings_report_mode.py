"""Tests for the standalone settings report mode."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from ghbot.modes.settings import MODE, SettingsCollectionReport, settings
from ghbot.processor import RepoResult, record_unavailable


def test_settings_mode_is_reportable_but_not_combinable():
    assert MODE.name == "settings"
    assert isinstance(MODE.new_collection({}), SettingsCollectionReport)
    assert not hasattr(MODE, "combine_key")


def test_settings_collection_renders_a_safe_document_and_unavailability():
    result = RepoResult(owner="acme", repo="api", status="partial")
    result.results.update(
        {
            "general": {"visibility": "PRIVATE", "default_branch": "main"},
            "security": {"vulnerability_alerts_enabled": True},
            "classic_protection": None,
            "rulesets": [],
            "actions_variables": ["DEPLOY_TARGET"],
            "actions_secrets": None,
        }
    )
    record_unavailable(result, "actions_secrets", reason="forbidden")
    record_unavailable(result, "ruleset_bypass_actors", reason="forbidden")
    report = SettingsCollectionReport([result])

    document = report.document()

    assert document["summary"] == {"repos_scanned": 1}
    assert document["repositories"][0]["repository"] == "acme/api"
    assert json.loads(report.render("json")) == document
    assert "acme/api" in report.render("plain")
    assert "N/A (forbidden)" in report.render("plain")
    assert "Ruleset bypass actors: N/A (forbidden)" in report.render("plain")


def test_settings_command_routes_plain_and_json_and_rejects_table():
    collection = MagicMock()
    collection.render.return_value = "report\n"
    with (
        patch(
            "ghbot.modes.settings.run_mode", new=AsyncMock(return_value=collection)
        ) as run_mode,
        patch("ghbot.modes.settings.write_report") as write_report,
    ):
        plain = CliRunner().invoke(settings, [], obj={"cfg": {}})
        json_result = CliRunner().invoke(settings, ["--json"], obj={"cfg": {}})
        table = CliRunner().invoke(settings, ["--table"], obj={"cfg": {}})

    assert plain.exit_code == 0
    assert json_result.exit_code == 0
    assert run_mode.await_args_list[0].args[2] == {"format": "plain"}
    assert run_mode.await_args_list[1].args[2] == {"format": "json"}
    assert write_report.call_count == 2
    assert table.exit_code != 0
    assert "No such option" in table.output


def test_settings_command_writes_requested_output_file(tmp_path):
    collection = MagicMock()
    collection.render.return_value = "report\n"
    destination = tmp_path / "settings.json"
    with (
        patch("ghbot.modes.settings.run_mode", new=AsyncMock(return_value=collection)),
        patch("ghbot.modes.settings.write_report") as write_report,
    ):
        result = CliRunner().invoke(
            settings, ["--json", "--output", str(destination)], obj={"cfg": {}}
        )

    assert result.exit_code == 0
    write_report.assert_called_once_with("report\n", destination)
