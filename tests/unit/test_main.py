"""Tests for the application shell and global Click configuration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from ghbot.processor import InfoRepoProcessor


def _capture_info_config(args: list[str]) -> tuple[object, dict]:
    captured: dict = {}

    async def run_processor(cfg, processor_cls):
        captured.update(cfg)
        return []

    with (
        patch("ghbot.modes.info.run_processor", side_effect=run_processor),
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, [*args, "info"])

    return result, captured


def test_no_subcommand_exits_nonzero():
    from ghbot.__main__ import cli

    assert CliRunner().invoke(cli, []).exit_code != 0


def test_package_owned_commands_are_registered():
    from ghbot.__main__ import cli

    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    for command in ("combo", "info", "schema", "security", "issues", "drift"):
        assert command in result.output


def test_package_mode_imports_remain_modules():
    from ghbot.modes import drift, issues, security

    assert drift.MODE.name == "drift"
    assert issues.MODE.name == "issues"
    assert security.MODE.name == "security"


def test_info_subcommand_runs_the_info_processor():
    with (
        patch(
            "ghbot.modes.info.run_processor", new=AsyncMock(return_value=[])
        ) as run_processor,
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["info"])

    assert result.exit_code == 0
    assert run_processor.call_args.args[1] is InfoRepoProcessor


def test_mode_specific_options_are_not_global():
    with patch("ghbot.modes.info.run_processor", new=AsyncMock()) as run_processor:
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["--json", "info"])

    assert result.exit_code != 0
    assert "No such option" in result.output
    assert "--json" in result.output
    run_processor.assert_not_awaited()


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


def test_rate_limit_options_apply_before_info_mode():
    result, captured = _capture_info_config(
        ["--max-rate-wait", "45", "--max-rate-limit-hits", "2"]
    )

    assert result.exit_code == 0
    assert captured["max-rate-wait"] == 45
    assert captured["max-rate-limit-hits"] == 2


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
        patch("ghbot.modes.info.run_processor", side_effect=run_processor),
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
        patch("ghbot.modes.info.run_processor", side_effect=run_processor),
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["--config", str(config), "--no-env", "info"])

    assert result.exit_code == 0
    assert captured["env"] is False


def test_repo_options_expand_bare_entries_and_preserve_qualified_entries():
    result, captured = _capture_info_config(
        ["--owner", "alice,bob", "--repo", "widget,acme/tools", "--repo", "api"]
    )

    assert result.exit_code == 0
    assert captured["explicit_repositories"] == (
        ("alice", "widget"),
        ("bob", "widget"),
        ("acme", "tools"),
        ("alice", "api"),
        ("bob", "api"),
    )


def test_qualified_repo_option_needs_no_owner():
    result, captured = _capture_info_config(["--repo", "acme/widgets"])

    assert result.exit_code == 0
    assert captured["owners"] == []
    assert captured["explicit_repositories"] == (("acme", "widgets"),)


def test_repo_option_uses_owners_from_config_file(tmp_path):
    config = tmp_path / "ghbot.toml"
    config.write_text('owners = "alice,bob"\n')

    result, captured = _capture_info_config(
        ["--config", str(config), "--repo", "widgets"]
    )

    assert result.exit_code == 0
    assert captured["explicit_repositories"] == (
        ("alice", "widgets"),
        ("bob", "widgets"),
    )


def test_repo_option_strips_whitespace_from_cli_owners():
    result, captured = _capture_info_config(
        ["--owner", "alice, bob", "--repo", "widgets"]
    )

    assert result.exit_code == 0
    assert captured["explicit_repositories"] == (
        ("alice", "widgets"),
        ("bob", "widgets"),
    )


def test_repo_option_strips_whitespace_from_config_owners(tmp_path):
    config = tmp_path / "ghbot.toml"
    config.write_text('owners = "alice, bob"\n')

    result, captured = _capture_info_config(
        ["--config", str(config), "--repo", "widgets"]
    )

    assert result.exit_code == 0
    assert captured["explicit_repositories"] == (
        ("alice", "widgets"),
        ("bob", "widgets"),
    )


def test_duplicate_cli_owners_are_deduplicated_before_repository_expansion(caplog):
    with caplog.at_level("WARNING"):
        result, captured = _capture_info_config(
            ["--owner", "Alice,bob", "--owner", "alice,BOB", "--repo", "widgets"]
        )

    assert result.exit_code == 0
    assert captured["owners"] == ["Alice", "bob"]
    assert captured["explicit_repositories"] == (
        ("Alice", "widgets"),
        ("bob", "widgets"),
    )
    assert (
        sum("Duplicate owner skipped" in record.message for record in caplog.records)
        == 2
    )


def test_duplicate_config_owners_are_deduplicated_before_repository_expansion(
    tmp_path, caplog
):
    config = tmp_path / "ghbot.toml"
    config.write_text('owners = "Alice,bob,ALICE"\n')

    with caplog.at_level("WARNING"):
        result, captured = _capture_info_config(
            ["--config", str(config), "--repo", "widgets"]
        )

    assert result.exit_code == 0
    assert captured["owners"] == ["Alice", "bob"]
    assert captured["explicit_repositories"] == (
        ("Alice", "widgets"),
        ("bob", "widgets"),
    )
    assert any("Duplicate owner skipped" in record.message for record in caplog.records)


def test_bare_repo_option_without_owners_is_a_usage_error():
    result, _ = _capture_info_config(["--repo", "widgets"])

    assert result.exit_code != 0
    assert "owner" in result.output.lower()
    assert "widgets" in result.output


def test_repo_files_follow_inline_entries_and_parse_comments_and_commas(tmp_path):
    repositories = tmp_path / "repositories.txt"
    repositories.write_text("\n  # ignored\nfile-one, acme/file-two\nfile-three\n")

    result, captured = _capture_info_config(
        ["--owner", "owner", "--repo", "inline", "--repos", str(repositories)]
    )

    assert result.exit_code == 0
    assert captured["explicit_repositories"] == (
        ("owner", "inline"),
        ("owner", "file-one"),
        ("acme", "file-two"),
        ("owner", "file-three"),
    )


def test_comment_only_repo_file_enables_empty_explicit_selection(tmp_path):
    repositories = tmp_path / "repositories.txt"
    repositories.write_text("\n  # no repositories\n\n")

    result, captured = _capture_info_config(
        ["--owner", "owner", "--repos", str(repositories)]
    )

    assert result.exit_code == 0
    assert captured["explicit_repositories"] == ()


@pytest.mark.parametrize("entry", ["owner/", "/repository", "one/two/three"])
def test_malformed_repo_option_is_a_usage_error(entry):
    result, _ = _capture_info_config(["--repo", entry])

    assert result.exit_code != 0
    assert entry in result.output


def test_unreadable_repo_file_is_a_usage_error(tmp_path):
    missing = tmp_path / "missing-repositories.txt"

    result, _ = _capture_info_config(["--repos", str(missing)])

    assert result.exit_code != 0
    assert str(missing) in result.output


def test_invalid_utf8_repo_file_is_a_usage_error(tmp_path):
    repositories = tmp_path / "repositories.txt"
    repositories.write_bytes(b"\xff")

    result, _ = _capture_info_config(["--repos", str(repositories)])

    assert result.exit_code != 0
    assert str(repositories) in result.output


def test_repo_file_strips_utf8_bom_from_first_entry(tmp_path):
    repositories = tmp_path / "repositories.txt"
    repositories.write_bytes(b"\xef\xbb\xbfacme/widgets\n")

    result, captured = _capture_info_config(["--repos", str(repositories)])

    assert result.exit_code == 0
    assert captured["explicit_repositories"] == (("acme", "widgets"),)


def test_repos_option_is_single_use(tmp_path):
    first = tmp_path / "first.txt"
    first.write_text("acme/one\n")
    second = tmp_path / "second.txt"
    second.write_text("acme/two\n")

    result, _ = _capture_info_config(["--repos", str(first), "--repos", str(second)])

    assert result.exit_code != 0
    assert "multiple" in result.output.lower()


def test_repo_candidates_are_case_insensitively_deduplicated(caplog):
    with caplog.at_level("WARNING"):
        result, captured = _capture_info_config(
            ["--owner", "Acme", "--repo", "widgets,acme/WIDGETS"]
        )

    assert result.exit_code == 0
    assert captured["explicit_repositories"] == (("Acme", "widgets"),)
    assert any("duplicate" in record.message.lower() for record in caplog.records)
