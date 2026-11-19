"""Tests for the combo coordinator command."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from ghbot.errors import AuthError


def _mode(name: str) -> MagicMock:
    mode = MagicMock()
    mode.name = name
    return mode


@pytest.mark.parametrize(
    ("arguments", "expected_format"),
    [
        ([], "plain"),
        (["--plain"], "plain"),
        (["--table"], "table"),
        (["--json"], "json"),
    ],
)
def test_combo_routes_discovered_modes_and_format(arguments, expected_format):
    from ghbot.combo import combo

    modes = (_mode("security"), _mode("issues"), _mode("drift"))
    report = MagicMock()
    report.render.return_value = "report\n"
    with (
        patch("ghbot.combo.combinable_modes", return_value=modes) as discover,
        patch("ghbot.combo.run_combo", new=AsyncMock(return_value=report)) as run_combo,
        patch("ghbot.combo.write_report") as write_report,
    ):
        result = CliRunner().invoke(combo, arguments, obj={"cfg": {}})

    assert result.exit_code == 0
    discover.assert_called_once_with()
    assert run_combo.await_args.args[:2] == ({}, modes)
    assert run_combo.await_args.args[2] == {
        "security": {"format": expected_format},
        "issues": {"format": expected_format, "labels": False},
        "drift": {"format": expected_format},
    }
    report.render.assert_called_once_with(expected_format)
    write_report.assert_called_once_with("report\n", None)


def test_combo_forwards_labels_only_to_issues_mode():
    from ghbot.combo import combo

    modes = (_mode("security"), _mode("issues"), _mode("drift"))
    report = MagicMock(render=MagicMock(return_value="report\n"))
    with (
        patch("ghbot.combo.combinable_modes", return_value=modes),
        patch("ghbot.combo.run_combo", new=AsyncMock(return_value=report)) as run_combo,
        patch("ghbot.combo.write_report"),
    ):
        result = CliRunner().invoke(combo, ["--labels"], obj={"cfg": {}})

    assert result.exit_code == 0
    assert run_combo.await_args.args[2]["issues"]["labels"] is True
    assert "labels" not in run_combo.await_args.args[2]["drift"]
    assert "labels" not in run_combo.await_args.args[2]["security"]


def test_combo_rejects_multiple_output_formats():
    from ghbot.combo import combo

    result = CliRunner().invoke(combo, ["--table", "--json"], obj={"cfg": {}})

    assert result.exit_code != 0
    assert "choose only one" in result.output


def test_combo_forwards_output_path(tmp_path):
    from ghbot.combo import combo

    destination = tmp_path / "combo.json"
    report = MagicMock(render=MagicMock(return_value="report\n"))
    with (
        patch("ghbot.combo.combinable_modes", return_value=()),
        patch("ghbot.combo.run_combo", new=AsyncMock(return_value=report)),
        patch("ghbot.combo.write_report") as write_report,
    ):
        result = CliRunner().invoke(
            combo, ["--output", str(destination)], obj={"cfg": {}}
        )

    assert result.exit_code == 0
    write_report.assert_called_once_with("report\n", destination)


def test_combo_exits_for_fatal_errors():
    from ghbot.combo import combo

    with (
        patch("ghbot.combo.combinable_modes", return_value=()),
        patch(
            "ghbot.combo.run_combo",
            new=AsyncMock(side_effect=AuthError("bad token")),
        ),
        patch("ghbot.combo.log.error") as log_error,
    ):
        result = CliRunner().invoke(combo, [], obj={"cfg": {}})

    assert result.exit_code == 1
    log_error.assert_called_once_with("bad token")
