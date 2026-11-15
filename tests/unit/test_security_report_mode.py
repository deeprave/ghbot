from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from ghbot.errors import AuthError
from ghbot.processor import RepoResult


def test_security_mode_unit_pairs_processor_with_collection_report():
    from ghbot.modes.security import (
        MODE,
        SecurityCollectionReport,
        SecurityRepoProcessor,
    )

    assert MODE.name == "security"
    assert MODE.processor_type is SecurityRepoProcessor
    assert isinstance(MODE.new_collection({}), SecurityCollectionReport)


def test_security_collection_aggregates_results():
    from ghbot.modes.security import MODE
    from ghbot.report_style import PlainReportStyle

    result = RepoResult(owner="acme", repo="api")
    result.results.update(
        {
            "dependabot_alerts": 2,
            "code_scanning_alerts": 0,
            "secret_scanning_alerts": 0,
            "dependabot_open_pull_requests": 0,
            "dependabot_ready_pull_requests": 0,
        }
    )
    report = MODE.new_collection({})
    report.add(result)

    assert report.document()["summary"]["dependabot_alerts"] == 2
    assert "acme/api" in report.render(PlainReportStyle())


def test_security_command_help_is_owned_by_the_mode():
    from ghbot.modes.security import security

    result = CliRunner().invoke(security, ["--help"])

    assert result.exit_code == 0
    assert "--plain" in result.output
    assert "--output" in result.output


@pytest.mark.parametrize(
    ("arguments", "expected_format"),
    [
        ([], "plain"),
        (["--plain"], "plain"),
        (["--table"], "table"),
        (["--json"], "json"),
    ],
)
def test_security_command_routes_format_to_its_runner(arguments, expected_format):
    from ghbot.modes.security import security

    collection = MagicMock()
    collection.render.return_value = "report\n"
    with (
        patch(
            "ghbot.modes.security.run_mode", new=AsyncMock(return_value=collection)
        ) as run_mode,
        patch("ghbot.modes.security.write_report") as write_report,
    ):
        result = CliRunner().invoke(security, arguments, obj={"cfg": {}})

    assert result.exit_code == 0
    assert run_mode.await_args.args[2] == {"format": expected_format}
    write_report.assert_called_once_with("report\n", None)


def test_security_command_rejects_multiple_output_formats():
    from ghbot.modes.security import security

    result = CliRunner().invoke(security, ["--table", "--json"], obj={"cfg": {}})

    assert result.exit_code != 0
    assert "choose only one" in result.output


def test_security_command_forwards_output(tmp_path):
    from ghbot.modes.security import security

    destination = tmp_path / "security.txt"
    collection = MagicMock()
    collection.render.return_value = "report\n"
    with (
        patch(
            "ghbot.modes.security.run_mode",
            new=AsyncMock(return_value=collection),
        ),
        patch("ghbot.modes.security.write_report") as write_report,
    ):
        result = CliRunner().invoke(
            security, ["--output", str(destination)], obj={"cfg": {}}
        )

    assert result.exit_code == 0
    write_report.assert_called_once_with("report\n", destination)


def test_security_command_exits_for_fatal_errors():
    from ghbot.modes.security import security

    with (
        patch(
            "ghbot.modes.security.run_mode",
            new=AsyncMock(side_effect=AuthError("bad token")),
        ),
        patch("ghbot.modes.security.log.error") as log_error,
    ):
        result = CliRunner().invoke(security, [], obj={"cfg": {}})

    assert result.exit_code == 1
    log_error.assert_called_once_with("bad token")
