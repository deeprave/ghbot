"""Tests for the cohesive issues mode unit and collection report."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from ghbot.errors import AuthError
from ghbot.modes.issues import MODE, IssuesCollectionReport, IssuesRepoProcessor
from ghbot.processor import RepoProcessor, RepoResult

_SCHEMA_MARKERS = {"$id", "schema", "schema_id", "schema_version"}


def _result() -> RepoResult:
    result = RepoResult(owner="acme", repo="web")
    result.results.update(
        {
            "open_item_count": 1,
            "open_items": [
                {
                    "number": 12,
                    "title": "Fix login",
                    "type": "issue",
                    "labels": ["bug"],
                }
            ],
            "dependabot_open_pull_requests": 0,
            "dependabot_merge_ready_pull_requests": 0,
            "other_open_pull_requests": 0,
            "other_merge_ready_pull_requests": 0,
            "oldest_dependabot_pull_request_created_at": None,
            "oldest_other_pull_request_created_at": None,
            "dependabot_pull_requests": [],
        }
    )
    return result


def test_mode_owns_issues_processor_and_collection_options():
    assert MODE.name == "issues"
    assert MODE.processor_type is IssuesRepoProcessor
    assert isinstance(IssuesRepoProcessor("a", "b", None, None), RepoProcessor)
    assert MODE.new_collection({"labels": True}).labels is True
    assert MODE.new_collection({"dates": True}).dates is True


def test_collection_aggregates_and_renders_labels_by_style():
    collection = IssuesCollectionReport(labels=True)
    collection.add(_result())

    assert collection.document()["summary"] == {
        "repos_scanned": 1,
        "repos_with_items": 1,
        "open_issues": 1,
        "open_prs": 0,
        "dependabot_open_pull_requests": 0,
        "dependabot_merge_ready_pull_requests": 0,
        "other_open_pull_requests": 0,
        "other_merge_ready_pull_requests": 0,
        "oldest_dependabot_pull_request_created_at": None,
        "oldest_other_pull_request_created_at": None,
        "pull_request_metrics_complete": True,
    }
    assert "+bug" in collection.render("plain")
    assert "Labels" in collection.render("table")
    assert '"labels": [' in collection.render("json")


def test_issues_collection_document_does_not_identify_its_schema():
    assert not _SCHEMA_MARKERS.intersection(IssuesCollectionReport().document())


def test_issues_command_help_is_owned_by_the_mode():
    from ghbot.modes.issues import issues

    result = CliRunner().invoke(issues, ["--help"])

    assert result.exit_code == 0
    assert "--labels" in result.output
    assert "--dates" in result.output
    assert "--output" in result.output


@pytest.mark.parametrize(
    ("arguments", "expected_options"),
    [
        ([], {"format": "plain", "labels": False, "dates": False}),
        (
            ["--plain", "--labels", "--dates"],
            {"format": "plain", "labels": True, "dates": True},
        ),
        (
            ["--table", "--dates"],
            {"format": "table", "labels": False, "dates": True},
        ),
        (
            ["--json", "--labels", "--dates"],
            {"format": "json", "labels": True, "dates": True},
        ),
    ],
)
def test_issues_command_routes_format_labels_and_dates_to_its_runner(
    arguments, expected_options
):
    from ghbot.modes.issues import issues

    collection = MagicMock()
    collection.render.return_value = "report\n"
    with (
        patch(
            "ghbot.modes.issues.run_mode", new=AsyncMock(return_value=collection)
        ) as run_mode,
        patch("ghbot.modes.issues.write_report") as write_report,
    ):
        result = CliRunner().invoke(issues, arguments, obj={"cfg": {}})

    assert result.exit_code == 0
    assert run_mode.await_args.args[2] == expected_options
    write_report.assert_called_once_with("report\n", None)


def test_issues_command_forwards_output(tmp_path):
    from ghbot.modes.issues import issues

    collection = MagicMock()
    collection.render.return_value = "report\n"
    destination = tmp_path / "issues.txt"
    with (
        patch(
            "ghbot.modes.issues.run_mode", new=AsyncMock(return_value=collection)
        ) as run_mode,
        patch("ghbot.modes.issues.write_report") as write_report,
    ):
        result = CliRunner().invoke(
            issues,
            ["--output", str(destination)],
            obj={"cfg": {}},
        )

    assert result.exit_code == 0
    assert run_mode.await_args.args[2] == {
        "format": "plain",
        "labels": False,
        "dates": False,
    }
    write_report.assert_called_once_with("report\n", destination)


def test_issues_command_rejects_multiple_output_formats():
    from ghbot.modes.issues import issues

    result = CliRunner().invoke(issues, ["--plain", "--table"], obj={"cfg": {}})

    assert result.exit_code != 0
    assert "choose only one" in result.output


def test_issues_command_exits_for_fatal_errors():
    from ghbot.modes.issues import issues

    with (
        patch(
            "ghbot.modes.issues.run_mode",
            new=AsyncMock(side_effect=AuthError("bad token")),
        ),
        patch("ghbot.modes.issues.log.error") as log_error,
    ):
        result = CliRunner().invoke(issues, [], obj={"cfg": {}})

    assert result.exit_code == 1
    log_error.assert_called_once_with("bad token")
