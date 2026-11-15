"""Tests for the application shell and global Click configuration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from ghbot.processor import InfoRepoProcessor


def test_no_subcommand_exits_nonzero():
    from ghbot.__main__ import cli

    assert CliRunner().invoke(cli, []).exit_code != 0


def test_package_owned_commands_are_registered():
    from ghbot.__main__ import cli

    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    for command in ("security", "issues", "drift"):
        assert command in result.output


def test_info_subcommand_runs_the_info_processor():
    with (
        patch(
            "ghbot.__main__.run_processor", new=AsyncMock(return_value=[])
        ) as run_processor,
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["info"])

    assert result.exit_code == 0
    assert run_processor.call_args.args[1] is InfoRepoProcessor


def test_mode_specific_options_are_not_global():
    from ghbot.__main__ import cli

    result = CliRunner().invoke(cli, ["--json", "info"])

    assert result.exit_code != 0


def test_owner_global_option_applies_before_security_mode():
    with (
        patch("ghbot.modes.security.run_mode", new=AsyncMock()) as run_mode,
        patch("ghbot.modes.security.write_report"),
        patch("ghbot.__main__.configure"),
    ):
        run_mode.return_value = MagicMock(render=MagicMock(return_value="report\n"))
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["--owner", "acme", "security"])

    assert result.exit_code == 0
    assert run_mode.await_args.args[0]["owners"] == ["acme"]


def test_env_flag_applies_before_drift_mode():
    with (
        patch("ghbot.modes.drift.run_mode", new=AsyncMock()) as run_mode,
        patch("ghbot.modes.drift.write_report"),
        patch("ghbot.__main__.configure"),
    ):
        run_mode.return_value = MagicMock(render=MagicMock(return_value="report\n"))
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["--env", "drift"])

    assert result.exit_code == 0
    assert run_mode.await_args.args[0]["env"] is True


@pytest.mark.parametrize("command", ["security", "issues", "drift"])
def test_registered_modes_accept_global_quiet(command):
    with patch("ghbot.__main__.configure") as configure:
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["--quiet", command, "--help"])

    assert result.exit_code == 0
    assert configure.call_args.kwargs["console_level"] == "warn"


def test_config_file_owners_apply_to_info(tmp_path):
    config = tmp_path / "ghbot.toml"
    config.write_text('owners = "config-owner"\n')
    captured: dict = {}

    async def run_processor(cfg, processor_cls):
        captured.update(cfg)
        return []

    with (
        patch("ghbot.__main__.run_processor", side_effect=run_processor),
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["--config", str(config), "info"])

    assert result.exit_code == 0
    assert captured["owners"] == ["config-owner"]


def test_no_env_overrides_configured_environment_token(tmp_path):
    config = tmp_path / "ghbot.toml"
    config.write_text("env = true\n")
    captured: dict = {}

    async def run_processor(cfg, processor_cls):
        captured.update(cfg)
        return []

    with (
        patch("ghbot.__main__.run_processor", side_effect=run_processor),
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["--config", str(config), "--no-env", "info"])

    assert result.exit_code == 0
    assert captured["env"] is False
