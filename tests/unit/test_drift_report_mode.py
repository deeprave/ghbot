"""Tests for the cohesive drift mode unit and collection report."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from ghbot.errors import AuthError
from ghbot.modes.drift import MODE, DriftCollectionReport, DriftRepoProcessor
from ghbot.processor import RepoProcessor, RepoResult


def test_mode_owns_drift_processor_and_collection():
    assert MODE.name == "drift"
    assert MODE.processor_type is DriftRepoProcessor
    assert isinstance(DriftRepoProcessor("a", "b", None, None), RepoProcessor)
    assert isinstance(MODE.new_collection({}), DriftCollectionReport)


def test_collection_filters_positive_drift_and_preserves_pypi_null():
    report = DriftCollectionReport()
    result = RepoResult(owner="acme", repo="api")
    result.results.update(
        {
            "latest_release_tag": "v1.0",
            "latest_release_published_at": None,
            "default_branch": "main",
            "commits_since_release": 2,
            "pypi_publishing_configured": None,
        }
    )
    report.add(result)

    assert report.document()["summary"]["repos_with_drift"] == 1
    assert "N/A" in report.render("plain")
    assert report.document()["repositories"][0]["pypi_publishing_configured"] is None


def test_drift_collection_document_does_not_identify_its_schema():
    assert "$id" not in DriftCollectionReport().document()


def test_drift_command_help_is_owned_by_the_mode():
    from ghbot.modes.drift import drift

    result = CliRunner().invoke(drift, ["--help"])

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
def test_drift_command_routes_format_to_its_runner(arguments, expected_format):
    from ghbot.modes.drift import drift

    collection = MagicMock()
    collection.render.return_value = "report\n"
    with (
        patch(
            "ghbot.modes.drift.run_mode", new=AsyncMock(return_value=collection)
        ) as run_mode,
        patch("ghbot.modes.drift.write_report") as write_report,
    ):
        result = CliRunner().invoke(drift, arguments, obj={"cfg": {}})

    assert result.exit_code == 0
    assert run_mode.await_args.args[2] == {"format": expected_format}
    write_report.assert_called_once_with("report\n", None)


def test_drift_command_rejects_multiple_output_formats():
    from ghbot.modes.drift import drift

    result = CliRunner().invoke(drift, ["--plain", "--json"], obj={"cfg": {}})

    assert result.exit_code != 0
    assert "choose only one" in result.output


def test_drift_command_forwards_output_and_exits_for_fatal_errors(tmp_path):
    from ghbot.modes.drift import drift

    destination = tmp_path / "drift.txt"
    collection = MagicMock()
    collection.render.return_value = "report\n"
    with (
        patch("ghbot.modes.drift.run_mode", new=AsyncMock(return_value=collection)),
        patch("ghbot.modes.drift.write_report") as write_report,
    ):
        result = CliRunner().invoke(
            drift, ["--output", str(destination)], obj={"cfg": {}}
        )

    assert result.exit_code == 0
    write_report.assert_called_once_with("report\n", destination)

    with (
        patch(
            "ghbot.modes.drift.run_mode",
            new=AsyncMock(side_effect=AuthError("bad token")),
        ),
        patch("ghbot.modes.drift.log.error") as log_error,
    ):
        result = CliRunner().invoke(drift, [], obj={"cfg": {}})

    assert result.exit_code == 1
    log_error.assert_called_once_with("bad token")
